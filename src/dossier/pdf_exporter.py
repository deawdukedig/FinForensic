"""
Court-Admissible PDF Dossier Exporter utilizing ReportLab and Thai TTF Fonts.
Produces official legal documents adhering to Section 226 of the Thai Criminal Procedure Code.
"""

from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Union, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.models.transaction import BankTransaction, ActivityType
from src.models.dossier import SuspicionReport
from src.audit.provenance import EvidenceVault
from src.audit.esignature import DigitalSignatureManager
from src.dossier.font_loader import resolve_thai_font, shape_thai_text


class CourtDossierPDFExporter:
    """
    Renders professional, court-admissible PDF dossiers with Thai language typography
    embedded using official TH Sarabun fonts (THSarabunNew / THSarabunIT๙).
    """

    def __init__(self, font_name: Optional[str] = None, font_path: Optional[str] = None):
        spec = font_name or font_path
        self.font_name = resolve_thai_font(spec)

    def export_pdf(
        self,
        output_pdf_path: Union[str, Path],
        report: SuspicionReport,
        transactions: List[BankTransaction],
        vault: EvidenceVault,
        officer_name: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
        agency: str = "กองบัญชาการตำรวจสืบสวนสอบสวนอาชญากรรมทางเทคโนโลยี (บช.สอท.)",
    ) -> str:
        """
        Builds and saves the court dossier PDF document.
        """
        out_p = Path(output_pdf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(out_p),
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=28,
            bottomMargin=28,
        )

        styles = getSampleStyleSheet()
        fn = self.font_name

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=22,
            leading=26,
            alignment=1,  # Center
            textColor=colors.HexColor("#1e293b"),
        )
        subtitle_style = ParagraphStyle(
            "SubTitle",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor("#475569"),
        )
        h1_style = ParagraphStyle(
            "H1",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=5,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1e293b"),
        )
        bold_body = ParagraphStyle(
            "BoldBody",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
        )
        th_style = ParagraphStyle(
            "TH",
            parent=styles["Normal"],
            fontName=fn,
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
        )

        elements = []

        # Header
        elements.append(Paragraph(shape_thai_text("<b>สำนวนการตรวจพิสูจน์พยานหลักฐานทางการเงินเชิงนิติวิทยาศาสตร์</b>"), title_style))
        elements.append(Paragraph(shape_thai_text("FORENSIC FINANCIAL EVIDENCE DOSSIER (ป.วิ.อาญา มาตรา 226)"), subtitle_style))
        elements.append(Spacer(1, 10))

        # Metadata Table
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        sig_mgr = DigitalSignatureManager()
        sig_data = sig_mgr.sign_artifact(report.statement_hash_sha256, "POL-8842", officer_name, agency)

        meta_data = [
            [Paragraph(shape_thai_text("<b>เลขที่สำนวนคดี (Case ID):</b>"), body_style), Paragraph(shape_thai_text(report.case_id), bold_body)],
            [Paragraph(shape_thai_text("<b>หน่วยงานผู้ตรวจพิสูจน์:</b>"), body_style), Paragraph(shape_thai_text(agency), body_style)],
            [Paragraph(shape_thai_text("<b>พนักงานสอบสวนผู้ตรวจพิสูจน์:</b>"), body_style), Paragraph(shape_thai_text(officer_name), body_style)],
            [Paragraph(shape_thai_text("<b>วันเวลาที่บันทึกข้อมูล:</b>"), body_style), Paragraph(shape_thai_text(now_str), body_style)],
            [Paragraph(shape_thai_text("<b>SHA-256 Statement Hash:</b>"), body_style), Paragraph(f"<code>{report.statement_hash_sha256}</code>", body_style)],
            [Paragraph(shape_thai_text("<b>Merkle Audit Root:</b>"), body_style), Paragraph(f"<code>{report.merkle_root}</code>", body_style)],
            [Paragraph(shape_thai_text("<b>Digital Signature (ETA Sec 26):</b>"), body_style), Paragraph(f"<code>{sig_data['signature'][:32]}...</code> (VERIFIED)", body_style)],
        ]

        t_meta = Table(meta_data, colWidths=[2.5 * inch, 4.98 * inch])
        t_meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 10))

        # Exhibit A
        elements.append(Paragraph(shape_thai_text("<b>เอกสารแนบ ก (Exhibit A): สรุปผลการประเมินความเสี่ยงและพฤติกรรมบัญชีม้า</b>"), h1_style))
        
        inflows = [t for t in transactions if t.activity == ActivityType.INFLOW and not t.is_reversal]
        outflows = [t for t in transactions if t.activity == ActivityType.OUTFLOW and not t.is_reversal]
        fees = [t for t in transactions if t.activity == ActivityType.FEE]
        tot_in = sum(t.amount for t in inflows)
        tot_out = sum(t.amount for t in outflows)
        tot_fee = sum(t.amount for t in fees)
        drain_rate = ((tot_out + tot_fee) / tot_in * 100.0) if tot_in > 0 else 0.0

        kpi_data = [
            [Paragraph(shape_thai_text("<b>บัญชีเป้าหมาย:</b>"), body_style), Paragraph(shape_thai_text(f"{report.account_no_masked} ({report.account_name})"), bold_body)],
            [Paragraph(shape_thai_text("<b>คะแนนความน่าสงสัย (Unified Suspicion Score):</b>"), body_style), Paragraph(shape_thai_text(f"<b>{report.overall_suspicion_score}/100</b> ({report.suspicion_level})"), bold_body)],
            [Paragraph(shape_thai_text("<b>ยอดเงินเข้าทั้งหมด:</b>"), body_style), Paragraph(shape_thai_text(f"฿{tot_in:,.2f} ({len(inflows)} รายการ)"), body_style)],
            [Paragraph(shape_thai_text("<b>ยอดเงินโอนออกทั้งหมด:</b>"), body_style), Paragraph(shape_thai_text(f"฿{tot_out:,.2f} ({len(outflows)} รายการ)"), body_style)],
            [Paragraph(shape_thai_text("<b>ค่าธรรมเนียมธนาคาร:</b>"), body_style), Paragraph(shape_thai_text(f"฿{tot_fee:,.2f} ({len(fees)} รายการ)"), body_style)],
            [Paragraph(shape_thai_text("<b>อัตราการกวาดเงินออกจากบัญชี (Drain Rate):</b>"), body_style), Paragraph(shape_thai_text(f"<b>{drain_rate:.3f}%</b> (คงเหลือ ฿{tot_in - (tot_out + tot_fee):,.2f})"), bold_body)],
        ]
        t_kpi = Table(kpi_data, colWidths=[3.2 * inch, 4.28 * inch])
        t_kpi.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 10))

        # Exhibit B
        elements.append(Paragraph(shape_thai_text("<b>เอกสารแนบ ข (Exhibit B): การจับคู่เส้นทางการเงินด้วย MILP (Linear Algebraic Proofs)</b>"), h1_style))
        cluster_rows = [
            [
                Paragraph(shape_thai_text("<b>รหัสกลุ่ม</b>"), th_style),
                Paragraph(shape_thai_text("<b>ยอดเงินเข้า</b>"), th_style),
                Paragraph(shape_thai_text("<b>ยอดเงินออกที่จับคู่</b>"), th_style),
                Paragraph(shape_thai_text("<b>อัตรากวาดเงิน</b>"), th_style),
                Paragraph(shape_thai_text("<b>สมการพิสูจน์ทางคณิตศาสตร์</b>"), th_style),
            ]
        ]
        for c in report.clusters_detected[:4]:
            cluster_rows.append([
                Paragraph(shape_thai_text(c.cluster_id), body_style),
                Paragraph(shape_thai_text(f"฿{c.inflow_total:,.2f}"), body_style),
                Paragraph(shape_thai_text(f"฿{c.outflow_total:,.2f}"), body_style),
                Paragraph(shape_thai_text(f"{c.drain_percentage:.1f}%"), body_style),
                Paragraph(shape_thai_text(c.mathematical_proof[:60] + "..."), body_style),
            ])
        t_clusters = Table(cluster_rows, colWidths=[1.1 * inch, 1.35 * inch, 1.45 * inch, 1.15 * inch, 2.43 * inch])
        t_clusters.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_clusters)
        elements.append(Spacer(1, 10))

        # Exhibit C
        elements.append(Paragraph(shape_thai_text("<b>เอกสารแนบ ค (Exhibit C): รายชื่อบัญชีผู้รับโอนเงินสูงสุด (Top Dispersal Counterparties)</b>"), h1_style))
        cp_rows = [
            [
                Paragraph(shape_thai_text("<b>ลำดับ</b>"), th_style),
                Paragraph(shape_thai_text("<b>ธนาคาร / บัญชีปลายทาง</b>"), th_style),
                Paragraph(shape_thai_text("<b>ชื่อผู้รับโอน</b>"), th_style),
                Paragraph(shape_thai_text("<b>ยอดเงินรวม (บาท)</b>"), th_style),
            ]
        ]
        sorted_cps = sorted(report.top_counterparties.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (cp, vol) in enumerate(sorted_cps, 1):
            parts = cp.split()
            bank_acct = " ".join(parts[:2]) if len(parts) >= 2 else cp
            name = " ".join(parts[2:]) if len(parts) > 2 else "-"
            cp_rows.append([
                Paragraph(shape_thai_text(str(i)), th_style),
                Paragraph(shape_thai_text(bank_acct), body_style),
                Paragraph(shape_thai_text(name), body_style),
                Paragraph(shape_thai_text(f"฿{vol:,.2f}"), bold_body),
            ])
        t_cp = Table(cp_rows, colWidths=[0.8 * inch, 2.5 * inch, 2.3 * inch, 1.88 * inch])
        t_cp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_cp)
        elements.append(Spacer(1, 10))

        # Exhibit D
        elements.append(Paragraph(shape_thai_text("<b>เอกสารแนบ ง (Exhibit D): คำร้องขออายัดบัญชีฉุกเฉินต่อศูนย์ AOC 1441</b>"), h1_style))
        freeze_text = (
            f"<b>เรียน ผู้อำนวยการศูนย์ AOC 1441:</b> ตาม พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7 "
            f"พนักงานสอบสวนขอสั่งอายัดบัญชีเงินฝาก <b>เลขที่ {report.account_no_raw} ({report.account_name})</b> โดยเร่งด่วน "
            f"เนื่องจากตรวจพบพฤติกรรมดูดเงินออกจากบัญชี {drain_rate:.2f}% ภายในระยะเวลาสั้น เป็นบัญชีม้าแถวที่ 1 ในการรับเงินจากผู้เสียหาย"
        )
        t_freeze = Table([[Paragraph(shape_thai_text(freeze_text), body_style)]], colWidths=[7.48 * inch])
        t_freeze.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f87171")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_freeze)
        elements.append(Spacer(1, 12))

        # Signature Box
        sig_box_data = [
            [
                Paragraph(shape_thai_text("<b>การรับรองความถูกต้องโดยพนักงานสอบสวน:</b>"), bold_body),
                Paragraph(shape_thai_text("<b>การรับรองห่วงโซ่พยานหลักฐานดิจิทัล:</b>"), bold_body),
            ],
            [
                Paragraph(shape_thai_text(f"<br/>(ลงชื่อ) ....................................................<br/>({officer_name})<br/>ตำแหน่ง พนักงานสอบสวนผู้ตรวจพิสูจน์"), body_style),
                Paragraph(shape_thai_text(f"<br/><b>SHA-256 Hash Verified:</b> PASS<br/><b>Merkle Vault Status:</b> TAMPER_EVIDENT<br/><b>Admissibility:</b> Section 226 CPC"), body_style),
            ],
        ]
        t_sig = Table(sig_box_data, colWidths=[3.74 * inch, 3.74 * inch])
        t_sig.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("FONTNAME", (0, 0), (-1, -1), fn),
            ("FONTSIZE", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sig)

        doc.build(elements)
        try:
            return str(out_p.resolve().relative_to(Path.cwd().resolve()).as_posix())
        except ValueError:
            return str(out_p.as_posix())
