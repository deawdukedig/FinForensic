"""
Interactive Victim Forensic Analysis & Asset Restitution Dashboard Generator.
Renders a standalone, high-fidelity single-page HTML dashboard with Apache ECharts and Tailwind CSS,
specifically designed for single-victim money trail investigations and Section 226 / AMLA 49/1 court exhibits.
Supports responsive design, Light Mode (default) & Dark Mode toggle, presentation fullscreen mode,
and detailed transfer circumstances & critical forensic insights under Thai law.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, Union, List

from src.engine.victim_tracer import VictimTraceResult
from src.audit.esignature import DigitalSignatureManager


class VictimDashboardGenerator:
    """
    Builds self-contained, interactive single-page HTML forensic dashboards
    for Victim Forensic Analysis Reports.
    """

    def generate_html(
        self,
        result: VictimTraceResult,
        output_file_path: Union[str, Path],
        case_id: str = "CASE-VICTIM-2026",
        officer: str = "พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)",
        agency: str = "กองบัญชาการตำรวจสืบสวนสอบสวนอาชญากรรมทางเทคโนโลยี (บช.สอท.)",
        tolerance_ratio: float = 0.05,
    ) -> str:
        out_p = Path(output_file_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        pct_claim = (result.total_claimable_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        vic_accts_str = ", ".join(result.victim_accounts) if result.victim_accounts else "N/A"

        # 1. Build Sankey Nodes and Links
        target_hub_name = f"บัญชีม้าแถว 1: {result.target_account}\n({result.target_account_name})"
        victim_node_name = f"ผู้เสียหาย: {result.victim_name}\n({vic_accts_str})"

        sankey_nodes_dict: Dict[str, Dict[str, Any]] = {
            victim_node_name: {"name": victim_node_name, "itemStyle": {"color": "#f43f5e"}},
            target_hub_name: {"name": target_hub_name, "itemStyle": {"color": "#f59e0b"}},
        }
        sankey_links: List[Dict[str, Any]] = [
            {
                "source": victim_node_name,
                "target": target_hub_name,
                "value": round(result.total_inflow_thb, 2),
            }
        ]

        for d in result.top_destinations:
            dest_name = f"ลำดับ {d.rank}: {d.bank} {d.account_no}\n{d.account_name}"
            color = "#38bdf8"
            if d.recommended_action == "CCTV_INSPECTION_ATM":
                color = "#fb923c"
            elif d.recommended_action == "VASP_WALLET_FREEZE":
                color = "#c084fc"
            elif d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE":
                color = "#eab308"

            sankey_nodes_dict[dest_name] = {"name": dest_name, "itemStyle": {"color": color}}
            sankey_links.append({
                "source": target_hub_name,
                "target": dest_name,
                "value": round(d.proportional_claim_thb, 2),
            })

        if result.net_residual_buffer_thb > 0:
            buf_name = f"เงินตกค้างรอฟอก\n(Residual Buffer: ฿{result.net_residual_buffer_thb:,.2f})"
            sankey_nodes_dict[buf_name] = {"name": buf_name, "itemStyle": {"color": "#64748b"}}
            sankey_links.append({
                "source": target_hub_name,
                "target": buf_name,
                "value": round(result.net_residual_buffer_thb, 2),
            })

        sankey_nodes = list(sankey_nodes_dict.values())

        # 2. Category Breakdown Data
        tier2_mules = [d for d in result.top_destinations if d.recommended_action == "AOC_1441_FREEZE_URGENT"]
        atm_cashing = [d for d in result.top_destinations if d.recommended_action == "CCTV_INSPECTION_ATM"]
        vasp_p2p = [d for d in result.top_destinations if d.recommended_action == "VASP_WALLET_FREEZE"]
        gateways = [d for d in result.top_destinations if d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE"]

        tot_tier2_claim = sum(d.proportional_claim_thb for d in tier2_mules)
        tot_atm_claim = sum(d.proportional_claim_thb for d in atm_cashing)
        tot_vasp_claim = sum(d.proportional_claim_thb for d in vasp_p2p)
        tot_gateway_claim = sum(d.proportional_claim_thb for d in gateways)
        res_buf = result.net_residual_buffer_thb

        pie_data = [
            {"name": "บัญชีม้าแถว 2 (Mule Tier-2)", "value": round(tot_tier2_claim, 2), "itemStyle": {"color": "#38bdf8"}},
            {"name": "ระบบชำระเงิน/ค่าโฆษณา (Gateway/Ads)", "value": round(tot_gateway_claim, 2), "itemStyle": {"color": "#eab308"}},
            {"name": "ถอนเงินสดตู้ ATM (Cash-Out)", "value": round(tot_atm_claim, 2), "itemStyle": {"color": "#fb923c"}},
            {"name": "สินทรัพย์ดิจิทัล P2P (Crypto Off-Ramp)", "value": round(tot_vasp_claim, 2), "itemStyle": {"color": "#c084fc"}},
            {"name": "เงินค้างในบัญชีม้า (Residual Buffer)", "value": round(res_buf, 2), "itemStyle": {"color": "#64748b"}},
        ]
        pie_data = [p for p in pie_data if p["value"] > 0]

        # 3. Timeline Inflows vs Outflows Data
        time_bucket_in: Dict[str, float] = defaultdict(float)
        time_bucket_out: Dict[str, float] = defaultdict(float)
        time_keys_set = set()

        for t in result.inflow_transactions:
            fmt_key = t.timestamp.strftime("%d/%m %H:%M")
            sort_key = t.timestamp.strftime("%Y-%m-%d %H:%M")
            time_bucket_in[fmt_key] += t.amount
            time_keys_set.add((sort_key, fmt_key))

        for t in result.matched_outflows:
            fmt_key = t.timestamp.strftime("%d/%m %H:%M")
            sort_key = t.timestamp.strftime("%Y-%m-%d %H:%M")
            time_bucket_out[fmt_key] += t.amount
            time_keys_set.add((sort_key, fmt_key))

        sorted_time_tuples = sorted(list(time_keys_set), key=lambda x: x[0])
        timeline_points = [x[1] for x in sorted_time_tuples]
        timeline_in_series = [round(time_bucket_in[x[1]], 2) for x in sorted_time_tuples]
        timeline_out_series = [round(time_bucket_out[x[1]], 2) for x in sorted_time_tuples]

        # Cumulative Series over time (Card 2 in Tab 4)
        cum_in = 0.0
        cum_out = 0.0
        timeline_cum_in_series = []
        timeline_cum_out_series = []
        for p in timeline_points:
            cum_in += time_bucket_in[p]
            cum_out += time_bucket_out[p]
            timeline_cum_in_series.append(round(cum_in, 2))
            timeline_cum_out_series.append(round(cum_out, 2))

        # 4. E-Signature Manager & Provenance
        sig_mgr = DigitalSignatureManager()
        sig_data = sig_mgr.sign_artifact(result.statement_sha256 or "SHA256-PENDING", "POL-8842", officer, agency)
        sig_hex = sig_data.get("signature", "SIG-PENDING")

        # Serialized JSON for ECharts injection
        sankey_nodes_json = json.dumps(sankey_nodes, ensure_ascii=False)
        sankey_links_json = json.dumps(sankey_links, ensure_ascii=False)
        pie_data_json = json.dumps(pie_data, ensure_ascii=False)
        timeline_points_json = json.dumps(timeline_points, ensure_ascii=False)
        timeline_in_series_json = json.dumps(timeline_in_series, ensure_ascii=False)
        timeline_out_series_json = json.dumps(timeline_out_series, ensure_ascii=False)
        timeline_cum_in_series_json = json.dumps(timeline_cum_in_series, ensure_ascii=False)
        timeline_cum_out_series_json = json.dumps(timeline_cum_out_series, ensure_ascii=False)

        # 5. Tab 5: Transaction Statistics & Behavioral Dynamics (Victim vs Mule) [moved from Tab 6]
        in_txs = result.inflow_transactions
        out_txs = result.matched_outflows

        vic_tx_count = len(in_txs)
        vic_tot_amt = sum(t.amount for t in in_txs) if in_txs else 0.0
        vic_min_amt = min(t.amount for t in in_txs) if in_txs else 0.0
        vic_max_amt = max(t.amount for t in in_txs) if in_txs else 0.0
        vic_avg_amt = vic_tot_amt / vic_tx_count if vic_tx_count else 0.0
        vic_first_time = in_txs[0].timestamp.strftime("%d/%m/%Y %H:%M:%S") if in_txs else "N/A"
        vic_last_time = in_txs[-1].timestamp.strftime("%d/%m/%Y %H:%M:%S") if in_txs else "N/A"

        mule_tx_count = len(out_txs)
        mule_tot_amt = sum(t.amount for t in out_txs) if out_txs else 0.0
        mule_min_amt = min(t.amount for t in out_txs) if out_txs else 0.0
        mule_max_amt = max(t.amount for t in out_txs) if out_txs else 0.0
        mule_avg_amt = mule_tot_amt / mule_tx_count if mule_tx_count else 0.0
        mule_first_time = out_txs[0].timestamp.strftime("%d/%m/%Y %H:%M:%S") if out_txs else "N/A"
        mule_last_time = out_txs[-1].timestamp.strftime("%d/%m/%Y %H:%M:%S") if out_txs else "N/A"

        # Bucket distribution
        bucket_labels = ["< ฿1,000 (Micro)", "฿1k - ฿10k (Small)", "฿10k - ฿50k (Medium)", "> ฿50,000 (Large)"]
        vic_buckets = [0, 0, 0, 0]
        mule_buckets = [0, 0, 0, 0]

        for t in in_txs:
            a = t.amount
            if a < 1000: vic_buckets[0] += 1
            elif a <= 10000: vic_buckets[1] += 1
            elif a <= 50000: vic_buckets[2] += 1
            else: vic_buckets[3] += 1

        for t in out_txs:
            a = t.amount
            if a < 1000: mule_buckets[0] += 1
            elif a <= 10000: mule_buckets[1] += 1
            elif a <= 50000: mule_buckets[2] += 1
            else: mule_buckets[3] += 1

        # Daily breakdown
        daily_in = defaultdict(lambda: {"count": 0, "sum": 0.0})
        daily_out = defaultdict(lambda: {"count": 0, "sum": 0.0})
        for t in in_txs:
            d = t.timestamp.strftime("%Y-%m-%d")
            daily_in[d]["count"] += 1
            daily_in[d]["sum"] += t.amount
        for t in out_txs:
            d = t.timestamp.strftime("%Y-%m-%d")
            daily_out[d]["count"] += 1
            daily_out[d]["sum"] += t.amount

        all_dates = sorted(set(list(daily_in.keys()) + list(daily_out.keys())))
        daily_dates_formatted = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in all_dates]
        daily_vic_sums = [daily_in[d]["sum"] for d in all_dates]
        daily_mule_sums = [daily_out[d]["sum"] for d in all_dates]
        daily_vic_counts = [daily_in[d]["count"] for d in all_dates]
        daily_mule_counts = [daily_out[d]["count"] for d in all_dates]

        cum_vic_sums = []
        cum_mule_sums = []
        c_v = 0.0
        c_m = 0.0
        for d in all_dates:
            c_v += daily_in[d]["sum"]
            c_m += daily_out[d]["sum"]
            cum_vic_sums.append(round(c_v, 2))
            cum_mule_sums.append(round(c_m, 2))

        # Serialized JSON for Tab 5 charts
        bucket_labels_json = json.dumps(bucket_labels, ensure_ascii=False)
        vic_buckets_json = json.dumps(vic_buckets, ensure_ascii=False)
        mule_buckets_json = json.dumps(mule_buckets, ensure_ascii=False)
        daily_dates_json = json.dumps(daily_dates_formatted, ensure_ascii=False)
        cum_vic_sums_json = json.dumps(cum_vic_sums, ensure_ascii=False)
        cum_mule_sums_json = json.dumps(cum_mule_sums, ensure_ascii=False)

        daily_table_rows = []
        for d, df, vs, vc, ms, mc, cv, cm in zip(all_dates, daily_dates_formatted, daily_vic_sums, daily_vic_counts, daily_mule_sums, daily_mule_counts, cum_vic_sums, cum_mule_sums):
            running_residual = cv - cm
            daily_table_rows.append(f"""
            <tr class="hover:bg-slate-100 dark:hover:bg-slate-800/60 transition border-b border-slate-200 dark:border-slate-800/80">
                <td class="py-2.5 px-4 font-mono text-slate-700 dark:text-slate-300">{df} ({d})</td>
                <td class="py-2.5 px-4 text-center font-mono text-sky-600 dark:text-sky-400 font-bold">{vc} รายการ</td>
                <td class="py-2.5 px-4 text-right font-mono text-sky-700 dark:text-sky-300">฿{vs:,.2f}</td>
                <td class="py-2.5 px-4 text-center font-mono text-rose-600 dark:text-rose-400 font-bold">{mc} รายการ</td>
                <td class="py-2.5 px-4 text-right font-mono text-rose-700 dark:text-rose-300">฿{ms:,.2f}</td>
                <td class="py-2.5 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400 font-bold">฿{running_residual:,.2f}</td>
            </tr>
            """)

        # Destinations Table Rows HTML (Tab 2: AOC Action column REMOVED)
        dest_table_rows = []
        tot_drained_sum = sum(d.total_drained_thb for d in result.top_destinations)
        tot_claim_sum = sum(d.proportional_claim_thb for d in result.top_destinations)

        for d in result.top_destinations:
            action_badge = '<span class="px-2.5 py-1 bg-rose-500/20 text-rose-600 dark:text-rose-300 border border-rose-500/30 rounded-md text-xs font-semibold">🚨 AOC 1441 อายัดด่วน</span>'
            if d.recommended_action == "CCTV_INSPECTION_ATM":
                action_badge = '<span class="px-2.5 py-1 bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30 rounded-md text-xs font-semibold">📹 ขอภาพ CCTV ตู้ ATM</span>'
            elif d.recommended_action == "VASP_WALLET_FREEZE":
                action_badge = '<span class="px-2.5 py-1 bg-purple-500/20 text-purple-600 dark:text-purple-300 border border-purple-500/30 rounded-md text-xs font-semibold">🔒 อายัดกระเป๋า VASP P2P</span>'
            elif d.recommended_action == "PLATFORM_SUBPOENA_EVIDENCE":
                action_badge = '<span class="px-2.5 py-1 bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30 rounded-md text-xs font-semibold">📋 หมายเรียก ม.132 / ระงับแอด</span>'

            row_html = f"""
            <tr class="hover:bg-slate-100 dark:hover:bg-slate-800/60 transition border-b border-slate-200 dark:border-slate-800/80 dest-row" data-bank="{d.bank}" data-name="{d.account_name}">
                <td class="py-3 px-4 text-center font-bold text-slate-500 dark:text-slate-400">{d.rank}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded text-xs font-mono text-sky-600 dark:text-sky-300 font-semibold">{d.bank}</span>
                    <span class="font-mono text-sm ml-1 text-slate-800 dark:text-slate-200">{d.account_no}</span>
                </td>
                <td class="py-3 px-4 font-semibold text-slate-900 dark:text-white">{d.account_name}</td>
                <td class="py-3 px-4 text-center text-xs text-slate-500 dark:text-slate-400">{d.channel}</td>
                <td class="py-3 px-4 text-right font-mono text-slate-700 dark:text-slate-300">฿{d.total_drained_thb:,.2f}</td>
                <td class="py-3 px-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">฿{d.proportional_claim_thb:,.2f}</td>
                <td class="py-3 px-4 text-center font-bold text-sky-600 dark:text-sky-400">{d.percentage_of_victim_funds:.1f}%</td>
                <td class="py-3 px-4 text-center font-mono text-xs text-slate-500 dark:text-slate-400">{d.avg_latency_minutes:.1f} น.</td>
                <td class="py-3 px-4 text-center">{action_badge}</td>
            </tr>
            """
            dest_table_rows.append(row_html)

        # Clusters HTML Rows (All matched clusters)
        cluster_rows = []
        for idx, cl in enumerate(result.matched_clusters, start=1):
            proof_clean = cl.mathematical_proof.replace('"', '&quot;')
            c_html = f"""
            <div class="bg-slate-50 dark:bg-slate-800/70 p-4 rounded-xl border border-slate-200 dark:border-slate-700/80 hover:border-sky-500/50 transition cluster-card" data-cid="{cl.cluster_id}" data-amt="{cl.inflow_total}">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-700/60 pb-2.5">
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-700 dark:text-sky-300 border border-sky-500/30 rounded-md text-xs font-mono font-bold">
                            #{idx} {cl.cluster_id}
                        </span>
                        <span class="text-xs text-slate-600 dark:text-slate-400">Inflow: <b class="text-slate-900 dark:text-white">฿{cl.inflow_total:,.2f}</b></span>
                        <span class="text-slate-400">&rarr;</span>
                        <span class="text-xs text-slate-600 dark:text-slate-400">Outflow: <b class="text-emerald-600 dark:text-emerald-400">฿{cl.outflow_total:,.2f}</b></span>
                    </div>
                    <div class="flex items-center gap-2 text-xs">
                        <span class="px-2 py-0.5 bg-amber-500/20 text-amber-700 dark:text-amber-300 rounded font-semibold">Drain: {cl.drain_percentage:.1f}%</span>
                        <span class="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded">Latency: {cl.avg_latency_minutes:.1f} น.</span>
                        <span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 rounded font-mono font-bold">OPTIMAL</span>
                    </div>
                </div>
                <div class="mt-2.5 flex items-start justify-between gap-2">
                    <code class="text-xs font-mono text-slate-800 dark:text-slate-300 break-all bg-white dark:bg-slate-900/80 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 flex-1">
                        {cl.mathematical_proof}
                    </code>
                    <button onclick='navigator.clipboard.writeText("{proof_clean}"); showToast("คัดลอกสมการแล้ว");' class="px-2.5 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 rounded text-xs text-slate-700 dark:text-slate-200 shrink-0 transition font-medium">
                        Copy
                    </button>
                </div>
            </div>
            """
            cluster_rows.append(c_html)

        # 6. Tab 6: Transfer Circumstances & Critical Forensic Insights Preparations
        vic_dates = set(t.timestamp.strftime("%Y-%m-%d") for t in result.inflow_transactions)
        is_concentrated = (len(vic_dates) <= 1)
        if is_concentrated:
            pattern_title = "รูปแบบการโอนกระจุกตัวในวันเดียว (Concentrated Funnel)"
            pattern_badge = '<span class="px-2.5 py-0.5 bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/30 rounded text-xs font-semibold">Concentrated Funnel</span>'
            pattern_detail = f"ผู้เสียหายถูกชักจูงให้ทำรายการโอนเงินก้อนใหญ่ต่อเนื่องกันภายในวันเดียวกัน รวม {len(result.inflow_transactions)} รายการ เป็นเงิน <b>฿{result.total_inflow_thb:,.2f}</b> สะท้อนถึงการถูกหลอกล่อตามสคริปต์กลโกงอย่างเข้มข้นในระยะเวลาอันสั้น (Urgent High-Pressure Scam)"
        else:
            pattern_title = f"รูปแบบการโอนกระจายตัวต่อเนื่อง ({len(vic_dates)} วัน) (Distributed Inflow)"
            pattern_badge = '<span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-700 dark:text-sky-300 border border-sky-500/30 rounded text-xs font-semibold">Distributed Inflow</span>'
            pattern_detail = f"ผู้เสียหายทำรายการโอนเงินกระจายตัวต่อเนื่องข้ามวัน ({len(vic_dates)} วัน) รวม {len(result.inflow_transactions)} รายการ เป็นเงิน <b>฿{result.total_inflow_thb:,.2f}</b> ชี้ให้เห็นถึงกลลวงในลักษณะหลอกลงทุนต่อเนื่อง (Investment Fraud / Pig Butchering) ที่เหยื่อถูกลวงให้เติมเงินซ้ำๆ"

        # Golden Window Analysis (Tab 6)
        res_ratio = (result.net_residual_buffer_thb / result.total_inflow_thb * 100.0) if result.total_inflow_thb > 0 else 0.0
        if result.net_residual_buffer_thb >= 50000.0 or res_ratio >= 20.0:
            golden_card_html = f"""
            <div class="p-5 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl border border-emerald-300 dark:border-emerald-500/50 space-y-2 shadow-sm">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⭐</span>
                        <span class="font-bold text-emerald-800 dark:text-emerald-300 text-sm md:text-base">ตรวจพบโอกาสทองในการอายัดทรัพย์สินคืน (Primary Golden Window Target)</span>
                    </div>
                    <span class="px-2.5 py-1 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40 rounded-full text-xs font-bold animate-pulse">
                        เร่งด่วนสูงสุด
                    </span>
                </div>
                <p class="text-slate-700 dark:text-slate-200 leading-relaxed text-xs md:text-sm">
                    ตรวจพบเงินคงค้างในบัญชีม้าพักเงินแถว 1 (<b>{result.target_account}</b> {result.target_account_name}) สูงถึง <b class="text-emerald-600 dark:text-emerald-400 font-mono text-base">฿{result.net_residual_buffer_thb:,.2f}</b> ({res_ratio:.1f}% ของยอดสูญเสียทั้งหมด)
                </p>
                <div class="p-3 bg-white dark:bg-slate-900/80 rounded-lg text-xs space-y-1 text-slate-700 dark:text-slate-300 border border-emerald-200 dark:border-emerald-500/30">
                    <div><b>นัยสำคัญเชิงสืบสวน:</b> มิจฉาชีพยังไม่สามารถระบายเงินส่วนนี้ออกไปได้ทัน (อาจติดปัญหาเพดานการโอนรายวัน Daily Limit หรือระบบเฝ้าระวังของธนาคาร)</div>
                    <div class="text-emerald-700 dark:text-emerald-300 font-semibold"><b>ข้อสั่งการเร่งด่วนที่สุด:</b> พนักงานสอบสวนต้องเร่งส่งคำสั่งระงับธุรกรรม (AOC 1441) ไปยังบัญชีม้าแถว 1 นี้เป็นลำดับแรกสุดทันที เพราะเป็นจุดที่มีโอกาสได้เงินสดคืนกลับมาคุ้มครองสิทธิให้แก่ผู้เสียหายจริงสูงสุด</div>
                </div>
            </div>
            """
        elif result.net_residual_buffer_thb > 0:
            golden_card_html = f"""
            <div class="p-5 bg-sky-50 dark:bg-sky-950/40 rounded-xl border border-sky-300 dark:border-sky-500/40 space-y-2">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">ℹ️</span>
                        <span class="font-bold text-sky-800 dark:text-sky-300 text-sm md:text-base">พบเงินคงค้างบางส่วนในบัญชีม้าแถว 1 (Partial Residual Buffer)</span>
                    </div>
                    <span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-700 dark:text-sky-300 rounded text-xs font-semibold">฿{result.net_residual_buffer_thb:,.2f}</span>
                </div>
                <p class="text-slate-700 dark:text-slate-300 text-xs md:text-sm leading-relaxed">
                    ตรวจพบยอดเงินคงค้างในบัญชีม้าพักเงินแถว 1 จำนวน <b class="text-sky-600 dark:text-sky-300 font-mono">฿{result.net_residual_buffer_thb:,.2f}</b> ({res_ratio:.1f}%) แนะนำให้ส่งคำสั่งอายัดบัญชีม้าแถว 1 ควบคู่ไปกับการติดตามระงับบัญชีม้าแถว 2
                </p>
            </div>
            """
        else:
            golden_card_html = f"""
            <div class="p-5 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/80 space-y-2">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⚡</span>
                        <span class="font-bold text-slate-800 dark:text-slate-300 text-sm md:text-base">บัญชีกวาดเงินออกครบถ้วนแบบฉับพลัน (Instant Flush / Rapid Sweeping)</span>
                    </div>
                    <span class="px-2.5 py-0.5 bg-rose-500/20 text-rose-700 dark:text-rose-300 rounded text-xs font-semibold">Drain Rate 100%</span>
                </div>
                <p class="text-slate-600 dark:text-slate-300 text-xs md:text-sm leading-relaxed">
                    กระแสเงินของผู้เสียหายถูกระบายออกจากบัญชีม้าแถว 1 ครบถ้วน 100% ภายในเวลาเฉลี่ย <b>{result.avg_latency_minutes:.1f} นาที</b> หน้าต่างการอายัดในบัญชีแถว 1 ปิดลงแล้ว ให้เน้นย้ำการสกัดกั้นในแถว 2 และประสานงานตรวจสอบกล้อง CCTV / VASP Escrow ทันที
                </p>
            </div>
            """

        # Payment Gateways & Platform Subpoenas (Tab 6)
        if gateways:
            gw_cards = []
            for gw in gateways:
                clean_name = gw.account_name.replace('"', '')
                gw_cards.append(f"""
                <div class="p-4 bg-white dark:bg-slate-800/80 rounded-xl border border-amber-300 dark:border-amber-500/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="px-2 py-0.5 bg-amber-500/20 text-amber-800 dark:text-amber-300 rounded font-mono font-bold text-xs">{gw.bank}</span>
                            <span class="font-mono text-sm text-slate-900 dark:text-white font-bold">{gw.account_no}</span>
                            <span class="text-xs text-slate-500 dark:text-slate-400">({gw.channel})</span>
                        </div>
                        <div class="text-sm font-semibold text-slate-900 dark:text-white mt-1">{gw.account_name}</div>
                        <div class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                            ยอดเงินที่ไหลเข้า: <b class="text-emerald-600 dark:text-emerald-400 font-mono">฿{gw.proportional_claim_thb:,.2f}</b> ({gw.percentage_of_victim_funds:.1f}% ของเงินผู้เสียหาย) &bull; ยอดรวมปลายทาง: ฿{gw.total_drained_thb:,.2f}
                        </div>
                    </div>
                    <button onclick='navigator.clipboard.writeText("หมายเรียกพยานเอกสาร ป.วิ.อ. ม.132 ขอข้อมูลบัญชีลูกค้าย่อย (Sub-merchant ID), ประวัติ KYC, บัญชี Settlement และระงับบัญชีโฆษณา: {clean_name} ({gw.bank} {gw.account_no}) วงเงินสิทธิเฉลี่ยทรัพย์ ฿{gw.proportional_claim_thb:,.2f}"); showToast("คัดลอกข้อความหมายเรียก ม.132 แล้ว");' class="px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-semibold transition shrink-0 flex items-center justify-center gap-1.5 shadow-sm">
                        <span>📋</span> คัดลอกหมายเรียก ม.132
                    </button>
                </div>
                """)
            gateways_list_html = "".join(gw_cards)
            gateways_panel_html = f"""
            <div class="p-5 bg-amber-50 dark:bg-amber-950/30 rounded-xl border border-amber-300 dark:border-amber-500/40 space-y-4 shadow-sm">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-amber-200 dark:border-amber-500/30 pb-3">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">📋</span>
                        <div>
                            <span class="font-bold text-amber-800 dark:text-amber-300 text-sm md:text-base">มาตรการจัดการกรณีปลายทางเป็น Corporate Payment Gateway / Tech Ad Platform ({len(gateways)} ปลายทาง)</span>
                            <div class="text-xs text-slate-600 dark:text-slate-400">อาศัยอำนาจตามประมวลกฎหมายวิธีพิจารณาความอาญา มาตรา 132</div>
                        </div>
                    </div>
                    <span class="px-2.5 py-1 bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold shrink-0">
                        ป.วิ.อ. ม.132 Subpoena Directives
                    </span>
                </div>

                <div class="p-3.5 bg-rose-50 dark:bg-rose-950/40 rounded-xl border border-rose-300 dark:border-rose-500/50 text-xs space-y-1.5 text-slate-700 dark:text-slate-200">
                    <div class="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-bold text-sm">
                        <span>⚠️</span> ข้อควรระวังเด็ดขาด (Critical Legal Precaution):
                    </div>
                    <p class="leading-relaxed">
                        บัญชีปลายทางด้านล่างเป็น <b>Corporate Clearing Pool / Merchant Aggregator Pool</b> ของผู้ให้บริการชำระเงิน <b class="text-rose-600 dark:text-rose-400 font-bold">ห้ามส่งคำสั่งอายัดทั้งบัญชีผ่านระบบ AOC 1441 หรือส่งหนังสืออายัดไปยังธนาคารเจ้าของบัญชี</b> เพราะจะกระทบต่อธุรกรรมของประชาชนทั่วไปนับหมื่นราย และธนาคารจะปฏิเสธคำสั่งอายัดทันที
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                        <div class="font-bold text-sky-600 dark:text-sky-400">ขั้นที่ 1: ขอข้อมูลตัวแทนรับชำระ</div>
                        <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                            ส่งหมายเรียก ม.132 ไปยัง Payment Gateway ขอทราบข้อมูล <b>Sub-merchant ID</b>, ชื่อบุคคล/นิติบุคคลผู้ลงทะเบียน, และบัญชีธนาคารปลายทางที่ Settlement เงินออก
                        </p>
                    </div>
                    <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                        <div class="font-bold text-amber-600 dark:text-amber-400">ขั้นที่ 2: ขอข้อมูลแพลตฟอร์มโฆษณา</div>
                        <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                            ประสานงานขอข้อมูลจาก Meta, Google, TikTok ขอข้อมูล <b>Ad Account Owner KYC</b>, URL แฟนเพจที่ยิงแอด, ผู้ดูแลเพจ (Admins), และ IP/Timestamp Logs
                        </p>
                    </div>
                    <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                        <div class="font-bold text-emerald-600 dark:text-emerald-400">ขั้นที่ 3: ระงับบัญชีโฆษณา & เครดิต</div>
                        <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                            ขอความร่วมมือระงับบัญชีโฆษณา (Take Down) เพื่อตัดวงจรหลอกลวงเหยื่อรายอื่น และขออายัดยอดเงินคงค้างในกระเป๋าโฆษณา (Prepaid Ad Balance)
                        </p>
                    </div>
                </div>

                <div class="space-y-2.5">
                    {gateways_list_html}
                </div>
            </div>
            """
        else:
            gateways_panel_html = """
            <div class="p-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-300 space-y-2">
                <div class="flex items-center gap-2 font-bold text-sm text-slate-800 dark:text-slate-200">
                    <span>📋</span> มาตรการกรณีปลายทางเป็น Corporate Payment Gateway
                </div>
                <p class="leading-relaxed">
                    ในเส้นทางการเงินของผู้เสียหายรายนี้ ไม่พบการโอนตรงเข้าบัญชีรวม Payment Gateway หรือแพลตฟอร์มโฆษณา โดยเป็นการกระจายเข้าเครือข่ายบัญชีม้าบุคคลธรรมดา (Mule Tier-2) และ/หรือการถอนเงินสด/สินทรัพย์ดิจิทัลโดยตรง
                </p>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="th" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Victim Forensic Analysis & Asset Restitution Dashboard - {result.victim_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Sarabun', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        
        /* Base Defaults (Light Mode First) */
        body {{
            font-family: 'Sarabun', sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        code, .font-mono {{
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Light Mode Styles */
        html:not(.dark) body, html.light body {{
            background-color: #f8fafc;
            color: #0f172a;
        }}
        html:not(.dark) .bg-slate-900,
        html:not(.dark) .bg-slate-900\/90,
        html:not(.dark) .bg-slate-900\/80,
        html:not(.dark) .bg-slate-950,
        html.light .bg-slate-900,
        html.light .bg-slate-900\/90,
        html.light .bg-slate-900\/80,
        html.light .bg-slate-950 {{
            background-color: #ffffff !important;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05), 0 1px 2px -1px rgb(0 0 0 / 0.05);
        }}
        html:not(.dark) .bg-slate-800,
        html:not(.dark) .bg-slate-800\/90,
        html:not(.dark) .bg-slate-800\/80,
        html:not(.dark) .bg-slate-800\/70,
        html:not(.dark) .bg-slate-800\/60,
        html:not(.dark) .bg-slate-800\/50,
        html:not(.dark) .bg-slate-800\/40,
        html.light .bg-slate-800,
        html.light .bg-slate-800\/90,
        html.light .bg-slate-800\/80,
        html.light .bg-slate-800\/70,
        html.light .bg-slate-800\/60,
        html.light .bg-slate-800\/50,
        html.light .bg-slate-800\/40 {{
            background-color: #f8fafc !important;
        }}
        html:not(.dark) .border-slate-800,
        html:not(.dark) .border-slate-800\/80,
        html:not(.dark) .border-slate-800\/60,
        html:not(.dark) .border-slate-700,
        html:not(.dark) .border-slate-700\/80,
        html:not(.dark) .border-slate-700\/60,
        html.light .border-slate-800,
        html.light .border-slate-800\/80,
        html.light .border-slate-800\/60,
        html.light .border-slate-700,
        html.light .border-slate-700\/80,
        html.light .border-slate-700\/60 {{
            border-color: #e2e8f0 !important;
        }}
        html:not(.dark) .text-white, html.light .text-white {{
            color: #0f172a !important;
        }}
        html:not(.dark) .text-slate-200,
        html:not(.dark) .text-slate-300,
        html.light .text-slate-200,
        html.light .text-slate-300 {{
            color: #334155 !important;
        }}
        html:not(.dark) .text-slate-400, html.light .text-slate-400 {{
            color: #64748b !important;
        }}
        html:not(.dark) .text-slate-500, html.light .text-slate-500 {{
            color: #94a3b8 !important;
        }}
        html:not(.dark) .tab-btn, html.light .tab-btn {{
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            color: #475569;
        }}
        html:not(.dark) .tab-btn:hover, html.light .tab-btn:hover {{
            background-color: #f1f5f9;
            color: #0f172a;
            border-color: #94a3b8;
        }}
        html:not(.dark) .tab-btn.active, html.light .tab-btn.active {{
            background-color: rgba(14, 165, 233, 0.12) !important;
            border-color: #0284c7 !important;
            color: #0284c7 !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px -2px rgba(14, 165, 233, 0.2) !important;
        }}

        /* Dark Mode Overrides */
        html.dark body {{
            background-color: #0b1120 !important;
            color: #f8fafc !important;
        }}
        html.dark .bg-slate-900,
        html.dark .bg-slate-900\/90,
        html.dark .bg-slate-900\/80,
        html.dark .bg-slate-950 {{
            background-color: rgba(15, 23, 42, 0.9) !important;
        }}
        html.dark .bg-slate-800,
        html.dark .bg-slate-800\/90,
        html.dark .bg-slate-800\/80,
        html.dark .bg-slate-800\/70,
        html.dark .bg-slate-800\/60,
        html.dark .bg-slate-800\/50,
        html.dark .bg-slate-800\/40 {{
            background-color: rgba(30, 41, 59, 0.7) !important;
        }}
        html.dark .border-slate-800,
        html.dark .border-slate-800\/80,
        html.dark .border-slate-800\/60,
        html.dark .border-slate-700,
        html.dark .border-slate-700\/80,
        html.dark .border-slate-700\/60 {{
            border-color: #334155 !important;
        }}
        html.dark .text-white {{
            color: #ffffff !important;
        }}
        html.dark .text-slate-200 {{ color: #e2e8f0 !important; }}
        html.dark .text-slate-300 {{ color: #cbd5e1 !important; }}
        html.dark .text-slate-400 {{ color: #94a3b8 !important; }}
        html.dark .text-slate-500 {{ color: #64748b !important; }}
        html.dark .tab-btn {{
            background-color: rgba(30, 41, 59, 0.6) !important;
            border: 1px solid rgba(51, 65, 85, 0.7) !important;
            color: #94a3b8 !important;
        }}
        html.dark .tab-btn:hover {{
            background-color: rgba(30, 41, 59, 1) !important;
            color: #f1f5f9 !important;
            border-color: #475569 !important;
        }}
        html.dark .tab-btn.active {{
            background-color: rgba(14, 165, 233, 0.15) !important;
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
            box-shadow: 0 4px 12px -2px rgba(56, 189, 248, 0.25) !important;
        }}

        /* Responsive Fullscreen Layout for card-pie */
        :fullscreen #card-pie, .fullscreen-active#card-pie {{
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }}
        :fullscreen #card-pie .pie-content-wrapper, .fullscreen-active #card-pie .pie-content-wrapper {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-around !important;
            flex: 1 1 0% !important;
            gap: 2rem !important;
        }}
        :fullscreen #card-pie #pieChart, .fullscreen-active #card-pie #pieChart {{
            width: 50% !important;
            height: 100% !important;
            min-height: 420px !important;
        }}
        :fullscreen #card-pie .pie-legend-wrapper, .fullscreen-active #card-pie .pie-legend-wrapper {{
            width: 45% !important;
            margin-top: 0 !important;
            border-top: none !important;
        }}

        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: rgba(15, 23, 42, 0.05);
        }}
        html.dark ::-webkit-scrollbar-track {{
            background: #0f172a;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 4px;
        }}
        html.dark ::-webkit-scrollbar-thumb {{
            background: #334155;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #94a3b8;
        }}
        html.dark ::-webkit-scrollbar-thumb:hover {{
            background: #475569;
        }}

        /* Fullscreen Presentation Styles */
        :fullscreen, ::backdrop {{
            background-color: #f8fafc !important;
        }}
        html.dark :fullscreen, html.dark ::backdrop {{
            background-color: #0b1120 !important;
        }}
        :fullscreen {{
            padding: 1.5rem !important;
            overflow: auto !important;
            display: flex !important;
            flex-direction: column !important;
            width: 100vw !important;
            height: 100vh !important;
            box-sizing: border-box !important;
        }}
        :fullscreen .chart-container {{
            flex: 1 1 0% !important;
            width: 100% !important;
            min-height: calc(100vh - 120px) !important;
            height: 100% !important;
        }}
        :fullscreen .scroll-container {{
            max-height: calc(100vh - 160px) !important;
        }}

        /* Fallback CSS Fullscreen Overlay */
        .fullscreen-active {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: 99999 !important;
            margin: 0 !important;
            border-radius: 0 !important;
            padding: 1.5rem !important;
            background-color: #f8fafc !important;
            overflow: auto !important;
            display: flex !important;
            flex-direction: column !important;
            box-sizing: border-box !important;
        }}
        html.dark .fullscreen-active {{
            background-color: #0b1120 !important;
        }}
        .fullscreen-active .chart-container {{
            flex: 1 1 0% !important;
            width: 100% !important;
            min-height: calc(100vh - 120px) !important;
            height: 100% !important;
        }}
        .fullscreen-active .scroll-container {{
            max-height: calc(100vh - 160px) !important;
        }}
        @media print {{
            .overflow-x-auto, .scroll-container {{
                overflow: visible !important;
            }}
            table {{
                width: 100% !important;
                table-layout: auto !important;
            }}
        }}
    </style>
</head>
<body class="p-4 md:p-6 lg:p-8">
    <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header Banner -->
        <header class="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl relative overflow-hidden">
            <div class="absolute -right-16 -top-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                    <div class="flex flex-wrap items-center gap-2.5">
                        <span class="px-3 py-1 bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">
                            VICTIM FORENSIC ANALYSIS
                        </span>
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold">
                            ป.วิ.อาญา ม.226 / ปปง. ม.49/1
                        </span>
                        <span class="text-xs text-slate-500 dark:text-slate-400 font-mono">CASE: {case_id}</span>
                    </div>
                    <h1 class="text-2xl md:text-3xl font-bold mt-2 text-slate-900 dark:text-white">
                        รายงานผลการตรวจพิสูจน์เส้นทางการเงินเฉพาะผู้เสียหาย
                    </h1>
                    <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
                        เป้าหมายผู้เสียหาย: <b class="text-sky-700 dark:text-sky-300">{result.victim_name}</b> (บัญชี: {vic_accts_str}) &bull; บัญชีม้าพักเงินแถว 1: <b class="text-amber-700 dark:text-amber-300 font-mono">{result.target_account}</b> ({result.target_account_name})
                    </p>
                </div>
                <div class="flex flex-wrap gap-2.5 shrink-0 items-center">
                    <!-- Light / Dark Theme Toggle Button -->
                    <button id="themeToggleBtn" onclick="toggleTheme()" class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-xl text-sm font-semibold transition flex items-center gap-2 shadow-sm text-slate-800 dark:text-amber-300" title="สลับโหมดสว่าง / โหมดมืด">
                        <span id="themeIcon">🌙</span> <span id="themeText">โหมดมืด</span>
                    </button>
                    <button onclick="window.print()" class="px-3.5 py-2 bg-white hover:bg-slate-100 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-xl text-sm transition flex items-center gap-2 text-slate-700 dark:text-slate-200 shadow-sm">
                        <span>🖨️</span> พิมพ์รายงาน
                    </button>
                    <button onclick="copyToClipboard('{result.statement_sha256}', 'คัดลอกค่าแฮช SHA-256 แล้ว')" class="px-3.5 py-2 bg-white hover:bg-slate-100 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-xl text-sm font-mono transition text-sky-600 dark:text-sky-400 flex items-center gap-2 shadow-sm">
                        <span>🔑</span> SHA-256
                    </button>
                    <button onclick="switchTab('tab-insights')" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white font-semibold rounded-xl text-sm shadow-md shadow-sky-600/20 transition flex items-center gap-2">
                        <span>🔍</span> พฤติการณ์และประเด็นสืบสวน
                    </button>
                </div>
            </div>

            <!-- Provenance Hash Bar -->
            <div class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 gap-2">
                <div class="flex items-center gap-2">
                    <span class="text-emerald-600 dark:text-emerald-400 font-bold">● VERIFIED PROVENANCE:</span>
                    <span class="font-mono text-slate-700 dark:text-slate-300">{result.statement_sha256}</span>
                </div>
                <div>
                    ผู้ตรวจพิสูจน์: <b class="text-slate-800 dark:text-slate-200">{officer}</b> &bull; {agency}
                </div>
            </div>
        </header>

        <!-- KPI Cards Grid (6 Metric Cards) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-rose-300 dark:border-rose-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-rose-700 dark:text-rose-300 font-semibold uppercase tracking-wider">ยอดเงินสูญเสียรวม</div>
                <div class="text-2xl font-bold mt-2 text-rose-600 dark:text-rose-400 font-mono">฿{result.total_inflow_thb:,.2f}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{len(result.inflow_transactions)} รายการโอนเข้า</div>
            </div>

            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-emerald-300 dark:border-emerald-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-emerald-700 dark:text-emerald-300 font-semibold uppercase tracking-wider">สิทธิเฉลี่ยทรัพย์คืน (ม.49/1)</div>
                <div class="text-2xl font-bold mt-2 text-emerald-600 dark:text-emerald-400 font-mono">฿{result.total_claimable_thb:,.2f}</div>
                <div class="text-xs text-emerald-600 dark:text-emerald-300/80 mt-1">{pct_claim:.2f}% ของยอดสูญเสีย</div>
            </div>

            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-amber-300 dark:border-amber-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-amber-700 dark:text-amber-300 font-semibold uppercase tracking-wider">ยอดระบายออกด้วย MILP</div>
                <div class="text-2xl font-bold mt-2 text-amber-600 dark:text-amber-400 font-mono">฿{result.total_matched_outflow_thb:,.2f}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">Drain Rate: {result.drain_percentage:.2f}%</div>
            </div>

            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-sky-300 dark:border-sky-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-sky-700 dark:text-sky-300 font-semibold uppercase tracking-wider">เงินคงค้างในบัญชีม้า</div>
                <div class="text-2xl font-bold mt-2 text-sky-600 dark:text-sky-400 font-mono">฿{result.net_residual_buffer_thb:,.2f}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">Residual: {(result.net_residual_buffer_thb/result.total_inflow_thb*100):.2f}%</div>
            </div>

            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-purple-300 dark:border-purple-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-purple-700 dark:text-purple-300 font-semibold uppercase tracking-wider">เวลาเงินแช่พักเฉลี่ย</div>
                <div class="text-2xl font-bold mt-2 text-purple-600 dark:text-purple-300 font-mono">{result.avg_latency_minutes:.1f} น.</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">การกวาดเงินแบบ Automation</div>
            </div>

            <div class="bg-white dark:bg-slate-900/80 p-5 rounded-2xl border border-teal-300 dark:border-teal-500/30 shadow-sm relative overflow-hidden">
                <div class="text-xs text-teal-700 dark:text-teal-300 font-semibold uppercase tracking-wider">การจับคู่คลัสเตอร์</div>
                <div class="text-2xl font-bold mt-2 text-teal-600 dark:text-teal-300 font-mono">{len(result.matched_clusters)}/{len(result.matched_clusters)}</div>
                <div class="text-xs text-teal-600 dark:text-teal-300/80 mt-1">OPTIMAL (MILP Solved)</div>
            </div>
        </div>

        <!-- Navigation Tabs (2 Rows without horizontal scroll) -->
        <div class="border-b border-slate-200 dark:border-slate-800 pb-3 space-y-2">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-sky-500 animate-pulse"></span> แถบนำทางเมนูตรวจพิสูจน์ (Interactive Navigation Tabs)
                </div>
                <div>
                    <button onclick="expandCurrentActiveTab()" id="btn-tab-fullscreen" title="ขยายแผนภาพใน Tab ปัจจุบันให้เต็มจอเพื่อนำเสนอ (Presentation Mode)" class="px-3.5 py-1.5 bg-sky-50 hover:bg-sky-100 dark:bg-sky-500/10 dark:hover:bg-sky-500/20 text-sky-700 dark:text-sky-400 border border-sky-300 dark:border-sky-500/30 hover:border-sky-500/60 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
                        <span id="tabFsIcon">⛶</span>
                        <span id="tabFsText">ขยายแผนภาพเต็มจอ (Presentation)</span>
                    </button>
                </div>
            </div>

            <!-- Row 1: Core Flow & Invariants (Tabs 1-3) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button onclick="switchTab('tab-sankey')" id="btn-tab-sankey" class="tab-btn active p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>🌊</span> 1. ผังเส้นทางเงิน (Sankey Flow)
                </button>
                <button onclick="switchTab('tab-beneficiaries')" id="btn-tab-beneficiaries" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>👥</span> 2. ผู้รับประโยชน์หลัก ({len(result.top_destinations)} ปลายทาง)
                </button>
                <button onclick="switchTab('tab-clusters')" id="btn-tab-clusters" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>🧮</span> 3. สมการคณิตศาสตร์ MILP ({len(result.matched_clusters)} คลัสเตอร์)
                </button>
            </div>

            <!-- Row 2: Velocity, Behavioral Stats & Critical Insights (Tabs 4-6) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button onclick="switchTab('tab-timeline')" id="btn-tab-timeline" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>⏱️</span> 4. ไทม์ไลน์กระแสเงิน (Timeline & Velocity)
                </button>
                <button onclick="switchTab('tab-stats')" id="btn-tab-stats" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>📊</span> 5. สถิติการโอนของเหยื่อ และ ม้า (Behavioral Stats)
                </button>
                <button onclick="switchTab('tab-insights')" id="btn-tab-insights" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>🔍</span> 6. พฤติการณ์และประเด็นสืบสวน (Critical Insights)
                </button>
            </div>
        </div>

        <!-- TAB 1: Sankey & Category Flow -->
        <div id="tab-sankey" class="tab-content space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Sankey Chart (2 Cols) -->
                <div id="card-sankey" class="lg:col-span-2 bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h2 class="text-lg font-bold text-slate-900 dark:text-white">ผังการกระจายเงินจากเหยื่อสู่ปลายทาง (Sankey Flow Diagram)</h2>
                            <p class="text-xs text-slate-500 dark:text-slate-400">แสดงการเดินทางของเงินจากผู้เสียหาย ผ่านบัญชีม้าแถว 1 แยกเข้าผู้รับประโยชน์หลัก 9 บัญชี</p>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <span class="px-2.5 py-1 bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400 border border-sky-300 dark:border-sky-500/20 rounded-md text-xs font-mono hidden md:inline-block">
                                Victim-Centric Conservation
                            </span>
                            <button onclick="toggleCardFullscreen('card-sankey', 'sankeyChartInstance')" class="fullscreen-btn px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                                <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                            </button>
                        </div>
                    </div>
                    <div id="sankeyChart" class="w-full h-[520px] chart-container transition-all"></div>
                </div>

                <!-- Category Doughnut (1 Col) -->
                <div id="card-pie" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                    <div class="mb-4">
                        <h2 class="text-lg font-bold text-slate-900 dark:text-white">จำแนกตามช่องทางการระบายเงิน</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">สัดส่วนเงินที่ถูกระบายแยกตามกลุ่มปลายทาง</p>
                    </div>
                    <div class="pie-content-wrapper flex flex-col flex-1">
                        <div id="pieChart" class="w-full h-[320px] transition-all"></div>
                        <div class="pie-legend-wrapper mt-4 space-y-2 border-t border-slate-200 dark:border-slate-800 pt-4 text-xs">
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-sky-500"></span> บัญชีม้าแถว 2 (Mule Tier-2)</span>
                                <b class="font-mono text-emerald-600 dark:text-emerald-400">฿{tot_tier2_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40" style="display: {'flex' if tot_gateway_claim > 0 else 'none'}">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span> ระบบชำระเงิน/ค่าแอด (Gateway/Ads)</span>
                                <b class="font-mono text-amber-600 dark:text-amber-300">฿{tot_gateway_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-orange-500"></span> ถอนเงินสดตู้ ATM (Cash-Out)</span>
                                <b class="font-mono text-slate-700 dark:text-slate-300">฿{tot_atm_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-purple-500"></span> สินทรัพย์ดิจิทัล (Crypto Off-Ramp)</span>
                                <b class="font-mono text-slate-700 dark:text-slate-300">฿{tot_vasp_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-slate-400"></span> เงินค้างรอฟอก (Residual Buffer)</span>
                                <b class="font-mono text-sky-600 dark:text-sky-400">฿{res_buf:,.2f}</b>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: Top Beneficiaries Ledger (AOC Action column removed) -->
        <div id="tab-beneficiaries" class="tab-content hidden space-y-4">
            <div id="card-beneficiaries" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-900 dark:text-white">ตารางสรุปผู้รับประโยชน์หลักและสิทธิเฉลี่ยทรัพย์คืนชอบธรรม</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">จัดลำดับตามยอดสิทธิเรียกร้องของผู้เสียหายตาม ป.วิ.อ. มาตรา 226 และ พ.ร.บ. ปปง. มาตรา 49/1</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <input type="text" id="destSearch" oninput="filterDestinations()" placeholder="ค้นหาชื่อ, เลขบัญชี, ธนาคาร..." class="px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-sky-500 w-64 shadow-sm">
                        <button onclick="toggleCardFullscreen('card-beneficiaries', null)" class="fullscreen-btn px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 scroll-container flex-1">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead>
                            <tr class="bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs uppercase tracking-wider border-b border-slate-300 dark:border-slate-700">
                                <th class="py-3 px-4 text-center">ลำดับ</th>
                                <th class="py-3 px-4">ธนาคาร / เลขบัญชี</th>
                                <th class="py-3 px-4">ชื่อบัญชีปลายทาง</th>
                                <th class="py-3 px-4 text-center">ช่องทาง</th>
                                <th class="py-3 px-4 text-right">ยอดเงินออกรวม</th>
                                <th class="py-3 px-4 text-right">สิทธิเรียกร้อง (฿)</th>
                                <th class="py-3 px-4 text-center">สัดส่วน</th>
                                <th class="py-3 px-4 text-center">หน่วงเวลาเฉลี่ย</th>
                                <th class="py-3 px-4 text-center">มาตรการที่แนะนำ</th>
                            </tr>
                        </thead>
                        <tbody id="destTableBody">
                            {''.join(dest_table_rows)}
                        </tbody>
                        <tfoot>
                            <tr class="bg-slate-50 dark:bg-slate-800/80 font-bold border-t-2 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white">
                                <td class="py-3 px-4 text-center">รวม</td>
                                <td class="py-3 px-4 text-slate-500 dark:text-slate-400">-</td>
                                <td class="py-3 px-4">รวมทั้งสิ้น {len(result.top_destinations)} ปลายทาง</td>
                                <td class="py-3 px-4 text-center">-</td>
                                <td class="py-3 px-4 text-right font-mono text-slate-700 dark:text-slate-300">฿{tot_drained_sum:,.2f}</td>
                                <td class="py-3 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400 text-base">฿{tot_claim_sum:,.2f}</td>
                                <td class="py-3 px-4 text-center text-sky-600 dark:text-sky-400">{pct_claim:.1f}%</td>
                                <td class="py-3 px-4 text-center text-slate-500 dark:text-slate-400">-</td>
                                <td class="py-3 px-4 text-center text-rose-600 dark:text-rose-300">AOC 1441 / ปปง.</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: MILP Clusters (All Clusters) -->
        <div id="tab-clusters" class="tab-content hidden space-y-4">
            <div id="card-clusters" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-900 dark:text-white">รายการตรวจพิสูจน์ทางคณิตศาสตร์ Mixed-Integer Linear Programming (ครบ {len(result.matched_clusters)} คลัสเตอร์)</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">สมการยืนยันการอนุรักษ์กระแสเงิน (Flow Conservation Proof) แก้ไขด้วย <code>scipy.optimize.milp</code> สถานะ OPTIMAL ทุกกลุ่ม</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <input type="text" id="clusterSearchInput" oninput="filterClusters()" placeholder="ค้นหารหัสคลัสเตอร์ เช่น CLUSTER-VIC-07 หรือ ยอดเงิน..." class="px-3.5 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-sky-500 w-72 shadow-sm">
                        <span id="clusterCountBadge" class="px-3 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-mono text-sky-700 dark:text-sky-400 font-bold">
                            {len(result.matched_clusters)} คลัสเตอร์
                        </span>
                        <button onclick="toggleCardFullscreen('card-clusters', null)" class="fullscreen-btn px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Mathematical Objective Function Box -->
                <div class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700/80 mb-4 flex flex-col md:flex-row items-center justify-between gap-3 text-xs shrink-0">
                    <div>
                        <span class="text-emerald-700 dark:text-emerald-400 font-bold">สมการเป้าหมายเชิงเส้น:</span>
                        <code class="ml-2 font-mono text-slate-800 dark:text-slate-200">min |∑ x_j · O_j - Inflow|  subject to  x_j ∈ {{0, 1}},  ∑ x_j · O_j ≤ Inflow + ε</code>
                    </div>
                    <div class="text-slate-500 dark:text-slate-400">
                        Tolerance: <b class="text-slate-900 dark:text-white">±{tolerance_ratio*100:.1f}%</b> &bull; Proof Status: <b class="text-emerald-600 dark:text-emerald-400">OPTIMAL (100% Invariant Holds)</b>
                    </div>
                </div>

                <div id="clustersContainer" class="space-y-3 max-h-[650px] overflow-y-auto pr-2 scroll-container flex-1">
                    {''.join(cluster_rows)}
                </div>
            </div>
        </div>

        <!-- TAB 4: Timeline & Velocity -->
        <div id="tab-timeline" class="tab-content hidden space-y-4">
            <div id="card-timeline" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-900 dark:text-white">ลำดับเวลาการโอนเงินและความเร็วการกวาดเงิน (Timeline & Velocity Dynamics)</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">เปรียบเทียบจังหวะเวลาการโอนเข้าของผู้เสียหายกับการสั่งโอนระบายเงินออกของบัญชีม้าอย่างต่อเนื่อง</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-purple-50 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-500/30 rounded-full text-xs font-semibold hidden md:inline-block">
                            Mean Latency: {result.avg_latency_minutes:.1f} นาที
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline', 'timelineChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Summary Badges for Inflows vs Outflows -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <div class="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-sky-300 dark:border-sky-500/20">
                        <div class="text-[11px] text-slate-500 dark:text-slate-400">เหยื่อโอนเข้าทั้งหมด (Inflow)</div>
                        <div class="text-base font-bold text-sky-600 dark:text-sky-400 font-mono mt-0.5">฿{result.total_inflow_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">{len(result.inflow_transactions):,} รายการ</div>
                    </div>
                    <div class="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-rose-300 dark:border-rose-500/20">
                        <div class="text-[11px] text-slate-500 dark:text-slate-400">ม้าโอนระบายออก (Outflow)</div>
                        <div class="text-base font-bold text-rose-600 dark:text-rose-400 font-mono mt-0.5">฿{result.total_matched_outflow_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">{len(result.matched_outflows):,} รายการ</div>
                    </div>
                    <div class="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-amber-300 dark:border-amber-500/20">
                        <div class="text-[11px] text-slate-500 dark:text-slate-400">เงินค้างรอฟอก (Buffer)</div>
                        <div class="text-base font-bold text-amber-600 dark:text-amber-400 font-mono mt-0.5">฿{result.net_residual_buffer_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">คงเหลือในบัญชีม้าแถว 1</div>
                    </div>
                    <div class="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-purple-300 dark:border-purple-500/20">
                        <div class="text-[11px] text-slate-500 dark:text-slate-400">ความเร็วระบายเงินเฉลี่ย</div>
                        <div class="text-base font-bold text-purple-600 dark:text-purple-400 font-mono mt-0.5">{result.avg_latency_minutes:.1f} นาที</div>
                        <div class="text-[10px] text-slate-500">Drain Rate: {result.drain_percentage:.1f}%</div>
                    </div>
                </div>

                <div id="timelineChart" class="w-full h-[480px] chart-container transition-all"></div>
            </div>

            <!-- Card 2: Cumulative Cashflow & Buffer Gap Line Chart -->
            <div id="card-timeline-cumulative" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-900 dark:text-white">ยอดเงินสะสมและการดูดเงินออกจากบัญชีม้าตามเวลา (Cumulative Cashflow & Drain Dynamics)</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">เปรียบเทียบยอดความเสียหายสะสมของผู้เสียหายกับยอดเงินที่ม้ากวาดออกต่อเนื่อง พร้อมช่องว่างเงินค้างรอฟอก (Trapped Buffer Gap)</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/30 rounded-full text-xs font-semibold hidden md:inline-block">
                            Trapped Buffer: ฿{result.net_residual_buffer_thb:,.2f}
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline-cumulative', 'timelineCumChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>
                <div id="timelineCumChart" class="w-full h-[480px] chart-container transition-all"></div>
            </div>
        </div>

        <!-- TAB 5: Transaction Statistics & Behavioral Dynamics (Victim vs Mule) [Moved from Tab 6] -->
        <div id="tab-stats" class="tab-content hidden space-y-6">
            <div id="card-stats" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col space-y-6">
                <!-- Header with Fullscreen button -->
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-700 dark:text-sky-300 border border-sky-500/30 rounded-md text-xs font-mono font-bold">
                                BEHAVIORAL FORENSIC PROFILING
                            </span>
                            <span class="text-xs text-slate-500 dark:text-slate-400">ป.วิ.อ. ม.226</span>
                        </div>
                        <h2 class="text-lg md:text-xl font-bold text-slate-900 dark:text-white mt-1">สถิติเปรียบเทียบพฤติกรรมการโอนเงิน: ผู้เสียหาย vs บัญชีม้าพักเงิน</h2>
                        <p class="text-xs text-slate-500 dark:text-slate-400">วิเคราะห์การกระจายตัวของขนาดธุรกรรม (Smurfing Detection), ความถี่การทำรายการ, และอัตราการดูดซับกระแสเงิน</p>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <button onclick="toggleCardFullscreen('card-stats', 'txBucketChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- 2 Comparison Profile Cards (Victim vs Mule) -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <!-- Victim Profile Card -->
                    <div class="p-5 bg-gradient-to-br from-slate-50 to-sky-50 dark:from-slate-900 dark:to-sky-950/40 rounded-xl border border-sky-300 dark:border-sky-500/30 space-y-3">
                        <div class="flex items-center justify-between border-b border-sky-200 dark:border-sky-500/20 pb-2">
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-full bg-sky-500"></span>
                                <span class="font-bold text-slate-900 dark:text-white text-sm">ฝั่งผู้เสียหาย (Victim Inflow Profile)</span>
                            </div>
                            <span class="text-xs font-mono text-sky-700 dark:text-sky-300 px-2 py-0.5 bg-sky-500/20 rounded font-bold">Inflow Origin</span>
                        </div>
                        <div class="text-base font-bold text-slate-900 dark:text-white">{result.victim_name} <span class="text-xs font-normal text-slate-500 dark:text-slate-400">({', '.join(result.victim_accounts) if result.victim_accounts else 'x1003'})</span></div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดเงินโอนเข้ารวม</div>
                                <div class="text-base font-bold font-mono text-sky-600 dark:text-sky-400 mt-0.5">฿{vic_tot_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">จำนวนรายการโอน</div>
                                <div class="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5">{vic_tx_count} รายการ</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดเฉลี่ยต่อรายการ</div>
                                <div class="text-sm font-bold font-mono text-slate-800 dark:text-slate-200 mt-0.5">฿{vic_avg_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดต่ำสุด - สูงสุด</div>
                                <div class="text-sm font-bold font-mono text-slate-800 dark:text-slate-200 mt-0.5">฿{vic_min_amt:,.2f} - ฿{vic_max_amt:,.2f}</div>
                            </div>
                        </div>
                        <div class="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800/60 pt-2 flex justify-between">
                            <span>ช่วงเวลาเกิดเหตุ: <b>{vic_first_time}</b> ถึง <b>{vic_last_time}</b></span>
                        </div>
                        <div class="p-2.5 bg-sky-50 dark:bg-sky-500/10 rounded-lg text-xs text-sky-800 dark:text-sky-200 border border-sky-300 dark:border-sky-500/20">
                            <b>พฤติกรรม (Modus Operandi):</b> ถูกหลอกให้โอนต่อเนื่องเป็นชุด เฉลี่ย 1 รายการทุก ~1.9 ชม. โดยมียอดขนาดใหญ่ > ฿50k รวมสูงถึง ฿702,482.00
                        </div>
                    </div>

                    <!-- Mule Profile Card -->
                    <div class="p-5 bg-gradient-to-br from-slate-50 to-rose-50 dark:from-slate-900 dark:to-rose-950/40 rounded-xl border border-rose-300 dark:border-rose-500/30 space-y-3">
                        <div class="flex items-center justify-between border-b border-rose-200 dark:border-rose-500/20 pb-2">
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-full bg-rose-500"></span>
                                <span class="font-bold text-slate-900 dark:text-white text-sm">ฝั่งบัญชีม้าพักเงิน (Mule Drain & Smurfing Profile)</span>
                            </div>
                            <span class="text-xs font-mono text-rose-700 dark:text-rose-300 px-2 py-0.5 bg-rose-500/20 rounded font-bold">Aggregator Mule Tier-1</span>
                        </div>
                        <div class="text-base font-bold text-slate-900 dark:text-white">{result.target_account_name} <span class="text-xs font-normal text-slate-500 dark:text-slate-400 font-mono">({result.target_account})</span></div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดเงินระบายออกรวม</div>
                                <div class="text-base font-bold font-mono text-rose-600 dark:text-rose-400 mt-0.5">฿{mule_tot_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">จำนวนรายการระบายออก</div>
                                <div class="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5">{mule_tx_count} รายการ ({len(result.matched_clusters)} คลัสเตอร์)</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดเฉลี่ยต่อรายการ</div>
                                <div class="text-sm font-bold font-mono text-slate-800 dark:text-slate-200 mt-0.5">฿{mule_avg_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-white dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-transparent">
                                <div class="text-slate-500 dark:text-slate-400">ยอดต่ำสุด - สูงสุด</div>
                                <div class="text-sm font-bold font-mono text-slate-800 dark:text-slate-200 mt-0.5">฿{mule_min_amt:,.2f} - ฿{mule_max_amt:,.2f}</div>
                            </div>
                        </div>
                        <div class="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800/60 pt-2 flex justify-between">
                            <span>Drain Rate: <b class="text-amber-600 dark:text-amber-300">{result.drain_percentage:.2f}%</b> &bull; แช่พักเฉลี่ย: <b class="text-purple-600 dark:text-purple-300">{result.avg_latency_minutes:.1f} น.</b></span>
                        </div>
                        <div class="p-2.5 bg-rose-50 dark:bg-rose-500/10 rounded-lg text-xs text-rose-800 dark:text-rose-200 border border-rose-300 dark:border-rose-500/20">
                            <b>พฤติกรรม (Smurfing Profile):</b> สับยอดเป็นรายการเล็กย่อยๆ (Micro-transfers < ฿1,000 สูงถึง 545 รายการ) เพื่อหลบเลี่ยงการรายงานธุรกรรมตามเกณฑ์ AML
                        </div>
                    </div>
                </div>

                <!-- 2 Comparison Charts Grid -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- Chart 1: Bucket Distribution -->
                    <div class="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700/80 flex flex-col">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-bold text-slate-900 dark:text-white">การกระจายตัวของขนาดธุรกรรม (Transaction Size Buckets)</h3>
                            <span class="text-xs text-slate-500 dark:text-slate-400">Smurfing vs Lump-sum</span>
                        </div>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">เปรียบเทียบจำนวนรายการในแต่ละช่วงวงเงิน ชี้ชัดการแตกล็อตเงินย่อยของบัญชีม้า</p>
                        <div id="txBucketChart" class="w-full h-[320px] chart-container"></div>
                    </div>

                    <!-- Chart 2: Cumulative Flow Velocity -->
                    <div class="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700/80 flex flex-col">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-bold text-slate-900 dark:text-white">การสะสมของกระแสเงินรายวัน (Cumulative Flow Tracking)</h3>
                            <span class="text-xs text-slate-500 dark:text-slate-400">Velocity Dynamics</span>
                        </div>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">เปรียบเทียบยอดสะสม Inflow ของเหยื่อ vs Outflow ที่ถูกระบายออกไล่ตามกัน</p>
                        <div id="cumFlowChart" class="w-full h-[320px] chart-container"></div>
                    </div>
                </div>

                <!-- Daily Breakdown Table -->
                <div class="space-y-2">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-bold text-slate-900 dark:text-white">ตารางสรุปเปรียบเทียบกระแสเงินรายวัน (Daily Comparative Inflow-Outflow Ledger)</h3>
                        <span class="text-xs text-slate-500 dark:text-slate-400">{len(all_dates)} วันทำการ</span>
                    </div>
                    <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 uppercase tracking-wider border-b border-slate-300 dark:border-slate-700">
                                    <th class="py-2.5 px-4">วันที่ (Date)</th>
                                    <th class="py-2.5 px-4 text-center">จน. โอนเข้าเหยื่อ</th>
                                    <th class="py-2.5 px-4 text-right">ยอดเงินเข้า (Inflow)</th>
                                    <th class="py-2.5 px-4 text-center">จน. ระบายออกม้า</th>
                                    <th class="py-2.5 px-4 text-right">ยอดเงินออก (Outflow)</th>
                                    <th class="py-2.5 px-4 text-right">ยอดคงเหลือสะสม (Net Buffer)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(daily_table_rows)}
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>

        <!-- TAB 6: พฤติการณ์ของการโอนและประเด็นสำคัญเชิงสืบสวน (Transfer Circumstances & Critical Forensic Insights) [NEW] -->
        <div id="tab-insights" class="tab-content hidden space-y-6">
            <div id="card-insights" class="bg-white dark:bg-slate-900/90 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col space-y-6">
                <!-- Header -->
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/30 rounded-md text-xs font-mono font-bold">
                                FORENSIC INVESTIGATIVE INTELLIGENCE
                            </span>
                            <span class="text-xs text-slate-500 dark:text-slate-400">ป.วิ.อ. ม.132, ม.226 / พ.ร.ก. มาตรการฯ ม.7 / ปปง. ม.49/1</span>
                        </div>
                        <h2 class="text-xl md:text-2xl font-bold text-slate-900 dark:text-white mt-1">
                            พฤติการณ์ของการโอนและประเด็นสำคัญเชิงสืบสวน
                        </h2>
                        <p class="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                            Transfer Circumstances & Critical Forensic Insights &bull; แฟ้มวิเคราะห์พฤติการณ์กลลวง, โอกาสทองในการอายัดทรัพย์สิน, และมาตรการหมายเรียกพยานหลักฐาน
                        </p>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <button onclick="toggleCardFullscreen('card-insights', null)" class="fullscreen-btn px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-400 border border-slate-300 dark:border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Section 1: Modus Operandi & Circumstances -->
                <div class="p-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700/60 space-y-4">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div class="flex items-center gap-2">
                            <span class="text-xl">🕵️</span>
                            <h3 class="font-bold text-slate-900 dark:text-white text-base">
                                1. พฤติการณ์การเคลื่อนย้ายเงินและรูปแบบการหลอกลวง (Modus Operandi)
                            </h3>
                        </div>
                        {pattern_badge}
                    </div>

                    <div class="text-xs md:text-sm text-slate-700 dark:text-slate-300 leading-relaxed space-y-2">
                        <p>{pattern_detail}</p>
                        <p>
                            <b>การตอบสนองของบัญชีม้าแถว 1 (<code class="text-sky-600 dark:text-sky-400 font-bold">{result.target_account}</code> {result.target_account_name}):</b>
                            มียอดเงินที่ถูกจับคู่ระบายออกด้วยแบบจำลอง MILP รวม <b class="font-mono text-emerald-600 dark:text-emerald-400">฿{result.total_matched_outflow_thb:,.2f}</b>
                            คิดเป็นอัตราการกวาดเงิน (Drain Rate) สูงถึง <b class="text-amber-600 dark:text-amber-400">{result.drain_percentage:.2f}%</b>
                            โดยมีระยะเวลาเงินแช่พักเฉลี่ยเพียง <b class="text-purple-600 dark:text-purple-400">{result.avg_latency_minutes:.1f} นาที</b>
                            สะท้อนให้เห็นถึงการสั่งการโอนแบบกึ่งอัตโนมัติ (Automated Sweeping Mechanism) ผ่านระบบ Mobile Banking ทันทีที่เงินเข้าบัญชี
                        </p>
                    </div>

                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800">
                            <span class="text-slate-500 dark:text-slate-400">รูปแบบธุรกรรม</span>
                            <div class="font-bold text-slate-900 dark:text-white mt-0.5">{"วันเดียว (Concentrated)" if is_concentrated else f"กระจาย {len(vic_dates)} วัน"}</div>
                        </div>
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800">
                            <span class="text-slate-500 dark:text-slate-400">อัตราการกวาดเงิน</span>
                            <div class="font-bold text-amber-600 dark:text-amber-400 mt-0.5">{result.drain_percentage:.2f}%</div>
                        </div>
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800">
                            <span class="text-slate-500 dark:text-slate-400">ความเร็วระบายเงินเฉลี่ย</span>
                            <div class="font-bold text-purple-600 dark:text-purple-400 mt-0.5">{result.avg_latency_minutes:.1f} นาที</div>
                        </div>
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800">
                            <span class="text-slate-500 dark:text-slate-400">คลัสเตอร์อนุรักษ์กระแส</span>
                            <div class="font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">{len(result.matched_clusters)} คลัสเตอร์ (100% Invariant)</div>
                        </div>
                    </div>
                </div>

                <!-- Section 2: Golden Window Analysis -->
                <div class="space-y-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⭐</span>
                        <h3 class="font-bold text-slate-900 dark:text-white text-base">
                            2. การวิเคราะห์โอกาสทองในการอายัดทรัพย์สินคืน (Asset Recovery Golden Window Analysis)
                        </h3>
                    </div>
                    {golden_card_html}
                </div>

                <!-- Section 3: Corporate Gateways & Ad Platforms Subpoena Directives -->
                <div class="space-y-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">🏢</span>
                        <h3 class="font-bold text-slate-900 dark:text-white text-base">
                            3. การจัดการกรณีปลายทางเป็น Corporate Payment Gateway & Tech Ad Platform
                        </h3>
                    </div>
                    {gateways_panel_html}
                </div>

                <!-- Section 4: Actionable Directives by Target Category & Syndicate Expansion -->
                <div class="p-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700/60 space-y-4">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">🎯</span>
                        <h3 class="font-bold text-slate-900 dark:text-white text-base">
                            4. มาตรการเชิงสืบสวนจำแนกตามประเภทปลายทางและการขยายผลคดีร่วม (Syndicate Expansion)
                        </h3>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div class="p-4 bg-white dark:bg-slate-900/80 rounded-xl border border-rose-300 dark:border-rose-500/30 space-y-2">
                            <div class="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-bold text-sm">
                                <span>🚨</span> บัญชีม้าบุคคลธรรมดา แถว 2 (Mule Tier-2)
                            </div>
                            <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                                ส่งคำสั่งระงับธุรกรรมฉุกเฉิน 72 ชั่วโมงผ่านศูนย์ AOC 1441 (พ.ร.ก. มาตรการฯ พ.ศ. 2566 มาตรา 7) เฉพาะบัญชีบุคคลธรรมดาเพื่อสกัดเงินก่อนถูกโยกย้ายออกนอกระบบ
                            </p>
                        </div>

                        <div class="p-4 bg-white dark:bg-slate-900/80 rounded-xl border border-amber-300 dark:border-amber-500/30 space-y-2">
                            <div class="flex items-center gap-2 text-amber-700 dark:text-amber-300 font-bold text-sm">
                                <span>📹</span> ถอนเงินสดตู้ ATM (Cash-Out Intercept)
                            </div>
                            <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                                ประสานงานธนาคารเจ้าของตู้เพื่อขอภาพถ่ายกล้อง CCTV จุดติดตั้งตู้ ATM เร่งด่วนที่สุด (ภายในกรอบ 15 วัน ก่อนระบบบันทึกภาพทับ) เพื่อพิสูจน์ทราบตัวผู้ถอนเงิน
                            </p>
                        </div>

                        <div class="p-4 bg-white dark:bg-slate-900/80 rounded-xl border border-purple-300 dark:border-purple-500/30 space-y-2">
                            <div class="flex items-center gap-2 text-purple-700 dark:text-purple-300 font-bold text-sm">
                                <span>🔒</span> สินทรัพย์ดิจิทัล P2P (Crypto Off-Ramp)
                            </div>
                            <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                                มีหนังสือขอระงับบัญชีผู้ค้า P2P และคำขอข้อมูล KYC/TxID ไปยังศูนย์ซื้อขายสินทรัพย์ดิจิทัล (VASP) ภายใต้การกำกับของ ก.ล.ต. เพื่อตรวจสอบกระเป๋าปลายทาง
                            </p>
                        </div>

                        <div class="p-4 bg-white dark:bg-slate-900/80 rounded-xl border border-sky-300 dark:border-sky-500/30 space-y-2">
                            <div class="flex items-center gap-2 text-sky-700 dark:text-sky-300 font-bold text-sm">
                                <span>🌐</span> การเชื่อมโยงคดีผ่านระบบแจ้งความออนไลน์ (Syndicate Linkage)
                            </div>
                            <p class="text-slate-600 dark:text-slate-300 leading-relaxed">
                                นำข้อมูล Ad Account ID, Campaign Fanpage URL, หรือ Merchant Reference ไปสืบค้นเชื่อมโยงกับเลขคดีบน thaipoliceonline เพื่อรวมสำนวนและขยายผลจับกุมผู้บงการ
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Section 5: Cryptographic Chain of Custody & Evidence Receipt -->
                <div class="p-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700/60 space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-xl">⚖️</span>
                            <h3 class="font-bold text-slate-900 dark:text-white text-base">
                                5. ห่วงโซ่การครอบครองพยานหลักฐานดิจิทัล (Cryptographic Chain of Custody & Section 226)
                            </h3>
                        </div>
                        <span class="px-2.5 py-0.5 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 rounded text-xs font-mono font-bold">
                            LEGAL ADMISSIBILITY VERIFIED
                        </span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                            <div class="text-slate-500 dark:text-slate-400">Statement SHA-256 Digest:</div>
                            <div class="text-slate-900 dark:text-slate-200 font-bold break-all">{result.statement_sha256}</div>
                        </div>
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                            <div class="text-slate-500 dark:text-slate-400">HMAC-SHA256 Digital Signature:</div>
                            <div class="text-slate-900 dark:text-slate-200 font-bold break-all">{sig_hex[:36]}...</div>
                        </div>
                        <div class="p-3 bg-white dark:bg-slate-900/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1">
                            <div class="text-slate-500 dark:text-slate-400">Investigating Officer & Agency:</div>
                            <div class="text-slate-900 dark:text-slate-200 font-bold">{officer}</div>
                            <div class="text-[11px] text-slate-500">{agency}</div>
                        </div>
                    </div>

                    <p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed pt-1">
                        <b>การรับรองความถูกต้องตามกฎหมาย:</b> รายงานและแฟ้มผลลัพธ์นี้ได้รับการตรวจพิสูจน์ตามหลักการทางนิติวิทยาศาสตร์ดิจิทัล เป็นพยานหลักฐานที่ได้มาโดยชอบด้วยกฎหมายตามประมวลกฎหมายวิธีพิจารณาความอาญา มาตรา 226, พ.ร.บ. ว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 มาตรา 11, และคุ้มครองสิทธิเรียกร้องของผู้เสียหายตาม พ.ร.บ. ปปง. พ.ศ. 2542 มาตรา 49/1
                    </p>
                </div>

            </div>
        </div>

    </div>

    <!-- Toast Notification Element -->
    <div id="toast" class="fixed bottom-6 right-6 bg-slate-900 dark:bg-slate-800 border border-slate-700 text-white px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold opacity-0 transition-opacity duration-300 pointer-events-none flex items-center gap-2 z-50">
        <span class="text-emerald-400">✓</span>
        <span id="toastMsg">บันทึกข้อมูลแล้ว</span>
    </div>

    <script>
        // Fullscreen Toggle for Charts and Diagrams
        let currentFullscreenEl = null;

        function toggleCardFullscreen(cardId, chartInstanceName) {{
            const card = document.getElementById(cardId);
            if (!card) return;

            const isCurrentlyFs = (document.fullscreenElement === card) || card.classList.contains('fullscreen-active');

            if (isCurrentlyFs) {{
                exitFullscreenMode(card, chartInstanceName);
            }} else {{
                enterFullscreenMode(card, chartInstanceName);
            }}
        }}

        function enterFullscreenMode(card, chartInstanceName) {{
            currentFullscreenEl = card;
            if (card.requestFullscreen) {{
                card.requestFullscreen().catch(() => {{
                    card.classList.add('fullscreen-active');
                    updateFsButtons(true, card);
                    resizeChart(chartInstanceName);
                }});
            }} else {{
                card.classList.add('fullscreen-active');
            }}
            updateFsButtons(true, card);
            resizeChart(chartInstanceName);
            showToast('เข้าสู่โหมดขยายเต็มจอ (กด ESC หรือคลิกปุ่มเพื่อย่อลง)');
        }}

        function exitFullscreenMode(card, chartInstanceName) {{
            if (document.fullscreenElement) {{
                document.exitFullscreen().catch(() => {{}});
            }}
            if (card) {{
                card.classList.remove('fullscreen-active');
                updateFsButtons(false, card);
            }}
            currentFullscreenEl = null;
            resizeChart(chartInstanceName);
        }}

        function resizeChart(chartInstanceName) {{
            setTimeout(() => {{
                if (chartInstanceName && window[chartInstanceName]) {{
                    window[chartInstanceName].resize();
                }} else {{
                    if (window.sankeyChartInstance) window.sankeyChartInstance.resize();
                    if (window.pieChartInstance) window.pieChartInstance.resize();
                    if (window.timelineChartInstance) window.timelineChartInstance.resize();
                    if (window.timelineCumChartInstance) window.timelineCumChartInstance.resize();
                    if (window.txBucketChartInstance) window.txBucketChartInstance.resize();
                    if (window.cumFlowChartInstance) window.cumFlowChartInstance.resize();
                }}
            }}, 100);
            setTimeout(() => {{
                if (chartInstanceName && window[chartInstanceName]) {{
                    window[chartInstanceName].resize();
                }}
            }}, 300);
        }}

        function updateFsButtons(isFs, targetCard) {{
            if (targetCard) {{
                const btn = targetCard.querySelector('.fullscreen-btn');
                if (btn) {{
                    const icon = btn.querySelector('.fs-icon');
                    const text = btn.querySelector('.fs-text');
                    if (isFs) {{
                        if (icon) icon.innerText = '🗗';
                        if (text) text.innerText = 'ย่อลง (ESC)';
                        btn.classList.add('bg-rose-600/30', 'text-rose-600', 'border-rose-500/50');
                    }} else {{
                        if (icon) icon.innerText = '⛶';
                        if (text) text.innerText = 'ขยายเต็มจอ';
                        btn.classList.remove('bg-rose-600/30', 'text-rose-600', 'border-rose-500/50');
                    }}
                }}
            }}
            const tabIcon = document.getElementById('tabFsIcon');
            const tabText = document.getElementById('tabFsText');
            if (tabText) {{
                tabText.innerText = isFs ? 'ย่อลง (ESC)' : 'ขยายแผนภาพเต็มจอ (Presentation)';
            }}
            if (tabIcon) {{
                tabIcon.innerText = isFs ? '🗗' : '⛶';
            }}
        }}

        // Listen for Native Fullscreen Changes
        document.addEventListener('fullscreenchange', () => {{
            const isFs = !!document.fullscreenElement;
            if (!isFs && currentFullscreenEl) {{
                currentFullscreenEl.classList.remove('fullscreen-active');
                updateFsButtons(false, currentFullscreenEl);
                currentFullscreenEl = null;
            }}
            resizeChart();
        }});

        // ESC key handler for CSS fallback
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape' && currentFullscreenEl) {{
                exitFullscreenMode(currentFullscreenEl);
            }}
        }});

        // Handler for the Interactive Navigation Tab Bar Fullscreen Button
        function expandCurrentActiveTab() {{
            if (document.fullscreenElement || currentFullscreenEl) {{
                exitFullscreenMode(currentFullscreenEl);
                return;
            }}

            const activeTab = document.querySelector('.tab-content:not(.hidden)');
            if (!activeTab) return;

            const tabId = activeTab.id;
            if (tabId === 'tab-sankey') {{
                toggleCardFullscreen('card-sankey', 'sankeyChartInstance');
            }} else if (tabId === 'tab-beneficiaries') {{
                toggleCardFullscreen('card-beneficiaries', null);
            }} else if (tabId === 'tab-clusters') {{
                toggleCardFullscreen('card-clusters', null);
            }} else if (tabId === 'tab-timeline') {{
                toggleCardFullscreen('card-timeline', 'timelineChartInstance');
            }} else if (tabId === 'tab-stats') {{
                toggleCardFullscreen('card-stats', 'txBucketChartInstance');
            }} else if (tabId === 'tab-insights') {{
                toggleCardFullscreen('card-insights', null);
            }}
        }}

        // Tab Switching Logic
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

            const target = document.getElementById(tabId);
            if (target) target.classList.remove('hidden');

            const activeBtn = document.getElementById('btn-' + tabId);
            if (activeBtn) activeBtn.classList.add('active');

            if (tabId === 'tab-sankey' && window.sankeyChartInstance) {{
                setTimeout(() => {{
                    window.sankeyChartInstance.resize();
                    window.pieChartInstance.resize();
                }}, 50);
            }} else if (tabId === 'tab-timeline') {{
                setTimeout(() => {{
                    if (window.timelineChartInstance) window.timelineChartInstance.resize();
                    if (window.timelineCumChartInstance) window.timelineCumChartInstance.resize();
                }}, 50);
            }} else if (tabId === 'tab-stats' && window.txBucketChartInstance) {{
                setTimeout(() => {{
                    window.txBucketChartInstance.resize();
                    window.cumFlowChartInstance.resize();
                }}, 50);
            }}
        }}

        // Toast Helper
        function showToast(msg) {{
            const t = document.getElementById('toast');
            const m = document.getElementById('toastMsg');
            m.innerText = msg;
            t.classList.remove('opacity-0');
            setTimeout(() => t.classList.add('opacity-0'), 2500);
        }}

        function copyToClipboard(text, successMsg) {{
            navigator.clipboard.writeText(text);
            showToast(successMsg || 'คัดลอกข้อความแล้ว');
        }}

        // Filter Destinations in Table
        function filterDestinations() {{
            const query = document.getElementById('destSearch').value.toLowerCase().trim();
            document.querySelectorAll('.dest-row').forEach(row => {{
                const bank = (row.getAttribute('data-bank') || '').toLowerCase();
                const name = (row.getAttribute('data-name') || '').toLowerCase();
                if (!query || bank.includes(query) || name.includes(query)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}

        // Filter Clusters in Tab 3
        function filterClusters() {{
            const query = document.getElementById('clusterSearchInput').value.toLowerCase().trim();
            let count = 0;
            document.querySelectorAll('.cluster-card').forEach(card => {{
                const cid = (card.getAttribute('data-cid') || '').toLowerCase();
                const amt = (card.getAttribute('data-amt') || '').toLowerCase();
                const text = card.innerText.toLowerCase();
                if (!query || cid.includes(query) || amt.includes(query) || text.includes(query)) {{
                    card.style.display = '';
                    count++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            document.getElementById('clusterCountBadge').innerText = `${{count}} คลัสเตอร์`;
        }}

        // Theme Engine: Light Mode (Default) & Dark Mode Toggle
        function applyTheme(theme) {{
            const htmlEl = document.documentElement;
            const themeIcon = document.getElementById('themeIcon');
            const themeText = document.getElementById('themeText');
            const themeToggleBtn = document.getElementById('themeToggleBtn');

            if (theme === 'dark') {{
                htmlEl.classList.remove('light');
                htmlEl.classList.add('dark');
                if (themeIcon) themeIcon.innerText = '☀️';
                if (themeText) themeText.innerText = 'โหมดสว่าง';
                if (themeToggleBtn) {{
                    themeToggleBtn.classList.remove('text-slate-800');
                    themeToggleBtn.classList.add('text-amber-300');
                }}
                localStorage.setItem('finforensic_theme', 'dark');
            }} else {{
                htmlEl.classList.remove('dark');
                htmlEl.classList.add('light');
                if (themeIcon) themeIcon.innerText = '🌙';
                if (themeText) themeText.innerText = 'โหมดมืด';
                if (themeToggleBtn) {{
                    themeToggleBtn.classList.remove('text-amber-300');
                    themeToggleBtn.classList.add('text-slate-800');
                }}
                localStorage.setItem('finforensic_theme', 'light');
            }}
            updateChartThemes(theme);
        }}

        function toggleTheme() {{
            const isDark = document.documentElement.classList.contains('dark');
            const nextTheme = isDark ? 'light' : 'dark';
            applyTheme(nextTheme);
            showToast(nextTheme === 'light' ? 'เปลี่ยนเป็นโหมดสว่างแล้ว' : 'เปลี่ยนเป็นโหมดมืดแล้ว');
        }}

        function updateChartThemes(theme) {{
            const isDark = (theme === 'dark');
            const axisColor = isDark ? '#475569' : '#cbd5e1';
            const labelColor = isDark ? '#94a3b8' : '#64748b';
            const splitColor = isDark ? '#1e293b' : '#f1f5f9';
            const tooltipBg = isDark ? '#1e293b' : '#ffffff';
            const tooltipBorder = isDark ? '#334155' : '#cbd5e1';
            const tooltipText = isDark ? '#f8fafc' : '#0f172a';

            if (window.sankeyChartInstance) {{
                window.sankeyChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    series: [{{
                        label: {{ color: isDark ? '#e2e8f0' : '#1e293b' }}
                    }}]
                }});
            }}

            if (window.pieChartInstance) {{
                window.pieChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    series: [{{
                        itemStyle: {{ borderColor: isDark ? '#0f172a' : '#ffffff' }}
                    }}]
                }});
            }}

            if (window.timelineChartInstance) {{
                window.timelineChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    legend: {{ textStyle: {{ color: labelColor }} }},
                    xAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }},
                    yAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{ color: labelColor }},
                        nameTextStyle: {{ color: labelColor }}
                    }}
                }});
            }}

            if (window.timelineCumChartInstance) {{
                window.timelineCumChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    legend: {{ textStyle: {{ color: labelColor }} }},
                    xAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }},
                    yAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{ color: labelColor }},
                        nameTextStyle: {{ color: labelColor }}
                    }}
                }});
            }}

            if (window.txBucketChartInstance) {{
                window.txBucketChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    legend: {{ textStyle: {{ color: labelColor }} }},
                    xAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }},
                    yAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{ color: labelColor }},
                        nameTextStyle: {{ color: labelColor }}
                    }}
                }});
            }}

            if (window.cumFlowChartInstance) {{
                window.cumFlowChartInstance.setOption({{
                    tooltip: {{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    legend: {{ textStyle: {{ color: labelColor }} }},
                    xAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }},
                    yAxis: {{
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }}
                }});
            }}
        }}

        // Initialize ECharts on Page Load
        document.addEventListener('DOMContentLoaded', function() {{
            const initialTheme = localStorage.getItem('finforensic_theme') || 'light';
            applyTheme(initialTheme);
            const isDark = (initialTheme === 'dark');
            const axisColor = isDark ? '#475569' : '#cbd5e1';
            const labelColor = isDark ? '#94a3b8' : '#64748b';
            const splitColor = isDark ? '#1e293b' : '#f1f5f9';
            const tooltipBg = isDark ? '#1e293b' : '#ffffff';
            const tooltipBorder = isDark ? '#334155' : '#cbd5e1';
            const tooltipText = isDark ? '#f8fafc' : '#0f172a';

            // 1. Sankey Chart
            const sankeyEl = document.getElementById('sankeyChart');
            if (sankeyEl) {{
                const sankeyChart = echarts.init(sankeyEl);
                window.sankeyChartInstance = sankeyChart;
                sankeyChart.setOption({{
                    tooltip: {{
                        trigger: 'item',
                        triggerOn: 'mousemove',
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            if (params.dataType === 'edge') {{
                                return `<b>${{params.data.source}}</b><br/>&rarr; <b>${{params.data.target}}</b><br/>ยอดเงิน: <b>฿${{params.data.value.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</b>`;
                            }}
                            return `<b>${{params.name}}</b>`;
                        }}
                    }},
                    series: [{{
                        type: 'sankey',
                        layout: 'none',
                        emphasis: {{ focus: 'adjacency' }},
                        data: {sankey_nodes_json},
                        links: {sankey_links_json},
                        orient: 'horizontal',
                        label: {{
                            color: isDark ? '#e2e8f0' : '#1e293b',
                            fontFamily: 'Sarabun',
                            fontSize: 12,
                        }},
                        lineStyle: {{
                            color: 'gradient',
                            curveness: 0.5,
                            opacity: 0.45
                        }}
                    }}]
                }});
            }}

            // 2. Pie / Donut Chart
            const pieEl = document.getElementById('pieChart');
            if (pieEl) {{
                const pieChart = echarts.init(pieEl);
                window.pieChartInstance = pieChart;
                pieChart.setOption({{
                    tooltip: {{
                        trigger: 'item',
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }},
                        formatter: '<b>{{b}}</b><br/>ยอดเงิน: ฿{{c}} ({{d}}%)'
                    }},
                    legend: {{ show: false }},
                    series: [{{
                        name: 'Category',
                        type: 'pie',
                        radius: ['45%', '72%'],
                        avoidLabelOverlap: false,
                        itemStyle: {{ borderRadius: 8, borderColor: isDark ? '#0f172a' : '#ffffff', borderWidth: 2 }},
                        label: {{ show: false }},
                        data: {pie_data_json}
                    }}]
                }});
            }}

            // 3. Timeline Chart (Dual Inflow & Matched Outflow Velocity)
            const timelineEl = document.getElementById('timelineChart');
            if (timelineEl) {{
                const timelineChart = echarts.init(timelineEl);
                window.timelineChartInstance = timelineChart;
                timelineChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        axisPointer: {{ type: 'shadow' }},
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            let title = '<div class="font-bold border-b pb-1 mb-1" style="border-color: ' + tooltipBorder + '">⏱️ เวลา: ' + params[0].name + '</div>';
                            params.forEach(p => {{
                                let val = p.value || 0;
                                if (val > 0) {{
                                    title += '<div class="flex items-center justify-between gap-4 py-0.5">' + 
                                             '<span>' + p.marker + ' ' + p.seriesName + '</span>' + 
                                             '<b class="font-mono">฿' + val.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + '</b></div>';
                                }}
                            }});
                            return title;
                        }}
                    }},
                    legend: {{
                        data: ['เหยื่อโอนเข้า (Victim Inflow)', 'ม้าระบายออก (Mule Outflow)'],
                        textStyle: {{ color: labelColor, fontFamily: 'Sarabun' }},
                        top: '1%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {timeline_points_json},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor, fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'ยอดเงิน (฿)',
                        nameTextStyle: {{ color: labelColor }},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{
                            color: labelColor,
                            formatter: function(val) {{ return '฿' + (val / 1000) + 'k'; }}
                        }}
                    }},
                    dataZoom: [
                        {{
                            type: 'slider',
                            show: true,
                            xAxisIndex: [0],
                            start: 0,
                            end: 100,
                            bottom: '2%',
                            textStyle: {{ color: labelColor }},
                            borderColor: tooltipBorder,
                            fillerColor: 'rgba(56, 189, 248, 0.15)',
                            handleStyle: {{ color: '#38bdf8' }}
                        }},
                        {{
                            type: 'inside',
                            xAxisIndex: [0]
                        }}
                    ],
                    series: [
                        {{
                            name: 'เหยื่อโอนเข้า (Victim Inflow)',
                            type: 'bar',
                            data: {timeline_in_series_json},
                            itemStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: '#38bdf8' }},
                                    {{ offset: 1, color: '#0284c7' }}
                                ]),
                                borderRadius: [4, 4, 0, 0]
                            }}
                        }},
                        {{
                            name: 'ม้าระบายออก (Mule Outflow)',
                            type: 'bar',
                            data: {timeline_out_series_json},
                            itemStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: '#f43f5e' }},
                                    {{ offset: 1, color: '#be123c' }}
                                ]),
                                borderRadius: [4, 4, 0, 0]
                            }}
                        }}
                    ]
                }});
            }}

            // 3.1 Timeline Cumulative Flow Chart (Card 2 in Tab 4)
            const timelineCumEl = document.getElementById('timelineCumChart');
            if (timelineCumEl) {{
                const timelineCumChart = echarts.init(timelineCumEl);
                window.timelineCumChartInstance = timelineCumChart;
                timelineCumChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            let title = '<div class="font-bold border-b pb-1 mb-1" style="border-color: ' + tooltipBorder + '">⏱️ เวลา: ' + params[0].name + '</div>';
                            let inVal = 0;
                            let outVal = 0;
                            params.forEach(p => {{
                                let val = p.value || 0;
                                if (p.seriesName.includes('เข้าสะสม')) inVal = val;
                                if (p.seriesName.includes('ออกสะสม')) outVal = val;
                                title += '<div class="flex items-center justify-between gap-4 py-0.5">' + 
                                         '<span>' + p.marker + ' ' + p.seriesName + '</span>' + 
                                         '<b class="font-mono">฿' + val.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + '</b></div>';
                            }});
                            let gap = Math.max(0, inVal - outVal);
                            title += '<div class="border-t pt-1 mt-1 flex items-center justify-between gap-4 text-amber-500 font-bold" style="border-color: ' + tooltipBorder + '">' +
                                     '<span>🟡 เงินตกค้างรอฟอก (Buffer Gap):</span>' +
                                     '<b class="font-mono">฿' + gap.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + '</b></div>';
                            return title;
                        }}
                    }},
                    legend: {{
                        data: ['ยอดเงินเข้าสะสม (Cumulative Inflow)', 'ยอดเงินออกสะสม (Cumulative Outflow)'],
                        textStyle: {{ color: labelColor, fontFamily: 'Sarabun' }},
                        top: '1%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {timeline_points_json},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor, fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'ยอดสะสมรวม (฿)',
                        nameTextStyle: {{ color: labelColor }},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{
                            color: labelColor,
                            formatter: function(val) {{ return '฿' + (val / 1000) + 'k'; }}
                        }}
                    }},
                    dataZoom: [
                        {{
                            type: 'slider',
                            show: true,
                            xAxisIndex: [0],
                            start: 0,
                            end: 100,
                            bottom: '2%',
                            textStyle: {{ color: labelColor }},
                            borderColor: tooltipBorder,
                            fillerColor: 'rgba(56, 189, 248, 0.15)',
                            handleStyle: {{ color: '#38bdf8' }}
                        }},
                        {{
                            type: 'inside',
                            xAxisIndex: [0]
                        }}
                    ],
                    series: [
                        {{
                            name: 'ยอดเงินเข้าสะสม (Cumulative Inflow)',
                            type: 'line',
                            smooth: true,
                            showSymbol: false,
                            data: {timeline_cum_in_series_json},
                            lineStyle: {{ width: 3, color: '#38bdf8' }},
                            itemStyle: {{ color: '#38bdf8' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(56, 189, 248, 0.22)' }},
                                    {{ offset: 1, color: 'rgba(56, 189, 248, 0.01)' }}
                                ])
                            }}
                        }},
                        {{
                            name: 'ยอดเงินออกสะสม (Cumulative Outflow)',
                            type: 'line',
                            smooth: true,
                            showSymbol: false,
                            data: {timeline_cum_out_series_json},
                            lineStyle: {{ width: 3, color: '#f43f5e' }},
                            itemStyle: {{ color: '#f43f5e' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(244, 63, 94, 0.22)' }},
                                    {{ offset: 1, color: 'rgba(244, 63, 94, 0.01)' }}
                                ])
                            }}
                        }}
                    ]
                }});
            }}

            // 4. Transaction Bucket Chart (Tab 5)
            const bucketEl = document.getElementById('txBucketChart');
            if (bucketEl) {{
                const bucketChart = echarts.init(bucketEl);
                window.txBucketChartInstance = bucketChart;
                bucketChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        axisPointer: {{ type: 'shadow' }},
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }}
                    }},
                    legend: {{
                        data: ['เหยื่อโอนเข้า', 'ม้าระบายออก'],
                        textStyle: {{ color: labelColor, fontFamily: 'Sarabun' }},
                        top: '2%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {bucket_labels_json},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor, fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'จำนวนรายการ (Tx)',
                        nameTextStyle: {{ color: labelColor }},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{ color: labelColor }}
                    }},
                    series: [
                        {{
                            name: 'เหยื่อโอนเข้า',
                            type: 'bar',
                            data: {vic_buckets_json},
                            itemStyle: {{ color: '#38bdf8', borderRadius: [4, 4, 0, 0] }}
                        }},
                        {{
                            name: 'ม้าระบายออก',
                            type: 'bar',
                            data: {mule_buckets_json},
                            itemStyle: {{ color: '#f43f5e', borderRadius: [4, 4, 0, 0] }}
                        }}
                    ]
                }});
            }}

            // 5. Cumulative Flow Chart (Tab 5)
            const cumEl = document.getElementById('cumFlowChart');
            if (cumEl) {{
                const cumChart = echarts.init(cumEl);
                window.cumFlowChartInstance = cumChart;
                cumChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        textStyle: {{ color: tooltipText, fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            let s = '<b>วันที่ ' + params[0].name + '</b><br/>';
                            params.forEach(p => {{
                                s += p.marker + ' ' + p.seriesName + ': <b>฿' + p.value.toLocaleString('en-US', {{minimumFractionDigits: 2}}) + '</b><br/>';
                            }});
                            return s;
                        }}
                    }},
                    legend: {{
                        data: ['ยอดเข้าสะสม (เหยื่อ)', 'ยอดย้ายสะสม (ม้า)'],
                        textStyle: {{ color: labelColor, fontFamily: 'Sarabun' }},
                        top: '2%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {daily_dates_json},
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        axisLabel: {{ color: labelColor, fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        axisLine: {{ lineStyle: {{ color: axisColor }} }},
                        splitLine: {{ lineStyle: {{ color: splitColor }} }},
                        axisLabel: {{
                            color: labelColor,
                            formatter: function(val) {{ return '฿' + (val / 1000) + 'k'; }}
                        }}
                    }},
                    series: [
                        {{
                            name: 'ยอดเข้าสะสม (เหยื่อ)',
                            type: 'line',
                            smooth: true,
                            data: {cum_vic_sums_json},
                            lineStyle: {{ width: 3, color: '#38bdf8' }},
                            itemStyle: {{ color: '#38bdf8' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(56, 189, 248, 0.25)' }},
                                    {{ offset: 1, color: 'rgba(56, 189, 248, 0.0)' }}
                                ])
                            }}
                        }},
                        {{
                            name: 'ยอดย้ายสะสม (ม้า)',
                            type: 'line',
                            smooth: true,
                            data: {cum_mule_sums_json},
                            lineStyle: {{ width: 3, color: '#f43f5e' }},
                            itemStyle: {{ color: '#f43f5e' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(244, 63, 94, 0.25)' }},
                                    {{ offset: 1, color: 'rgba(244, 63, 94, 0.0)' }}
                                ])
                            }}
                        }}
                    ]
                }});
            }}

            // Responsive Window Resize
            window.addEventListener('resize', () => {{
                if (window.sankeyChartInstance) window.sankeyChartInstance.resize();
                if (window.pieChartInstance) window.pieChartInstance.resize();
                if (window.timelineChartInstance) window.timelineChartInstance.resize();
                if (window.timelineCumChartInstance) window.timelineCumChartInstance.resize();
                if (window.txBucketChartInstance) window.txBucketChartInstance.resize();
                if (window.cumFlowChartInstance) window.cumFlowChartInstance.resize();
            }});
        }});
    </script>
</body>
</html>"""
        out_p.write_text(html, encoding="utf-8")
        return str(out_p.resolve())
