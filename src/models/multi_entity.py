"""
Data models for Multi-Entity Graph & Money Trail Suite.
Implements strict Pydantic v2 schemas for KYC Entities, Directed Transaction Edges,
and 5-Hop Syndicate Network Graphs.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class EntityRole(str, Enum):
    VICTIM = "Victim"
    MULE_TIER_1 = "Mule Tier-1 (Gate Mule)"
    MULE_TIER_2 = "Mule Tier-2 (Layering Hub)"
    MULE_TIER_3 = "Mule Tier-3 (Consolidation)"
    CASH_RUNNER = "Cash Runner (ATM Dispenser)"
    CRYPTO_BROKER = "Crypto OTC Broker (Off-Ramp)"
    SYNDICATE_TREASURY = "Syndicate Treasury (Offshore Vault)"
    UNKNOWN = "Unknown"


class HopLevel(str, Enum):
    HOP_1 = "Hop-1 (Injection)"
    HOP_2 = "Hop-2 (Layering Hub)"
    HOP_3 = "Hop-3 (Consolidation)"
    HOP_4 = "Hop-4 (ATM Cash-Out)"
    HOP_5 = "Hop-5 (Crypto Off-Ramp)"
    DIRECT = "Direct"


class EntityKYC(BaseModel):
    """KYC and demographic profile of a person or legal entity."""
    model_config = ConfigDict(frozen=False, extra="ignore")

    entity_id: str
    entity_name: str
    role: str
    risk_category: str = "Medium"
    kyc_status: str = "Verified"
    declared_income: float = Field(default=0.0, ge=0.0)
    flagged_aml: bool = False
    actual_inflow_volume: float = 0.0
    actual_outflow_volume: float = 0.0


class TransactionEdge(BaseModel):
    """Directed financial transaction edge between accounts and entities."""
    model_config = ConfigDict(frozen=False, extra="ignore")

    trace_id: str
    case_id: str
    timestamp: datetime
    hop_level: str
    source_account: str
    source_entity: str
    target_account: str
    target_entity: str
    amount_thb: float = Field(gt=0.0)
    channel: str = "Mobile Banking"
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    geolocation: Optional[str] = None
    forensic_rule_triggered: Optional[str] = None
    ai_anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    investigation_status: str = "Active"


class MultiEntityNetworkSummary(BaseModel):
    """Summary of multi-entity network flow analysis."""
    case_id: str
    total_entities: int
    total_transactions: int
    total_flow_volume_thb: float
    hop_volumes: Dict[str, float]
    top_gateways: List[Dict[str, Any]]
    device_clusters: Dict[str, List[str]]
    geolocation_anomalies: List[Dict[str, Any]]
    kingpin_entities: List[str]
