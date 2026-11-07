"""
Flow match cluster models and mathematical attribution data structures.
"""

from __future__ import annotations
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class TaintedFundFlow(BaseModel):
    """Represents tainted fund propagation from inflow to outflow."""
    model_config = ConfigDict(frozen=True)

    inflow_tx_id: str
    outflow_tx_id: str
    allocated_amount: float = Field(gt=0.0)
    taint_ratio: float = Field(ge=0.0, le=1.0)
    latency_minutes: float = Field(ge=0.0)


class FlowMatchCluster(BaseModel):
    """
    Mathematical cluster of matched inflows and outflows (M-to-N Flow Matching).
    Derived from scipy.optimize.milp or sliding window attribution.
    """
    model_config = ConfigDict(frozen=False, extra="ignore")

    cluster_id: str = Field(description="Unique cluster identifier")
    inflow_tx_ids: List[str] = Field(default_factory=list, description="IDs of inflow transactions in this cluster")
    inflow_total: float = Field(default=0.0, description="Sum of matched inflows")
    outflow_tx_ids: List[str] = Field(default_factory=list, description="IDs of matched outflow transactions")
    outflow_total: float = Field(default=0.0, description="Sum of matched outflows")
    fee_total: float = Field(default=0.0, description="Sum of banking fees incurred")
    residual_balance: float = Field(default=0.0, description="Remaining funds trapped or retained in account")
    avg_latency_minutes: float = Field(default=0.0, description="Average transit residence time in minutes")
    drain_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Drain percentage ((outflow+fees)/inflow * 100)")
    is_circular: bool = Field(default=False, description="Flag indicating circular washing cycle (A -> B -> C -> A)")
    circular_cycle_path: Optional[List[str]] = Field(default=None, description="Sequence of account nodes in cycle")
    mathematical_proof: str = Field(default="", description="Linear algebraic constraint representation (A * x = b +/- eps)")
