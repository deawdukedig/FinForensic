"""
Reversal and chargeback reconciliation module.
Eliminates artificial volume inflation from bounced, failed, or reversed transactions.
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Any
from datetime import timedelta
from src.models.transaction import BankTransaction, ActivityType


REVERSAL_KEYWORDS = ["ยกเลิก", "คืนเงิน", "REVERSAL", "RVS", "CHARGEBACK", "BOUNCE", "FAILED"]


class ReversalReconciler:
    """
    Reconciles reversals and failed bank transfers.
    Matches paired transactions within a sliding temporal window (default 24 hours).
    """

    def __init__(self, match_window_hours: int = 24):
        self.match_window = timedelta(hours=match_window_hours)

    def reconcile(self, transactions: List[BankTransaction]) -> Tuple[List[BankTransaction], Dict[str, Any]]:
        """
        Scans transaction list for reversal pairs, marks them with is_reversal=True,
        and links them via reversal_ref_id.
        """
        reconciled = [tx.model_copy() for tx in transactions]
        reconciled_pairs: List[Tuple[str, str, float]] = []
        total_reconciled_amount = 0.0

        # Pass 1: Identify explicit reversal keywords in descriptions or ActivityType.REVERSAL
        for i, tx in enumerate(reconciled):
            desc_upper = tx.description.upper()
            is_explicit_rev = (tx.activity == ActivityType.REVERSAL) or any(k in desc_upper for k in REVERSAL_KEYWORDS)
            
            if is_explicit_rev and not tx.is_reversal:
                # Search for corresponding opposing transaction
                target_activity = ActivityType.OUTFLOW if tx.activity == ActivityType.INFLOW else ActivityType.INFLOW
                
                for j in range(i - 1, -1, -1):
                    prior = reconciled[j]
                    if prior.is_reversal:
                        continue
                    if prior.activity == target_activity and abs(prior.amount - tx.amount) < 0.01:
                        if abs(tx.timestamp - prior.timestamp) <= self.match_window:
                            # Found match
                            tx.is_reversal = True
                            tx.reversal_ref_id = prior.tx_id
                            prior.is_reversal = True
                            prior.reversal_ref_id = tx.tx_id
                            reconciled_pairs.append((prior.tx_id, tx.tx_id, tx.amount))
                            total_reconciled_amount += tx.amount
                            break

        summary = {
            "reversal_pairs_count": len(reconciled_pairs),
            "reconciled_volume": total_reconciled_amount,
            "pairs": reconciled_pairs,
        }
        return reconciled, summary
