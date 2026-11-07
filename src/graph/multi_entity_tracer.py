"""
Multi-Entity Graph Analytics and 5-Hop Syndicate Money Trail Engine.
Analyzes complex multi-layered mule networks, device fingerprint clusters,
income-to-flow discrepancy anomalies, and end-to-end money trails.
"""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from src.models.multi_entity import EntityKYC, TransactionEdge, MultiEntityNetworkSummary


class MultiEntityTracer:
    """
    Engine for tracing multi-entity money laundering syndicates
    from Victims through Gate Mules, Layering Hubs, Consolidation Nodes,
    and ultimate Cash-Out or Crypto Off-Ramp destinations.
    """

    def __init__(self):
        self.entities: Dict[str, EntityKYC] = {}
        self.edges: List[TransactionEdge] = []
        self.accounts_to_entity: Dict[str, str] = {}
        self.case_id: str = "CASE-MULTI-ENTITY-DEFAULT"

    def load_from_csv(
        self,
        nodes_csv_path: str | Path,
        edges_csv_path: str | Path,
    ) -> MultiEntityNetworkSummary:
        """
        Ingests Entity Master KYC and Transaction Edges CSV files.
        """
        p_nodes = Path(nodes_csv_path)
        p_edges = Path(edges_csv_path)

        if not p_nodes.exists():
            raise FileNotFoundError(f"Nodes file not found: {nodes_csv_path}")
        if not p_edges.exists():
            raise FileNotFoundError(f"Edges file not found: {edges_csv_path}")

        # 1. Load Entities
        self.entities.clear()
        with open(p_nodes, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row.get("entity_id", "").strip()
                if not eid:
                    continue
                name = row.get("entity_name", eid)
                role = row.get("role", "Unknown")
                risk = row.get("risk_category", "Medium")
                kyc = row.get("kyc_status", "Verified")
                try:
                    income = float(row.get("declared_income", 0))
                except ValueError:
                    income = 0.0
                flagged = row.get("flagged_aml", "0") in ("1", "true", "True")

                self.entities[eid] = EntityKYC(
                    entity_id=eid,
                    entity_name=name,
                    role=role,
                    risk_category=risk,
                    kyc_status=kyc,
                    declared_income=income,
                    flagged_aml=flagged,
                )

        # 2. Load Transaction Edges
        self.edges.clear()
        self.accounts_to_entity.clear()
        with open(p_edges, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get("trace_id", "")
                cid = row.get("case_id", "CASE-UNKNOWN")
                self.case_id = cid
                ts_str = row.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("/", "-"))
                except Exception:
                    ts = datetime.now()

                hop = row.get("hop_level", "Direct")
                src_acct = row.get("source_account", "N/A")
                src_ent = row.get("source_entity", "N/A")
                tgt_acct = row.get("target_account", "N/A")
                tgt_ent = row.get("target_entity", "N/A")
                amt = float(row.get("amount_thb", 0))
                channel = row.get("channel", "Mobile Banking")
                ip = row.get("ip_address")
                dev = row.get("device_fingerprint")
                geo = row.get("geolocation")
                rule = row.get("forensic_rule_triggered")
                try:
                    score = float(row.get("ai_anomaly_score", 0))
                except ValueError:
                    score = 0.0
                status = row.get("investigation_status", "Active")

                edge = TransactionEdge(
                    trace_id=tid,
                    case_id=cid,
                    timestamp=ts,
                    hop_level=hop,
                    source_account=src_acct,
                    source_entity=src_ent,
                    target_account=tgt_acct,
                    target_entity=tgt_ent,
                    amount_thb=amt,
                    channel=channel,
                    ip_address=ip,
                    device_fingerprint=dev,
                    geolocation=geo,
                    forensic_rule_triggered=rule,
                    ai_anomaly_score=score,
                    investigation_status=status,
                )
                self.edges.append(edge)

                if src_acct and src_ent:
                    self.accounts_to_entity[src_acct] = src_ent
                if tgt_acct and tgt_ent:
                    self.accounts_to_entity[tgt_acct] = tgt_ent

                # Aggregate volumes on entities
                if src_ent in self.entities:
                    self.entities[src_ent].actual_outflow_volume += amt
                if tgt_ent in self.entities:
                    self.entities[tgt_ent].actual_inflow_volume += amt

        return self.get_summary()

    def get_summary(self) -> MultiEntityNetworkSummary:
        """Computes statistical summary of the multi-entity money trail."""
        total_vol = sum(e.amount_thb for e in self.edges)
        hop_vols: Dict[str, float] = defaultdict(float)
        for e in self.edges:
            hop_vols[e.hop_level] += e.amount_thb

        # Device clusters: devices associated with multiple entities
        dev_map: Dict[str, Set[str]] = defaultdict(set)
        for e in self.edges:
            if e.device_fingerprint and e.device_fingerprint not in ("User_Personal_Device", "N/A"):
                if e.source_entity:
                    dev_map[e.device_fingerprint].add(e.source_entity)
                if e.target_entity:
                    dev_map[e.device_fingerprint].add(e.target_entity)

        shared_devices = {dev: sorted(list(ents)) for dev, ents in dev_map.items() if len(ents) >= 2}

        # Gateways: Top recipient accounts in Hop 1 and Hop 2
        gw_map: Dict[str, float] = defaultdict(float)
        for e in self.edges:
            if "Hop-1" in e.hop_level or "Hop-2" in e.hop_level:
                gw_map[e.target_entity] += e.amount_thb

        top_gateways = [
            {"entity_id": eid, "name": self.entities[eid].entity_name if eid in self.entities else eid, "volume_thb": vol}
            for eid, vol in sorted(gw_map.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Kingpin entities (Entities in Hop-5 or Treasury role)
        kingpins = [eid for eid, ent in self.entities.items() if "Treasury" in ent.role or "Kingpin" in ent.role or "Offshore" in ent.role]

        return MultiEntityNetworkSummary(
            case_id=self.case_id,
            total_entities=len(self.entities),
            total_transactions=len(self.edges),
            total_flow_volume_thb=total_vol,
            hop_volumes=dict(hop_vols),
            top_gateways=top_gateways,
            device_clusters=shared_devices,
            geolocation_anomalies=[],
            kingpin_entities=kingpins,
        )

    def find_5hop_paths(self, max_paths: int = 10) -> List[List[Dict[str, Any]]]:
        """
        Traces complete end-to-end paths from Victims to Cash Runners / Crypto Vaults.
        """
        # Build adjacency by hop level
        adj: Dict[str, List[TransactionEdge]] = defaultdict(list)
        for e in self.edges:
            adj[e.source_entity].append(e)

        victim_ids = [eid for eid, ent in self.entities.items() if "Victim" in ent.role]
        all_paths: List[List[Dict[str, Any]]] = []

        def dfs(current_eid: str, current_path: List[Dict[str, Any]], visited: Set[str]):
            if len(all_paths) >= max_paths:
                return
            curr_ent = self.entities.get(current_eid)
            curr_role = curr_ent.role if curr_ent else ""
            curr_name = curr_ent.entity_name if curr_ent else current_eid

            if len(current_path) >= 4 or "Kingpin" in curr_role or "Treasury" in curr_role:
                all_paths.append(list(current_path))
                return

            for edge in adj.get(current_eid, []):
                tgt = edge.target_entity
                if tgt not in visited:
                    visited.add(tgt)
                    tgt_ent = self.entities.get(tgt)
                    tgt_name = tgt_ent.entity_name if tgt_ent else tgt

                    current_path.append({
                        "from_entity": current_eid,
                        "from_name": curr_name,
                        "to_entity": tgt,
                        "to_name": tgt_name,
                        "hop": edge.hop_level,
                        "amount": edge.amount_thb,
                        "channel": edge.channel,
                        "timestamp": edge.timestamp.isoformat(),
                    })
                    dfs(tgt, current_path, visited)
                    current_path.pop()
                    visited.remove(tgt)

        for vic in victim_ids[:3]:
            dfs(vic, [], {vic})

        return all_paths

    def export_mermaid(self) -> str:
        """Generates visual Mermaid flowchart of the 5-Hop Syndicate Network."""
        lines = ["flowchart LR"]
        lines.append("    subgraph H1 [Hop 1: เหยื่อหลายราย]")
        for eid, ent in self.entities.items():
            if "Victim" in ent.role:
                lines.append(f'        {eid}["{ent.entity_name}<br/>({ent.role})"]')
        lines.append("    end")

        lines.append("    subgraph H2 [Hop 2: บัญชีม้าแถว 1 (Gate Mules)]")
        for eid, ent in self.entities.items():
            if "Mule Tier-1" in ent.role:
                lines.append(f'        {eid}["{ent.entity_name}<br/>(In: ฿{ent.actual_inflow_volume/1e6:.1f}M)"]:::mule1')
        lines.append("    end")

        lines.append("    subgraph H3 [Hop 3: บัญชีม้าแถว 2 (Layering Hubs)]")
        for eid, ent in self.entities.items():
            if "Mule Tier-2" in ent.role:
                lines.append(f'        {eid}["{ent.entity_name}<br/>(In: ฿{ent.actual_inflow_volume/1e6:.1f}M)"]:::mule2')
        lines.append("    end")

        lines.append("    subgraph H4 [Hop 4: ศูนย์รวบรวม (Consolidation)]")
        for eid, ent in self.entities.items():
            if "Mule Tier-3" in ent.role:
                lines.append(f'        {eid}["{ent.entity_name}<br/>(In: ฿{ent.actual_inflow_volume/1e6:.1f}M)"]:::mule3')
        lines.append("    end")

        lines.append("    subgraph H5 [Hop 5: ฟอกเงินออก (Cash-Out & Crypto)]")
        for eid, ent in self.entities.items():
            if "Runner" in ent.role or "Crypto" in ent.role or "Treasury" in ent.role:
                lines.append(f'        {eid}["{ent.entity_name}<br/>({ent.role})"]:::dest')
        lines.append("    end")

        # Aggregate flow edges between entities
        flow_pairs: Dict[Tuple[str, str], float] = defaultdict(float)
        for e in self.edges:
            flow_pairs[(e.source_entity, e.target_entity)] += e.amount_thb

        for (src, tgt), vol in sorted(flow_pairs.items(), key=lambda x: x[1], reverse=True)[:25]:
            lines.append(f'    {src} -->|฿{vol/1e6:.1f}M| {tgt}')

        lines.append("    classDef mule1 fill:#fed7aa,stroke:#ea580c,stroke-width:2px;")
        lines.append("    classDef mule2 fill:#fecdd3,stroke:#e11d48,stroke-width:2px;")
        lines.append("    classDef mule3 fill:#fbcfe8,stroke:#db2777,stroke-width:2px;")
        lines.append("    classDef dest fill:#cbd5e1,stroke:#475569,stroke-width:2px;")
        return "\n".join(lines)
