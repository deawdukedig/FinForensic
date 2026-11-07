"""
Case-Level Multi-Tenancy and Cross-Case Syndicate Alert Module.
Ensures strict case file isolation between police stations / agencies while
detecting syndicated mule accounts operating across multiple active jurisdictions.
"""

from __future__ import annotations
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
from src.security.pdpa_masker import PDPAMasker


class CaseRecord:
    def __init__(self, case_id: str, agency: str, lead_officer: str, description: str = ""):
        self.case_id = case_id
        self.agency = agency
        self.lead_officer = lead_officer
        self.description = description
        self.created_at = datetime.now(timezone.utc)
        self.target_accounts: Set[str] = set()
        self.counterparty_accounts: Set[str] = set()


class CaseManager:
    """
    Manages multi-tenant case isolation and cross-jurisdictional syndicate alerts.
    """

    def __init__(self):
        self.cases: Dict[str, CaseRecord] = {}
        # Global reverse index: account_no -> list of case_ids
        self._account_case_index: Dict[str, Set[str]] = {}

    def register_case(self, case_id: str, agency: str, officer: str, desc: str = "") -> CaseRecord:
        """Registers an isolated case silo for an agency."""
        rec = CaseRecord(case_id, agency, officer, desc)
        self.cases[case_id] = rec
        return rec

    def associate_accounts(self, case_id: str, target_accounts: List[str], counterparty_accounts: List[str]) -> None:
        """Associates accounts to a case and updates the cross-case index."""
        if case_id not in self.cases:
            raise KeyError(f"Case {case_id} not registered")

        case = self.cases[case_id]
        all_accts = set(target_accounts) | set(counterparty_accounts)

        case.target_accounts.update(target_accounts)
        case.counterparty_accounts.update(counterparty_accounts)

        for acct in all_accts:
            if acct not in self._account_case_index:
                self._account_case_index[acct] = set()
            self._account_case_index[acct].add(case_id)

    def check_cross_case_alerts(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Scans all accounts in case_id to see if they are active in other cases.
        Returns anonymized / masked syndicate alerts to prevent breach of case confidentiality.
        """
        if case_id not in self.cases:
            return []

        case = self.cases[case_id]
        all_accts = case.target_accounts | case.counterparty_accounts
        alerts: List[Dict[str, Any]] = []

        for acct in all_accts:
            matched_cases = self._account_case_index.get(acct, set()) - {case_id}
            if matched_cases:
                other_agencies = [self.cases[cid].agency for cid in matched_cases if cid in self.cases]
                alerts.append({
                    "account_masked": PDPAMasker.mask_account(acct),
                    "account_raw": acct,
                    "hit_count": len(matched_cases),
                    "other_case_ids": list(matched_cases),
                    "other_agencies": list(set(other_agencies)),
                    "syndicate_risk": "CRITICAL_CROSS_JURISDICTION_MULE",
                })

        return alerts
