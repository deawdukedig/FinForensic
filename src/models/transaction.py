"""
Banking transaction data models conforming to Pydantic v2.
Defines ActivityType and BankTransaction with strict validation.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ActivityType(str, Enum):
    """Transaction activity classifications."""
    INFLOW = "XD"
    OUTFLOW = "XW"
    FEE = "FE"
    REVERSAL = "REV"


class BankTransaction(BaseModel):
    """
    Core banking transaction record adhering to Forensic Architecture Section 8.
    """
    model_config = ConfigDict(frozen=False, extra="ignore")

    tx_id: str = Field(description="Unique identifier for the transaction record")
    account_no: str = Field(description="Target investigated account number")
    account_name: str = Field(description="Account holder or company name")
    timestamp: datetime = Field(description="Transaction date and time")
    activity: ActivityType = Field(description="XD (Deposit/Inflow), XW (Withdrawal/Outflow), FE (Fee), REV (Reversal)")
    channel: str = Field(default="", description="Transaction channel: ENET, BCMS, ATM, CDM, etc.")
    amount: float = Field(gt=0.0, description="Transaction monetary amount (must be > 0)")
    balance: float = Field(ge=0.0, description="Remaining balance after transaction")
    description: str = Field(default="", description="Raw transaction narrative or note")
    counterparty_bank: Optional[str] = Field(default=None, description="Extracted counterparty bank code (e.g. KBANK, SCB)")
    counterparty_account: Optional[str] = Field(default=None, description="Extracted counterparty masked or raw account")
    counterparty_name: Optional[str] = Field(default=None, description="Extracted counterparty individual or business name")
    is_reversal: bool = Field(default=False, description="Whether this transaction has been identified as a reversal/chargeback")
    reversal_ref_id: Optional[str] = Field(default=None, description="Reference tx_id of the negated transaction")
    cfr_blacklist_hit: bool = Field(default=False, description="Flagged against AOC/CFR Central Fraud Registry blacklist")
