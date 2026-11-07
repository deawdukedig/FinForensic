"""
AOC 1441 and Central Fraud Registry (CFR) Interoperability Module.
Provides blacklist checking against known fraud syndicate accounts and
formats standardized JSON payloads for urgent account suspension requests.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from src.models.transaction import BankTransaction


# Mock high-risk syndicate blacklist from Central Fraud Registry
CFR_BLACKLIST_SAMPLE = {
    "x8004": {"name": "MRS. SOPHEA SAR", "risk_level": "CATEGORY_1_MULE", "flagged_by": "AOC-1441", "reason": "Cross-border scam syndicate"},
    "x8005": {"name": "นาย ธีรภัทร บุญเสริม", "risk_level": "CATEGORY_2_MULE", "flagged_by": "AMLO", "reason": "High-velocity structuring recipient"},
}


class AOCFraudRegistryClient:
    """
    Client for checking suspect entities against the Central Fraud Registry (CFR)
    and generating automated emergency freezing requests to AOC 1441.
    """

    def __init__(self, api_endpoint: str = "https://api.aoc1441.go.th/v1"):
        self.endpoint = api_endpoint

    def check_blacklist(self, transactions: List[BankTransaction]) -> List[Dict[str, Any]]:
        """
        Cross-checks counterparties against the CFR blacklist database.
        """
        hits: List[Dict[str, Any]] = []
        for tx in transactions:
            acct = tx.counterparty_account
            if acct and acct in CFR_BLACKLIST_SAMPLE:
                info = CFR_BLACKLIST_SAMPLE[acct]
                hits.append({
                    "tx_id": tx.tx_id,
                    "account": acct,
                    "name": tx.counterparty_name or info["name"],
                    "risk_level": info["risk_level"],
                    "flagged_by": info["flagged_by"],
                    "reason": info["reason"],
                    "amount": tx.amount,
                    "timestamp": tx.timestamp.isoformat(),
                })
        return hits

    def generate_freeze_payload(
        self,
        case_id: str,
        investigator_id: str,
        target_account: str,
        bank_code: str,
        account_name: str,
        drain_percentage: float,
        matched_outflow_total: float,
        reason: str = "Urgent suspension under Anti-Cyber Crime Royal Decree B.E. 2566 Section 7",
    ) -> Dict[str, Any]:
        """
        Generates official AOC 1441 freeze dispatch JSON payload.
        """
        now = datetime.now(timezone.utc).isoformat()
        return {
            "dispatch_header": {
                "agency": "ROYAL_THAI_POLICE_CCIB",
                "officer_id": investigator_id,
                "case_reference": case_id,
                "timestamp_utc": now,
                "priority": "URGENT_EMERGENCY_FREEZE",
                "legal_basis": "พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7",
            },
            "target_account": {
                "account_number": target_account,
                "account_name": account_name,
                "bank_code": bank_code,
                "account_tier": "TIER_1_AGGREGATOR_MULE",
                "drain_rate_percent": round(drain_percentage, 2),
                "disbursed_sum_thb": matched_outflow_total,
            },
            "freeze_scope": {
                "action": "SUSPEND_ALL_DEBIT_CHANNELS",
                "channels": ["MOBILE_BANKING", "ATM", "COUNTER", "PROMPTPAY"],
                "duration_hours": 72,
            },
            "justification": reason,
        }
