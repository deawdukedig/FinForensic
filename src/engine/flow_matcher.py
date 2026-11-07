"""
Flow Matching Engine utilizing Mathematical Optimization (MILP via scipy.optimize.milp).
Solves M-to-N transaction matching with temporal penalties, fee-buffer tolerance,
and 5.0-second timeout fallback.
"""

from __future__ import annotations
import time
from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from src.models.transaction import BankTransaction, ActivityType
from src.models.cluster import FlowMatchCluster, TaintedFundFlow


class FlowMatchingEngine:
    """
    Mathematical solver for tracing fund dispersal and structuring.
    Computes optimal subset of outflows matching an inbound fund pool.
    """

    def __init__(
        self,
        time_limit_sec: float = 5.0,
        tolerance_ratio: float = 0.05,
        mip_rel_gap: float = 0.005,
    ):
        self.time_limit = time_limit_sec
        self.tolerance_ratio = tolerance_ratio  # Default 5% tolerance for residual buffer
        self.mip_rel_gap = mip_rel_gap

    def solve_cluster(
        self,
        cluster_id: str,
        inflows: List[BankTransaction],
        candidate_outflows: List[BankTransaction],
        tolerance_amt: Optional[float] = None,
    ) -> FlowMatchCluster:
        """
        Solves the subset sum matching problem using Mixed-Integer Linear Programming.
        """
        inflow_total = sum(tx.amount for tx in inflows)
        inflow_tx_ids = [tx.tx_id for tx in inflows]

        if not candidate_outflows or inflow_total <= 0:
            return FlowMatchCluster(
                cluster_id=cluster_id,
                inflow_tx_ids=inflow_tx_ids,
                inflow_total=inflow_total,
                outflow_tx_ids=[],
                outflow_total=0.0,
                fee_total=0.0,
                residual_balance=inflow_total,
                avg_latency_minutes=0.0,
                drain_percentage=0.0,
                mathematical_proof=f"No outflows available to match against inflow ฿{inflow_total:,.2f}",
            )

        tol = tolerance_amt if tolerance_amt is not None else (inflow_total * self.tolerance_ratio)
        max_bound = inflow_total + tol

        # Pre-filter candidate outflows exceeding max_bound (cannot be part of any subset <= max_bound)
        filtered_candidates = [tx for tx in candidate_outflows if tx.amount <= max_bound]
        candidates = filtered_candidates if filtered_candidates else candidate_outflows

        n = len(candidates)
        amounts = np.array([tx.amount for tx in candidates], dtype=np.float64)

        # Calculate temporal weights (penalize longer residence time slightly to prefer rapid drain)
        base_time = min(tx.timestamp for tx in inflows)
        latencies_min = np.array([
            max(0.0, (tx.timestamp - base_time).total_seconds() / 60.0)
            for tx in candidates
        ], dtype=np.float64)

        # Normalized objective coefficients:
        # We want to maximize total matched amount while keeping latency small
        # In MILP minimize c^T z:
        # c_i = -amount_i + (0.01 * latency_i)
        c = -amounts + (0.001 * latencies_min)

        # Constraint 1: sum(amount_i * z_i) <= max_bound
        # Constraint 2: sum(amount_i * z_i) >= 0
        A = amounts.reshape(1, n)
        constraints = LinearConstraint(A, lb=0.0, ub=max_bound)

        # Binary bounds: z_i in {0, 1}
        integrality = np.ones(n, dtype=int)  # 1 indicates integer/binary
        bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))

        solver_opts = {"time_limit": self.time_limit}
        if self.mip_rel_gap is not None:
            solver_opts["mip_rel_gap"] = self.mip_rel_gap

        start_time = time.time()
        res = milp(
            c=c,
            integrality=integrality,
            bounds=bounds,
            constraints=constraints,
            options=solver_opts,
        )
        elapsed = time.time() - start_time

        selected_indices: List[int] = []
        solver_status = "UNKNOWN"

        if res.success and res.x is not None:
            # Optimal or feasible solution within time limit
            selected_indices = [i for i, val in enumerate(res.x) if val > 0.5]
            solver_status = f"OPTIMAL (Solved in {elapsed:.3f}s via scipy.optimize.milp)"
        else:
            # Fallback to greedy subset sum if solver timed out or infeasible
            selected_indices = self._fallback_greedy(amounts, max_bound)
            solver_status = f"FALLBACK_GREEDY (Timeout/Infeasible after {elapsed:.3f}s)"

        matched_txs = [candidates[i] for i in selected_indices]
        matched_outflow_txs = [tx for tx in matched_txs if tx.activity == ActivityType.OUTFLOW]
        matched_fee_txs = [tx for tx in matched_txs if tx.activity == ActivityType.FEE]

        outflow_sum = sum(tx.amount for tx in matched_outflow_txs)
        fee_sum = sum(tx.amount for tx in matched_fee_txs)
        total_dispersed = outflow_sum + fee_sum
        residual = max(0.0, inflow_total - total_dispersed)
        drain_pct = min(100.0, (total_dispersed / inflow_total) * 100.0) if inflow_total > 0 else 0.0

        avg_lat = float(np.mean([latencies_min[i] for i in selected_indices])) if selected_indices else 0.0

        # Construct deterministic mathematical proof string
        terms = [f"{tx.amount:,.2f}" for tx in matched_txs]
        terms_str = " + ".join(terms) if terms else "0.00"
        proof_eq = f"{terms_str} = {total_dispersed:,.2f} <= {inflow_total:,.2f} (Residual: ฿{residual:,.2f}) [{solver_status}]"

        return FlowMatchCluster(
            cluster_id=cluster_id,
            inflow_tx_ids=inflow_tx_ids,
            inflow_total=inflow_total,
            outflow_tx_ids=[tx.tx_id for tx in matched_txs],
            outflow_total=outflow_sum,
            fee_total=fee_sum,
            residual_balance=residual,
            avg_latency_minutes=avg_lat,
            drain_percentage=drain_pct,
            mathematical_proof=proof_eq,
        )

    def solve_clusters_parallel(
        self,
        cluster_specs: List[Tuple[str, List[BankTransaction], List[BankTransaction], Optional[float]]],
        max_workers: Optional[int] = None,
    ) -> List[FlowMatchCluster]:
        """
        Solves multiple flow matching clusters concurrently using ThreadPoolExecutor.
        Preserves original cluster ordering.

        Args:
            cluster_specs: List of (cluster_id, inflows, candidate_outflows, tolerance_amt) tuples.
            max_workers: Maximum number of worker threads (default: min(len(specs), 6)).
        """
        if not cluster_specs:
            return []

        if len(cluster_specs) == 1:
            cid, infs, cands, tol = cluster_specs[0]
            return [self.solve_cluster(cid, infs, cands, tol)]

        from concurrent.futures import ThreadPoolExecutor

        def _worker(item: Tuple[int, Tuple[str, List[BankTransaction], List[BankTransaction], Optional[float]]]) -> Tuple[int, FlowMatchCluster]:
            idx, (cid, infs, cands, tol) = item
            return idx, self.solve_cluster(cid, infs, cands, tol)

        workers = min(len(cluster_specs), max_workers or 6)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_worker, enumerate(cluster_specs)))

        results.sort(key=lambda x: x[0])
        return [res for _, res in results]

    def _fallback_greedy(self, amounts: np.ndarray, max_bound: float) -> List[int]:
        """Greedy approximation fallback if MILP solver exceeds time limit."""
        sorted_indices = np.argsort(-amounts)
        chosen: List[int] = []
        current_sum = 0.0
        for idx in sorted_indices:
            val = float(amounts[idx])
            if current_sum + val <= max_bound:
                chosen.append(int(idx))
                current_sum += val
        return sorted(chosen)
