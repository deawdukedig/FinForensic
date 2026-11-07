"""
Entity extraction and counterparty parsing module.
Extracts bank codes, account identifiers, personal titles, and names from transaction descriptions.
"""

from __future__ import annotations
import re
from functools import lru_cache
from typing import Dict, Optional, Tuple, Set


# Standard Thai Bank Codes recognized in Statements and Clearing Systems
THAI_BANKS = {
    "KBANK", "SCB", "KTB", "BBL", "GSB", "TTB", "BAY", "KK", "CIMB",
    "TISCO", "UOB", "BAAC", "GHB", "EXIM", "PROMPTPAY", "พร้อมเพย์"
}

# Thai Military and Civil Titles
TITLES = [
    "จ่าสิบตรี", "จ่าสิบโท", "จ่าสิบเอก", "ร้อยตรี", "ร้อยโท", "ร้อยเอก",
    "พันตรี", "พันโท", "พันเอก", "พลตรี", "พลโท", "พลเอก",
    "นายดาบตำรวจ", "สิบตำรวจตรี", "สิบตำรวจโท", "สิบตำรวจเอก",
    "ร้อยตำรวจตรี", "ร้อยตำรวจโท", "ร้อยตำรวจเอก",
    "นาย", "นาง", "นางสาว", "น.ส.", "MR.", "MRS.", "MS.", "MISS", "MR", "MRS", "MS"
]

# Non-human, merchant, corporate, or operational channel keywords (Not individual persons)
NON_HUMAN_KEYWORDS = {
    "counter", "fresh", "shop", "store", "market", "mart", "otc", "dispenser",
    "atm", "cash", "bank", "vault", "branch", "tier", "mule", "consolidation",
    "company", "service", "trading", "enterprises", "corporation",
    "บริษัท", "หจก", "จำกัด", "co.", "ltd", "corp", "inc"
}


class EntityExtractor:
    """
    Parses unstructured Thai banking narrative descriptions into structured
    counterparty metadata (Bank, Account, Name, Title, Entity Type).
    """

    # Regex patterns for statement narratives
    # Example: "รับโอนจาก KTB x1005 MRS.SOMSRI THAISONG"
    # Example: "โอนไป BBL x8001 MR.SOKHA CHAN"
    # Example: "โอนไปพร้อมเพย์ x8003 นางสาว กมลพร วงศ์สุวรรณ"
    # Example: "ค่าธรรมเนียมโอนไป BBL x8001 MR.SOKHA CH"
    
    PATTERN_TRANSFER = re.compile(
        r"(?:รับโอนจาก|โอนไป|ค่าธรรมเนียมโอนไป|ค่าธรรมเนียมพร้อมเพย์|โอนไปพร้อมเพย์)\s*([A-Za-zก-๙]+)?\s*(x\d+|\d+)?\s*(.+)?",
        re.IGNORECASE
    )

    @classmethod
    def parse_description(cls, desc: str) -> Dict[str, Optional[str]]:
        """
        Extracts counterparty bank, account, and name from a transaction narrative.
        """
        if not desc or not desc.strip():
            return {"counterparty_bank": None, "counterparty_account": None, "counterparty_name": None}
        bank, acct, name = cls._parse_description_cached(desc.strip())
        return {
            "counterparty_bank": bank,
            "counterparty_account": acct,
            "counterparty_name": name,
        }

    @staticmethod
    @lru_cache(maxsize=4096)
    def _parse_description_cached(clean_desc: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        bank: Optional[str] = None
        acct: Optional[str] = None
        name: Optional[str] = None

        # Check for PromptPay keyword
        if "พร้อมเพย์" in clean_desc or "PROMPTPAY" in clean_desc.upper():
            bank = "PROMPTPAY"

        # Check for known Thai banks
        for b in THAI_BANKS:
            if re.search(rf"\b{b}\b", clean_desc, re.IGNORECASE):
                bank = b.upper() if b != "พร้อมเพย์" else "PROMPTPAY"
                break

        # Check for account pattern (e.g. x1001, x8004, or 10-12 digits)
        acct_match = re.search(r"\b(x\d{3,6}|\d{10,15})\b", clean_desc)
        if acct_match:
            acct = acct_match.group(1)

        # Extract name part by stripping transfer prefix, bank, and account
        name_candidate = clean_desc
        # Strip common prefixes
        for prefix in ["ค่าธรรมเนียมโอนไป", "ค่าธรรมเนียมพร้อมเพย์", "รับโอนจาก", "โอนไปพร้อมเพย์", "โอนไป"]:
            if name_candidate.startswith(prefix):
                name_candidate = name_candidate[len(prefix):].strip()
                break

        # Remove bank and acct from name candidate if found
        if bank and bank != "PROMPTPAY":
            name_candidate = re.sub(rf"\b{bank}\b", "", name_candidate, flags=re.IGNORECASE).strip()
        elif bank == "PROMPTPAY":
            name_candidate = re.sub(r"(?:พร้อมเพย์|PROMPTPAY)", "", name_candidate, flags=re.IGNORECASE).strip()

        if acct:
            name_candidate = name_candidate.replace(acct, "").strip()

        name_candidate = re.sub(r"\s+", " ", name_candidate).strip()
        if name_candidate:
            name = name_candidate

        return bank, acct, name

    @staticmethod
    @lru_cache(maxsize=4096)
    def extract_surname(full_name: Optional[str]) -> Optional[str]:
        """
        Extracts surname for Thai names to detect familial networks / entity resolution.
        Strips parentheticals, excludes non-human/corporate entities, and caches lookups.
        """
        if not full_name:
            return None

        # Strip parentheticals and bracketed notes
        cleaned = re.sub(r"\(.*?\)", "", full_name).strip()
        cleaned = re.sub(r"\[.*?\]", "", cleaned).strip()

        lower_name = cleaned.lower()
        if any(kw in lower_name for kw in NON_HUMAN_KEYWORDS):
            return None

        # Strip titles
        for title in TITLES:
            if cleaned.startswith(title):
                cleaned = cleaned[len(title):].strip()
                break

        tokens = cleaned.split()
        if len(tokens) >= 2:
            candidate = tokens[-1].strip()
            if candidate and len(candidate) >= 2 and candidate.lower() not in NON_HUMAN_KEYWORDS:
                return candidate
        return None
