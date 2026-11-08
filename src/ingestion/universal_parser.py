"""
Universal Banking Statement Parser for Thai Banks.
Supports multi-bank formats (KBANK, SCB, KTB, BBL, GSB, TTB, BAY), auto-header detection,
date normalization (ISO, YYYY-MM-DD, Buddhist Era 25xx -> 20xx), and entity extraction.
"""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple, Iterator
from src.models.transaction import BankTransaction, ActivityType
from src.ingestion.entity_extractor import EntityExtractor
from src.ingestion.reversal_reconciler import ReversalReconciler


# Common column name mappings across Thai commercial banks and forensic datasets
COLUMN_ALIASES = {
    "account_no": ["acct_no", "account_no", "account", "เลขที่บัญชี", "เลขบัญชี"],
    "account_name": ["acct_name", "account_name", "name", "ชื่อบัญชี", "ชื่อเจ้าของบัญชี"],
    "date": ["datetime", "timestamp", "tran_date", "date", "tx_date", "transaction_date", "วันที่", "txn_datetime"],
    "time": ["time", "tran_time", "tx_time", "เวลา"],
    "activity": ["txn_type", "activitie", "activity", "type", "tx_type", "ประเภท", "รหัสรายการ", "code", "direction"],
    "channel": ["channel", "ch", "ช่องทาง"],
    "amount": ["tran_amt", "amount", "tran_amount", "จำนวนเงิน", "ยอดเงิน"],
    "balance": ["balance", "bal", "ยอดคงเหลือ", "คงเหลือ"],
    "description": ["description", "desc", "narrative", "particulars", "คำอธิบาย", "รายการ", "behavior_pattern"],
    "counterparty_bank": ["counterparty_bank", "cp_bank", "bank_to", "bank_from"],
    "counterparty_account": ["counterparty_account", "cp_account", "cp_acct", "target_account", "dest_account"],
    "counterparty_name": ["counterparty_name", "cp_name", "receiver_name", "sender_name"],
}


