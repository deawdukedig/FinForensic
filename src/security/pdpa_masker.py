"""
PDPA (Personal Data Protection Act B.E. 2562) Data Masking Module.
Protects Personally Identifiable Information (PII) including bank account numbers,
national identity numbers, phone numbers, and individual names.
"""

from __future__ import annotations
import re
from typing import Optional


class PDPAMasker:
    """
    Masks sensitive financial and personal identifiers to ensure compliance
    with Thai PDPA regulations during triage and cross-agency sharing.
    """

    @staticmethod
    def mask_account(account_no: Optional[str], show_first: int = 4, show_last: int = 2) -> str:
        """
        Masks bank account number: 9012345678 -> 9012xxxx78
        """
        if not account_no:
            return "N/A"
        clean = account_no.replace("-", "").strip()
        if len(clean) <= (show_first + show_last):
            return clean[:show_first] + "****"

        masked_len = len(clean) - (show_first + show_last)
        return clean[:show_first] + ("x" * masked_len) + clean[-show_last:]

    @staticmethod
    def mask_citizen_id(id_card: Optional[str]) -> str:
        """
        Masks Thai 13-digit National ID: 1100501234567 -> 1-xxxx-xxxxx-67
        """
        if not id_card:
            return "N/A"
        clean = re.sub(r"\D", "", id_card)
        if len(clean) != 13:
            return id_card[:2] + "****" + id_card[-2:] if len(id_card) >= 4 else "****"

        return f"{clean[0]}-xxxx-xxxxx-{clean[-2:]}"

    @staticmethod
    def mask_phone(phone: Optional[str]) -> str:
        """
        Masks telephone / PromptPay number: 0891234567 -> 089-xxx-4567
        """
        if not phone:
            return "N/A"
        clean = re.sub(r"\D", "", phone)
        if len(clean) == 10:
            return f"{clean[:3]}-xxx-{clean[-4:]}"
        elif len(clean) == 9:
            return f"{clean[:2]}-xxx-{clean[-4:]}"
        return phone[:3] + "****"

    @staticmethod
    def mask_name(full_name: Optional[str]) -> str:
        """
        Partially masks individual names for public or cross-agency triage.
        Example: 'นาย ธีรภัทร บุญเสริม' -> 'นาย ธี***ร บุ***ม'
        """
        if not full_name:
            return "Unknown Entity"

        tokens = full_name.strip().split()
        masked_tokens = []
        for tok in tokens:
            if len(tok) <= 2:
                masked_tokens.append(tok)
            elif len(tok) <= 4:
                masked_tokens.append(tok[0] + "*" * (len(tok) - 1))
            else:
                masked_tokens.append(tok[:2] + "*" * (len(tok) - 4) + tok[-2:])

        return " ".join(masked_tokens)
