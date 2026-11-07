"""
Audit record, forensic assessment report, and court dossier data contracts.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.models.cluster import FlowMatchCluster


class MerkleAuditRecord(BaseModel):
    """Immutable audit log record for Chain of Custody (พ.ร.บ.ธุรกรรมอิเล็กทรอนิกส์ มาตรา 26)."""
    model_config = ConfigDict(frozen=True)

    record_id: str = Field(description="Unique record hash or sequential ID")
    case_id: str = Field(description="Associated police or agency case number")
    officer_id: str = Field(description="Investigating officer identifier")
    action_type: str = Field(description="INGEST, SOLVE, PIN, EXCLUDE, EXPORT")
    timestamp: datetime = Field(description="Audit timestamp in UTC/ICT")
    previous_hash: str = Field(description="Cryptographic hash of the parent node")
    current_hash: str = Field(description="SHA-256 hash representing current state")
    signature: Optional[str] = Field(default=None, description="Cryptographic digital signature or HMAC")


class SuspicionReport(BaseModel):
    """
    Forensic evaluation report combining multi-dimensional behavioral,
    flow matching, and graph scoring. Strictly maintains Corroboration-Gated Neutrality.
    """
    model_config = ConfigDict(frozen=False, extra="ignore")

    case_id: str = Field(description="Case reference identifier")
    account_no_masked: str = Field(description="PDPA-masked account number (e.g. 9012xxxx78)")
    account_no_raw: str = Field(description="Unmasked account number (restricted to authorized officer)")
    account_name: str = Field(description="Investigated account or legal entity name")
    statement_hash_sha256: str = Field(description="SHA-256 hash of original ingested statement")
    overall_suspicion_score: float = Field(ge=0.0, le=100.0, description="Composite score (0-100)")
    suspicion_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL / HIGH SUSPICION REQUIRES REVIEW")
    clusters_detected: List[FlowMatchCluster] = Field(default_factory=list, description="Identified flow clusters")
    top_counterparties: Dict[str, float] = Field(default_factory=dict, description="Primary counterparties by volume")
    cfr_hits: List[Dict[str, Any]] = Field(default_factory=list, description="Matches against AOC 1441 / CFR Blacklist")
    merkle_root: str = Field(default="", description="Root hash of evidence audit vault")
    admissibility_receipt: Dict[str, str] = Field(default_factory=dict, description="Legal admissibility receipts under Section 226")
