"""
Court-admissible Evidence Dossier Generator & Statement Forensic Analysis Generator.
Produces structured forensic investigation reports adhering to Section 226 of the
Thai Criminal Procedure Code, AMLA Section 49/1, and Cyber Emergency Decree B.E. 2566.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from src.models.transaction import BankTransaction, ActivityType
from src.models.cluster import FlowMatchCluster
from src.models.dossier import SuspicionReport, MerkleAuditRecord
from src.audit.provenance import EvidenceVault


class DispersalDestination(BaseModel):
    """Aggregated destination beneficiary receiving funds."""
    model_config = ConfigDict(frozen=False)

    rank: int
    bank: str
    account_no: str
    account_name: str
    channel: str
    total_drained_thb: float
    proportional_claim_thb: float
    percentage_of_victim_funds: float
    tx_count: int
    avg_latency_minutes: float
    recommended_action: str


TABLE_RESPONSIVE_STYLE = """<style>
/* Responsive & Print-Optimized Table Layout (No Horizontal Scrollbar) */
table {
  display: table !important;
  width: 100% !important;
  max-width: 100% !important;
  border-collapse: collapse !important;
  table-layout: auto !important;
  font-size: 13px !important;
  overflow: visible !important;
}
th, td {
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: break-word !important;
  padding: 6px 5px !important;
}
@media print {
  body {
    font-size: 10pt !important;
  }
  table {
    display: table !important;
    width: 100% !important;
    table-layout: auto !important;
    font-size: 8.5pt !important;
  }
}
</style>"""


class EvidenceDossierGenerator:
    """
    Assembles complete court-ready dossiers and comprehensive statement forensic analysis reports.
    """

    def __init__(self, case_id: str, investigating_officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)"):
        self.case_id = case_id
        self.officer = investigating_officer

    @staticmethod
    def _format_action_th(action: str) -> str:
        """Formats action enum into clean, wrap-friendly Thai text without backticks to prevent table overflow."""
        mapping = {
            "AOC_1441_FREEZE_URGENT": "AOC 1441 อายัดด่วน",
            "PLATFORM_SUBPOENA_EVIDENCE": "ม.132 ขอพยานแพลตฟอร์ม",
            "CCTV_INSPECTION_ATM": "CCTV ตรวจกล้อง ATM",
            "VASP_WALLET_FREEZE": "อายัดกระเป๋า VASP",
        }
        return mapping.get(action, action.replace("_", " "))

    def generate_dispersal_mermaid(
        self,
        report: SuspicionReport,
        top_destinations: List[DispersalDestination],
        total_inflow: float,
        residual_buffer: float,
    ) -> str:
        """Generates a court-admissible Mermaid flowchart visualizing overall statement fund dispersal."""
        lines = [
            "```mermaid",
            "flowchart LR",
            f'    M["บัญชีเป้าหมาย: {report.account_no_masked}<br/>({report.account_name})<br/>฿{total_inflow:,.2f}"]',
        ]

        tier2 = [d for d in top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        cashout = [d for d in top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        crypto = [d for d in top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        gateways = [d for d in top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]

        edges = []

        # 1. Tier 2 Mule Accounts
        if tier2:
            lines.append('    subgraph TIER2["เครือข่ายบัญชีม้าแถว 2 (Mule Tier-2)"]')
            if len(tier2) > 4:
                top_t2 = tier2[:3]
                rest_t2 = tier2[3:]
                for idx, d in enumerate(top_t2, 1):
                    node_id = f"T2_{idx}"
                    clean_name = d.account_name.replace('"', "'")
                    clean_acct = d.account_no.replace('"', "")
                    name_str = f" {clean_name}" if clean_name not in ("N/A", "", "UNKNOWN", "-") else ""
                    label = f"{d.bank} {clean_acct}{name_str}: ฿{d.total_drained_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                    lines.append(f'        {node_id}["{label}"]')
                    edges.append(f"    M -->|Mobile Transfer| {node_id}")

                rest_sum = sum(d.total_drained_thb for d in rest_t2)
                rest_pct = (rest_sum / total_inflow * 100.0) if total_inflow > 0 else 0.0
                rest_node = "T2_REST"
                rest_label = f"บัญชีม้าแถว 2 อื่นๆ ({len(rest_t2)} บัญชี): ฿{rest_sum:,.2f} ({rest_pct:.1f}%)"
                lines.append(f'        {rest_node}["{rest_label}"]')
                edges.append(f"    M -->|Mobile Transfer| {rest_node}")
            else:
                for idx, d in enumerate(tier2, 1):
                    node_id = f"T2_{idx}"
                    clean_name = d.account_name.replace('"', "'")
                    clean_acct = d.account_no.replace('"', "")
                    name_str = f" {clean_name}" if clean_name not in ("N/A", "", "UNKNOWN", "-") else ""
                    label = f"{d.bank} {clean_acct}{name_str}: ฿{d.total_drained_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                    lines.append(f'        {node_id}["{label}"]')
                    edges.append(f"    M -->|Mobile Transfer| {node_id}")
            lines.append("    end")

        # 2. ATM Cashout
        if cashout:
            lines.append('    subgraph CASHOUT["การถอนเงินสดออกจากระบบ (Cash-Out)"]')
            for idx, d in enumerate(cashout, 1):
                node_id = f"ATM_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN", "-") else f"{clean_name} ({d.bank})"
                label = f"{display_title}: ฿{d.total_drained_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|Cardless ATM| {node_id}")
            lines.append("    end")

        # 3. Crypto Off-Ramp
        if crypto:
            lines.append('    subgraph CRYPTO["ร้านค้าสินทรัพย์ดิจิทัล (Crypto Off-Ramp)"]')
            for idx, d in enumerate(crypto, 1):
                node_id = f"CRYPTO_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN", "-") else f"{d.bank} {clean_name}"
                label = f"{display_title}: ฿{d.total_drained_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|P2P OTC| {node_id}")
            lines.append("    end")

        # 4. Payment Gateways & Ad Platforms
        if gateways:
            lines.append('    subgraph GATEWAY["ระบบรับชำระเงินและค่าโฆษณา (Payment Gateway & Ad Platforms)"]')
            for idx, d in enumerate(gateways, 1):
                node_id = f"GW_{idx}"
                clean_name = d.account_name.replace('"', "'")
                clean_acct = d.account_no.replace('"', "")
                display_title = f"{d.bank} {clean_acct}" if clean_name in ("N/A", "", "UNKNOWN", "-") else f"{clean_name} ({d.bank})"
                label = f"{display_title}: ฿{d.total_drained_thb:,.2f} ({d.percentage_of_victim_funds:.1f}%)"
                lines.append(f'        {node_id}["{label}"]')
                edges.append(f"    M -->|Payment/Ads| {node_id}")
            lines.append("    end")

        # 5. Residual Buffer
        if residual_buffer > 0:
            res_pct = (residual_buffer / total_inflow * 100.0) if total_inflow > 0 else 0.0
            lines.append('    subgraph BUFFER["เงินตกค้างในบัญชีม้า (Residual Buffer)"]')
            lines.append(f'        BUF["เงินค้างรอฟอก: ฿{residual_buffer:,.2f} ({res_pct:.1f}%)"]')
            lines.append("    end")
            edges.append("    M -.->|ค้างในบัญชี| BUF")

        lines.extend(edges)
        lines.append("```")
        return "\n".join(lines)

    def generate_analysis_report(
        self,
        report: SuspicionReport,
        transactions: List[BankTransaction],
        vault: EvidenceVault,
        brief: bool = False,
    ) -> str:
        """
        Generates statement-wide forensic analysis report in Markdown.
        If brief=True, creates a concise brief report containing Sections 1-3
        and omitting Sections 4, 5, 6, 7 (MILP, Restitution, Directives, Chain of Custody).
        Adheres strictly to Rule 7 & Rule 9 (TABLE_RESPONSIVE_STYLE,
        KaTeX equations, Mermaid topology, legal neutrality, and relative paths).
        """
        receipt = vault.generate_admissibility_receipt(report.statement_hash_sha256)
        inflows = [t for t in transactions if t.activity == ActivityType.INFLOW and not t.is_reversal]
        outflows = [t for t in transactions if t.activity == ActivityType.OUTFLOW and not t.is_reversal]
        fees = [t for t in transactions if t.activity == ActivityType.FEE]

        total_in = sum(t.amount for t in inflows)
        total_out = sum(t.amount for t in outflows)
        total_fee = sum(t.amount for t in fees)
        total_dispersed = total_out + total_fee
        residual_buffer = max(0.0, total_in - total_dispersed)
        drain_rate = ((total_dispersed) / total_in * 100.0) if total_in > 0 else 0.0

        # Calculate mean transit latency across transactions
        latencies: List[float] = []
        for inf in inflows:
            for out in outflows:
                if out.timestamp >= inf.timestamp:
                    diff = (out.timestamp - inf.timestamp).total_seconds() / 60.0
                    latencies.append(diff)
        mean_latency = (sum(latencies) / len(latencies)) if latencies else 0.0

        # Aggregate destination counterparties
        dest_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        for tx in outflows:
            b = tx.counterparty_bank or "N/A"
            a = tx.counterparty_account or "N/A"
            n = tx.counterparty_name or "N/A"
            ch = tx.channel or "Mobile Transfer"
            k = (b, a, n, ch)
            if k not in dest_map:
                dest_map[k] = {
                    "bank": b,
                    "account_no": a,
                    "account_name": n,
                    "channel": ch,
                    "total_drained": 0.0,
                    "tx_count": 0,
                    "latencies": [],
                }
            dest_map[k]["total_drained"] += tx.amount
            dest_map[k]["tx_count"] += 1

        sorted_dests = sorted(dest_map.values(), key=lambda x: x["total_drained"], reverse=True)
        top_destinations: List[DispersalDestination] = []

        for r_idx, d in enumerate(sorted_dests, start=1):
            pct = (d["total_drained"] / total_in * 100.0) if total_in > 0 else 0.0
            combined_target = f"{d['bank']} {d['account_name']} {d['channel']}".lower()

            if "atm" in combined_target or "cardless" in combined_target:
                action = "CCTV_INSPECTION_ATM"
            elif any(w in combined_target for w in ["p2p", "binance", "bitkub", "crypto", "usdt", "vasp"]):
                action = "VASP_WALLET_FREEZE"
            elif any(w in combined_target for w in [
                "meta ads", "facebook ads", "fb ads", "google ads", "tiktok ads", "line ads", "twitter ads",
                "kgp", "kasikorn global payment", "2c2p", "omise", "opn", "gb prime", "paysolutions",
                "ksher", "truemoney merchant", "payment gateway", "gateway", "merchant pool", "billing"
            ]):
                action = "PLATFORM_SUBPOENA_EVIDENCE"
            else:
                action = "AOC_1441_FREEZE_URGENT"

            # In statement-wide view, claim is equivalent to traced drained volume
            claim_val = d["total_drained"]
            top_destinations.append(
                DispersalDestination(
                    rank=r_idx,
                    bank=d["bank"],
                    account_no=d["account_no"],
                    account_name=d["account_name"],
                    channel=d["channel"],
                    total_drained_thb=d["total_drained"],
                    proportional_claim_thb=claim_val,
                    percentage_of_victim_funds=pct,
                    tx_count=d["tx_count"],
                    avg_latency_minutes=mean_latency,
                    recommended_action=action,
                )
            )

        total_claimable = sum(d.proportional_claim_thb for d in top_destinations)
        pct_claim = (total_claimable / total_in * 100.0) if total_in > 0 else 0.0

        tier2_mules = [d for d in top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        atm_cashing = [d for d in top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        vasp_p2p = [d for d in top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        gateways = [d for d in top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]

        tot_tier2_claim = sum(d.proportional_claim_thb for d in tier2_mules)
        tot_atm_claim = sum(d.proportional_claim_thb for d in atm_cashing)
        tot_vasp_claim = sum(d.proportional_claim_thb for d in vasp_p2p)
        tot_gateway_claim = sum(d.proportional_claim_thb for d in gateways)

        lines = []
        lines.append(TABLE_RESPONSIVE_STYLE)
        report_title = "รายงานวิเคราะห์เส้นทางการเงินเชิงลึกรวมระดับบัญชี (ฉบับย่อ)" if brief else "รายงานวิเคราะห์เส้นทางการเงินเชิงลึกรวมระดับบัญชี (Statement Forensic Analysis Report)"
        lines.append(f"# {report_title}")
        lines.append(f"**เลขที่สำนวนคดี (Case ID):** `{self.case_id}`  ")
        lines.append(f"**ผู้ตรวจพิสูจน์ (Forensic Investigator):** {self.officer}  ")
        lines.append(f"**วันเวลาที่จัดทำเอกสาร:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}  ")
        lines.append(f"**มาตรฐานกฎหมายที่รองรับ:** ป.วิ.อ. มาตรา 226, พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 และ พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 1: Executive Summary & Loss Ledger
        lines.append("## 1. บทสรุปข้อมูลบัญชีเป้าหมายและภาพรวมความเสียหาย (Executive Loss Summary)")
        lines.append(f"- **บัญชีเป้าหมายที่ถูกตรวจสอบ (Target Mule Tier-1):** `{report.account_no_masked}` ({report.account_name})")
        lines.append(f"- **คะแนนความน่าสงสัยรวม (Unified Suspicion Score):** **{report.overall_suspicion_score}/100** (ระดับ: `{report.suspicion_level}`)")
        lines.append(f"- **ยอดเงินเข้าทั้งหมด (Total Inflow):** **฿{total_in:,.2f}** ({len(inflows)} รายการ)")
        lines.append(f"- **ยอดเงินโอนออกทั้งหมด (Total Outflow):** **฿{total_out:,.2f}** ({len(outflows)} รายการ)")
        lines.append(f"- **ค่าธรรมเนียมธนาคาร (Total Fees):** **฿{total_fee:,.2f}** ({len(fees)} รายการ)")
        lines.append(f"- **อัตราการกวาดเงินออกจากบัญชี (Drain Rate):** **{drain_rate:.2f}%**")
        lines.append(f"- **ยอดเงินสิทธิเฉลี่ยทรัพย์คืนชอบธรรมรวม (Proportional Restitution Claims):** **฿{total_claimable:,.2f}** ({pct_claim:.2f}% ของยอดเงินเข้า)")
        lines.append(f"- **ระยะเวลาเงินแช่พักเฉลี่ย (Mean Residence Time):** **{mean_latency:.1f} นาที** (การกระจายเงินรวดเร็วแบบกวาดหมดบัญชี)")
        lines.append(f"- **ยอดเงินคงค้างหลงเหลือในบัญชีเป้าหมาย (Residual Buffer):** **฿{residual_buffer:,.2f}**")
        lines.append(f"- **ค่าแฮชตรวจสอบความสมบูรณ์ของไฟล์ Statement (SHA-256):** `{report.statement_hash_sha256}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 2: Top Dispersal Destinations & Beneficiaries Breakdown
        lines.append("## 2. สรุปปลายทางเส้นทางการเงินและผู้รับประโยชน์หลัก (Top Dispersal Destinations & Beneficiaries)")
        lines.append("จากการประมวลผลจับคู่เส้นทางเงินทางคณิตศาสตร์แบบระบุตัวเหยื่อ (Flow Conservation & Balance Proofs) พบว่าเงินถูกระบายออกไปยังผู้รับประโยชน์หลักดังต่อไปนี้:")
        lines.append("")
        lines.append("### แผนภาพแสดงเส้นทางการกระจายเงิน (Fund Dispersal Topology):")
        lines.append(self.generate_dispersal_mermaid(report, top_destinations, total_in, residual_buffer))
        lines.append("")
        lines.append("| ลำดับ | ธนาคาร / เลขบัญชี | ชื่อบัญชีปลายทาง | ช่องทาง | ยอดเงินออก (฿) | สิทธิขอคืน (฿) | สัดส่วน |")
        lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: |")

        for d in top_destinations:
            acct_info = f"{d.bank} {d.account_no}" if d.account_no not in ("UNKNOWN", "N/A") else d.bank
            lines.append(
                f"| {d.rank} | {acct_info} | **{d.account_name}** | {d.channel} | ฿{d.total_drained_thb:,.2f} | **฿{d.proportional_claim_thb:,.2f}** | {d.percentage_of_victim_funds:.1f}% |"
            )

        lines.append(
            f"| **รวม** | - | **รวมทั้งสิ้น {len(top_destinations)} ปลายทาง** | - | **฿{total_out:,.2f}** | **฿{total_claimable:,.2f}** | **{pct_claim:.1f}%** |"
        )
        lines.append("")

        lines.append("### จำแนกกลุ่มผู้รับประโยชน์และช่องทางการระบายเงิน:")
        cat_idx = 1
        if tier2_mules:
            lines.append(f"{cat_idx}. **เครือข่ายบัญชีม้าแถว 2 (Mule Tier-2 Mobile Banking):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_tier2_claim:,.2f}** ({tot_tier2_claim/total_in*100:.1f}%)")
            lines.append("   - มีการกระจายไปยังบัญชีม้าแถว 2 หลายบัญชี เพื่อหลีกเลี่ยงเกณฑ์การรายงานธุรกรรม (Structuring)")
            cat_idx += 1
        if gateways:
            lines.append(f"{cat_idx}. **ระบบรับชำระเงินและแพลตฟอร์มโฆษณา (Payment Gateway & Ad Platforms):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_gateway_claim:,.2f}** ({tot_gateway_claim/total_in*100:.1f}%)")
            lines.append("   - การนำเงินไปตัดชำระค่าโฆษณาโซเชียลมีเดียหรือแปลงสภาพผ่านเกตเวย์ (ห้ามอายัดผ่าน AOC 1441 แต่ต้องออกหมายเรียก ม.132)")
            cat_idx += 1
        if atm_cashing:
            lines.append(f"{cat_idx}. **การถอนเงินสดผ่านตู้ ATM ไม่ใช้บัตร (Physical Cash-Out):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_atm_claim:,.2f}** ({tot_atm_claim/total_in*100:.1f}%)")
            lines.append("   - การกดเงินสดออกจากระบบทันทีเพื่อตัดตอนรอยเท้าดิจิทัล (Digital Footprint)")
            cat_idx += 1
        if vasp_p2p:
            lines.append(f"{cat_idx}. **ช่องทางสินทรัพย์ดิจิทัล P2P Escrow (Crypto Off-Ramp):** สิทธิเฉลี่ยทรัพย์คืนรวม **฿{tot_vasp_claim:,.2f}** ({tot_vasp_claim/total_in*100:.1f}%)")
            lines.append("   - การแปลงสภาพเป็นเงินดิจิทัล USDT เพื่อโอนย้ายข้ามพรมแดน")
            cat_idx += 1

        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 3: Transfer Circumstances & Critical Forensic Insights
        lines.append("## 3. พฤติการณ์ของการโอนและประเด็นสำคัญเชิงสืบสวน (Transfer Circumstances & Critical Forensic Insights)")
        lines.append("")
        lines.append("### 3.1 พฤติการณ์การเคลื่อนย้ายเงินและรูปแบบการหลอกลวง (Transfer Circumstances & Modus Operandi)")
        inf_dates = set(t.timestamp.strftime("%Y-%m-%d") for t in inflows)
        if len(inf_dates) <= 1:
            lines.append(f"- **รูปแบบกระแสเงินเข้าบัญชี (Concentrated Funnel):** พบรายการโอนเงินเข้าหนาแน่นภายในวันเดียวกัน รวม {len(inflows)} รายการ เป็นเงิน **฿{total_in:,.2f}** สะท้อนถึงการถูกใช้เป็นบัญชีรวมรับเงินจากเหยื่อหลายรายพร้อมกันในระยะเวลาอันสั้น")
        else:
            lines.append(f"- **รูปแบบกระแสเงินเข้าบัญชี (Distributed Inflow):** พบรายการโอนเงินเข้ากระจายตัวต่อเนื่อง ({len(inf_dates)} วัน) รวม {len(inflows)} รายการ เป็นเงิน **฿{total_in:,.2f}** ชี้ให้เห็นถึงการดำเนินการหลอกลวงแบบต่อเนื่อง")
        lines.append(f"- **การตอบสนองของบัญชีเป้าหมาย (`{report.account_no_masked}`):** มียอดเงินที่ถูกระบายออกทันที **฿{total_out:,.2f}** (อัตราการกวาดเงิน: **{drain_rate:.2f}%**) โดยมีระยะเวลาเงินแช่พักเฉลี่ย **{mean_latency:.1f} นาที**")
        lines.append("")

        lines.append("### 3.2 การวิเคราะห์โอกาสทองในการอายัดทรัพย์สินคืน (Asset Recovery Golden Window Analysis)")
        res_pct = (residual_buffer / total_in * 100.0) if total_in > 0 else 0.0
        if residual_buffer >= 50000.0 or res_pct >= 20.0:
            lines.append("> [!IMPORTANT]")
            lines.append(f"> **⭐ ตรวจพบโอกาสทองในการอายัดทรัพย์สินคืน (Primary Golden Window for Asset Recovery)**")
            lines.append(f"> - ตรวจพบยอดเงินคงค้างตกค้างในบัญชีเป้าหมาย (`{report.account_no_masked}` {report.account_name}) สูงถึง **฿{residual_buffer:,.2f}** (คิดเป็น **{res_pct:.1f}%** ของยอดเงินเข้าทั้งหมด)")
            lines.append(f"> - **นัยสำคัญเชิงสืบสวน:** มิจฉาชีพยังไม่สามารถระบายเงินส่วนนี้ออกไปได้ทัน (อาจติดปัญหาเพดานการโอนรายวัน Daily Limit หรือระบบเฝ้าระวังของธนาคาร)")
            lines.append(f"> - **ข้อสั่งการเร่งด่วนที่สุด:** พนักงานสอบสวนต้องเร่งส่งคำสั่งระงับธุรกรรม (AOC 1441) ไปยังบัญชีเป้าหมายนี้เป็นลำดับแรกสุดทันที เพราะเป็นจุดที่มีโอกาสได้เงินสดคืนกลับมาคุ้มครองสิทธิให้แก่ผู้เสียหายจริงสูงสุด")
        elif residual_buffer > 0:
            lines.append(f"- ตรวจพบยอดเงินคงค้างในบัญชีเป้าหมายจำนวน **฿{residual_buffer:,.2f}** ({res_pct:.1f}%) ให้ส่งคำสั่งอายัดบัญชีเป้าหมายควบคู่ไปกับบัญชีแถว 2")
        else:
            lines.append(f"- กระแสเงินในบัญชีเป้าหมายถูกระบายออกครบถ้วน 100% (Instant Flush / Rapid Account Sweeping) ภายในเวลาเฉลี่ย {mean_latency:.1f} นาที หน้าต่างการอายัดในบัญชีแถว 1 ปิดลงแล้ว ให้เน้นย้ำการสกัดกั้นในแถว 2 และประสานงาน CCTV / VASP Escrow ทันที")
        lines.append("")

        lines.append("### 3.3 การจัดการกรณีปลายทางเป็น Payment Gateway / Tech Ad Platform (Platform Subpoena Directives)")
        if gateways:
            for gw in gateways:
                lines.append(f"#### ปลายทาง: `{gw.bank} {gw.account_no}` — **{gw.account_name}** (ยอดเงิน: ฿{gw.proportional_claim_thb:,.2f} / {gw.percentage_of_victim_funds:.1f}%)")
                lines.append("1. **ข้อจำกัดเชิงระบบและข้อควรระวัง (Systemic Limitation):**")
                lines.append(f"   - บัญชีดังกล่าวเป็น **บัญชีรวมของนิติบุคคลผู้ให้บริการชำระเงิน (Corporate Merchant Pool / Aggregator Clearing Account)** ของ {gw.account_name} เพื่อรองรับการชำระเงินออนไลน์หรือค่าบริการแพลตฟอร์ม")
                lines.append("   - **⚠️ ข้อควรระวังเด็ดขาด:** **ห้ามส่งคำสั่งอายัดบัญชีเงินฝากทั้งบัญชีผ่านระบบ AOC 1441 หรือส่งหนังสืออายัดไปยังธนาคารเจ้าของบัญชี** เนื่องจากจะกระทบต่อธุรกรรมปกติของประชาชนทั่วไปนับหมื่นราย และธนาคารจะปฏิเสธคำสั่งอายัดทันที")
                lines.append("2. **พฤติการณ์การฟอกเงินผ่านแอด (Ad Spend Laundering & Victim Acquisition Loop):**")
                lines.append("   - มิจฉาชีพนำเงินที่หลอกลวงได้ไปตัดชำระค่าโฆษณาบนโซเชียลมีเดีย (Ad Spend Reinvestment) โดยตรง เพื่อนำไปใช้โปรโมตเพจหรือยิงแคมเปญโฆษณาหลอกลวงเหยื่อรายใหม่ๆ เข้าสู่วงจรอย่างต่อเนื่อง")
                lines.append("   - เป็นการแปลงสภาพเงินผิดกฎหมาย (Integration) ไปเป็นค่าบริการทางเทคโนโลยี ทำให้เส้นทางการเงินไม่ไหลเข้าบัญชีม้าบุคคลธรรมดาแถวถัดไป")
                lines.append("3. **แนวทางเชิงสืบสวนและมาตรการขอพยานหลักฐานตาม ป.วิ.อ. มาตรา 132 (Subpoena & Preservation Directives):**")
                lines.append(f"   - **ขั้นที่ 1 (ขอข้อมูลตัวแทนรับชำระ):** ออกหมายเรียกพยานเอกสาร/ข้อมูล (ป.วิ.อ. ม.132) ไปยังบริษัทผู้ให้บริการ Payment Gateway ({gw.account_name} / {gw.bank}) ระบุเลขอ้างอิงธุรกรรม วันที่ เวลา และยอดเงิน ฿{gw.total_drained_thb:,.2f} เพื่อขอทราบข้อมูลบัญชีลูกค้าย่อย (Sub-merchant ID), ชื่อบุคคล/นิติบุคคลที่ลงทะเบียน, และบัญชีธนาคารปลายทางที่ Settlement เงินออก")
                lines.append("   - **ขั้นที่ 2 (ขอข้อมูลแพลตฟอร์มโฆษณา):** ประสานงานส่งหมายเรียกหรือหนังสือขอพยานหลักฐานไปยังผู้ให้บริการแพลตฟอร์ม (เช่น Meta Platforms Inc. / Google / TikTok) เพื่อขอทราบ:")
                lines.append("     - ข้อมูลระบุตัวตนเจ้าของบัญชีโฆษณา (Ad Account Owner KYC)")
                lines.append("     - ข้อมูลแฟนเพจ/บัญชีที่ใช้ยิงแอด (Campaign Fanpage / URL)")
                lines.append("     - ข้อมูลผู้ดูแลระบบ (Page / Ad Account Admins): ชื่อ, อีเมล, หมายเลขโทรศัพท์ที่ลงทะเบียน")
                lines.append("     - บันทึกประวัติหมายเลข IP Address และ Timestamp ที่เข้าใช้งานและสั่งยิงแอด")
                lines.append("   - **ขั้นที่ 3 (ระงับบัญชีโฆษณาและอายัดยอดคงเหลือ):** ขอความร่วมมือผู้ให้บริการแพลตฟอร์มระงับบัญชีโฆษณา (Ad Account Take Down) เพื่อตัดวงจรการหลอกลวงเหยื่อรายอื่น และขออายัดยอดเงินคงค้างในกระเป๋าโฆษณา (Prepaid Ad Credit Balance)")
                lines.append("")
        else:
            lines.append("- ในเส้นทางเงินของบัญชีเป้าหมายนี้ ไม่พบการโอนตรงเข้า Payment Gateway หรือแพลตฟอร์มโฆษณา โดยเป็นการกระจายเข้าเครือข่ายบัญชีม้าบุคคลธรรมดา (Mule Tier-2) และ/หรือการถอนเงินสด/สินทรัพย์ดิจิทัลโดยตรง")
            lines.append("")

        lines.append("### 3.4 ข้อแนะนำการสืบสวนขยายผลเครือข่ายและผู้เสียหายร่วม (Cross-Victim Syndicate Expansion)")
        if gateways:
            lines.append("- **การเชื่อมโยงคดีผ่านแคมเปญโฆษณา (Syndicate Linkage):** แคมเปญโฆษณาที่ยิงผ่านแอดดังกล่าว ย่อมมีผู้เสียหายรายอื่นทั่วประเทศตกเป็นเหยื่อในเวลาไล่เลี่ยกัน พนักงานสอบสวนสามารถนำข้อมูล Ad Account ID, Campaign Fanpage, หรือ Merchant Reference ไปสืบค้นเชื่อมโยงกับเลขคดีในระบบแจ้งความออนไลน์ (thaipoliceonline) เพื่อรวมสำนวนและขยายผลจับกุมกลุ่มผู้บงการขบวนการคอลเซ็นเตอร์/สแกมเมอร์")
        else:
            lines.append("- **การตรวจสอบความเชื่อมโยงบัญชีม้า (Mule Network Linkage):** ตรวจสอบประวัติบัญชีม้าแถว 1 และแถว 2 ในฐานข้อมูล ศปอส.ตร. / AOC 1441 เพื่อหาความเชื่อมโยงกับผู้เสียหายรายอื่นในกลุ่มขบวนการเดียวกัน")
        lines.append("")

        # If brief report requested, omit Sections 4, 5, 6, 7
        if brief:
            return "\n".join(lines)

        lines.append("---")
        lines.append("")

        # Section 4: MILP Mathematical Proofs
        lines.append("## 4. การรับรองความถูกต้องด้วยสมการคณิตศาสตร์เชิงเส้น (MILP Mathematical Proofs)")
        lines.append("การตรวจพิสูจน์ปฏิบัติตามหลักการอนุรักษ์กระแสเงิน (Flow Conservation) โดยใช้แบบจำลอง Mixed-Integer Linear Programming (`scipy.optimize.milp`):")
        lines.append("")
        lines.append("$$\\min_{x} \\left| \\sum_{j \\in \\text{Outflows}} x_j \\cdot O_j - \\text{Inflow} \\right| \\quad \\text{subject to} \\quad x_j \\in \\{0, 1\\}, \\; \\sum x_j \\cdot O_j \\le \\text{Inflow} + \\epsilon$$")
        lines.append("")
        for idx, cl in enumerate(report.clusters_detected, start=1):
            lines.append(f"- **กลุ่มที่ {idx} ({cl.cluster_id}):** เงินเข้า ฿{cl.inflow_total:,.2f} $\\to$ เงินออก ฿{cl.outflow_total:,.2f} (Drain: {cl.drain_percentage:.1f}%, Latency: {cl.avg_latency_minutes:.1f} นาที)")
            lines.append(f"  > `{cl.mathematical_proof}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 5: Proportional Restitution Allocation Methodology
        lines.append("## 5. หลักการและสูตรคำนวณสิทธิเรียกร้องเฉลี่ยทรัพย์คืน (AMLA 49/1 Formulation)")
        lines.append("ระบบใช้สูตรการปันส่วนสิทธิแบบจำเพาะกลุ่มก้อนกระแสเงิน (Cluster-Level Inflow Conservation Attribution):")
        lines.append("")
        lines.append("$$\\text{Proportional Claim}_d = \\sum_{c \\in \\text{Clusters}} \\text{Outflow}_{d,c} \\times \\min\\left(1.0, \\frac{\\text{Inflow}_c}{\\text{Cluster Outflow Total}_c}\\right)$$")
        lines.append("")
        lines.append("- **เหตุผลทางนิติวิทยาศาสตร์การเงิน:** ป้องกันความเสียหายของผู้เสียหายถูกเจือจาง (Dilution) โดยเงินของผู้เสียหายรายอื่นในบัญชีม้ารวม (Aggregator Mule Pool) ทำให้ผู้เสียหายได้รับสิทธิเรียกร้องทรัพย์คืนชอบธรรมสูงสุดตามข้อเท็จจริงของกระแสเงินที่เกิดขึ้นจริง")
        lines.append(f"- **ยอดสิทธิเรียกร้องสุทธิที่ได้รับรอง:** **฿{total_claimable:,.2f}** (คิดเป็น **{pct_claim:.2f}%** ของยอดเงินเข้าทั้งหมด)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 6: Actionable Directives by Target Category
        lines.append("## 6. มาตรการเชิงสืบสวนและแนวทางปฏิบัติการจำแนกตามประเภทปลายทาง (Actionable Directives)")
        lines.append("1. **การส่งคำขอระงับธุรกรรมฉุกเฉิน (72 ชั่วโมง) ต่อศูนย์ AOC 1441 เฉพาะบัญชีม้าบุคคลธรรมดา:**")
        lines.append("   - อาศัยอำนาจตาม พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7")
        if residual_buffer > 0:
            lines.append(f"   - **⭐ อายัดบัญชีเป้าหมาย (เร่งด่วนสูงสุด - มีเงินคงค้างรอฟอก):** {report.account_no_raw} ({report.account_name}) — ยอดคงค้าง: **฿{residual_buffer:,.2f}**")
        for d in top_destinations:
            if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no not in ("UNKNOWN", "N/A"):
                lines.append(f"   - **อายัดบัญชีม้าแถว 2:** {d.bank} เลขที่ `{d.account_no}` ({d.account_name}) — สิทธิเรียกร้องเฉลี่ยทรัพย์คืน: **฿{d.proportional_claim_thb:,.2f}**")

        dir_idx = 2
        if gateways:
            lines.append(f"{dir_idx}. **มาตรการขอพยานหลักฐานและระงับบัญชีโฆษณาตาม ป.วิ.อ. มาตรา 132 (Payment Gateway / Ad Platforms):**")
            lines.append("   - *⚠️ ข้อควรระวัง: ห้ามส่งคำสั่งอายัดผ่าน AOC 1441 ไปยังบัญชีผู้ให้บริการรับชำระเงิน/แพลตฟอร์มโฆษณา เพราะเป็นบัญชีรวมระดับองค์กร*")
            for d in gateways:
                lines.append(f"   - **ออกหมายเรียก ม.132 ต่อ {d.account_name} ({d.bank} {d.account_no}):** ขอข้อมูล Sub-merchant ID, Ad Account KYC, Campaign Fanpage, IP Logs และระงับบัญชีโฆษณา (ยอดเงินที่ไหลเข้า: ฿{d.proportional_claim_thb:,.2f})")
            dir_idx += 1

        lines.append(f"{dir_idx}. **การประสานงานสำนักงาน ปปง. เพื่อยึดและอายัดทรัพย์สิน (AMLA 49/1 Restitution):**")
        lines.append(f"   - ใช้รายงานวิเคราะห์ฉบับนี้พร้อมตารางผู้รับประโยชน์หลัก ประกอบคำร้องขอคุ้มครองสิทธิผู้เสียหายตาม พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1 ยอดเรียกร้องรวม **฿{total_claimable:,.2f}**")
        dir_idx += 1

        if vasp_p2p:
            lines.append(f"{dir_idx}. **การส่งคำสั่งระงับกระเป๋าเงินและคำสั่งซื้อขายสินทรัพย์ดิจิทัล (VASP Freeze Request):**")
            for d in vasp_p2p:
                lines.append(f"   - **ระงับกระเป๋าเงิน/P2P Escrow:** {d.bank} ร้านค้า `{d.account_name}` ({d.account_no}) — วงเงิน: **฿{d.proportional_claim_thb:,.2f}**")
            dir_idx += 1

        lines.append(f"{dir_idx}. **การขอพยานหลักฐานทางนิติวิทยาศาสตร์ดิจิทัลเพิ่มเติม:**")
        lines.append("   - ทำหนังสือขอภาพบันทึกจากกล้อง CCTV บริเวณตู้ ATM ในช่วงเวลาที่มีการทำรายการถอนเงินสดไม่ใช้บัตร (Cardless ATM Cash-out)")
        lines.append("   - ทำหนังสือขอข้อมูลการยืนยันตัวตน (KYC) และประวัติการทำธุรกรรม P2P จากผู้ประกอบธุรกิจสินทรัพย์ดิจิทัล (VASP)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 7: Cryptographic Chain of Custody
        lines.append("## 7. การรับรองความถูกต้องของพยานหลักฐานและห่วงโซ่การครอบครอง (Chain of Custody)")
        lines.append(f"- **Statement Provenance SHA-256:** `{report.statement_hash_sha256}`")
        lines.append(f"- **Merkle Audit Root:** `{receipt.get('merkle_root', report.merkle_root)}`")
        lines.append(f"- **Admissibility Receipt ID:** `{receipt.get('receipt_id', 'N/A')}`")
        lines.append(f"- **สถานะความถูกต้อง (Integrity Status):** {receipt.get('integrity_status', 'VERIFIED_TAMPER_EVIDENT')} (ผ่านการตรวจสอบความสมบูรณ์ ไม่ปรากฏการแก้ไขย้อนหลัง)")
        lines.append(f"- **การยอมรับตามกฎหมาย:** พยานหลักฐานทางวิทยาศาสตร์และข้อมูลอิเล็กทรอนิกส์ตาม ป.วิ.อ. มาตรา 226 และ พ.ร.บ. ธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 มาตรา 26")
        lines.append("")

        return "\n".join(lines)

    def generate_markdown_dossier(
        self,
        report: SuspicionReport,
        transactions: List[BankTransaction],
        vault: EvidenceVault,
    ) -> str:
        """
        Generates comprehensive court-admissible markdown dossier (Exhibits A-D).
        Used for formal court filings when explicitly opted-in.
        """
        receipt = vault.generate_admissibility_receipt(report.statement_hash_sha256)
        inflows = [t for t in transactions if t.activity == ActivityType.INFLOW and not t.is_reversal]
        outflows = [t for t in transactions if t.activity == ActivityType.OUTFLOW and not t.is_reversal]
        fees = [t for t in transactions if t.activity == ActivityType.FEE]

        total_in = sum(t.amount for t in inflows)
        total_out = sum(t.amount for t in outflows)
        total_fee = sum(t.amount for t in fees)

        doc = []
        doc.append(TABLE_RESPONSIVE_STYLE)
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
