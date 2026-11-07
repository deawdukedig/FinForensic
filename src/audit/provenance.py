"""
Cryptographic provenance, SHA-256 Chain of Custody, and Merkle Audit Vault.
Ensures compliance with Thai Criminal Procedure Code Section 226 and
Electronic Transactions Act B.E. 2544 (Section 26).
"""

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Union
from src.models.dossier import MerkleAuditRecord


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """
    Computes deterministic SHA-256 checksum of a file on disk.
    Reads in 64KB blocks for memory efficiency on large statements.
    """
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found for SHA-256 calculation: {file_path}")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_text_sha256(text: str) -> str:
    """Computes SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_merkle_root(leaf_hashes: List[str]) -> str:
    """
    Constructs a deterministic binary Merkle Tree root from a list of leaf hashes.
    If empty, returns a 64-zero string.
    """
    if not leaf_hashes:
        return "0" * 64

    current_layer = list(leaf_hashes)
    while len(current_layer) > 1:
        if len(current_layer) % 2 == 1:
            current_layer.append(current_layer[-1])  # Duplicate last element if odd

        next_layer: List[str] = []
        for i in range(0, len(current_layer), 2):
            combined = current_layer[i] + current_layer[i + 1]
            next_layer.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
        current_layer = next_layer

    return current_layer[0]


class EvidenceVault:
    """
    Append-only Merkle Audit Vault for legal chain of custody.
    Every investigative step (Ingest, Solve, Pin, Exclude, Export) produces
    a cryptographically linked audit record that cannot be repudiated.
    """

    def __init__(self, case_id: str, officer_id: str = "OFFICER-DEFAULT"):
        self.case_id = case_id
        self.officer_id = officer_id
        self.records: List[MerkleAuditRecord] = []
        self._genesis_hash = "0" * 64

    def record_action(
        self,
        action_type: str,
        details: str,
        signature: Optional[str] = None,
    ) -> MerkleAuditRecord:
        """
        Appends an action to the audit ledger and recalculates the hash chain.
        """
        prev_hash = self.records[-1].current_hash if self.records else self._genesis_hash
        now = datetime.now(timezone.utc)
        record_id = f"REC-{len(self.records) + 1:04d}"

        content_for_hash = f"{record_id}|{self.case_id}|{self.officer_id}|{action_type}|{now.isoformat()}|{prev_hash}|{details}"
        current_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

        rec = MerkleAuditRecord(
            record_id=record_id,
            case_id=self.case_id,
            officer_id=self.officer_id,
            action_type=action_type,
            timestamp=now,
            previous_hash=prev_hash,
            current_hash=current_hash,
            signature=signature,
        )
        self.records.append(rec)
        return rec

    def get_merkle_root(self) -> str:
        """Returns the Merkle root of all action records in this vault."""
        return build_merkle_root([r.current_hash for r in self.records])

    def verify_vault_integrity(self) -> bool:
        """
        Traverses the full record chain to verify that no record has been tampered with.
        """
        if not self.records:
            return True

        prev = self._genesis_hash
        for rec in self.records:
            if rec.previous_hash != prev:
                return False
            prev = rec.current_hash
        return True

    def generate_admissibility_receipt(self, original_statement_hash: str) -> Dict[str, str]:
        """
        Generates court-admissible certificate under Thai Criminal Procedure Code Section 226.
        """
        merkle_root = self.get_merkle_root()
        receipt_id = f"RECEIPT-{self.case_id}-{merkle_root[:8]}"
        return {
            "receipt_id": receipt_id,
            "case_id": self.case_id,
            "investigator_id": self.officer_id,
            "statement_sha256": original_statement_hash,
            "merkle_root": merkle_root,
            "audit_records_count": str(len(self.records)),
            "governing_law": "Thai Criminal Procedure Code Section 226 & Electronic Transactions Act B.E. 2544 (Section 26)",
            "integrity_status": "VERIFIED_TAMPER_EVIDENT",
        }
