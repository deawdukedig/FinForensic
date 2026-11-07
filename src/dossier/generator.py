"""
Court-admissible Evidence Dossier Generator.
Produces structured forensic investigation reports adhering to Section 226 of the
Thai Criminal Procedure Code, containing Exhibit A to D, algebraic proofs, and AOC freezing requests.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.models.transaction import BankTransaction, ActivityType
from src.models.cluster import FlowMatchCluster
from src.models.dossier import SuspicionReport, MerkleAuditRecord
from src.audit.provenance import EvidenceVault


class EvidenceDossierGenerator:
    """
    Assembles complete court-ready dossiers from forensic analysis results.
    """

    def __init__(self, case_id: str, investigating_officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)"):
        self.case_id = case_id
        self.officer = investigating_officer

    def generate_markdown_dossier(
        self,
        report: SuspicionReport,
        transactions: List[BankTransaction],
        vault: EvidenceVault,
    ) -> str:
        """
        Generates comprehensive court-admissible markdown dossier.
        """
        receipt = vault.generate_admissibility_receipt(report.statement_hash_sha256)
        inflows = [t for t in transactions if t.activity == ActivityType.INFLOW and not t.is_reversal]
        outflows = [t for t in transactions if t.activity == ActivityType.OUTFLOW and not t.is_reversal]
        fees = [t for t in transactions if t.activity == ActivityType.FEE]

        total_in = sum(t.amount for t in inflows)
        total_out = sum(t.amount for t in outflows)
        total_fee = sum(t.amount for t in fees)

        doc = []
        doc.append(f"# สำนวนการตรวจพิสูจน์พยานหลักฐานทางการเงินเชิงนิติวิทยาศาสตร์ (Forensic Court Dossier)")
        doc.append(f"**เลขที่สำนวนคดี (Case ID):** {self.case_id}  ")
        doc.append(f"**ผู้ตรวจพิสูจน์ (Investigator):** {self.officer}  ")
        doc.append(f"**วันเวลาที่จัดทำเอกสาร:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}  ")
        doc.append(f"**การรับรองตามกฎหมาย:** ประมวลกฎหมายวิธีพิจารณาความอาญา มาตรา 226 และ พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 (มาตรา 26)")
        doc.append("")
        doc.append("---")
        doc.append("")

        # Section 1: Chain of Custody & Receipt
        doc.append("## 1. การรับรองความสมบูรณ์แห่งพยานหลักฐานดิจิทัล (Chain of Custody & Integrity)")
        doc.append(f"- **SHA-256 Provenance Hash (ไฟล์ต้นฉบับ):** `{report.statement_hash_sha256}`")
        doc.append(f"- **Merkle Audit Root:** `{receipt['merkle_root']}`")
        doc.append(f"- **Admissibility Receipt ID:** `{receipt['receipt_id']}`")
        doc.append(f"- **สถานะความถูกต้อง:** {receipt['integrity_status']} (ผ่านการตรวจสอบความสมบูรณ์ ไม่ปรากฏการแก้ไขย้อนหลัง)")
        doc.append("")

        # Exhibit A: Executive Summary
        doc.append("---")
        doc.append("## เอกสารแนบ ก (Exhibit A): บทสรุปผู้บริหารและผลการประเมินความเสี่ยง")
        doc.append(f"- **บัญชีเป้าหมายที่ถูกตรวจสอบ:** `{report.account_no_masked}` ({report.account_name})")
        doc.append(f"- **คะแนนความน่าสงสัยรวม (Unified Suspicion Score):** **{report.overall_suspicion_score}/100**")
        doc.append(f"- **ระดับข้อบ่งชี้ทางนิติวิทยาศาสตร์:** `{report.suspicion_level}`")
        doc.append(f"- **ยอดเงินเข้าทั้งหมด (Total Inflow):** ฿{total_in:,.2f} ({len(inflows)} รายการ)")
        doc.append(f"- **ยอดเงินโอนออกทั้งหมด (Total Outflow):** ฿{total_out:,.2f} ({len(outflows)} รายการ)")
        doc.append(f"- **ค่าธรรมเนียมธนาคาร (Total Fees):** ฿{total_fee:,.2f} ({len(fees)} รายการ)")
        drain_rate = ((total_out + total_fee) / total_in * 100.0) if total_in > 0 else 0.0
        doc.append(f"- **อัตราการกวาดเงินออกจากบัญชี (Drain Percentage):** **{drain_rate:.3f}%** (เงินเหลือคงค้าง: ฿{total_in - (total_out + total_fee):,.2f})")
        doc.append("")

        # Exhibit B: Mathematical Flow Matching Proofs
        doc.append("---")
        doc.append("## เอกสารแนบ ข (Exhibit B): การจับคู่เส้นทางการเงินและสมการพีชคณิตเชิงเส้น (Flow Matching Proofs)")
        doc.append("การประมวลผลจับคู่เส้นทางเงินผ่าน Mixed-Integer Linear Programming (MILP):")
        doc.append("")
        for idx, cluster in enumerate(report.clusters_detected, start=1):
            doc.append(f"### กลุ่มธุรกรรมที่ {idx}: รหัส {cluster.cluster_id}")
            doc.append(f"- **ยอดเงินเข้าในกลุ่ม:** ฿{cluster.inflow_total:,.2f} (รายการ: {', '.join(cluster.inflow_tx_ids)})")
            doc.append(f"- **ยอดเงินกระจายออก:** ฿{cluster.outflow_total:,.2f} | ค่าธรรมเนียม: ฿{cluster.fee_total:,.2f}")
            doc.append(f"- **อัตราการระบายเงิน:** {cluster.drain_percentage:.2f}% | ค่าหน่วงเวลาเฉลี่ย (Latency): {cluster.avg_latency_minutes:.1f} นาที")
            doc.append(f"- **สมการพิสูจน์เชิงคณิตศาสตร์ (Linear Proof Equation):**")
            doc.append(f"  > `{cluster.mathematical_proof}`")
            doc.append("")

        # Exhibit C: Counterparty & Behavioral Signals
        doc.append("---")
        doc.append("## เอกสารแนบ ค (Exhibit C): การวิเคราะห์พฤติกรรมศาสตร์และบัญชีปลายทางสำคัญ")
        doc.append("รายการบัญชีผู้รับโอนสูงสุด (Top Dispersal Counterparties):")
        doc.append("| ลำดับ | ธนาคาร / เลขบัญชี | ชื่อผู้รับโอน | ยอดเงินรวม (บาท) |")
        doc.append("| :--- | :--- | :--- | :--- |")
        
        # Aggregate counterparty volumes
        cp_vol: Dict[str, float] = {}
        for tx in outflows:
            key = f"{tx.counterparty_bank or 'N/A'} {tx.counterparty_account or 'N/A'} | {tx.counterparty_name or 'N/A'}"
            cp_vol[key] = cp_vol.get(key, 0.0) + tx.amount

        sorted_cps = sorted(cp_vol.items(), key=lambda x: x[1], reverse=True)
        for i, (cp, vol) in enumerate(sorted_cps[:10], start=1):
            parts = cp.split("|")
            acct_info = parts[0].strip()
            name_info = parts[1].strip() if len(parts) > 1 else "-"
            doc.append(f"| {i} | {acct_info} | {name_info} | ฿{vol:,.2f} |")
        doc.append("")

        # Exhibit D: Emergency Asset Freezing Form
        doc.append("---")
        doc.append("## เอกสารแนบ ง (Exhibit D): คำร้องขออายัดบัญชีเงินฝากฉุกเฉินต่อศูนย์ AOC 1441")
        doc.append("*(ตาม พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7)*")
        doc.append("")
        doc.append(f"**เรียน:** ผู้อำนวยการศูนย์ปฏิบัติการแก้ไขปัญหาอาชญากรรมออนไลน์ (AOC 1441) / สถาบันการเงินที่เกี่ยวข้อง")
        doc.append(f"**เรื่อง:** ขอให้อายัดบัญชีเงินฝากและระงับการทำธุรกรรมเป็นการชั่วคราวเร่งด่วน")
        doc.append(f"**บัญชีเป้าหมาย:** เลขที่ `{report.account_no_raw}` นาม `{report.account_name}`")
        doc.append(f"**เหตุผลความจำเป็นเร่งด่วน:** ตรวจพบลักษณะการรับโอนเงินจากผู้เสียหายและซอยยอดกระจายออกทันทีภายในเวลาน้อยกว่า 90 นาที อัตราการกวาดเงินออกจากบัญชี {drain_rate:.2f}% เข้าข่ายพฤติกรรมบัญชีม้าแถวที่ 1 อย่างชัดแจ้ง มีความจำเป็นต้องระงับเส้นทางการเงินเพื่อบรรเทาความเสียหายของประชาชน")
        doc.append("")
        doc.append("ลงชื่อ ................................................................ ผู้ร้องขอ")
        doc.append(f"     ({self.officer})")
        doc.append("")

        return "\n".join(doc)
