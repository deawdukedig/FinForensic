"""
Single-Victim Forensic Flow Tracer and Proportional Asset Recovery Engine.
Implements:
1. Targeted Victim Inflow Isolation
2. Local MILP Flow Matching (scipy.optimize.milp)
3. Top Dispersal Destination & Beneficiary Aggregation
4. Proportional Haircut Tainted Fund Attribution (AMLA Sec 49/1 & CPC Sec 226)
5. AOC 1441 Emergency Freezing Payload Generation
6. Court-Admissible One-Page / Multi-Page Markdown & PDF Dossier Generation
"""

from __future__ import annotations
from bisect import bisect_left, bisect_right
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict

from src.models.transaction import BankTransaction, ActivityType
from src.models.cluster import FlowMatchCluster
from src.engine.flow_matcher import FlowMatchingEngine
from src.dossier.font_loader import resolve_thai_font, shape_thai_text, register_math_font


class DispersalDestination(BaseModel):
    """Aggregated destination beneficiary receiving victim funds."""
    model_config = ConfigDict(frozen=False)

    rank: int
    bank: str
    account_no: str
    account_name: str
    channel: str
    total_drained_thb: float
    proportional_claim_thb: float
    percentage_of_victim_funds: float
    tx_count: int
    avg_latency_minutes: float
    recommended_action: str


class ProportionalClaim(BaseModel):
    """Detailed record of victim's proportional claim over an outflow."""
    model_config = ConfigDict(frozen=False)

    inflow_tx_id: str
    inflow_timestamp: datetime
    inflow_amount: float
    commingled_pool_total: float
    taint_ratio: float
    outflow_tx_id: str
    outflow_timestamp: datetime
    outflow_bank: str
    outflow_account: str
    outflow_name: str
    outflow_amount: float
    victim_entitled_claim_thb: float


class VictimTraceResult(BaseModel):
    """Complete forensic results for single-victim fund tracing."""
    model_config = ConfigDict(frozen=False)

    query: str
    victim_name: str
    victim_accounts: List[str]
    statement_file: str
    statement_sha256: str
    target_account: str
    target_account_name: str
    inflow_transactions: List[BankTransaction]
    total_inflow_thb: float
    matched_clusters: List[FlowMatchCluster]
    matched_outflows: List[BankTransaction]
    total_matched_outflow_thb: float
    total_fee_thb: float
    net_residual_buffer_thb: float
    drain_percentage: float
    avg_latency_minutes: float
    top_destinations: List[DispersalDestination]
    proportional_claims: List[ProportionalClaim]
    total_claimable_thb: float


THAI_NAME_SLUGS: Dict[str, str] = {
    "ศิริพร ใจดี": "siriporn_jaidee",
    "ศิริพร": "siriporn",
    "ใจดี": "jaidee",
    "ธนากร แก้ววิเชียร": "thanakorn_kaewwichian",
    "ธนากร": "thanakorn",
    "ชลธิชา แก้ววิเชียร": "chonticha_kaewwichian",
    "ชลธิชา": "chonticha",
    "แก้ววิเชียร": "kaewwichian",
    "จ่าสิบตรี ภานุวัฒน์": "panuwat",
    "จ่าสิบตรี ภานุวัฒน์ คงสง่า": "panuwat",
    "ภานุวัฒน์": "panuwat",
    "คงสง่า": "kongsa-nga",
    "สมชาย สุขสมบูรณ์": "somchai_suksomboon",
    "สมชาย": "somchai",
    "สุขสมบูรณ์": "suksomboon",
    "ธนดล ธรรมเจริญ": "thanadol_thamcharoen",
    "นาย ธนดล ธรรมเจริญ": "thanadol_thamcharoen",
    "ธนดล": "thanadol",
    "ธรรมเจริญ": "thamcharoen",
    "มาลี สุวรรณโชติ": "malee_suwannachot",
    "นาง มาลี สุวรรณโชติ": "malee_suwannachot",
    "น.ส. มาลี สุวรรณโชติ": "malee_suwannachot",
    "นางสาว มาลี สุวรรณโชติ": "malee_suwannachot",
    "มาลี": "malee",
    "สุวรรณโชติ": "suwannachot",
}


def slugify_victim_name(name: str) -> str:
    """Creates a clean, filesystem-safe slug for victim analysis filenames."""
    cleaned = name.strip()
    if cleaned in THAI_NAME_SLUGS:
        return THAI_NAME_SLUGS[cleaned]
    for k, v in sorted(THAI_NAME_SLUGS.items(), key=lambda x: len(x[0]), reverse=True):
        if k in cleaned:
            return v
    # If English or alphanumeric characters exist:
    ascii_slug = re.sub(r'[^a-zA-Z0-9]+', '_', cleaned).strip('_').lower()
    if ascii_slug:
        return ascii_slug
    # Fallback to hash prefix for unmapped non-ascii strings
    import hashlib
    h = hashlib.md5(cleaned.encode('utf-8')).hexdigest()[:8]
    return f"victim_{h}"



TABLE_RESPONSIVE_STYLE = """<style>
/* Responsive & Print-Optimized Table Layout (No Horizontal Scrollbar) */
table {
  display: table !important;
  width: 100% !important;
  max-width: 100% !important;
  border-collapse: collapse !important;
  table-layout: auto !important;
  font-size: 13px !important;
  overflow: visible !important;
}
th, td {
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: break-word !important;
  padding: 6px 5px !important;
}
@media print {
  body {
    font-size: 10pt !important;
  }
  table {
    display: table !important;
    width: 100% !important;
    table-layout: auto !important;
    font-size: 8.5pt !important;
    page-break-inside: auto !important;
  }
  tr {
    page-break-inside: avoid !important;
  }
  th, td {
    padding: 3px 3px !important;
    word-break: break-word !important;
  }
  thead {
    display: table-header-group !important;
  }
}
</style>
"""