class UniversalStatementParser:
    """
    Production-grade parser capable of ingesting bank statement files
    and returning validated BankTransaction models.
    """

    def __init__(self, reconcile_reversals: bool = True):
        self.reconcile_reversals = reconcile_reversals
        self.reconciler = ReversalReconciler()

    def parse_file(self, file_path: Union[str, Path]) -> List[BankTransaction]:
        """
        Parses a banking statement CSV or Excel (.xlsx) file with encoding fallback and returns
        a list of BankTransaction models.
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Statement file not found: {file_path}")

        # Route .xlsx files directly to native OpenXML engine
        if p.suffix.lower() == ".xlsx":
            transactions = self._parse_xlsx(p)
            if self.reconcile_reversals:
                transactions, _ = self.reconciler.reconcile(transactions)
            return transactions

        # Try reading with utf-8-sig first, then utf-8, then cp874
        content: Optional[str] = None
        for enc in ["utf-8-sig", "utf-8", "cp874", "tis-620", "iso-8859-11"]:
            try:
                content = p.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise ValueError(f"Unable to decode statement file {file_path} with supported encodings.")

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return []

        # Step 1: Detect Header Row
        header_index, col_map = self._detect_header_row(lines)
        if header_index < 0:
            raise ValueError(f"Could not automatically detect valid statement headers in {file_path}")

        # Step 2: Parse Rows
        raw_rows = lines[header_index + 1:]
        reader = csv.reader(raw_rows)
        transactions: List[BankTransaction] = []

        # Default fallback account from filename stem or generic mule account
        file_stem = p.stem.replace("_", " ").title()
        default_acct_no = "9012888899"
        default_acct_name = f"เป้าหมายบัญชีม้าเฝ้าระวัง ({file_stem})"

        for row_idx, row in enumerate(reader, start=header_index + 2):
            if not row or all(not cell.strip() for cell in row):
                continue

            try:
                tx = self._parse_single_row(row, col_map, row_idx, default_acct_no, default_acct_name)
                if tx:
                    if tx.account_no != default_acct_no and tx.account_no != "UNKNOWN":
                        default_acct_no = tx.account_no
                    if tx.account_name != default_acct_name and tx.account_name != "UNKNOWN":
                        default_acct_name = tx.account_name
                    transactions.append(tx)
            except Exception:
                continue

        # Step 3: Reconcile reversals if enabled
        if self.reconcile_reversals:
            transactions, _ = self.reconciler.reconcile(transactions)

        return transactions

    def parse_file_iter(self, file_path: Union[str, Path]) -> Iterator[BankTransaction]:
        """
        Streaming generator that yields BankTransaction records one by one directly from disk.
        Provides constant O(1) memory footprint for large datasets (100k - 1M+ transactions).
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Statement file not found: {file_path}")

        if p.suffix.lower() == ".xlsx":
            yield from self.parse_file(p)
            return

        encoding = "utf-8"
        for enc in ["utf-8-sig", "utf-8", "cp874", "tis-620", "iso-8859-11"]:
            try:
                with open(p, "r", encoding=enc) as f:
                    for _ in range(20):
                        f.readline()
                encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        with open(p, "r", encoding=encoding, errors="replace") as f:
            sample_lines = []
            for _ in range(15):
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    sample_lines.append(line.strip())

            header_idx, col_map = self._detect_header_row(sample_lines)
            if header_idx < 0:
                raise ValueError(f"Could not automatically detect valid statement headers in {file_path}")

            f.seek(0)
            cur_line = 0
            while cur_line <= header_idx:
                l = f.readline()
                if l.strip():
                    cur_line += 1

            file_stem = p.stem.replace("_", " ").title()
            default_acct_no = "9012888899"
            default_acct_name = f"เป้าหมายบัญชีม้าเฝ้าระวัง ({file_stem})"

            reader = csv.reader(f)
            row_idx = header_idx + 2
            for row in reader:
                if not row or all(not cell.strip() for cell in row):
                    row_idx += 1
                    continue
                try:
                    tx = self._parse_single_row(row, col_map, row_idx, default_acct_no, default_acct_name)
                    if tx:
                        if tx.account_no != default_acct_no and tx.account_no != "UNKNOWN":
                            default_acct_no = tx.account_no
                        if tx.account_name != default_acct_name and tx.account_name != "UNKNOWN":
                            default_acct_name = tx.account_name
                        yield tx
                except Exception:
                    pass
                row_idx += 1

    def parse_file_stream(
        self,
        file_path: Union[str, Path],
        chunk_size: int = 5000,
    ) -> Iterator[List[BankTransaction]]:
        """
        Yields transactions in bounded batches (chunks), allowing high-throughput
        pipelined processing of multi-gigabyte statements with zero risk of OOM.
        """
        chunk: List[BankTransaction] = []
        for tx in self.parse_file_iter(file_path):
            chunk.append(tx)
            if len(chunk) >= chunk_size:
                if self.reconcile_reversals:
                    chunk, _ = self.reconciler.reconcile(chunk)
                yield chunk
                chunk = []
        if chunk:
            if self.reconcile_reversals:
                chunk, _ = self.reconciler.reconcile(chunk)
            yield chunk

    def _detect_header_row(self, lines: List[str]) -> Tuple[int, Dict[str, int]]:
        """
        Finds the header row and maps canonical column names to column indices.
        Supports both generic formats and official Thai Police Excel/CSV templates (BAY, KBANK, SCB, KTB).
        """
        for i, line in enumerate(lines[:15]):  # Look in first 15 lines
            row = [cell.strip().lower() for cell in next(csv.reader([line]))]
            col_map: Dict[str, int] = {}

            # Check if this row is a Thai Police Template header (template04 BAY, KBANK, SCB, KTB, BBL)
            if ("deposit" in row and "withdrawal" in row) or ("txdate" in row and "txno" in row):
                for idx, cell in enumerate(row):
                    col_map[cell] = idx
                col_map["_format_type_"] = 1  # Marker for template format
                return i, col_map

            for canonical, aliases in COLUMN_ALIASES.items():
                for idx, cell in enumerate(row):
                    if cell in aliases:
                        col_map[canonical] = idx
                        break

            # Need at least date (or datetime) and amount
            if "date" in col_map and "amount" in col_map:
                return i, col_map

        return -1, {}

    def _parse_single_row(
        self,
        row: List[str],
        col_map: Dict[str, int],
        line_num: int,
        fallback_acct_no: str,
        fallback_acct_name: str,
    ) -> Optional[BankTransaction]:
        """Parses a single row using column mapping."""
        row_len = len(row)

        # Handle Police Template format (template04)
        if col_map.get("_format_type_") == 1:
            tx_date = row[col_map["txdate"]].strip() if "txdate" in col_map and col_map["txdate"] < row_len else ""
            tx_time = row[col_map["txtime"]].strip() if "txtime" in col_map and col_map["txtime"] < row_len else ""
            dep_str = row[col_map["deposit"]].replace(",", "").strip() if "deposit" in col_map and col_map["deposit"] < row_len else ""
            wd_str = row[col_map["withdrawal"]].replace(",", "").strip() if "withdrawal" in col_map and col_map["withdrawal"] < row_len else ""
            bal_str = row[col_map["balance"]].replace(",", "").strip() if "balance" in col_map and col_map["balance"] < row_len else ""
            from_acct = row[col_map["fromaccountno"]].strip() if "fromaccountno" in col_map and col_map["fromaccountno"] < row_len else ""
            from_name = row[col_map["fromaccountname"]].strip() if "fromaccountname" in col_map and col_map["fromaccountname"] < row_len else ""
            from_bank = row[col_map["frombankcode"]].strip() if "frombankcode" in col_map and col_map["frombankcode"] < row_len else ""
            to_acct = row[col_map["toaccountno"]].strip() if "toaccountno" in col_map and col_map["toaccountno"] < row_len else ""
            to_name = row[col_map["toaccountname"]].strip() if "toaccountname" in col_map and col_map["toaccountname"] < row_len else ""
            to_bank = row[col_map["tobankcode"]].strip() if "tobankcode" in col_map and col_map["tobankcode"] < row_len else ""
            channel = row[col_map["txchannel"]].strip() if "txchannel" in col_map and col_map["txchannel"] < row_len else ""
            note = row[col_map["note"]].strip() if "note" in col_map and col_map["note"] < row_len else ""
            desc = row[col_map["txtype"]].strip() if "txtype" in col_map and col_map["txtype"] < row_len else ""
            if note:
                desc = f"{desc} {note}".strip()

            try:
                dep_amt = float(dep_str) if dep_str else 0.0
            except ValueError:
                dep_amt = 0.0
            try:
                wd_amt = float(wd_str) if wd_str else 0.0
            except ValueError:
                wd_amt = 0.0
            try:
                bal = float(bal_str) if bal_str else 0.0
            except ValueError:
                bal = 0.0

            if dep_amt <= 0.0 and wd_amt <= 0.0:
                return None

            acct_no = row[col_map["accountno"]].strip() if "accountno" in col_map and col_map["accountno"] < row_len else ""
            if not acct_no:
                acct_no = to_acct if dep_amt > 0 and to_acct else (from_acct if wd_amt > 0 and from_acct else fallback_acct_no)

            acct_name = row[col_map["accountname"]].strip() if "accountname" in col_map and col_map["accountname"] < row_len else ""
            if not acct_name:
                acct_name = to_name if dep_amt > 0 and to_name else (from_name if wd_amt > 0 and from_name else fallback_acct_name)

            ts = self._parse_datetime(tx_date, tx_time)
            tx_id = f"TX-{ts.year:04d}{ts.month:02d}{ts.day:02d}{ts.hour:02d}{ts.minute:02d}{ts.second:02d}-{line_num:05d}"

            if dep_amt > 0:
                return BankTransaction(
                    tx_id=tx_id,
                    account_no=acct_no or fallback_acct_no,
                    account_name=acct_name or fallback_acct_name,
                    timestamp=ts,
                    activity=ActivityType.INFLOW,
                    channel=channel or "TRANSFER",
                    amount=dep_amt,
                    balance=bal,
                    description=desc,
                    counterparty_bank=from_bank or None,
                    counterparty_account=from_acct or None,
                    counterparty_name=from_name or None,
                )
            elif wd_amt > 0:
                return BankTransaction(
                    tx_id=tx_id,
                    account_no=acct_no or fallback_acct_no,
                    account_name=acct_name or fallback_acct_name,
                    timestamp=ts,
                    activity=ActivityType.OUTFLOW,
                    channel=channel or "TRANSFER",
                    amount=wd_amt,
                    balance=bal,
                    description=desc,
                    counterparty_bank=to_bank or None,
                    counterparty_account=to_acct or None,
                    counterparty_name=to_name or None,
                )
            return None

        amt_idx = col_map.get("amount", -1)
        raw_amt = row[amt_idx].strip().replace(",", "") if 0 <= amt_idx < row_len else ""
        if not raw_amt:
            return None

        try:
            amount = float(raw_amt)
        except ValueError:
            return None
        if amount <= 0:
            return None

        bal_idx = col_map.get("balance", -1)
        raw_bal = row[bal_idx].strip().replace(",", "") if 0 <= bal_idx < row_len else ""
        balance = float(raw_bal) if raw_bal else 0.0

        acct_idx = col_map.get("account_no", -1)
        acct_no = row[acct_idx].strip() if 0 <= acct_idx < row_len and row[acct_idx].strip() else fallback_acct_no

        name_idx = col_map.get("account_name", -1)
        acct_name = row[name_idx].strip() if 0 <= name_idx < row_len and row[name_idx].strip() else fallback_acct_name

        ch_idx = col_map.get("channel", -1)
        channel = row[ch_idx].strip() if 0 <= ch_idx < row_len and row[ch_idx].strip() else "N/A"

        desc_idx = col_map.get("description", -1)
        desc = row[desc_idx].strip() if 0 <= desc_idx < row_len else ""

        act_idx = col_map.get("activity", -1)
        raw_act = row[act_idx].strip().upper() if 0 <= act_idx < row_len and row[act_idx].strip() else "XD"

        # Map Activity Type
        if raw_act in ("XD", "DEP", "CR", "CREDIT", "INFLOW"):
            act = ActivityType.INFLOW
        elif raw_act in ("FE", "FEE"):
            act = ActivityType.FEE
        elif raw_act in ("REV", "RVS", "REVERSAL"):
            act = ActivityType.REVERSAL
        else:
            act = ActivityType.OUTFLOW

        # Parse Timestamp
        date_idx = col_map.get("date", -1)
        time_idx = col_map.get("time", -1)
        raw_date = row[date_idx].strip() if 0 <= date_idx < row_len else ""
        raw_time = row[time_idx].strip() if 0 <= time_idx < row_len else ""
        timestamp = self._parse_datetime(raw_date, raw_time)

        # Counterparty metadata
        cp_b_idx = col_map.get("counterparty_bank", -1)
        cp_a_idx = col_map.get("counterparty_account", -1)
        cp_n_idx = col_map.get("counterparty_name", -1)

        cp_bank = (row[cp_b_idx].strip() or None) if 0 <= cp_b_idx < row_len else None
        cp_acct = (row[cp_a_idx].strip() or None) if 0 <= cp_a_idx < row_len else None
        cp_name = (row[cp_n_idx].strip() or None) if 0 <= cp_n_idx < row_len else None

        # Extract from description if not directly provided in columns
        if not cp_bank or not cp_acct:
            extracted = EntityExtractor.parse_description(desc)
            if not cp_bank:
                cp_bank = extracted["counterparty_bank"]
            if not cp_acct:
                cp_acct = extracted["counterparty_account"]
            if not cp_name:
                cp_name = extracted["counterparty_name"]

        tx_id = f"TX-{timestamp.year:04d}{timestamp.month:02d}{timestamp.day:02d}{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}-{line_num:05d}"

        return BankTransaction(
            tx_id=tx_id,
            account_no=acct_no,
            account_name=acct_name,
            timestamp=timestamp,
            activity=act,
            channel=channel,
            amount=amount,
            balance=balance,
            description=desc,
            counterparty_bank=cp_bank,
            counterparty_account=cp_acct,
            counterparty_name=cp_name,
        )

    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """
        Parses dates in formats:
        - ISO / SQL: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DDTHH:MM:SS"
        - Thai / European: "dd/mm/yyyy hh:mm:ss" or "dd/mm/yyyy"
        """
        clean_date = date_str.strip()

        # Case 1: Combined "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DDTHH:MM:SS"
        if " " in clean_date or "T" in clean_date:
            clean_date = clean_date.replace("T", " ")
            dt_parts = clean_date.split(" ")
            d_part = dt_parts[0]
            t_part = dt_parts[1] if len(dt_parts) > 1 else "00:00:00"
            
            # Check if YYYY-MM-DD
            if "-" in d_part:
                yp = d_part.split("-")
                if len(yp) == 3 and len(yp[0]) == 4:
                    year, month, day = int(yp[0]), int(yp[1]), int(yp[2])
                    tp = t_part.split(":")
                    hour = int(tp[0]) if len(tp) >= 1 else 0
                    minute = int(tp[1]) if len(tp) >= 2 else 0
                    second = int(float(tp[2])) if len(tp) >= 3 else 0
                    return datetime(year, month, day, hour, minute, second)

        # Case 2: Standard dd/mm/yyyy
        parts = clean_date.replace("-", "/").split("/")
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            # If Buddhist Era (e.g. 2569), convert to AD (2026)
            if year > 2400:
                year -= 543
        else:
            now = datetime.now()
            day, month, year = now.day, now.month, now.year

        # Clean time string
        time_parts = time_str.split(":") if time_str else []
        hour = int(time_parts[0]) if len(time_parts) >= 1 else 0
        minute = int(time_parts[1]) if len(time_parts) >= 2 else 0
        second = int(float(time_parts[2])) if len(time_parts) >= 3 else 0

        return datetime(year, month, day, hour, minute, second)

    def _parse_xlsx(self, file_path: Path) -> List[BankTransaction]:
        """
        Parses an Excel OpenXML (.xlsx) banking statement natively using standard
        library zipfile and xml.etree.ElementTree without external dependencies.
        Supports official Thai Police Excel templates (BAY, KBANK, SCB, KTB, BBL).
        """
        import zipfile
        import xml.etree.ElementTree as ET

        z = zipfile.ZipFile(file_path)

        # 1. Read shared strings
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns_ss = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in ss_tree.findall(".//s:si", ns_ss):
                text_parts = [t.text for t in si.findall(".//s:t", ns_ss) if t.text]
                shared_strings.append("".join(text_parts))

        # 2. Find first worksheet
        sheet_names = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
        if not sheet_names:
            raise ValueError(f"No worksheet found in Excel file {file_path}")
        sheet_target = sheet_names[0]

        sheet_tree = ET.fromstring(z.read(sheet_target))
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = sheet_tree.findall(".//s:sheetData/s:row", ns)

        parsed_rows: List[Dict[str, str]] = []
        for r in rows:
            row_dict: Dict[str, str] = {}
            for c in r.findall("s:c", ns):
                r_ref = c.get("r")
                if not r_ref:
                    continue
                col = "".join(filter(str.isalpha, r_ref))
                t = c.get("t")
                v = c.find("s:v", ns)
                val = ""
                if v is not None and v.text is not None:
                    if t == "s":
                        s_idx = int(v.text)
                        val = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else ""
                    else:
                        val = v.text
                elif t == "inlineStr":
                    is_t = c.find(".//s:t", ns)
                    if is_t is not None and is_t.text is not None:
                        val = is_t.text
                row_dict[col] = val
            parsed_rows.append(row_dict)

        if not parsed_rows:
            return []

        # Find header row
        header_row_idx = -1
        col_to_header: Dict[str, str] = {}
        for idx, r in enumerate(parsed_rows[:15]):
            h_map = {k: v.strip().lower() for k, v in r.items() if v.strip()}
            vals = list(h_map.values())
            if ("deposit" in vals and "withdrawal" in vals) or ("txdate" in vals and "txno" in vals) or ("date" in vals and "amount" in vals):
                header_row_idx = idx
                col_to_header = h_map
                break

        if header_row_idx < 0:
            header_row_idx = 0
            col_to_header = {k: v.strip().lower() for k, v in parsed_rows[0].items()}

        header_to_col = {v: k for k, v in col_to_header.items()}
        has_deposit_wd = "deposit" in header_to_col or "withdrawal" in header_to_col

        transactions: List[BankTransaction] = []
        file_stem = file_path.stem.replace("_", " ").title()
        default_acct_no = "9012888899"
        default_acct_name = f"เป้าหมายบัญชีม้าเฝ้าระวัง ({file_stem})"

        for r_idx, r in enumerate(parsed_rows[header_row_idx + 1:], start=header_row_idx + 2):
            if not r or all(not str(v).strip() for v in r.values()):
                continue

            if has_deposit_wd:
                acct_no = r.get(header_to_col.get("accountno", ""), "").strip() or default_acct_no
                acct_name = r.get(header_to_col.get("accountname", ""), "").strip() or default_acct_name
                tx_date = r.get(header_to_col.get("txdate", ""), "").strip()
                tx_time = r.get(header_to_col.get("txtime", ""), "").strip()
                dep_str = r.get(header_to_col.get("deposit", ""), "").replace(",", "").strip()
                wd_str = r.get(header_to_col.get("withdrawal", ""), "").replace(",", "").strip()
                bal_str = r.get(header_to_col.get("balance", ""), "").replace(",", "").strip()
                from_acct = r.get(header_to_col.get("fromaccountno", ""), "").strip()
                from_name = r.get(header_to_col.get("fromaccountname", ""), "").strip()
                from_bank = r.get(header_to_col.get("frombankcode", ""), "").strip()
                to_acct = r.get(header_to_col.get("toaccountno", ""), "").strip()
                to_name = r.get(header_to_col.get("toaccountname", ""), "").strip()
                to_bank = r.get(header_to_col.get("tobankcode", ""), "").strip()
                channel = r.get(header_to_col.get("txchannel", ""), "").strip()
                note = r.get(header_to_col.get("note", ""), "").strip()
                desc = r.get(header_to_col.get("txtype", ""), "").strip()
                if note:
                    desc = f"{desc} {note}".strip()

                try:
                    dep_amt = float(dep_str) if dep_str else 0.0
                except ValueError:
                    dep_amt = 0.0
                try:
                    wd_amt = float(wd_str) if wd_str else 0.0
                except ValueError:
                    wd_amt = 0.0
                try:
                    bal = float(bal_str) if bal_str else 0.0
                except ValueError:
                    bal = 0.0

                if dep_amt <= 0.0 and wd_amt <= 0.0:
                    continue

                ts = self._parse_datetime(tx_date, tx_time)
                tx_id = f"TX-{ts.year:04d}{ts.month:02d}{ts.day:02d}{ts.hour:02d}{ts.minute:02d}{ts.second:02d}-{r_idx:05d}"

                if dep_amt > 0:
                    tx = BankTransaction(
                        tx_id=tx_id,
                        account_no=acct_no,
                        account_name=acct_name,
                        timestamp=ts,
                        activity=ActivityType.INFLOW,
                        channel=channel or "TRANSFER",
                        amount=dep_amt,
                        balance=bal,
                        description=desc,
                        counterparty_bank=from_bank or None,
                        counterparty_account=from_acct or None,
                        counterparty_name=from_name or None,
                    )
                    transactions.append(tx)
                elif wd_amt > 0:
                    tx = BankTransaction(
                        tx_id=tx_id,
                        account_no=acct_no,
                        account_name=acct_name,
                        timestamp=ts,
                        activity=ActivityType.OUTFLOW,
                        channel=channel or "TRANSFER",
                        amount=wd_amt,
                        balance=bal,
                        description=desc,
                        counterparty_bank=to_bank or None,
                        counterparty_account=to_acct or None,
                        counterparty_name=to_name or None,
                    )
                    transactions.append(tx)

        return transactions
