"""
Behavioral and forensic signal analysis module.
Computes Pass-through Velocity, Structuring/Smurfing Evasion, Round-Number Clustering,
and generates the Unified Suspicion Score (0-100).
"""

from __future__ import annotations
from bisect import bisect_right
from typing import List, Dict, Any, Tuple
import numpy as np
from src.models.transaction import BankTransaction, ActivityType


class ForensicBehavioralSignals:
    """
    Extracts behavioral signals indicating money laundering or mule account operations.
    """

    @staticmethod
    def calculate_residence_latencies(
        inflows: List[BankTransaction],
        outflows: List[BankTransaction],
    ) -> List[float]:
        """
        Calculates transit residence time in minutes for outflows relative to recent inflows.
        Optimized via sorted timestamp binary search O((N_in + N_out) log N_in).
        """
        if not inflows or not outflows:
            return []

        sorted_inflows = sorted(inflows, key=lambda x: x.timestamp)
        inflow_times = [inf.timestamp for inf in sorted_inflows]

        latencies: List[float] = []
        for out_tx in outflows:
            idx = bisect_right(inflow_times, out_tx.timestamp)
            if idx > 0:
                closest_ts = inflow_times[idx - 1]
                latency_min = (out_tx.timestamp - closest_ts).total_seconds() / 60.0
                latencies.append(max(0.0, latency_min))
            else:
                latencies.append(0.0)

        return latencies

    @staticmethod
    def calculate_drain_rate(total_inflow: float, total_outflow: float, final_balance: float) -> float:
        """
        Computes drain percentage. Mule accounts typically drain >= 99% of deposited funds.
        """
        if total_inflow <= 0:
            return 0.0
        drained = total_outflow
        return min(100.0, (drained / total_inflow) * 100.0)

    @staticmethod
    def evaluate_round_number_ratio(transactions: List[BankTransaction]) -> float:
        """
        Calculates proportion of round-sum transactions (divisible by 10,000 or 1,000).
        """
        if not transactions:
            return 0.0
        round_count = sum(1 for tx in transactions if (tx.amount >= 1000 and tx.amount % 1000 == 0))
        return round_count / len(transactions)

    @staticmethod
    def detect_structuring_signals(transactions: List[BankTransaction]) -> Dict[str, Any]:
        """
        Checks for structuring patterns: repetitive amounts just under reporting or verification thresholds.
        Optimized single-pass scan.
        """
        sub_50k_count = 0
        sub_2m_count = 0
        micro_deposits = 0
        for tx in transactions:
            amt = tx.amount
            if 40000 <= amt < 50000:
                sub_50k_count += 1
            elif 1900000 <= amt < 2000000:
                sub_2m_count += 1
            if amt < 1000 and tx.activity == ActivityType.INFLOW:
                micro_deposits += 1

        return {
            "sub_50k_count": sub_50k_count,
            "sub_2m_count": sub_2m_count,
            "micro_deposits_count": micro_deposits,
            "has_structuring_risk": (sub_50k_count >= 2 or sub_2m_count >= 1 or micro_deposits >= 5),
        }