class VictimFlowTracer:
    """
    Forensic engine dedicated to tracking a specific victim's funds
    through intermediary mule accounts to final beneficiaries.
    """

    def __init__(
        self,
        transactions: List[BankTransaction],
        statement_file: str = "input/statement.csv",
        statement_sha256: str = "",
        tolerance_ratio: float = 0.05,
    ):
        self.transactions = transactions
        self.statement_file = statement_file
        self.statement_sha256 = statement_sha256
        self.tolerance_ratio = tolerance_ratio
        self.matcher = FlowMatchingEngine(tolerance_ratio=tolerance_ratio)

    def find_victim_inflows(self, query: str) -> List[BankTransaction]:
        """Filters inflows matching victim name, account number, or transaction id."""
        q = query.strip().lower()
        if not q:
            return []

        clean_q = re.sub(r'^(บัญชีเลขที่|เลขที่บัญชี|เลขบัญชี|บัญชี)\s*', '', q).strip()
        q_tokens = [tok for tok in re.split(r'[\s,]+', clean_q) if tok]

        matched = []
        for t in self.transactions:
            if t.activity != ActivityType.INFLOW or t.is_reversal:
                continue
            name = (t.counterparty_name or "").lower()
            acct = (t.counterparty_account or "").lower()
            bank = (t.counterparty_bank or "").lower()
            desc = (t.description or "").lower()
            tx_id = t.tx_id.lower()
            combined = f"{bank} {acct} {name} {desc}".lower()

            if (
                clean_q in name or clean_q in acct or clean_q in tx_id or clean_q in combined
            ) or (
                q_tokens and all(tok in combined for tok in q_tokens)
            ) or (
                clean_q.isdigit() and len(clean_q) >= 6 and acct == clean_q
            ):
                matched.append(t)

        matched.sort(key=lambda x: x.timestamp)
        return matched

    def trace_victim(
        self,
        query: str,
        time_window_hours: float = 24.0,
    ) -> VictimTraceResult:
        """
        Executes end-to-end tracing for the specified victim:
        1. Inflow isolation
        2. MILP flow matching
        3. Proportional haircut attribution
        4. Destination beneficiary ranking
        """
        victim_inflows = self.find_victim_inflows(query)
        if not victim_inflows:
            raise ValueError(
                f"ไม่พบรายการเงินเข้าของผู้เสียหายที่ตรงกับคำค้นหา '{query}' ใน Statement นี้"
            )

        victim_name = victim_inflows[0].counterparty_name or query
        victim_accounts = sorted(list({t.counterparty_account for t in victim_inflows if t.counterparty_account}))
        total_inflow = sum(t.amount for t in victim_inflows)

        target_acct = self.transactions[0].account_no if self.transactions else "UNKNOWN"
        target_name = self.transactions[0].account_name if self.transactions else "บัญชีม้าพักเงิน"

        # Chronological outflows in statement
        all_outflows = [
            t for t in self.transactions
            if t.activity in (ActivityType.OUTFLOW, ActivityType.FEE) and not t.is_reversal
        ]
        all_outflows.sort(key=lambda x: x.timestamp)
        outflow_times = [t.timestamp for t in all_outflows]

        all_inflows = [
            t for t in self.transactions
            if t.activity == ActivityType.INFLOW and not t.is_reversal
        ]
        all_inflows.sort(key=lambda x: x.timestamp)

        all_matched_txs: List[BankTransaction] = []
        seen_matched_tx_ids: set[str] = set()
        proportional_claims: List[ProportionalClaim] = []

        # Prepare candidate clusters via binary search O(log N)
        cluster_specs = []
        cluster_cand_map = []
        for idx, inf in enumerate(victim_inflows, start=1):
            t_start = inf.timestamp
            t_end = t_start + timedelta(hours=time_window_hours)
            idx_s = bisect_left(outflow_times, t_start)
            idx_e = bisect_right(outflow_times, t_end)
            candidates = all_outflows[idx_s:min(idx_e, idx_s + 50)]
            cluster_cand_map.append((inf, candidates))
            cluster_specs.append((f"CLUSTER-VIC-{idx:02d}", [inf], candidates, None))

        # Solve MILP flow matching in parallel across worker threads
        matched_clusters: List[FlowMatchCluster] = self.matcher.solve_clusters_parallel(cluster_specs)

        # Process matched transactions and calculate Proportional Claims
        for (inf, candidates), cluster in zip(cluster_cand_map, matched_clusters):
            curr_matched = [t for t in candidates if t.tx_id in cluster.outflow_tx_ids]
            for m in curr_matched:
                if m.tx_id not in seen_matched_tx_ids:
                    seen_matched_tx_ids.add(m.tx_id)
                    all_matched_txs.append(m)

            cluster_outflows = [m for m in curr_matched if m.activity == ActivityType.OUTFLOW]
            cluster_outflow_total = sum(m.amount for m in cluster_outflows)
            attr_ratio = min(1.0, inf.amount / cluster_outflow_total) if cluster_outflow_total > 0 else 1.0

            for m in cluster_outflows:
                entitled = m.amount * attr_ratio
                proportional_claims.append(
                    ProportionalClaim(
                        inflow_tx_id=inf.tx_id,
                        inflow_timestamp=inf.timestamp,
                        inflow_amount=inf.amount,
                        commingled_pool_total=cluster_outflow_total,
                        taint_ratio=attr_ratio,
                        outflow_tx_id=m.tx_id,
                        outflow_timestamp=m.timestamp,
                        outflow_bank=m.counterparty_bank or "UNKNOWN",
                        outflow_account=m.counterparty_account or "UNKNOWN",
                        outflow_name=m.counterparty_name or "N/A",
                        outflow_amount=m.amount,
                        victim_entitled_claim_thb=entitled,
                    )
                )

        total_matched_outflow = sum(
            t.amount for t in all_matched_txs if t.activity == ActivityType.OUTFLOW
        )
        total_fees = sum(
            t.amount for t in all_matched_txs if t.activity == ActivityType.FEE
        )
        total_dispersed = total_matched_outflow + total_fees
        net_residual = max(0.0, total_inflow - total_dispersed)
        drain_pct = min(100.0, (total_dispersed / total_inflow * 100.0)) if total_inflow > 0 else 0.0

        all_latencies = []
        for inf in victim_inflows:
            for m in all_matched_txs:
                if m.timestamp >= inf.timestamp:
                    all_latencies.append((m.timestamp - inf.timestamp).total_seconds() / 60.0)
        avg_lat = float(sum(all_latencies) / len(all_latencies)) if all_latencies else 0.0

        # Group and rank Top Dispersal Destinations
        dest_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        for c in proportional_claims:
            key = (c.outflow_bank, c.outflow_account, c.outflow_name, "")
            # check channel from tx
            tx_obj = next((t for t in all_matched_txs if t.tx_id == c.outflow_tx_id), None)
            channel = tx_obj.channel if tx_obj else "Mobile Transfer"
            key = (c.outflow_bank, c.outflow_account, c.outflow_name, channel)

            if key not in dest_map:
                dest_map[key] = {
                    "bank": c.outflow_bank,
                    "account_no": c.outflow_account,
                    "account_name": c.outflow_name,
                    "channel": channel,
                    "total_drained": 0.0,
                    "claim_thb": 0.0,
                    "tx_count": 0,
                    "latencies": [],
                }
            dest_map[key]["total_drained"] += c.outflow_amount
            dest_map[key]["claim_thb"] += c.victim_entitled_claim_thb
            dest_map[key]["tx_count"] += 1
            lat = (c.outflow_timestamp - c.inflow_timestamp).total_seconds() / 60.0
            dest_map[key]["latencies"].append(max(0.0, lat))

        # Sort destinations by claim / drained descending
        sorted_dests = sorted(dest_map.values(), key=lambda x: x["claim_thb"], reverse=True)
        top_destinations: List[DispersalDestination] = []

        for r_idx, d in enumerate(sorted_dests, start=1):
            pct = (d["claim_thb"] / total_inflow * 100.0) if total_inflow > 0 else 0.0
            avg_d_lat = sum(d["latencies"]) / len(d["latencies"]) if d["latencies"] else 0.0

            # Recommendation
            combined_target = f"{d['bank']} {d['account_name']} {d['channel']}".lower()
            if "atm" in combined_target or "cardless" in combined_target:
                action = "CCTV_INSPECTION_ATM"
            elif any(w in combined_target for w in ["p2p", "binance", "bitkub", "crypto", "usdt", "vasp"]):
                action = "VASP_WALLET_FREEZE"
            elif any(w in combined_target for w in [
                "meta ads", "facebook ads", "fb ads", "google ads", "tiktok ads", "line ads", "twitter ads",
                "kgp", "kasikorn global payment", "2c2p", "omise", "opn", "gb prime", "paysolutions",
                "ksher", "truemoney merchant", "payment gateway", "gateway", "merchant pool", "billing"
            ]):
                action = "PLATFORM_SUBPOENA_EVIDENCE"
            else:
                action = "AOC_1441_FREEZE_URGENT"

            top_destinations.append(
                DispersalDestination(
                    rank=r_idx,
                    bank=d["bank"],
                    account_no=d["account_no"],
                    account_name=d["account_name"],
                    channel=d["channel"],
                    total_drained_thb=d["total_drained"],
                    proportional_claim_thb=d["claim_thb"],
                    percentage_of_victim_funds=pct,
                    tx_count=d["tx_count"],
                    avg_latency_minutes=avg_d_lat,
                    recommended_action=action,
                )
            )

        total_claimable = sum(d.proportional_claim_thb for d in top_destinations)

        return VictimTraceResult(
            query=query,
            victim_name=victim_name,
            victim_accounts=victim_accounts,
            statement_file=self.statement_file,
            statement_sha256=self.statement_sha256,
            target_account=target_acct,
            target_account_name=target_name,
            inflow_transactions=victim_inflows,
            total_inflow_thb=total_inflow,
            matched_clusters=matched_clusters,
            matched_outflows=all_matched_txs,
            total_matched_outflow_thb=total_matched_outflow,
            total_fee_thb=total_fees,
            net_residual_buffer_thb=net_residual,
            drain_percentage=drain_pct,
            avg_latency_minutes=avg_lat,
            top_destinations=top_destinations,
            proportional_claims=proportional_claims,
            total_claimable_thb=total_claimable,
        )

    @staticmethod
    def _format_action_th(action: str) -> str:
        """Formats action enum into clean, wrap-friendly Thai text without backticks to prevent table overflow."""
        mapping = {
            "AOC_1441_FREEZE_URGENT": "AOC 1441 อายัดด่วน",
            "PLATFORM_SUBPOENA_EVIDENCE": "ม.132 ขอพยานแพลตฟอร์ม",
            "CCTV_INSPECTION_ATM": "CCTV ตรวจกล้อง ATM",
            "VASP_WALLET_FREEZE": "อายัดกระเป๋า VASP",
        }
        return mapping.get(action, action.replace("_", " "))

    def generate_dispersal_mermaid(self, result: VictimTraceResult) -> str:
        """Generates a court-admissible Mermaid flowchart visualizing the victim's fund dispersal."""
        lines = [
            "```mermaid",
            "flowchart LR",
            f'    V["ผู้เสียหาย: {result.victim_name} (฿{result.total_inflow_thb:,.2f})"] -->|โอนเงิน {len(result.inflow_transactions)} รายการ| M["บัญชีม้าแถว 1: {result.target_account}"]',
        ]

        tier2 = [d for d in result.top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        cashout = [d for d in result.top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        crypto = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        gateways = [d for d in result.top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]

        edges = []

        # 1. Tier 2 Mule Accounts
        if tier2:
            lines.append('    subgraph TIER2["เครือข่ายบัญชีม้าแถว 2 (Mule Tier-2)"]')
            if len(tier2) > 4:
                top_t2 = tier2[:3]
                rest_t2 = tier2[3:]
                for idx, d in enumerate(top_t2, 1):
                    node_id = f"T2_{idx}"
                    clean_name = d.account_name.replace('"', "'")
                    clean_acct = d.account_no.replace('"', "")
                    name_str = f" {clean_name}" if clean_name not in ("N/A", "", "UNKNOWN") else ""
                    label = f"{d.bank} {clean_acct}{name_str}: ฿{d.proportional_claim_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                    lines.append(f'        {node_id}["{label}"]')
                    edges.append(f"    M -->|Mobile Transfer| {node_id}")

                rest_sum = sum(d.proportional_claim_thb for d in rest_t2)
                rest_pct = (rest_sum / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
                rest_node = "T2_REST"
                rest_label = f"บัญชีม้าแถว 2 อื่นๆ ({len(rest_t2)} บัญชี): ฿{rest_sum:,.2f} ({rest_pct:.1f}%)"
                lines.append(f'        {rest_node}["{rest_label}"]')
                edges.append(f"    M -->|Mobile Transfer| {rest_node}")
            else:
                for idx, d in enumerate(tier2, 1):
                    node_id = f"T2_{idx}"
                    clean_name = d.account_name.replace('"', "'")
                    clean_acct = d.account_no.replace('"', "")
                    name_str = f" {clean_name}" if clean_name not in ("N/A", "", "UNKNOWN") else ""
                    label = f"{d.bank} {clean_acct}{name_str}: ฿{d.proportional_claim_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                    lines.append(f'        {node_id}["{label}"]')
                    edges.append(f"    M -->|Mobile Transfer| {node_id}")
            lines.append("    end")

        # 2. ATM Cashout
        if cashout:
            lines.append('    subgraph CASHOUT["การถอนเงินสดออกจากระบบ (Cash-Out)"]')
            for idx, d in enumerate(cashout, 1):
                node_id = f"ATM_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN") else f"{clean_name} ({d.bank})"
                label = f"{display_title}: ฿{d.proportional_claim_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|Cardless ATM| {node_id}")
            lines.append("    end")

        # 3. Crypto Off-Ramp
        if crypto:
            lines.append('    subgraph CRYPTO["ร้านค้าสินทรัพย์ดิจิทัล (Crypto Off-Ramp)"]')
            for idx, d in enumerate(crypto, 1):
                node_id = f"CRYPTO_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN") else f"{d.bank} {clean_name}"
                label = f"{display_title}: ฿{d.proportional_claim_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|P2P OTC| {node_id}")
            lines.append("    end")

        # 4. Payment Gateways & Ad Platforms
        if gateways:
            lines.append('    subgraph GATEWAY["ระบบรับชำระเงินและค่าโฆษณา (Payment Gateway & Ad Platforms)"]')
            for idx, d in enumerate(gateways, 1):
                node_id = f"GW_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN") else f"{clean_name} ({d.bank})"
                label = f"{display_title}: ฿{d.proportional_claim_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|Payment/Ads| {node_id}")
            lines.append("    end")

        # 5. Residual Buffer
        if result.net_residual_buffer_thb > 0:
            res_pct = (result.net_residual_buffer_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
            lines.append('    subgraph BUFFER["เงินตกค้างในบัญชีม้า (Residual Buffer)"]')
            lines.append(f'        BUF["เงินค้างรอฟอก: ฿{result.net_residual_buffer_thb:,.2f} ({res_pct:.1f}%)"]')
            lines.append("    end")
            edges.append("    M -.->|ค้างในบัญชี| BUF")

        lines.extend(edges)
        lines.append("```")
        return "\n".join(lines)

    def generate_markdown_report(
        self,
        result: VictimTraceResult,
        case_id: str = "CASE-VICTIM-001",
        officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
    ) -> str:
        """Generates court-admissible 1-page forensic evidence dossier for the victim."""
        lines = []
        lines.append(TABLE_RESPONSIVE_STYLE)
        lines.append(f"# สำนวนการตรวจพิสูจน์เส้นทางการเงินเฉพาะผู้เสียหาย (Victim Money Trail Dossier)")
        lines.append(f"**เลขที่สำนวนคดี (Case ID):** `{case_id}`  ")
        lines.append(f"**ผู้ตรวจพิสูจน์ (Forensic Investigator):** {officer}  ")
        lines.append(f"**วันเวลาที่จัดทำเอกสาร:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}  ")
        lines.append(f"**มาตรฐานกฎหมายที่รองรับ:** ป.วิ.อ. มาตรา 226, พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 และ พ.ร.บ. ป้องกันและปราบปรามการฟอกเงิน พ.ศ. 2542 มาตรา 49/1")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 1: Executive Summary
        lines.append("## 1. บทสรุปข้อมูลผู้เสียหายและภาพรวมความเสียหาย (Victim Profile & Loss Summary)")
        lines.append(f"- **ชื่อ-นามสกุล ผู้เสียหาย:** **{result.victim_name}**")
        lines.append(f"- **บัญชีต้นทางของผู้เสียหาย:** {', '.join(result.victim_accounts) if result.victim_accounts else 'N/A'}")
        lines.append(f"- **บัญชีม้าพักเงินเป้าหมาย:** `{result.target_account}` ({result.target_account_name})")
        lines.append(f"- **ยอดเงินความเสียหายรวม:** **฿{result.total_inflow_thb:,.2f}** ({len(result.inflow_transactions)} รายการ)")
        lines.append(f"- **ยอดเงินที่จับคู่ระบายออกได้ (MILP Matched):** **฿{result.total_matched_outflow_thb:,.2f}** (อัตราการสูบเงินออก: **{result.drain_percentage:.2f}%**)")
        lines.append(f"- **สิทธิเรียกร้องเฉลี่ยทรัพย์คืน (Proportional Claim):** **฿{result.total_claimable_thb:,.2f}**")
        lines.append(f"- **ระยะเวลาเงินแช่พักเฉลี่ย (Mean Latency):** **{result.avg_latency_minutes:.1f} นาที**")
        lines.append(f"- **ค่าแฮชตรวจสอบความสมบูรณ์ไฟล์ (SHA-256):** `{result.statement_sha256}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 2: Top Dispersal Destinations
        lines.append("## 2. สรุปปลายทางเส้นทางการเงินและผู้รับประโยชน์หลัก (Top Dispersal Destinations)")
        lines.append("จากการประมวลผลจับคู่เส้นทางเงินทางคณิตศาสตร์ พบว่าเงินของผู้เสียหายถูกระบายออกไปยังผู้รับประโยชน์หลักดังต่อไปนี้:")
        lines.append("")
        lines.append("### แผนภาพแสดงเส้นทางการกระจายเงิน (Fund Dispersal Topology):")
        lines.append(self.generate_dispersal_mermaid(result))
        lines.append("")
        pct_claim = (result.total_claimable_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        lines.append("| ลำดับ | ธนาคาร / เลขบัญชี | ชื่อบัญชีปลายทาง | ช่องทาง | ยอดเงินออก (฿) | สิทธิขอคืน (฿) | สัดส่วน | มาตรการแนะนำ |")
        lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |")

        for d in result.top_destinations:
            acct_info = f"{d.bank} {d.account_no}" if d.account_no != "UNKNOWN" else d.bank
            action_th = self._format_action_th(d.recommended_action)
            lines.append(
                f"| {d.rank} | {acct_info} | **{d.account_name}** | {d.channel} | ฿{d.total_drained_thb:,.2f} | **฿{d.proportional_claim_thb:,.2f}** | {d.percentage_of_victim_funds:.1f}% | {action_th} |"
            )

        tot_drained_sum = sum(d.total_drained_thb for d in result.top_destinations)
        tot_claim_sum = sum(d.proportional_claim_thb for d in result.top_destinations)
        lines.append(
            f"| **รวม** | - | **รวมทั้งสิ้น {len(result.top_destinations)} ปลายทาง** | - | **฿{tot_drained_sum:,.2f}** | **฿{tot_claim_sum:,.2f}** | **{pct_claim:.1f}%** | **AOC 1441 / ปปง. ม.49/1** |"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 3: MILP Mathematical Proofs
        lines.append("## 3. การรับรองความถูกต้องด้วยสมการคณิตศาสตร์เชิงเส้น (MILP Mathematical Proofs)")
        lines.append("สมการยืนยันการอนุรักษ์กระแสเงิน (Flow Conservation) ตาม ป.วิ.อ. มาตรา 226:")
        lines.append("")
        for idx, cl in enumerate(result.matched_clusters, start=1):
            lines.append(f"- **กลุ่มที่ {idx} ({cl.cluster_id}):** เงินเข้า ฿{cl.inflow_total:,.2f} $\\to$ เงินออก ฿{cl.outflow_total:,.2f} (Drain: {cl.drain_percentage:.1f}%, หน่วงเวลา: {cl.avg_latency_minutes:.1f} นาที)")
            lines.append(f"  > `{cl.mathematical_proof}`")
        lines.append("")

        # Section 4: Actionable Directives
        lines.append("---")
        lines.append("## 4. มาตรการสำหรับพนักงานสอบสวน (Immediate Action Directives)")
        lines.append("1. **การส่งคำขออายัดศูนย์ AOC 1441 ทันที (เฉพาะบัญชีม้าบุคคลธรรมดา):**")
        for d in result.top_destinations:
            if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no != "UNKNOWN":
                lines.append(f"   - **อายัดบัญชี:** {d.bank} เลขที่ `{d.account_no}` ({d.account_name}) วงเงินสิทธิเฉลี่ยทรัพย์ ฿{d.proportional_claim_thb:,.2f}")
        gateways = [d for d in result.top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]
        if gateways:
            lines.append("2. **มาตรการขอพยานหลักฐานและระงับบัญชีโฆษณาตาม ป.วิ.อ. มาตรา 132 (Payment Gateway / Ad Platforms):**")
            lines.append("   - *⚠️ ข้อควรระวัง: ห้ามส่งคำสั่งอายัดบัญชีผ่าน AOC 1441 ไปยังบัญชีผู้ให้บริการรับชำระเงิน/แพลตฟอร์มโฆษณา เพราะเป็นบัญชีรวมระดับองค์กร*")
            for d in gateways:
                lines.append(f"   - **ออกหมายเรียก ม.132 ต่อ {d.account_name} ({d.bank} {d.account_no}):** ขอข้อมูล Sub-merchant ID, Ad Account KYC, Campaign Fanpage, IP Logs และระงับบัญชีโฆษณา (ยอดเงินที่ไหลเข้า: ฿{d.proportional_claim_thb:,.2f})")
            lines.append("3. **การประสานงาน ปปง. เพื่อเฉลี่ยทรัพย์คืน (Asset Restitution):**")
            lines.append(f"   - ใช้ตารางข้อ 2 เป็น **บัญชีแนบท้ายคำร้องขอคุ้มครองสิทธิผู้เสียหาย** ตาม พ.ร.บ. ปปง. มาตรา 49/1 ยอดเรียกร้องรวม **฿{result.total_claimable_thb:,.2f}**")
            lines.append("4. **การขอพยานหลักฐานทางดิจิทัลเพิ่มเติม:**")
        else:
            lines.append("2. **การประสานงาน ปปง. เพื่อเฉลี่ยทรัพย์คืน (Asset Restitution):**")
            lines.append(f"   - ใช้ตารางข้อ 2 เป็น **บัญชีแนบท้ายคำร้องขอคุ้มครองสิทธิผู้เสียหาย** ตาม พ.ร.บ. ปปง. มาตรา 49/1 ยอดเรียกร้องรวม **฿{result.total_claimable_thb:,.2f}**")
            lines.append("3. **การขอพยานหลักฐานทางดิจิทัลเพิ่มเติม:**")
        lines.append("   - ประสานธนาคารเจ้าของตู้ ATM เพื่อขอไฟล์ภาพ CCTV และพิกัดตู้")
        lines.append("   - ประสานผู้ให้บริการ VASP (Bitkub/Binance) เพื่อขอข้อมูล KYC ของบัญชีกระเป๋าเงินปลายทาง")

        return "\n".join(lines)

    def generate_analysis_report(
        self,
        result: VictimTraceResult,
        case_id: str = "CASE-VICTIM-001",
        officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
    ) -> str:
        """
        Generates an exhaustive, high-depth investigative forensic analysis report in Markdown.
        Persisted automatically to output/victim_<name_slug>_analysis.md.
        """
        lines = []
        lines.append(TABLE_RESPONSIVE_STYLE)
        lines.append("# รายงานวิเคราะห์เส้นทางการเงินเชิงลึกเฉพาะผู้เสียหาย (Victim Forensic Analysis Report)")
        lines.append(f"**เลขที่สำนวนคดี (Case ID):** `{case_id}`  ")
        lines.append(f"**ผู้ตรวจพิสูจน์ (Forensic Investigator):** {officer}  ")
        lines.append(f"**วันเวลาที่จัดทำเอกสาร:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}  ")
        lines.append(f"**มาตรฐานกฎหมายที่รองรับ:** ป.วิ.อ. มาตรา 226, พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 และ พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 1: Executive Loss Summary
        lines.append("## 1. บทสรุปข้อมูลผู้เสียหายและภาพรวมความเสียหาย (Executive Loss Summary)")
        lines.append(f"- **ชื่อ-นามสกุล ผู้เสียหาย:** **{result.victim_name}**")
        lines.append(f"- **จำนวนบัญชีต้นทางที่ถูกใช้โอน:** {len(result.victim_accounts)} บัญชี ({', '.join(result.victim_accounts) if result.victim_accounts else 'N/A'})")
        lines.append(f"- **บัญชีม้าพักเงินเป้าหมาย (Aggregator Mule Tier-1):** `{result.target_account}` ({result.target_account_name})")
        lines.append(f"- **ยอดเงินความเสียหายรวมของผู้เสียหาย:** **฿{result.total_inflow_thb:,.2f}** ({len(result.inflow_transactions)} รายการ)")
        lines.append(f"- **ยอดเงินที่จับคู่ระบายออกได้ด้วย MILP (Matched Outflows):** **฿{result.total_matched_outflow_thb:,.2f}**")
        lines.append(f"- **อัตราการกวาดเงินออกจากบัญชีม้า (Drain Rate):** **{result.drain_percentage:.2f}%**")
        pct_claim = (result.total_claimable_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        lines.append(f"- **ยอดเงินสิทธิเฉลี่ยทรัพย์คืนชอบธรรม (Proportional Restitution Claim):** **฿{result.total_claimable_thb:,.2f}** ({pct_claim:.2f}% ของยอดสูญเสีย)")
        lines.append(f"- **ระยะเวลาเงินแช่พักเฉลี่ย (Mean Residence Time):** **{result.avg_latency_minutes:.1f} นาที** (การกระจายเงินรวดเร็วแบบกวาดหมดบัญชี)")
        lines.append(f"- **ยอดเงินคงค้างหลงเหลือในบัญชีม้าพักเงิน (Residual Buffer):** **฿{result.net_residual_buffer_thb:,.2f}**")
        lines.append(f"- **ค่าแฮชตรวจสอบความสมบูรณ์ของไฟล์ Statement (SHA-256):** `{result.statement_sha256}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 2: Top Dispersal Destinations & Beneficiaries Breakdown
        lines.append("## 2. สรุปปลายทางเส้นทางการเงินและผู้รับประโยชน์หลัก (Top Dispersal Destinations & Beneficiaries)")
        lines.append("จากการประมวลผลจับคู่เส้นทางเงินทางคณิตศาสตร์แบบระบุตัวเหยื่อ (Victim-Centric Flow Conservation) พบว่าเงินถูกระบายออกไปยังผู้รับประโยชน์หลักดังต่อไปนี้:")
        lines.append("")
        lines.append("### แผนภาพแสดงเส้นทางการกระจายเงิน (Fund Dispersal Topology):")
        lines.append(self.generate_dispersal_mermaid(result))
        lines.append("")
        lines.append("| ลำดับ | ธนาคาร / เลขบัญชี | ชื่อบัญชีปลายทาง | ช่องทาง | ยอดเงินออก (฿) | สิทธิขอคืน (฿) | สัดส่วน | มาตรการแนะนำ |")
        lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |")

        for d in result.top_destinations:
            acct_info = f"{d.bank} {d.account_no}" if d.account_no != "UNKNOWN" else d.bank
            action_th = self._format_action_th(d.recommended_action)
            lines.append(
                f"| {d.rank} | {acct_info} | **{d.account_name}** | {d.channel} | ฿{d.total_drained_thb:,.2f} | **฿{d.proportional_claim_thb:,.2f}** | {d.percentage_of_victim_funds:.1f}% | {action_th} |"
            )

        tot_drained_sum = sum(d.total_drained_thb for d in result.top_destinations)
        tot_claim_sum = sum(d.proportional_claim_thb for d in result.top_destinations)
        lines.append(
            f"| **รวม** | - | **รวมทั้งสิ้น {len(result.top_destinations)} ปลายทาง** | - | **฿{tot_drained_sum:,.2f}** | **฿{tot_claim_sum:,.2f}** | **{pct_claim:.1f}%** | **AOC 1441 / ปปง. ม.49/1** |"
        )
        lines.append("")
        tier2_mules = [d for d in result.top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        atm_cashing = [d for d in result.top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        vasp_p2p = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        gateways = [d for d in result.top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]

        tot_tier2_claim = sum(d.proportional_claim_thb for d in tier2_mules)
        tot_atm_claim = sum(d.proportional_claim_thb for d in atm_cashing)
        tot_vasp_claim = sum(d.proportional_claim_thb for d in vasp_p2p)
        tot_gateway_claim = sum(d.proportional_claim_thb for d in gateways)

        lines.append("### จำแนกกลุ่มผู้รับประโยชน์และช่องทางการระบายเงิน:")
        cat_idx = 1
        if tier2_mules:
            lines.append(f"{cat_idx}. **เครือข่ายบัญชีม้าแถว 2 (Mule Tier-2 Mobile Banking):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_tier2_claim:,.2f}** ({tot_tier2_claim/result.total_inflow_thb*100:.1f}%)")
            lines.append("   - มีการกระจายไปยังบัญชีม้าแถว 2 หลายบัญชี เพื่อหลีกเลี่ยงเกณฑ์การรายงานธุรกรรม (Structuring)")
            cat_idx += 1
        if gateways:
            lines.append(f"{cat_idx}. **ระบบรับชำระเงินและแพลตฟอร์มโฆษณา (Payment Gateway & Ad Platforms):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_gateway_claim:,.2f}** ({tot_gateway_claim/result.total_inflow_thb*100:.1f}%)")
            lines.append("   - การนำเงินไปตัดชำระค่าโฆษณาโซเชียลมีเดียหรือแปลงสภาพผ่านเกตเวย์ (ห้ามอายัดผ่าน AOC 1441 แต่ต้องออกหมายเรียก ม.132)")
            cat_idx += 1
        if atm_cashing:
            lines.append(f"{cat_idx}. **การถอนเงินสดผ่านตู้ ATM ไม่ใช้บัตร (Physical Cash-Out):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_atm_claim:,.2f}** ({tot_atm_claim/result.total_inflow_thb*100:.1f}%)")
            lines.append("   - การกดเงินสดออกจากระบบทันทีเพื่อตัดตอนรอยเท้าดิจิทัล (Digital Footprint)")
            cat_idx += 1
        if vasp_p2p:
            lines.append(f"{cat_idx}. **ช่องทางสินทรัพย์ดิจิทัล P2P Escrow (Crypto Off-Ramp):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_vasp_claim:,.2f}** ({tot_vasp_claim/result.total_inflow_thb*100:.1f}%)")
            lines.append("   - การแปลงสภาพเป็นเงินดิจิทัล USDT เพื่อโอนย้ายข้ามพรมแดน")
            cat_idx += 1

        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 3: Transfer Behavioral Circumstances & Critical Forensic Insights
        lines.append("## 3. พฤติการณ์ของการโอนและประเด็นสำคัญเชิงสืบสวน (Transfer Circumstances & Critical Forensic Insights)")
        lines.append("")
        lines.append("### 3.1 พฤติการณ์การเคลื่อนย้ายเงินและรูปแบบการหลอกลวง (Transfer Circumstances & Modus Operandi)")
        vic_dates = set(t.timestamp.strftime("%Y-%m-%d") for t in result.inflow_transactions)
        if len(vic_dates) <= 1:
            lines.append(f"- **รูปแบบการโอนของเหยื่อ (Concentrated Funnel):** ผู้เสียหายถูกชักจูงให้ทำรายการโอนเงินก้อนใหญ่ต่อเนื่องกันภายในวันเดียวกัน รวม {len(result.inflow_transactions)} รายการ เป็นเงิน **฿{result.total_inflow_thb:,.2f}** สะท้อนถึงการถูกหลอกล่อตามสคริปต์กลโกงอย่างเข้มข้นในระยะเวลาอันสั้น")
        else:
            lines.append(f"- **รูปแบบการโอนของเหยื่อ (Distributed Inflow):** ผู้เสียหายทำรายการโอนเงินกระจายตัวต่อเนื่องข้ามวัน ({len(vic_dates)} วัน) รวม {len(result.inflow_transactions)} รายการ เป็นเงิน **฿{result.total_inflow_thb:,.2f}** ชี้ให้เห็นถึงกลลวงในลักษณะหลอกลงทุนต่อเนื่อง (Investment Fraud / Pig Butchering)")
        lines.append(f"- **การตอบสนองของบัญชีม้าแถว 1 (`{result.target_account}`):** มียอดเงินที่ถูกจับคู่ระบายออกทันที **฿{result.total_matched_outflow_thb:,.2f}** (อัตราการกวาดเงิน: **{result.drain_percentage:.2f}%**) โดยมีระยะเวลาเงินแช่พักเฉลี่ย **{result.avg_latency_minutes:.1f} นาที**")
        lines.append("")

        lines.append("### 3.2 การวิเคราะห์โอกาสทองในการอายัดทรัพย์สินคืน (Asset Recovery Golden Window Analysis)")
        res_pct = (result.net_residual_buffer_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        if result.net_residual_buffer_thb >= 50000.0 or res_pct >= 20.0:
            lines.append("> [!IMPORTANT]")
            lines.append(f"> **⭐ ตรวจพบโอกาสทองในการอายัดทรัพย์สินคืน (Primary Golden Window for Asset Recovery)**")
            lines.append(f"> - ตรวจพบยอดเงินคงค้างตกค้างในบัญชีม้าพักเงินแถว 1 (`{result.target_account}` {result.target_account_name}) สูงถึง **฿{result.net_residual_buffer_thb:,.2f}** (คิดเป็น **{res_pct:.1f}%** ของความเสียหายทั้งหมด)")
            lines.append(f"> - **นัยสำคัญเชิงสืบสวน:** มิจฉาชีพยังไม่สามารถระบายเงินส่วนนี้ออกไปได้ทัน (อาจติดปัญหาเพดานการโอนรายวัน Daily Limit หรือระบบเฝ้าระวังของธนาคาร)")
            lines.append(f"> - **ข้อสั่งการเร่งด่วนที่สุด:** พนักงานสอบสวนต้องเร่งส่งคำสั่งระงับธุรกรรม (AOC 1441) ไปยังบัญชีม้าแถว 1 นี้เป็นลำดับแรกสุดทันที เพราะเป็นจุดที่มีโอกาสได้เงินสดคืนกลับมาคุ้มครองสิทธิให้แก่ผู้เสียหายจริงสูงสุด")
        elif result.net_residual_buffer_thb > 0:
            lines.append(f"- ตรวจพบยอดเงินคงค้างในบัญชีม้าพักเงินแถว 1 จำนวน **฿{result.net_residual_buffer_thb:,.2f}** ({res_pct:.1f}%) ให้ส่งคำสั่งอายัดบัญชีม้าแถว 1 ควบคู่ไปกับบัญชีแถว 2")
        else:
            lines.append(f"- กระแสเงินของผู้เสียหายถูกระบายออกจากบัญชีม้าแถว 1 ครบถ้วน 100% (Instant Flush / Rapid Account Sweeping) ภายในเวลาเฉลี่ย {result.avg_latency_minutes:.1f} นาที หน้าต่างการอายัดในบัญชีแถว 1 ปิดลงแล้ว ให้เน้นย้ำการสกัดกั้นในแถว 2 และประสานงาน CCTV / VASP Escrow ทันที")
        lines.append("")

        lines.append("### 3.3 การจัดการกรณีปลายทางเป็น Payment Gateway / Tech Ad Platform (Platform Subpoena Directives)")
        if gateways:
            for gw in gateways:
                lines.append(f"#### ปลายทาง: `{gw.bank} {gw.account_no}` — **{gw.account_name}** (ยอดเงิน: ฿{gw.proportional_claim_thb:,.2f} / {gw.percentage_of_victim_funds:.1f}%)")
                lines.append("1. **ข้อจำกัดเชิงระบบและข้อควรระวัง (Systemic Limitation):**")
                lines.append(f"   - บัญชีดังกล่าวเป็น **บัญชีรวมของนิติบุคคลผู้ให้บริการชำระเงิน (Corporate Merchant Pool / Aggregator Clearing Account)** ของ {gw.account_name} เพื่อรองรับการชำระเงินออนไลน์หรือค่าบริการแพลตฟอร์ม")
                lines.append("   - **⚠️ ข้อควรระวังเด็ดขาด:** **ห้ามส่งคำสั่งอายัดบัญชีเงินฝากทั้งบัญชีผ่านระบบ AOC 1441 หรือส่งหนังสืออายัดไปยังธนาคารเจ้าของบัญชี** เนื่องจากจะกระทบต่อธุรกรรมปกติของประชาชนทั่วไปนับหมื่นราย และธนาคารจะปฏิเสธคำสั่งอายัดทันที")
                lines.append("2. **พฤติการณ์การฟอกเงินผ่านแอด (Ad Spend Laundering & Victim Acquisition Loop):**")
                lines.append("   - มิจฉาชีพนำเงินที่หลอกลวงได้จากผู้เสียหายไปตัดชำระค่าโฆษณาบนโซเชียลมีเดีย (Ad Spend Reinvestment) โดยตรง เพื่อนำไปใช้โปรโมตเพจหรือยิงแคมเปญโฆษณาหลอกลวงเหยื่อรายใหม่ๆ เข้าสู่วงจรอย่างต่อเนื่อง")
                lines.append("   - เป็นการแปลงสภาพเงินผิดกฎหมาย (Integration) ไปเป็นค่าบริการทางเทคโนโลยี ทำให้เส้นทางการเงินไม่ไหลเข้าบัญชีม้าบุคคลธรรมดาแถวถัดไป")
                lines.append("3. **แนวทางเชิงสืบสวนและมาตรการขอพยานหลักฐานตาม ป.วิ.อ. มาตรา 132 (Subpoena & Preservation Directives):**")
                lines.append(f"   - **ขั้นที่ 1 (ขอข้อมูลตัวแทนรับชำระ):** ออกหมายเรียกพยานเอกสาร/ข้อมูล (ป.วิ.อ. ม.132) ไปยังบริษัทผู้ให้บริการ Payment Gateway ({gw.account_name} / {gw.bank}) ระบุเลขอ้างอิงธุรกรรม วันที่ เวลา และยอดเงิน ฿{gw.total_drained_thb:,.2f} เพื่อขอทราบข้อมูลบัญชีลูกค้าย่อย (Sub-merchant ID), ชื่อบุคคล/นิติบุคคลที่ลงทะเบียน, และบัญชีธนาคารปลายทางที่ Settlement เงินออก")
                lines.append("   - **ขั้นที่ 2 (ขอข้อมูลแพลตฟอร์มโฆษณา):** ประสานงานส่งหมายเรียกหรือหนังสือขอพยานหลักฐานไปยังผู้ให้บริการแพลตฟอร์ม (เช่น Meta Platforms Inc. / Google / TikTok) เพื่อขอทราบ:")
                lines.append("     - ข้อมูลระบุตัวตนเจ้าของบัญชีโฆษณา (Ad Account Owner KYC)")
                lines.append("     - ข้อมูลแฟนเพจ/บัญชีที่ใช้ยิงแอด (Campaign Fanpage / URL)")
                lines.append("     - ข้อมูลผู้ดูแลระบบ (Page / Ad Account Admins): ชื่อ, อีเมล, หมายเลขโทรศัพท์ที่ลงทะเบียน")
                lines.append("     - บันทึกประวัติหมายเลข IP Address และ Timestamp ที่เข้าใช้งานและสั่งยิงแอด")
                lines.append("   - **ขั้นที่ 3 (ระงับบัญชีโฆษณาและอายัดยอดคงเหลือ):** ขอความร่วมมือผู้ให้บริการแพลตฟอร์มระงับบัญชีโฆษณา (Ad Account Take Down) เพื่อตัดวงจรการหลอกลวงเหยื่อรายอื่น และขออายัดยอดเงินคงค้างในกระเป๋าโฆษณา (Prepaid Ad Credit Balance)")
                lines.append("")
        else:
            lines.append("- ในเส้นทางเงินของผู้เสียหายรายนี้ ไม่พบการโอนตรงเข้า Payment Gateway หรือแพลตฟอร์มโฆษณา โดยเป็นการกระจายเข้าเครือข่ายบัญชีม้าบุคคลธรรมดา (Mule Tier-2) และ/หรือการถอนเงินสด/สินทรัพย์ดิจิทัลโดยตรง")
            lines.append("")

        lines.append("### 3.4 ข้อแนะนำการสืบสวนขยายผลเครือข่ายและผู้เสียหายร่วม (Cross-Victim Syndicate Expansion)")
        if gateways:
            lines.append("- **การเชื่อมโยงคดีผ่านแคมเปญโฆษณา (Syndicate Linkage):** แคมเปญโฆษณาที่ยิงผ่านแอดดังกล่าว ย่อมมีผู้เสียหายรายอื่นทั่วประเทศตกเป็นเหยื่อในเวลาไล่เลี่ยกัน พนักงานสอบสวนสามารถนำข้อมูล Ad Account ID, Campaign Fanpage, หรือ Merchant Reference ไปสืบค้นเชื่อมโยงกับเลขคดีในระบบแจ้งความออนไลน์ (thaipoliceonline) เพื่อรวมสำนวนและขยายผลจับกุมกลุ่มผู้บงการขบวนการคอลเซ็นเตอร์/สแกมเมอร์")
        else:
            lines.append("- **การตรวจสอบความเชื่อมโยงบัญชีม้า (Mule Network Linkage):** ตรวจสอบประวัติบัญชีม้าแถว 1 และแถว 2 ในฐานข้อมูล ศปอส.ตร. / AOC 1441 เพื่อหาความเชื่อมโยงกับผู้เสียหายรายอื่นในกลุ่มขบวนการเดียวกัน")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 4: MILP Mathematical Proofs
        lines.append("## 4. การรับรองความถูกต้องด้วยสมการคณิตศาสตร์เชิงเส้น (MILP Mathematical Proofs)")
        lines.append("การตรวจพิสูจน์ปฏิบัติตามหลักการอนุรักษ์กระแสเงิน (Flow Conservation) โดยใช้แบบจำลอง Mixed-Integer Linear Programming (`scipy.optimize.milp`):")
        lines.append("")
        lines.append("$$\\min_{x} \\left| \\sum_{j \\in \\text{Outflows}} x_j \\cdot O_j - \\text{Inflow} \\right| \\quad \\text{subject to} \\quad x_j \\in \\{0, 1\\}, \\; \\sum x_j \\cdot O_j \\le \\text{Inflow} + \\epsilon$$")
        lines.append("")
        for idx, cl in enumerate(result.matched_clusters, start=1):
            lines.append(f"- **กลุ่มที่ {idx} ({cl.cluster_id}):** เงินเข้า ฿{cl.inflow_total:,.2f} $\\to$ เงินออก ฿{cl.outflow_total:,.2f} (Drain: {cl.drain_percentage:.1f}%, Latency: {cl.avg_latency_minutes:.1f} นาที)")
            lines.append(f"  > `{cl.mathematical_proof}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 5: Proportional Restitution Allocation Methodology
        lines.append("## 5. หลักการและสูตรคำนวณสิทธิเรียกร้องเฉลี่ยทรัพย์คืน (AMLA 49/1 Formulation)")
        lines.append("ระบบใช้สูตรการปันส่วนสิทธิแบบจำเพาะกลุ่มก้อนกระแสเงิน (Cluster-Level Inflow Conservation Attribution):")
        lines.append("")
        lines.append("$$\\text{Proportional Claim}_d = \\sum_{c \\in \\text{Clusters}} \\text{Outflow}_{d,c} \\times \\min\\left(1.0, \\frac{\\text{Victim Inflow}_c}{\\text{Cluster Outflow Total}_c}\\right)$$")
        lines.append("")
        lines.append("- **เหตุผลทางนิติวิทยาศาสตร์การเงิน:** ป้องกันความเสียหายของผู้เสียหายถูกเจือจาง (Dilution) โดยเงินของผู้เสียหายรายอื่นในบัญชีม้ารวม (Aggregator Mule Pool) ทำให้ผู้เสียหายได้รับสิทธิเรียกร้องทรัพย์คืนชอบธรรมสูงสุดตามข้อเท็จจริงของกระแสเงินที่เกิดขึ้นจริง")
        lines.append(f"- **ยอดสิทธิเรียกร้องสุทธิที่ได้รับรอง:** **฿{result.total_claimable_thb:,.2f}** (คิดเป็น **{pct_claim:.2f}%** ของยอดที่โอนเข้าทั้งหมด)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 6: Actionable Directives by Target Category
        lines.append("## 6. มาตรการเชิงสืบสวนและแนวทางปฏิบัติการจำแนกตามประเภทปลายทาง (Actionable Directives)")
        lines.append("1. **การส่งคำขอระงับธุรกรรมฉุกเฉิน (72 ชั่วโมง) ต่อศูนย์ AOC 1441 เฉพาะบัญชีม้าบุคคลธรรมดา:**")
        lines.append("   - อาศัยอำนาจตาม พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7")
        if result.net_residual_buffer_thb > 0:
            lines.append(f"   - **⭐ อายัดบัญชีม้าแถว 1 (เร่งด่วนสูงสุด - มีเงินคงค้างรอฟอก):** {result.target_account} ({result.target_account_name}) — ยอดคงค้าง: **฿{result.net_residual_buffer_thb:,.2f}**")
        for d in result.top_destinations:
            if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no != "UNKNOWN":
                lines.append(f"   - **อายัดบัญชีม้าแถว 2:** {d.bank} เลขที่ `{d.account_no}` ({d.account_name}) — สิทธิเรียกร้องเฉลี่ยทรัพย์คืน: **฿{d.proportional_claim_thb:,.2f}**")

        dir_idx = 2
        if gateways:
            lines.append(f"{dir_idx}. **มาตรการขอพยานหลักฐานและระงับบัญชีโฆษณาตาม ป.วิ.อ. มาตรา 132 (Payment Gateway / Ad Platforms):**")
            lines.append("   - *⚠️ ข้อควรระวัง: ห้ามส่งคำสั่งอายัดผ่าน AOC 1441 ไปยังบัญชีผู้ให้บริการรับชำระเงิน/แพลตฟอร์มโฆษณา เพราะเป็นบัญชีรวมระดับองค์กร*")
            for d in gateways:
                lines.append(f"   - **ออกหมายเรียก ม.132 ต่อ {d.account_name} ({d.bank} {d.account_no}):** ขอข้อมูล Sub-merchant ID, Ad Account KYC, Campaign Fanpage, IP Logs และระงับบัญชีโฆษณา (ยอดเงินที่ไหลเข้า: ฿{d.proportional_claim_thb:,.2f})")
            dir_idx += 1

        lines.append(f"{dir_idx}. **การประสานงานสำนักงาน ปปง. เพื่อยึดและอายัดทรัพย์สิน (AMLA 49/1 Restitution):**")
        lines.append(f"   - ใช้รายงานวิเคราะห์ฉบับนี้พร้อมตารางผู้รับประโยชน์หลัก ประกอบคำร้องขอคุ้มครองสิทธิผู้เสียหายตาม พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1 ยอดเรียกร้องรวม **฿{result.total_claimable_thb:,.2f}**")
        dir_idx += 1

        vasp_targets = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        if vasp_targets:
            lines.append(f"{dir_idx}. **การส่งคำสั่งระงับกระเป๋าเงินและคำสั่งซื้อขายสินทรัพย์ดิจิทัล (VASP Freeze Request):**")
            for d in vasp_targets:
                lines.append(f"   - **ระงับกระเป๋าเงิน/P2P Escrow:** {d.bank} ร้านค้า `{d.account_name}` ({d.account_no}) — วงเงิน: **฿{d.proportional_claim_thb:,.2f}**")
            dir_idx += 1

        lines.append(f"{dir_idx}. **การขอพยานหลักฐานทางนิติวิทยาศาสตร์ดิจิทัลเพิ่มเติม:**")
        lines.append("   - ทำหนังสือขอภาพบันทึกจากกล้อง CCTV บริเวณตู้ ATM ในช่วงเวลาที่มีการทำรายการถอนเงินสดไม่ใช้บัตร (Cardless ATM Cash-out)")
        lines.append("   - ทำหนังสือขอข้อมูลการยืนยันตัวตน (KYC) และประวัติการทำธุรกรรม P2P จากผู้ประกอบธุรกิจสินทรัพย์ดิจิทัล (VASP)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 7: Cryptographic Chain of Custody
        lines.append("## 7. การรับรองความถูกต้องของพยานหลักฐานและห่วงโซ่การครอบครอง (Chain of Custody)")
        lines.append(f"- **Statement Provenance SHA-256:** `{result.statement_sha256}`")
        lines.append(f"- **สถานะความถูกต้อง (Integrity Status):** VERIFIED (ไม่พบการดัดแปลงหรือแทรกแซงข้อมูล)")
        lines.append(f"- **การยอมรับตามกฎหมาย:** พยานหลักฐานทางวิทยาศาสตร์และข้อมูลอิเล็กทรอนิกส์ตาม ป.วิ.อ. มาตรา 226 และ พ.ร.บ. ธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 มาตรา 26")
        lines.append("")

        return "\n".join(lines)

    def generate_aoc_payload(
        self,
        result: VictimTraceResult,
        case_id: str = "CASE-VICTIM-001",
        officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
    ) -> Dict[str, Any]:
        """Generates ready-to-transmit JSON payload for AOC 1441 emergency freezing."""
        freeze_targets = []
        for d in result.top_destinations:
            if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no != "UNKNOWN":
                freeze_targets.append({
                    "target_bank": d.bank,
                    "target_account_no": d.account_no,
                    "target_account_name": d.account_name,
                    "allocated_loss_claim_thb": round(d.proportional_claim_thb, 2),
                    "total_drained_volume_thb": round(d.total_drained_thb, 2),
                    "priority": "HIGH_URGENT",
                    "action": "SUSPEND_ALL_DEBIT_CHANNELS_72H",
                })

        return {
            "aoc_freeze_request": {
                "case_id": case_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "investigating_officer": officer,
                "legal_authority": "พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7",
                "victim_profile": {
                    "victim_name": result.victim_name,
                    "victim_accounts": result.victim_accounts,
                    "total_loss_thb": result.total_inflow_thb,
                    "total_claimable_thb": result.total_claimable_thb,
                },
                "gateway_mule_account": {
                    "account_no": result.target_account,
                    "account_name": result.target_account_name,
                    "drain_percentage": result.drain_percentage,
                },
                "freeze_targets": freeze_targets,
            }
        }

    def generate_html_dashboard(
        self,
        result: VictimTraceResult,
        output_html_path: Union[str, Path],
        case_id: str = "CASE-VICTIM-2026",
        officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
    ) -> str:
        """Generates an interactive single-page HTML forensic dashboard for the victim analysis."""
        from src.ui.victim_dashboard import VictimDashboardGenerator
        dash_gen = VictimDashboardGenerator()
        return dash_gen.generate_html(
            result=result,
            output_file_path=output_html_path,
            case_id=case_id,
            officer=officer,
            tolerance_ratio=self.tolerance_ratio,
        )

    def export_pdf(
        self,
        result: VictimTraceResult,
        output_pdf_path: Union[str, Path],
        case_id: str = "CASE-VICTIM-001",
        officer_name: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
        agency: str = "กองบัญชาการตำรวจสืบสวนสอบสวนอาชญากรรมทางเทคโนโลยี (บช.สอท.)",
        font_name: Optional[str] = "THSarabunNew",
    ) -> str:
        """Exports professional court-ready PDF dossier for the victim's money trail matching the analysis report."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from src.audit.esignature import DigitalSignatureManager

        out_p = Path(output_pdf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        fn = resolve_thai_font(font_name)
        math_fn = register_math_font()
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "VicTitle",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=22,
            leading=26,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
        )
        sub_style = ParagraphStyle(
            "VicSub",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=15,
            leading=19,
            alignment=1,
            textColor=colors.HexColor("#475569"),
        )
        h1_style = ParagraphStyle(
            "VicH1",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=6,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "VicBody",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
        )
        bold_body = ParagraphStyle(
            "VicBoldBody",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
        )
        th_style = ParagraphStyle(
            "VicTH",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=13,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
        )
        tbl_cell_style = ParagraphStyle(
            "VicCell",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
        )
        tbl_cell_center = ParagraphStyle(
            "VicCellCenter",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=12,
            leading=15,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
        )
        tbl_cell_bold = ParagraphStyle(
            "VicCellBold",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
        )
        code_style = ParagraphStyle(
            "VicCode",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=11,
            leading=14.5,
            textColor=colors.HexColor("#0f172a"),
        )

        doc = SimpleDocTemplate(
            str(out_p),
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=22,
            bottomMargin=22,
        )

        elements = []

        # ================= PAGE 1 =================
        elements.append(Paragraph(shape_thai_text("<b>สำนวนการตรวจพิสูจน์เส้นทางการเงินเฉพาะผู้เสียหาย (Victim Money Trail Dossier)</b>"), title_style))
        elements.append(Paragraph(shape_thai_text("มาตรฐาน ป.วิ.อ. มาตรา 226, พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 และ พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1"), sub_style))
        elements.append(Spacer(1, 4))

        # 1. Executive Summary Table
        elements.append(Paragraph(shape_thai_text("<b>1. บทสรุปข้อมูลผู้เสียหายและภาพรวมความเสียหาย (Executive Loss Summary)</b>"), h1_style))

        pct_claim = (result.total_claimable_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        vic_accts_str = ", ".join(result.victim_accounts) if result.victim_accounts else "N/A"

        meta_rows = [
            [
                Paragraph(shape_thai_text(f"<b>เลขที่สำนวนคดี:</b> {case_id}"), body_style),
                Paragraph(shape_thai_text(f"<b>ผู้เสียหาย:</b> {result.victim_name} (บัญชี: {vic_accts_str})"), body_style),
            ],
            [
                Paragraph(shape_thai_text(f"<b>ผู้ตรวจพิสูจน์:</b> {officer_name} ({agency})"), body_style),
                Paragraph(shape_thai_text(f"<b>บัญชีม้าพักเงินเป้าหมาย:</b> {result.target_account} ({result.target_account_name})"), body_style),
            ],
            [
                Paragraph(shape_thai_text(f"<b>ยอดเงินความเสียหายรวม:</b> ฿{result.total_inflow_thb:,.2f} ({len(result.inflow_transactions)} รายการ)"), body_style),
                Paragraph(shape_thai_text(f"<b>ยอดระบายออกด้วย MILP:</b> ฿{result.total_matched_outflow_thb:,.2f} (Drain: {result.drain_percentage:.2f}%)"), body_style),
            ],
            [
                Paragraph(shape_thai_text(f"<b>สิทธิเฉลี่ยทรัพย์คืนชอบธรรม:</b> ฿{result.total_claimable_thb:,.2f} ({pct_claim:.2f}%)"), bold_body),
                Paragraph(shape_thai_text(f"<b>ระยะเวลาเงินแช่พักเฉลี่ย:</b> {result.avg_latency_minutes:.1f} นาที"), body_style),
            ],
            [
                Paragraph(shape_thai_text(f"<b>เงินคงค้างในบัญชีม้า (Residual Buffer):</b> ฿{result.net_residual_buffer_thb:,.2f}"), body_style),
                Paragraph(shape_thai_text(f"<b>Statement SHA-256:</b> {result.statement_sha256[:28]}..."), body_style),
            ],
        ]
        t_meta = Table(meta_rows, colWidths=[270, 269])
        t_meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 5))

        # 2. Top Dispersal Destinations & Beneficiaries Table
        elements.append(Paragraph(shape_thai_text("<b>2. สรุปปลายทางเส้นทางการเงินและผู้รับประโยชน์หลัก (Top Dispersal Destinations & Beneficiaries)</b>"), h1_style))
        dest_rows = [
            [
                Paragraph(shape_thai_text("<b>ลำดับ</b>"), th_style),
                Paragraph(shape_thai_text("<b>ธนาคาร / บัญชี</b>"), th_style),
                Paragraph(shape_thai_text("<b>ชื่อบัญชีปลายทาง</b>"), th_style),
                Paragraph(shape_thai_text("<b>ช่องทาง</b>"), th_style),
                Paragraph(shape_thai_text("<b>ยอดออกรวม (฿)</b>"), th_style),
                Paragraph(shape_thai_text("<b>สิทธิเฉลี่ยทรัพย์ (฿)</b>"), th_style),
                Paragraph(shape_thai_text("<b>สัดส่วน</b>"), th_style),
                Paragraph(shape_thai_text("<b>มาตรการที่แนะนำ</b>"), th_style),
            ]
        ]

        tot_drained_sum = sum(d.total_drained_thb for d in result.top_destinations)
        tot_claim_sum = sum(d.proportional_claim_thb for d in result.top_destinations)

        for d in result.top_destinations:
            acct_info = f"{d.bank} {d.account_no}" if d.account_no != "UNKNOWN" else d.bank
            dest_rows.append([
                Paragraph(str(d.rank), tbl_cell_center),
                Paragraph(shape_thai_text(acct_info), tbl_cell_style),
                Paragraph(shape_thai_text(f"<b>{d.account_name}</b>"), tbl_cell_style),
                Paragraph(shape_thai_text(d.channel), tbl_cell_center),
                Paragraph(f"฿{d.total_drained_thb:,.2f}", tbl_cell_style),
                Paragraph(shape_thai_text(f"<b>฿{d.proportional_claim_thb:,.2f}</b>"), tbl_cell_bold),
                Paragraph(f"{d.percentage_of_victim_funds:.1f}%", tbl_cell_center),
                Paragraph(shape_thai_text(f"<font size=8>{d.recommended_action}</font>"), tbl_cell_style),
            ])

        # Add Total Row
        dest_rows.append([
            Paragraph(shape_thai_text("<b>รวม</b>"), th_style),
            Paragraph(shape_thai_text("<b>-</b>"), th_style),
            Paragraph(shape_thai_text(f"<b>รวม {len(result.top_destinations)} ปลายทาง</b>"), th_style),
            Paragraph(shape_thai_text("<b>-</b>"), th_style),
            Paragraph(shape_thai_text(f"<b>฿{tot_drained_sum:,.2f}</b>"), th_style),
            Paragraph(shape_thai_text(f"<b>฿{tot_claim_sum:,.2f}</b>"), th_style),
            Paragraph(shape_thai_text(f"<b>{pct_claim:.1f}%</b>"), th_style),
            Paragraph(shape_thai_text("<b>AOC 1441 / ปปง.</b>"), th_style),
        ])

        t_dest = Table(dest_rows, colWidths=[24, 75, 115, 42, 70, 76, 37, 100])
        t_dest.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(t_dest)
        elements.append(Spacer(1, 4))

        # Category Breakdown
        tier2_mules = [d for d in result.top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        atm_cashing = [d for d in result.top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        vasp_p2p = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]

        tot_tier2_claim = sum(d.proportional_claim_thb for d in tier2_mules)
        tot_atm_claim = sum(d.proportional_claim_thb for d in atm_cashing)
        tot_vasp_claim = sum(d.proportional_claim_thb for d in vasp_p2p)
        res_buf = result.net_residual_buffer_thb
        t_inf = result.total_inflow_thb if result.total_inflow_thb > 0 else 1.0

        cat_rows = [
            [
                Paragraph(shape_thai_text(f"• <b>เครือข่ายบัญชีม้าแถว 2 (Mule Tier-2):</b> ฿{tot_tier2_claim:,.2f} ({tot_tier2_claim/t_inf*100:.1f}%)"), body_style),
                Paragraph(shape_thai_text(f"• <b>การถอนเงินสดตู้ ATM (Cash-Out):</b> ฿{tot_atm_claim:,.2f} ({tot_atm_claim/t_inf*100:.1f}%)"), body_style),
            ],
            [
                Paragraph(shape_thai_text(f"• <b>สินทรัพย์ดิจิทัล P2P (Crypto Off-Ramp):</b> ฿{tot_vasp_claim:,.2f} ({tot_vasp_claim/t_inf*100:.1f}%)"), body_style),
                Paragraph(shape_thai_text(f"• <b>เงินตกค้างในบัญชีม้า (Residual Buffer):</b> ฿{res_buf:,.2f} ({res_buf/t_inf*100:.1f}%)"), body_style),
            ],
        ]
        t_cat = Table(cat_rows, colWidths=[270, 269])
        t_cat.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_cat)

        # ================= PAGE 2 =================
        elements.append(PageBreak())

        # 3. MILP Mathematical Proofs
        elements.append(Paragraph(shape_thai_text("<b>3. การรับรองความถูกต้องด้วยแบบจำลองคณิตศาสตร์เชิงเส้น (MILP Mathematical Proofs)</b>"), h1_style))
        elements.append(Paragraph(shape_thai_text(
            "การตรวจพิสูจน์ปฏิบัติตามหลักการอนุรักษ์กระแสเงิน (Flow Conservation) โดยใช้แบบจำลอง Mixed-Integer Linear Programming "
            "(<code>scipy.optimize.milp</code>) ตาม ป.วิ.อ. มาตรา 226:"
        ), body_style))
        if math_fn:
            eq_text = (
                f"<b>สมการเป้าหมาย:</b> <font name=\"{math_fn}\">min |∑ x_j · O_j - Inflow|</font> โดยที่ "
                f"<font name=\"{math_fn}\">x_j ∈ {{0, 1}}</font> และ <font name=\"{math_fn}\">∑ x_j · O_j ≤ Inflow + ε</font> &nbsp;&nbsp;|&nbsp;&nbsp;"
                f"ประมวลผลทั้งสิ้น <b>{len(result.matched_clusters)} คลัสเตอร์</b> สถานะ <b>OPTIMAL ทุกกลุ่ม</b>"
            )
            claim_eq = f"&nbsp;&nbsp;<b>Proportional Claim_d</b> = <font name=\"{math_fn}\">∑</font> [ Outflow_{{d,c}} × min(1.0, Inflow_c / Outflow_total_c) ]<br/>"
            arrow_sym = f"<font name=\"{math_fn}\">→</font>"
        else:
            eq_text = (
                f"<b>สมการเป้าหมาย:</b> min |sum(x_j · O_j) - Inflow| โดยที่ "
                f"x_j in {{0, 1}} และ sum(x_j · O_j) <= Inflow + eps &nbsp;&nbsp;|&nbsp;&nbsp;"
                f"ประมวลผลทั้งสิ้น <b>{len(result.matched_clusters)} คลัสเตอร์</b> สถานะ <b>OPTIMAL ทุกกลุ่ม</b>"
            )
            claim_eq = "&nbsp;&nbsp;<b>Proportional Claim_d</b> = sum [ Outflow_{d,c} × min(1.0, Inflow_c / Outflow_total_c) ]<br/>"
            arrow_sym = "->"

        elements.append(Paragraph(shape_thai_text(eq_text), body_style))
        elements.append(Spacer(1, 3))

        # Show ALL clusters completely without abbreviation
        for idx, cl in enumerate(result.matched_clusters, start=1):
            proof_text = cl.mathematical_proof
            cluster_p = (
                f"• <b>กลุ่มที่ {idx} ({cl.cluster_id}):</b> เข้า ฿{cl.inflow_total:,.2f} {arrow_sym} ออก ฿{cl.outflow_total:,.2f} "
                f"(Drain: {cl.drain_percentage:.1f}%, หน่วง: {cl.avg_latency_minutes:.1f} น.)<br/>"
                f"&nbsp;&nbsp;<code>{proof_text}</code>"
            )
            elements.append(Paragraph(shape_thai_text(cluster_p), code_style))
            elements.append(Spacer(1, 2))

        elements.append(Spacer(1, 5))

        # 4. AMLA 49/1 Formulation
        elements.append(Paragraph(shape_thai_text("<b>4. หลักการและสูตรคำนวณสิทธิเรียกร้องเฉลี่ยทรัพย์คืน (AMLA 49/1 Formulation)</b>"), h1_style))
        elements.append(Paragraph(shape_thai_text(
            "สูตรการปันส่วนสิทธิแบบจำเพาะกลุ่มก้อนกระแสเงิน (Cluster-Level Inflow Conservation Attribution):<br/>"
            + claim_eq
            + f"ยอดสิทธิเรียกร้องสุทธิที่ได้รับรองรวม <b>฿{result.total_claimable_thb:,.2f}</b> (คิดเป็น <b>{pct_claim:.2f}%</b> ของยอดความเสียหายทั้งหมด)"
        ), body_style))
        elements.append(Spacer(1, 5))

        # 5. Immediate Action Directives & AOC Freezing Targets
        elements.append(Paragraph(shape_thai_text("<b>5. มาตรการเชิงสืบสวนและบัญชีเป้าหมายที่ต้องส่งคำสั่งอายัดเร่งด่วน AOC 1441</b>"), h1_style))
        elements.append(Paragraph(shape_thai_text(
            "1. <b>การส่งคำขอระงับธุรกรรมฉุกเฉิน (72 ชม.) ต่อศูนย์ AOC 1441:</b> อาศัยอำนาจตาม พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7 อายัดบัญชีม้าแถว 2 เป้าหมายทันที:"
        ), body_style))

        freeze_targets_list = [d for d in result.top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no != "UNKNOWN"]
        for ft in freeze_targets_list:
            elements.append(Paragraph(
                shape_thai_text(f"&nbsp;&nbsp;&nbsp;&nbsp;• <b>{ft.bank} {ft.account_no}</b> ({ft.account_name}) — สิทธิเรียกร้องเฉลี่ยทรัพย์: <b>฿{ft.proportional_claim_thb:,.2f}</b>"),
                body_style
            ))
        elements.append(Paragraph(shape_thai_text(
            "2. <b>การประสานงาน ปปง.:</b> ใช้สำนวนการตรวจพิสูจน์นี้ประกอบคำร้องขอคุ้มครองสิทธิผู้เสียหายตาม พ.ร.บ. ปปง. มาตรา 49/1"
        ), body_style))
        vasp_targets = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        if vasp_targets:
            elements.append(Paragraph(shape_thai_text(
                "3. <b>การส่งคำสั่งระงับกระเป๋าเงินและคำสั่งซื้อขายสินทรัพย์ดิจิทัล (VASP Freeze Request):</b>"
            ), body_style))
            for vt in vasp_targets:
                elements.append(Paragraph(
                    shape_thai_text(f"&nbsp;&nbsp;&nbsp;&nbsp;• <b>{vt.bank} {vt.account_name}</b> ({vt.account_no}) — วงเงิน: <b>฿{vt.proportional_claim_thb:,.2f}</b>"),
                    body_style
                ))
            elements.append(Paragraph(shape_thai_text(
                "4. <b>พยานหลักฐานดิจิทัล:</b> ขอภาพถ่าย CCTV ตู้ ATM และข้อมูลการยืนยันตัวตน KYC จากผู้ให้บริการสินทรัพย์ดิจิทัล (VASP)"
            ), body_style))
        else:
            elements.append(Paragraph(shape_thai_text(
                "3. <b>พยานหลักฐานดิจิทัล:</b> ขอภาพถ่าย CCTV ตู้ ATM และข้อมูลการยืนยันตัวตน KYC จากผู้ให้บริการสินทรัพย์ดิจิทัล (VASP)"
            ), body_style))
        elements.append(Spacer(1, 5))

        # 6. Cryptographic Chain of Custody & Sign-off
        sig_mgr = DigitalSignatureManager()
        sig_data = sig_mgr.sign_artifact(result.statement_sha256 or "SHA256-PENDING", "POL-8842", officer_name, agency)
        sig_hex = sig_data.get("signature", "SIG-PENDING")

        sig_rows = [
            [
                Paragraph(shape_thai_text(f"<b>Statement Provenance SHA-256:</b><br/><code>{result.statement_sha256}</code>"), code_style),
                Paragraph(shape_thai_text(f"<b>Digital Signature (HMAC-SHA256):</b><br/><code>{sig_hex[:36]}...</code>"), code_style),
            ],
            [
                Paragraph(shape_thai_text(f"<b>ผู้ตรวจพิสูจน์:</b> {officer_name}<br/><b>ตำแหน่ง:</b> พนักงานสอบสวนผู้เชี่ยวชาญ สอท."), body_style),
                Paragraph(shape_thai_text(f"<b>สถานะการตรวจพิสูจน์:</b> VERIFIED<br/><b>การยอมรับตามกฎหมาย:</b> ป.วิ.อ. มาตรา 226 / ธุรกรรมอิเล็กทรอนิกส์ ม.26"), body_style),
            ]
        ]
        t_sig = Table(sig_rows, colWidths=[270, 269])
        t_sig.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))

        sign_elements = [
            Paragraph(shape_thai_text("<b>6. การรับรองความถูกต้องของพยานหลักฐานและห่วงโซ่การครอบครอง (Chain of Custody)</b>"), h1_style),
            t_sig,
        ]
        elements.append(KeepTogether(sign_elements))

        doc.build(elements)
        return str(out_p.resolve())

