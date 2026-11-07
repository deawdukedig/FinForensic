"""
Graph Network Analytics and Multi-Hop Tracing Engine.
Builds directed graph topologies, traces multi-hop layering, detects shared identifiers,
and exports Cypher queries and Mermaid network diagrams.
"""

from __future__ import annotations
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from src.models.transaction import BankTransaction, ActivityType
from src.ingestion.entity_extractor import EntityExtractor


class GraphTracer:
    """
    Constructs transaction graphs for multi-hop forensic tracing
    (Victim -> Mule Tier 1 -> Mule Tier 2 -> VASP / Cashier).
    """

    def __init__(self, target_account: str):
        self.target_account = target_account
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def build_graph(self, transactions: List[BankTransaction]) -> Dict[str, Any]:
        """
        Builds graph structures from a list of transactions.
        """
        for tx in transactions:
            acct = tx.account_no
            if acct not in self.nodes:
                self.nodes[acct] = {
                    "account_no": acct,
                    "name": tx.account_name,
                    "bank": "TARGET",
                    "in_volume": 0.0,
                    "out_volume": 0.0,
                    "is_target": True,
                }

            if tx.activity == ActivityType.INFLOW and tx.counterparty_account:
                cp_acct = tx.counterparty_account
                if cp_acct not in self.nodes:
                    self.nodes[cp_acct] = {
                        "account_no": cp_acct,
                        "name": tx.counterparty_name or "Unknown Inflow Party",
                        "bank": tx.counterparty_bank or "Unknown",
                        "in_volume": 0.0,
                        "out_volume": 0.0,
                        "is_target": False,
                    }
                self.nodes[cp_acct]["out_volume"] += tx.amount
                self.nodes[acct]["in_volume"] += tx.amount
                self.edges.append({
                    "from": cp_acct,
                    "to": acct,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp,
                    "tx_id": tx.tx_id,
                })

            elif tx.activity == ActivityType.OUTFLOW and tx.counterparty_account:
                cp_acct = tx.counterparty_account
                if cp_acct not in self.nodes:
                    self.nodes[cp_acct] = {
                        "account_no": cp_acct,
                        "name": tx.counterparty_name or "Unknown Outflow Party",
                        "bank": tx.counterparty_bank or "Unknown",
                        "in_volume": 0.0,
                        "out_volume": 0.0,
                        "is_target": False,
                    }
                self.nodes[acct]["out_volume"] += tx.amount
                self.nodes[cp_acct]["in_volume"] += tx.amount
                self.edges.append({
                    "from": acct,
                    "to": cp_acct,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp,
                    "tx_id": tx.tx_id,
                })

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "target_account": self.target_account,
        }

    def detect_shared_surnames(self) -> List[Dict[str, Any]]:
        """
        Finds accounts sharing the same family surname (Entity Resolution).
        """
        surname_map: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        EXCLUDE_SURNAMES = {
            "party", "unknown", "n/a", "none", "entity", "account", "inflow", "outflow",
            "counter", "fresh", "shop", "store", "dispenser", "tier", "mule"
        }
        for acct, data in self.nodes.items():
            surname = EntityExtractor.extract_surname(data["name"])
            if surname and len(surname) > 3 and surname.lower() not in EXCLUDE_SURNAMES:
                surname_map[surname].append({"account": acct, "name": data["name"], "bank": data["bank"]})

        shared: List[Dict[str, Any]] = []
        for surname, accounts in sorted(surname_map.items(), key=lambda x: len(x[1]), reverse=True):
            if len(accounts) >= 2:
                shared.append({
                    "surname": surname,
                    "accounts": accounts,
                    "count": len(accounts),
                })
        return shared

    def export_cypher(self) -> str:
        """
        Generates Neo4j Cypher ingestion statements.
        """
        cypher_lines = ["// Neo4j Forensic Cypher Statements"]
        for node_id, data in self.nodes.items():
            cypher_lines.append(
                f'MERGE (a:Account {{account_number: "{node_id}"}}) '
                f'SET a.name = "{data["name"]}", a.bank = "{data["bank"]}", a.is_target = {str(data["is_target"]).lower()};'
            )

        for edge in self.edges:
            cypher_lines.append(
                f'MATCH (u:Account {{account_number: "{edge["from"]}"}}), (v:Account {{account_number: "{edge["to"]}"}}) '
                f'CREATE (u)-[:TRANSFERRED {{amount: {edge["amount"]}, timestamp: "{edge["timestamp"].isoformat()}", tx_id: "{edge["tx_id"]}"}}]->(v);'
            )

        return "\n".join(cypher_lines)

    def export_mermaid(self, max_edges: int = 25) -> str:
        """
        Generates Mermaid diagram string for markdown visual rendering.
        """
        mermaid = ["flowchart LR"]
        target_name = self.nodes.get(self.target_account, {}).get("name", self.target_account)
        mermaid.append(f'    TARGET["{target_name}<br/>({self.target_account})"]:::targetNode')

        for idx, edge in enumerate(self.edges[:max_edges], start=1):
            from_name = self.nodes.get(edge["from"], {}).get("name", edge["from"])
            to_name = self.nodes.get(edge["to"], {}).get("name", edge["to"])
            from_acct = edge["from"]
            to_acct = edge["to"]
            amt_str = f"฿{edge['amount']:,.0f}"

            if edge["from"] == self.target_account:
                node_id = f"OUT_{idx}"
                mermaid.append(f'    TARGET -->|"{amt_str}"| {node_id}["{to_name}<br/>({to_acct})"]')
            else:
                node_id = f"IN_{idx}"
                mermaid.append(f'    {node_id}["{from_name}<br/>({from_acct})"] -->|"{amt_str}"| TARGET')

        mermaid.append("    classDef targetNode fill:#f96,stroke:#333,stroke-width:2px;")
        return "\n".join(mermaid)