class SuspicionScoringEngine:
    """
    Evaluates multi-dimensional risk signals into a composite Suspicion Score (0-100).
    Adheres strictly to Section 226 Corroboration-Gated Neutrality standards.
    """

    def __init__(
        self,
        w_amount: float = 0.25,
        w_time: float = 0.30,
        w_balance: float = 0.25,
        w_network: float = 0.20,
    ):
        self.w_amount = w_amount
        self.w_time = w_time
        self.w_balance = w_balance
        self.w_network = w_network

    def score(
        self,
        transactions: List[BankTransaction],
        cfr_hit_count: int = 0,
        is_circular: bool = False,
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculates composite suspicion score and returns (score, level, breakdown).
        Optimized single-pass partitioning.
        """
        inflows = []
        outflows = []
        unique_out_recipients = set()
        total_in = 0.0
        total_out = 0.0
        sub_50k_count = 0
        sub_2m_count = 0
        micro_deposits = 0
        round_count = 0
        pure_out_count = 0

        for tx in transactions:
            amt = tx.amount
            if 40000 <= amt < 50000:
                sub_50k_count += 1
            elif 1900000 <= amt < 2000000:
                sub_2m_count += 1

            if not tx.is_reversal:
                act = tx.activity
                if act == ActivityType.INFLOW:
                    inflows.append(tx)
                    total_in += amt
                    if amt < 1000:
                        micro_deposits += 1
                elif act in (ActivityType.OUTFLOW, ActivityType.FEE):
                    outflows.append(tx)
                    total_out += amt
                    if act == ActivityType.OUTFLOW:
                        pure_out_count += 1
                        if amt >= 1000 and amt % 1000 == 0:
                            round_count += 1
                        if tx.counterparty_account:
                            unique_out_recipients.add(tx.counterparty_account)

        final_bal = transactions[-1].balance if transactions else 0.0

        # 1. S_time: Residence latency factor (0 - 100)
        latencies = ForensicBehavioralSignals.calculate_residence_latencies(inflows, outflows)
        avg_latency = float(np.mean(latencies)) if latencies else 999.0
        if avg_latency <= 15.0:
            s_time = 100.0  # Critical rapid drain
        elif avg_latency <= 60.0:
            s_time = 80.0
        elif avg_latency <= 120.0:
            s_time = 60.0
        elif avg_latency <= 360.0:
            s_time = 30.0
        else:
            s_time = 10.0

        # 2. S_balance: Drain rate factor (0 - 100)
        drain_pct = ForensicBehavioralSignals.calculate_drain_rate(total_in, total_out, final_bal)
        if drain_pct >= 99.0:
            s_balance = 100.0
        elif drain_pct >= 95.0:
            s_balance = 85.0
        elif drain_pct >= 80.0:
            s_balance = 50.0
        else:
            s_balance = 20.0

        # 3. S_amount: Structuring and round number anomaly (0 - 100)
        has_structuring = (sub_50k_count >= 2 or sub_2m_count >= 1 or micro_deposits >= 5)
        structuring = {
            "sub_50k_count": sub_50k_count,
            "sub_2m_count": sub_2m_count,
            "micro_deposits_count": micro_deposits,
            "has_structuring_risk": has_structuring,
        }
        round_ratio = (round_count / pure_out_count) if pure_out_count > 0 else 0.0
        s_amount = 0.0
        if has_structuring:
            s_amount += 50.0
        if round_ratio >= 0.5:
            s_amount += 50.0
        else:
            s_amount += round_ratio * 60.0
        s_amount = min(100.0, s_amount)

        # 4. S_network: Blacklist hits and cycle detection (0 - 100)
        s_network = 0.0
        if cfr_hit_count > 0:
            s_network += 60.0
        if is_circular:
            s_network += 40.0
        # If large counterparty concentration
        if 1 <= len(unique_out_recipients) <= 5 and total_out > 100000:
            s_network += 30.0
        s_network = min(100.0, s_network)

        # Composite Weighted Score
        total_score = (
            (self.w_amount * s_amount)
            + (self.w_time * s_time)
            + (self.w_balance * s_balance)
            + (self.w_network * s_network)
        )
        total_score = round(min(100.0, max(0.0, total_score)), 1)

        # Neutrality classification
        if total_score >= 85.0:
            level = "HIGH SUSPICION / REQUIRES REVIEW"
        elif total_score >= 65.0:
            level = "HIGH"
        elif total_score >= 40.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        breakdown = {
            "total_inflow": total_in,
            "total_outflow": total_out,
            "final_balance": final_bal,
            "drain_percentage": round(drain_pct, 2),
            "avg_latency_minutes": round(avg_latency, 1),
            "s_amount": round(s_amount, 1),
            "s_time": round(s_time, 1),
            "s_balance": round(s_balance, 1),
            "s_network": round(s_network, 1),
            "structuring_signals": structuring,
        }

        return total_score, level, breakdown
