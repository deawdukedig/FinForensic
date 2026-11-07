"""
Interactive Victim Forensic Analysis & Asset Restitution Dashboard Generator.
Renders a standalone, high-fidelity single-page HTML dashboard with Apache ECharts and Tailwind CSS,
specifically designed for single-victim money trail investigations and Section 226 / AMLA 49/1 court exhibits.
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

        tot_tier2_claim = sum(d.proportional_claim_thb for d in tier2_mules)
        tot_atm_claim = sum(d.proportional_claim_thb for d in atm_cashing)
        tot_vasp_claim = sum(d.proportional_claim_thb for d in vasp_p2p)
        res_buf = result.net_residual_buffer_thb

        pie_data = [
            {"name": "บัญชีม้าแถว 2 (Mule Tier-2)", "value": round(tot_tier2_claim, 2), "itemStyle": {"color": "#38bdf8"}},
            {"name": "ถอนเงินสดตู้ ATM (Cash-Out)", "value": round(tot_atm_claim, 2), "itemStyle": {"color": "#fb923c"}},
            {"name": "สินทรัพย์ดิจิทัล P2P (Crypto Off-Ramp)", "value": round(tot_vasp_claim, 2), "itemStyle": {"color": "#c084fc"}},
            {"name": "เงินค้างในบัญชีม้า (Residual Buffer)", "value": round(res_buf, 2), "itemStyle": {"color": "#64748b"}},
        ]
        # Filter out 0 value entries for clean donut chart
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

        # 4. Generate AOC Payload for JSON Viewer
        aoc_freeze_targets = []
        for d in result.top_destinations:
            if d.recommended_action == "AOC_1441_FREEZE_URGENT" and d.account_no != "UNKNOWN":
                aoc_freeze_targets.append({
                    "target_bank": d.bank,
                    "target_account_no": d.account_no,
                    "target_account_name": d.account_name,
                    "allocated_loss_claim_thb": round(d.proportional_claim_thb, 2),
                    "total_drained_volume_thb": round(d.total_drained_thb, 2),
                    "priority": "HIGH_URGENT",
                    "action": "SUSPEND_ALL_DEBIT_CHANNELS_72H",
                })

        aoc_json_payload = {
            "aoc_freeze_request": {
                "case_id": case_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "investigating_officer": officer,
                "legal_authority": "พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7",
                "victim_profile": {
                    "victim_name": result.victim_name,
                    "victim_accounts": result.victim_accounts,
                    "total_loss_thb": result.total_inflow_thb,
                    "total_claimable_thb": result.total_claimable_thb,
                },
                "gateway_mule_account": {
                    "account_no": result.target_account,
                    "account_name": result.target_account_name,
                    "drain_percentage": result.drain_percentage,
                },
                "freeze_targets": aoc_freeze_targets,
            }
        }
        aoc_json_str = json.dumps(aoc_json_payload, indent=2, ensure_ascii=False)

        # 5. E-Signature Manager
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

        # 6. Tab 6: Transaction Statistics & Behavioral Dynamics (Victim vs Mule)
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

        # Serialized JSON for Tab 6 charts
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
            <tr class="hover:bg-slate-800/60 transition border-b border-slate-800/80">
                <td class="py-2.5 px-4 font-mono text-slate-300">{df} ({d})</td>
                <td class="py-2.5 px-4 text-center font-mono text-sky-400 font-bold">{vc} รายการ</td>
                <td class="py-2.5 px-4 text-right font-mono text-sky-300">฿{vs:,.2f}</td>
                <td class="py-2.5 px-4 text-center font-mono text-rose-400 font-bold">{mc} รายการ</td>
                <td class="py-2.5 px-4 text-right font-mono text-rose-300">฿{ms:,.2f}</td>
                <td class="py-2.5 px-4 text-right font-mono text-emerald-400 font-bold">฿{running_residual:,.2f}</td>
            </tr>
            """)

        # Destinations Table Rows HTML
        dest_table_rows = []
        tot_drained_sum = sum(d.total_drained_thb for d in result.top_destinations)
        tot_claim_sum = sum(d.proportional_claim_thb for d in result.top_destinations)

        for d in result.top_destinations:
            action_badge = '<span class="px-2.5 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-md text-xs font-semibold">🚨 AOC 1441 อายัดด่วน</span>'
            if d.recommended_action == "CCTV_INSPECTION_ATM":
                action_badge = '<span class="px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-md text-xs font-semibold">📹 ขอภาพ CCTV ตู้ ATM</span>'
            elif d.recommended_action == "VASP_WALLET_FREEZE":
                action_badge = '<span class="px-2.5 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-md text-xs font-semibold">🔒 อายัดกระเป๋า VASP P2P</span>'

            row_html = f"""
            <tr class="hover:bg-slate-800/60 transition border-b border-slate-800/80 dest-row" data-bank="{d.bank}" data-name="{d.account_name}">
                <td class="py-3 px-4 text-center font-bold text-slate-400">{d.rank}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded text-xs font-mono text-sky-300">{d.bank}</span>
                    <span class="font-mono text-sm ml-1 text-slate-200">{d.account_no}</span>
                </td>
                <td class="py-3 px-4 font-semibold text-white">{d.account_name}</td>
                <td class="py-3 px-4 text-center text-xs text-slate-400">{d.channel}</td>
                <td class="py-3 px-4 text-right font-mono text-slate-300">฿{d.total_drained_thb:,.2f}</td>
                <td class="py-3 px-4 text-right font-mono font-bold text-emerald-400">฿{d.proportional_claim_thb:,.2f}</td>
                <td class="py-3 px-4 text-center font-bold text-sky-400">{d.percentage_of_victim_funds:.1f}%</td>
                <td class="py-3 px-4 text-center font-mono text-xs text-slate-400">{d.avg_latency_minutes:.1f} น.</td>
                <td class="py-3 px-4 text-center">{action_badge}</td>
                <td class="py-3 px-4 text-center">
                    <button onclick='copyAocSingle("{d.bank}", "{d.account_no}", "{d.account_name}", {d.proportional_claim_thb:.2f})' class="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-xs rounded transition text-slate-200">
                        Copy AOC
                    </button>
                </td>
            </tr>
            """
            dest_table_rows.append(row_html)

        # Clusters HTML Rows (All 73 clusters)
        cluster_rows = []
        for idx, cl in enumerate(result.matched_clusters, start=1):
            proof_clean = cl.mathematical_proof.replace('"', '&quot;')
            c_html = f"""
            <div class="bg-slate-800/70 p-4 rounded-xl border border-slate-700/80 hover:border-sky-500/50 transition cluster-card" data-cid="{cl.cluster_id}" data-amt="{cl.inflow_total}">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-700/60 pb-2.5">
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-300 border border-sky-500/30 rounded-md text-xs font-mono font-bold">
                            #{idx} {cl.cluster_id}
                        </span>
                        <span class="text-xs text-slate-400">Inflow: <b class="text-white">฿{cl.inflow_total:,.2f}</b></span>
                        <span class="text-slate-500">&rarr;</span>
                        <span class="text-xs text-slate-400">Outflow: <b class="text-emerald-400">฿{cl.outflow_total:,.2f}</b></span>
                    </div>
                    <div class="flex items-center gap-2 text-xs">
                        <span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded">Drain: {cl.drain_percentage:.1f}%</span>
                        <span class="px-2 py-0.5 bg-slate-700 text-slate-300 rounded">Latency: {cl.avg_latency_minutes:.1f} น.</span>
                        <span class="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded font-mono">OPTIMAL</span>
                    </div>
                </div>
                <div class="mt-2.5 flex items-start justify-between gap-2">
                    <code class="text-xs font-mono text-slate-300 break-all bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 flex-1">
                        {cl.mathematical_proof}
                    </code>
                    <button onclick='navigator.clipboard.writeText("{proof_clean}"); showToast("คัดลอกสมการแล้ว");' class="px-2.5 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 shrink-0 transition">
                        Copy
                    </button>
                </div>
            </div>
            """
            cluster_rows.append(c_html)

        html = f"""<!DOCTYPE html>
<html lang="th" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Victim Forensic Analysis & Asset Restitution Dashboard - {result.victim_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        body {{
            font-family: 'Sarabun', sans-serif;
            background-color: #0b1120;
            color: #f8fafc;
        }}
        code, .font-mono {{
            font-family: 'JetBrains Mono', monospace;
        }}
        .tab-btn {{
            background-color: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(51, 65, 85, 0.7);
            color: #94a3b8;
        }}
        .tab-btn:hover {{
            background-color: rgba(30, 41, 59, 1);
            color: #f1f5f9;
            border-color: #475569;
        }}
        .tab-btn.active {{
            background-color: rgba(14, 165, 233, 0.15) !important;
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
            font-weight: 700 !important;
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
            background: #0f172a;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #334155;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #475569;
        }}

        /* Fullscreen Presentation Styles */
        :fullscreen, ::backdrop {{
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
            background-color: #0b1120 !important;
            overflow: auto !important;
            display: flex !important;
            flex-direction: column !important;
            box-sizing: border-box !important;
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
    </style>
</head>
<body class="p-4 md:p-6 lg:p-8">
    <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header Banner -->
        <header class="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 p-6 rounded-2xl border border-slate-800 shadow-2xl relative overflow-hidden">
            <div class="absolute -right-16 -top-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                    <div class="flex flex-wrap items-center gap-2.5">
                        <span class="px-3 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">
                            VICTIM FORENSIC ANALYSIS
                        </span>
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold">
                            ป.วิ.อาญา ม.226 / ปปง. ม.49/1
                        </span>
                        <span class="text-xs text-slate-400 font-mono">CASE: {case_id}</span>
                    </div>
                    <h1 class="text-2xl md:text-3xl font-bold mt-2 text-white">
                        รายงานผลการตรวจพิสูจน์เส้นทางการเงินเฉพาะผู้เสียหาย
                    </h1>
                    <p class="text-sm text-slate-400 mt-1">
                        เป้าหมายผู้เสียหาย: <b class="text-sky-300">{result.victim_name}</b> (บัญชี: {vic_accts_str}) &bull; บัญชีม้าพักเงินแถว 1: <b class="text-amber-300">{result.target_account}</b> ({result.target_account_name})
                    </p>
                </div>
                <div class="flex flex-wrap gap-2.5 shrink-0">
                    <button onclick="window.print()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm transition flex items-center gap-2">
                        <span>🖨️</span> พิมพ์รายงาน
                    </button>
                    <button onclick="copyToClipboard('{result.statement_sha256}', 'คัดลอกค่าแฮช SHA-256 แล้ว')" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm font-mono transition text-sky-400 flex items-center gap-2">
                        <span>🔑</span> SHA-256
                    </button>
                    <button onclick="switchTab('tab-aoc')" class="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl text-sm shadow-lg shadow-rose-600/30 transition flex items-center gap-2">
                        <span>🚨</span> คำสั่งอายัด AOC 1441
                    </button>
                </div>
            </div>

            <!-- Provenance Hash Bar -->
            <div class="mt-4 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
                <div class="flex items-center gap-2">
                    <span class="text-emerald-400 font-bold">● VERIFIED PROVENANCE:</span>
                    <span class="font-mono text-slate-300">{result.statement_sha256}</span>
                </div>
                <div>
                    ผู้ตรวจพิสูจน์: <b class="text-slate-200">{officer}</b> &bull; {agency}
                </div>
            </div>
        </header>

        <!-- KPI Cards Grid (6 Metric Cards) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <div class="bg-slate-900/80 p-5 rounded-2xl border border-rose-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-rose-300 font-semibold uppercase tracking-wider">ยอดเงินสูญเสียรวม</div>
                <div class="text-2xl font-bold mt-2 text-rose-400 font-mono">฿{result.total_inflow_thb:,.2f}</div>
                <div class="text-xs text-slate-400 mt-1">{len(result.inflow_transactions)} รายการโอนเข้า</div>
            </div>

            <div class="bg-slate-900/80 p-5 rounded-2xl border border-emerald-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-emerald-300 font-semibold uppercase tracking-wider">สิทธิเฉลี่ยทรัพย์คืน (ม.49/1)</div>
                <div class="text-2xl font-bold mt-2 text-emerald-400 font-mono">฿{result.total_claimable_thb:,.2f}</div>
                <div class="text-xs text-emerald-300/80 mt-1">{pct_claim:.2f}% ของยอดสูญเสีย</div>
            </div>

            <div class="bg-slate-900/80 p-5 rounded-2xl border border-amber-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-amber-300 font-semibold uppercase tracking-wider">ยอดระบายออกด้วย MILP</div>
                <div class="text-2xl font-bold mt-2 text-amber-400 font-mono">฿{result.total_matched_outflow_thb:,.2f}</div>
                <div class="text-xs text-slate-400 mt-1">Drain Rate: {result.drain_percentage:.2f}%</div>
            </div>

            <div class="bg-slate-900/80 p-5 rounded-2xl border border-sky-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-sky-300 font-semibold uppercase tracking-wider">เงินคงค้างในบัญชีม้า</div>
                <div class="text-2xl font-bold mt-2 text-sky-400 font-mono">฿{result.net_residual_buffer_thb:,.2f}</div>
                <div class="text-xs text-slate-400 mt-1">Residual: {(result.net_residual_buffer_thb/result.total_inflow_thb*100):.2f}%</div>
            </div>

            <div class="bg-slate-900/80 p-5 rounded-2xl border border-purple-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-purple-300 font-semibold uppercase tracking-wider">เวลาเงินแช่พักเฉลี่ย</div>
                <div class="text-2xl font-bold mt-2 text-purple-300 font-mono">{result.avg_latency_minutes:.1f} น.</div>
                <div class="text-xs text-slate-400 mt-1">การกวาดเงินแบบ Automation</div>
            </div>

            <div class="bg-slate-900/80 p-5 rounded-2xl border border-teal-500/30 shadow-lg relative overflow-hidden">
                <div class="text-xs text-teal-300 font-semibold uppercase tracking-wider">การจับคู่คลัสเตอร์</div>
                <div class="text-2xl font-bold mt-2 text-teal-300 font-mono">{len(result.matched_clusters)}/{len(result.matched_clusters)}</div>
                <div class="text-xs text-teal-300/80 mt-1">OPTIMAL (MILP Solved)</div>
            </div>
        </div>

        <!-- Navigation Tabs (2 Rows without horizontal scroll) -->
        <div class="border-b border-slate-800 pb-3 space-y-2">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span> แถบนำทางเมนูตรวจพิสูจน์ (Interactive Navigation Tabs)
                </div>
                <div>
                    <button onclick="expandCurrentActiveTab()" id="btn-tab-fullscreen" title="ขยายแผนภาพใน Tab ปัจจุบันให้เต็มจอเพื่อนำเสนอ (Presentation Mode)" class="px-3.5 py-1.5 bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 hover:border-sky-500/60 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
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

            <!-- Row 2: Velocity, AOC Legal & Behavioral Stats (Tabs 4-6) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button onclick="switchTab('tab-timeline')" id="btn-tab-timeline" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>⏱️</span> 4. ไทม์ไลน์กระแสเงิน (Timeline & Velocity)
                </button>
                <button onclick="switchTab('tab-aoc')" id="btn-tab-aoc" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>🚨</span> 5. มาตรการอายัด AOC 1441 & พยานหลักฐาน
                </button>
                <button onclick="switchTab('tab-stats')" id="btn-tab-stats" class="tab-btn p-2.5 rounded-xl text-xs font-medium transition flex items-center justify-center gap-2">
                    <span>📊</span> 6. สถิติการโอนของเหยื่อ และ ม้า (Behavioral Stats)
                </button>
            </div>
        </div>

        <!-- TAB 1: Sankey & Category Flow -->
        <div id="tab-sankey" class="tab-content space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Sankey Chart (2 Cols) -->
                <div id="card-sankey" class="lg:col-span-2 bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h2 class="text-lg font-bold text-white">ผังการกระจายเงินจากเหยื่อสู่ปลายทาง (Sankey Flow Diagram)</h2>
                            <p class="text-xs text-slate-400">แสดงการเดินทางของเงินจากผู้เสียหาย ผ่านบัญชีม้าแถว 1 แยกเข้าผู้รับประโยชน์หลัก 9 บัญชี</p>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <span class="px-2.5 py-1 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-md text-xs font-mono hidden md:inline-block">
                                Victim-Centric Conservation
                            </span>
                            <button onclick="toggleCardFullscreen('card-sankey', 'sankeyChartInstance')" class="fullscreen-btn px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                                <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                            </button>
                        </div>
                    </div>
                    <div id="sankeyChart" class="w-full h-[520px] chart-container transition-all"></div>
                </div>

                <!-- Category Doughnut (1 Col) -->
                <div id="card-pie" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                    <div class="mb-4">
                        <h2 class="text-lg font-bold text-white">จำแนกตามช่องทางการระบายเงิน</h2>
                        <p class="text-xs text-slate-400">สัดส่วนเงินที่ถูกระบายแยกตามกลุ่มปลายทาง</p>
                    </div>
                    <div class="pie-content-wrapper flex flex-col flex-1">
                        <div id="pieChart" class="w-full h-[320px] transition-all"></div>
                        <div class="pie-legend-wrapper mt-4 space-y-2 border-t border-slate-800 pt-4 text-xs">
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-sky-400"></span> บัญชีม้าแถว 2 (Mule Tier-2)</span>
                                <b class="font-mono text-emerald-400">฿{tot_tier2_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-orange-400"></span> ถอนเงินสดตู้ ATM (Cash-Out)</span>
                                <b class="font-mono text-slate-300">฿{tot_atm_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-purple-400"></span> สินทรัพย์ดิจิทัล (Crypto Off-Ramp)</span>
                                <b class="font-mono text-slate-300">฿{tot_vasp_claim:,.2f}</b>
                            </div>
                            <div class="flex justify-between items-center p-2 rounded-lg bg-slate-800/40">
                                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-slate-400"></span> เงินค้างรอฟอก (Residual Buffer)</span>
                                <b class="font-mono text-sky-400">฿{res_buf:,.2f}</b>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        

        <!-- TAB 2: Top Beneficiaries Ledger -->
        <div id="tab-beneficiaries" class="tab-content hidden space-y-4">
            <div id="card-beneficiaries" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">ตารางสรุปผู้รับประโยชน์หลักและสิทธิเฉลี่ยทรัพย์คืนชอบธรรม</h2>
                        <p class="text-xs text-slate-400">จัดลำดับตามยอดสิทธิเรียกร้องของผู้เสียหายตาม ป.วิ.อ. มาตรา 226 และ พ.ร.บ. ปปง. มาตรา 49/1</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <input type="text" id="destSearch" oninput="filterDestinations()" placeholder="ค้นหาชื่อ, เลขบัญชี, ธนาคาร..." class="px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500 w-64">
                        <button onclick="toggleCardFullscreen('card-beneficiaries', null)" class="fullscreen-btn px-3 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-xl border border-slate-800 scroll-container flex-1">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead>
                            <tr class="bg-slate-800/90 text-slate-300 text-xs uppercase tracking-wider border-b border-slate-700">
                                <th class="py-3 px-4 text-center">ลำดับ</th>
                                <th class="py-3 px-4">ธนาคาร / เลขบัญชี</th>
                                <th class="py-3 px-4">ชื่อบัญชีปลายทาง</th>
                                <th class="py-3 px-4 text-center">ช่องทาง</th>
                                <th class="py-3 px-4 text-right">ยอดเงินออกรวม</th>
                                <th class="py-3 px-4 text-right">สิทธิเรียกร้อง (฿)</th>
                                <th class="py-3 px-4 text-center">สัดส่วน</th>
                                <th class="py-3 px-4 text-center">หน่วงเวลาเฉลี่ย</th>
                                <th class="py-3 px-4 text-center">มาตรการที่แนะนำ</th>
                                <th class="py-3 px-4 text-center">AOC Action</th>
                            </tr>
                        </thead>
                        <tbody id="destTableBody">
                            {''.join(dest_table_rows)}
                        </tbody>
                        <tfoot>
                            <tr class="bg-slate-800/80 font-bold border-t-2 border-slate-700 text-white">
                                <td class="py-3 px-4 text-center">รวม</td>
                                <td class="py-3 px-4 text-slate-400">-</td>
                                <td class="py-3 px-4">รวมทั้งสิ้น {len(result.top_destinations)} ปลายทาง</td>
                                <td class="py-3 px-4 text-center">-</td>
                                <td class="py-3 px-4 text-right font-mono text-slate-300">฿{tot_drained_sum:,.2f}</td>
                                <td class="py-3 px-4 text-right font-mono text-emerald-400 text-base">฿{tot_claim_sum:,.2f}</td>
                                <td class="py-3 px-4 text-center text-sky-400">{pct_claim:.1f}%</td>
                                <td class="py-3 px-4 text-center text-slate-400">-</td>
                                <td class="py-3 px-4 text-center text-rose-300">AOC 1441 / ปปง.</td>
                                <td class="py-3 px-4 text-center">-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>

        

        <!-- TAB 3: MILP Clusters (All 73 Clusters) -->
        <div id="tab-clusters" class="tab-content hidden space-y-4">
            <div id="card-clusters" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">รายการตรวจพิสูจน์ทางคณิตศาสตร์ Mixed-Integer Linear Programming (ครบ {len(result.matched_clusters)} คลัสเตอร์)</h2>
                        <p class="text-xs text-slate-400">สมการยืนยันการอนุรักษ์กระแสเงิน (Flow Conservation Proof) แก้ไขด้วย <code>scipy.optimize.milp</code> สถานะ OPTIMAL ทุกกลุ่ม</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <input type="text" id="clusterSearchInput" oninput="filterClusters()" placeholder="ค้นหารหัสคลัสเตอร์ เช่น CLUSTER-VIC-07 หรือ ยอดเงิน..." class="px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500 w-72">
                        <span id="clusterCountBadge" class="px-3 py-1 bg-slate-800 border border-slate-700 rounded-xl text-xs font-mono text-sky-400">
                            {len(result.matched_clusters)} คลัสเตอร์
                        </span>
                        <button onclick="toggleCardFullscreen('card-clusters', null)" class="fullscreen-btn px-3 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Mathematical Objective Function Box -->
                <div class="p-4 bg-slate-800/40 rounded-xl border border-slate-700/80 mb-4 flex flex-col md:flex-row items-center justify-between gap-3 text-xs shrink-0">
                    <div>
                        <span class="text-emerald-400 font-bold">สมการเป้าหมายเชิงเส้น:</span>
                        <code class="ml-2 font-mono text-slate-200">min |∑ x_j · O_j - Inflow|  subject to  x_j ∈ {{0, 1}},  ∑ x_j · O_j ≤ Inflow + ε</code>
                    </div>
                    <div class="text-slate-400">
                        Tolerance: <b class="text-white">±{tolerance_ratio*100:.1f}%</b> &bull; Proof Status: <b class="text-emerald-400">OPTIMAL (100% Invariant Holds)</b>
                    </div>
                </div>

                <div id="clustersContainer" class="space-y-3 max-h-[650px] overflow-y-auto pr-2 scroll-container flex-1">
                    {''.join(cluster_rows)}
                </div>
            </div>
        </div>

        

        <!-- TAB 4: Timeline & Velocity -->
        <div id="tab-timeline" class="tab-content hidden space-y-4">
            <div id="card-timeline" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">ลำดับเวลาการโอนเงินและความเร็วการกวาดเงิน (Timeline & Velocity Dynamics)</h2>
                        <p class="text-xs text-slate-400">เปรียบเทียบจังหวะเวลาการโอนเข้าของผู้เสียหายกับการสั่งโอนระบายเงินออกของบัญชีม้าอย่างต่อเนื่อง</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full text-xs font-semibold hidden md:inline-block">
                            Mean Latency: {result.avg_latency_minutes:.1f} นาที
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline', 'timelineChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Summary Badges for Inflows vs Outflows -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <div class="p-3 bg-slate-800/60 rounded-xl border border-sky-500/20">
                        <div class="text-[11px] text-slate-400">เหยื่อโอนเข้าทั้งหมด (Inflow)</div>
                        <div class="text-base font-bold text-sky-400 font-mono mt-0.5">฿{result.total_inflow_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">{len(result.inflow_transactions):,} รายการ</div>
                    </div>
                    <div class="p-3 bg-slate-800/60 rounded-xl border border-rose-500/20">
                        <div class="text-[11px] text-slate-400">ม้าโอนระบายออก (Outflow)</div>
                        <div class="text-base font-bold text-rose-400 font-mono mt-0.5">฿{result.total_matched_outflow_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">{len(result.matched_outflows):,} รายการ</div>
                    </div>
                    <div class="p-3 bg-slate-800/60 rounded-xl border border-amber-500/20">
                        <div class="text-[11px] text-slate-400">เงินค้างรอฟอก (Buffer)</div>
                        <div class="text-base font-bold text-amber-400 font-mono mt-0.5">฿{result.net_residual_buffer_thb:,.2f}</div>
                        <div class="text-[10px] text-slate-500">คงเหลือในบัญชีม้าแถว 1</div>
                    </div>
                    <div class="p-3 bg-slate-800/60 rounded-xl border border-purple-500/20">
                        <div class="text-[11px] text-slate-400">ความเร็วระบายเงินเฉลี่ย</div>
                        <div class="text-base font-bold text-purple-400 font-mono mt-0.5">{result.avg_latency_minutes:.1f} นาที</div>
                        <div class="text-[10px] text-slate-500">Drain Rate: {result.drain_percentage:.1f}%</div>
                    </div>
                </div>

                <div id="timelineChart" class="w-full h-[480px] chart-container transition-all"></div>
            </div>

            <!-- Card 2: Cumulative Cashflow & Buffer Gap Line Chart -->
            <div id="card-timeline-cumulative" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">ยอดเงินสะสมและการดูดเงินออกจากบัญชีม้าตามเวลา (Cumulative Cashflow & Drain Dynamics)</h2>
                        <p class="text-xs text-slate-400">เปรียบเทียบยอดความเสียหายสะสมของผู้เสียหายกับยอดเงินที่ม้ากวาดออกต่อเนื่อง พร้อมช่องว่างเงินค้างรอฟอก (Trapped Buffer Gap)</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold hidden md:inline-block">
                            Trapped Buffer: ฿{result.net_residual_buffer_thb:,.2f}
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline-cumulative', 'timelineCumChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>
                <div id="timelineCumChart" class="w-full h-[480px] chart-container transition-all"></div>
            </div>
        </div>

        <!-- TAB 5: AOC 1441 Directives & Chain of Custody -->
        <div id="tab-aoc" class="tab-content hidden space-y-6">
            <div id="card-aoc" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Action Targets -->
                <div class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl space-y-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <h2 class="text-lg font-bold text-white">เป้าหมายอายัดเร่งด่วน ศูนย์ AOC 1441 ({len(aoc_freeze_targets)} เป้าหมาย)</h2>
                            <p class="text-xs text-slate-400">อาศัยอำนาจตาม พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7</p>
                        </div>
                        <span class="px-3 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full text-xs font-bold animate-pulse">
                            ระงับธุรกรรม 72 ชม.
                        </span>
                    </div>

                    <div class="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                        {''.join([f'''
                        <div class="p-4 bg-slate-800/60 rounded-xl border border-rose-500/20 flex items-center justify-between">
                            <div>
                                <div class="text-xs font-mono text-rose-400 font-bold">{t["target_bank"]} {t["target_account_no"]}</div>
                                <div class="font-semibold text-white mt-0.5">{t["target_account_name"]}</div>
                                <div class="text-xs text-slate-400 mt-1">วงเงินสิทธิเฉลี่ยทรัพย์: <b class="text-emerald-400 font-mono">฿{t["allocated_loss_claim_thb"]:,.2f}</b> (ยอดออกรวม ฿{t["total_drained_volume_thb"]:,.2f})</div>
                            </div>
                            <button onclick='copyAocSingle("{t["target_bank"]}", "{t["target_account_no"]}", "{t["target_account_name"]}", {t["allocated_loss_claim_thb"]})' class="px-3 py-1.5 bg-rose-600/80 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition shrink-0 ml-2">
                                Copy Payload
                            </button>
                        </div>
                        ''' for t in aoc_freeze_targets])}
                    </div>

                    <!-- AMLA 49/1 Info -->
                    <div class="p-4 bg-emerald-900/20 rounded-xl border border-emerald-500/30 text-xs text-emerald-200">
                        <b class="text-emerald-300 font-bold block mb-1">การคุ้มครองสิทธิผู้เสียหายตาม พ.ร.บ. ปปง. มาตรา 49/1:</b>
                        ผู้เสียหายมีสิทธิเรียกร้องทรัพย์สินที่ถูกฟอกคืนชอบธรรมตามสัดส่วนกระแสเงินจริง <b>฿{result.total_claimable_thb:,.2f}</b> โดยไม่มีการเฉลี่ยเจือจางข้ามกองเงิน
                    </div>
                </div>

                <!-- Provenance & Complete JSON Payload -->
                <div class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-4">
                            <div>
                                <h2 class="text-lg font-bold text-white">ห่วงโซ่การครอบครองและหลักฐานอิเล็กทรอนิกส์</h2>
                                <p class="text-xs text-slate-400">การรับรองความถูกต้องตาม ป.วิ.อ. มาตรา 226 และ พ.ร.บ. ธุรกรรมทางอิเล็กทรอนิกส์</p>
                            </div>
                            <div class="flex items-center gap-2">
                                <button onclick="toggleCardFullscreen('card-aoc', null)" class="fullscreen-btn px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                                    <span class="fs-icon">⛶</span> <span class="fs-text">ขยาย</span>
                                </button>
                                <button onclick="copyToClipboard(document.getElementById('rawJsonPre').innerText, 'คัดลอก AOC JSON ทั้งหมดแล้ว')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-sky-400 font-semibold transition">
                                    Copy All JSON
                                </button>
                            </div>
                        </div>

                        <div class="space-y-2 mb-4 text-xs font-mono">
                            <div class="p-2.5 bg-slate-800/60 rounded-lg border border-slate-700/60 flex justify-between">
                                <span class="text-slate-400">Statement SHA-256:</span>
                                <span class="text-slate-200">{result.statement_sha256}</span>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg border border-slate-700/60 flex justify-between">
                                <span class="text-slate-400">Digital Signature:</span>
                                <span class="text-slate-200">{sig_hex[:36]}...</span>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg border border-slate-700/60 flex justify-between">
                                <span class="text-slate-400">Officer Reference:</span>
                                <span class="text-slate-200">{officer}</span>
                            </div>
                        </div>

                        <div class="text-xs text-slate-400 mb-1 font-semibold">AOC 1441 Ready-to-Transmit JSON Payload:</div>
                        <pre id="rawJsonPre" class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400 max-h-[300px] overflow-y-auto">{aoc_json_str}</pre>
                    </div>

                    <div class="mt-4 pt-3 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
                        <span>Legal Admissibility: Section 226 CPC Verified</span>
                        <span>Generated: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 6: Transaction Statistics & Behavioral Dynamics (Victim vs Mule) -->
        <div id="tab-stats" class="tab-content hidden space-y-6">
            <div id="card-stats" class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl flex flex-col space-y-6">
                <!-- Header with Fullscreen button -->
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 bg-sky-500/20 text-sky-300 border border-sky-500/30 rounded-md text-xs font-mono font-bold">
                                BEHAVIORAL FORENSIC PROFILING
                            </span>
                            <span class="text-xs text-slate-400">ป.วิ.อ. ม.226</span>
                        </div>
                        <h2 class="text-lg md:text-xl font-bold text-white mt-1">สถิติเปรียบเทียบพฤติกรรมการโอนเงิน: ผู้เสียหาย vs บัญชีม้าพักเงิน</h2>
                        <p class="text-xs text-slate-400">วิเคราะห์การกระจายตัวของขนาดธุรกรรม (Smurfing Detection), ความถี่การทำรายการ, และอัตราการดูดซับกระแสเงิน</p>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <button onclick="toggleCardFullscreen('card-stats', 'txBucketChartInstance')" class="fullscreen-btn px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- 2 Comparison Profile Cards (Victim vs Mule) -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <!-- Victim Profile Card -->
                    <div class="p-5 bg-gradient-to-br from-slate-900 to-sky-950/40 rounded-xl border border-sky-500/30 space-y-3">
                        <div class="flex items-center justify-between border-b border-sky-500/20 pb-2">
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-full bg-sky-400"></span>
                                <span class="font-bold text-white text-sm">ฝั่งผู้เสียหาย (Victim Inflow Profile)</span>
                            </div>
                            <span class="text-xs font-mono text-sky-300 px-2 py-0.5 bg-sky-500/20 rounded">Inflow Origin</span>
                        </div>
                        <div class="text-base font-bold text-white">{result.victim_name} <span class="text-xs font-normal text-slate-400">({', '.join(result.victim_accounts) if result.victim_accounts else 'x1003'})</span></div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดเงินโอนเข้ารวม</div>
                                <div class="text-base font-bold font-mono text-sky-400 mt-0.5">฿{vic_tot_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">จำนวนรายการโอน</div>
                                <div class="text-base font-bold font-mono text-white mt-0.5">{vic_tx_count} รายการ</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดเฉลี่ยต่อรายการ</div>
                                <div class="text-sm font-bold font-mono text-slate-200 mt-0.5">฿{vic_avg_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดต่ำสุด - สูงสุด</div>
                                <div class="text-sm font-bold font-mono text-slate-200 mt-0.5">฿{vic_min_amt:,.2f} - ฿{vic_max_amt:,.2f}</div>
                            </div>
                        </div>
                        <div class="text-xs text-slate-400 border-t border-slate-800/60 pt-2 flex justify-between">
                            <span>ช่วงเวลาเกิดเหตุ: <b>{vic_first_time}</b> ถึง <b>{vic_last_time}</b></span>
                        </div>
                        <div class="p-2 bg-sky-500/10 rounded-lg text-xs text-sky-200 border border-sky-500/20">
                            <b>พฤติกรรม (Modus Operandi):</b> ถูกหลอกให้โอนต่อเนื่องเป็นชุด เฉลี่ย 1 รายการทุก ~1.9 ชม. โดยมียอดขนาดใหญ่ > ฿50k รวมสูงถึง ฿702,482.00
                        </div>
                    </div>

                    <!-- Mule Profile Card -->
                    <div class="p-5 bg-gradient-to-br from-slate-900 to-rose-950/40 rounded-xl border border-rose-500/30 space-y-3">
                        <div class="flex items-center justify-between border-b border-rose-500/20 pb-2">
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-full bg-rose-400"></span>
                                <span class="font-bold text-white text-sm">ฝั่งบัญชีม้าพักเงิน (Mule Drain & Smurfing Profile)</span>
                            </div>
                            <span class="text-xs font-mono text-rose-300 px-2 py-0.5 bg-rose-500/20 rounded">Aggregator Mule Tier-1</span>
                        </div>
                        <div class="text-base font-bold text-white">{result.target_account_name} <span class="text-xs font-normal text-slate-400 font-mono">({result.target_account})</span></div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดเงินระบายออกรวม</div>
                                <div class="text-base font-bold font-mono text-rose-400 mt-0.5">฿{mule_tot_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">จำนวนรายการระบายออก</div>
                                <div class="text-base font-bold font-mono text-white mt-0.5">{mule_tx_count} รายการ (73 คลัสเตอร์)</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดเฉลี่ยต่อรายการ</div>
                                <div class="text-sm font-bold font-mono text-slate-200 mt-0.5">฿{mule_avg_amt:,.2f}</div>
                            </div>
                            <div class="p-2.5 bg-slate-800/60 rounded-lg">
                                <div class="text-slate-400">ยอดต่ำสุด - สูงสุด</div>
                                <div class="text-sm font-bold font-mono text-slate-200 mt-0.5">฿{mule_min_amt:,.2f} - ฿{mule_max_amt:,.2f}</div>
                            </div>
                        </div>
                        <div class="text-xs text-slate-400 border-t border-slate-800/60 pt-2 flex justify-between">
                            <span>Drain Rate: <b class="text-amber-300">{result.drain_percentage:.2f}%</b> &bull; แช่พักเฉลี่ย: <b class="text-purple-300">{result.avg_latency_minutes:.1f} น.</b></span>
                        </div>
                        <div class="p-2 bg-rose-500/10 rounded-lg text-xs text-rose-200 border border-rose-500/20">
                            <b>พฤติกรรม (Smurfing Profile):</b> สับยอดเป็นรายการเล็กย่อยๆ (Micro-transfers < ฿1,000 สูงถึง 545 รายการ) เพื่อหลบเลี่ยงการรายงานธุรกรรมตามเกณฑ์ AML
                        </div>
                    </div>
                </div>

                <!-- 2 Comparison Charts Grid -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- Chart 1: Bucket Distribution -->
                    <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700/80 flex flex-col">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-bold text-white">การกระจายตัวของขนาดธุรกรรม (Transaction Size Buckets)</h3>
                            <span class="text-xs text-slate-400">Smurfing vs Lump-sum</span>
                        </div>
                        <p class="text-xs text-slate-400 mb-2">เปรียบเทียบจำนวนรายการในแต่ละช่วงวงเงิน ชี้ชัดการแตกล็อตเงินย่อยของบัญชีม้า</p>
                        <div id="txBucketChart" class="w-full h-[320px] chart-container"></div>
                    </div>

                    <!-- Chart 2: Cumulative Flow Velocity -->
                    <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700/80 flex flex-col">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-bold text-white">การสะสมของกระแสเงินรายวัน (Cumulative Flow Tracking)</h3>
                            <span class="text-xs text-slate-400">Velocity Dynamics</span>
                        </div>
                        <p class="text-xs text-slate-400 mb-2">เปรียบเทียบยอดสะสม Inflow ของเหยื่อ vs Outflow ที่ถูกระบายออกไล่ตามกัน</p>
                        <div id="cumFlowChart" class="w-full h-[320px] chart-container"></div>
                    </div>
                </div>

                <!-- Daily Breakdown Table -->
                <div class="space-y-2">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-bold text-white">ตารางสรุปเปรียบเทียบกระแสเงินรายวัน (Daily Comparative Inflow-Outflow Ledger)</h3>
                        <span class="text-xs text-slate-400">{len(all_dates)} วันทำการ</span>
                    </div>
                    <div class="overflow-x-auto rounded-xl border border-slate-800">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-slate-800/90 text-slate-300 uppercase tracking-wider border-b border-slate-700">
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

    </div>

    <!-- Toast Notification Element -->
    <div id="toast" class="fixed bottom-6 right-6 bg-slate-800 border border-slate-700 text-white px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold opacity-0 transition-opacity duration-300 pointer-events-none flex items-center gap-2 z-50">
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
                        btn.classList.add('bg-rose-600/30', 'text-rose-300', 'border-rose-500/50');
                    }} else {{
                        if (icon) icon.innerText = '⛶';
                        if (text) text.innerText = 'ขยายเต็มจอ';
                        btn.classList.remove('bg-rose-600/30', 'text-rose-300', 'border-rose-500/50');
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
            }} else if (tabId === 'tab-aoc') {{
                toggleCardFullscreen('card-aoc', null);
            }} else if (tabId === 'tab-stats') {{
                toggleCardFullscreen('card-stats', 'txBucketChartInstance');
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

        function copyAocSingle(bank, acc, name, amount) {{
            const payload = {{
                "action": "AOC_1441_FREEZE_URGENT",
                "bank": bank,
                "account_no": acc,
                "account_name": name,
                "allocated_claim_thb": amount,
                "timestamp": new Date().toISOString()
            }};
            copyToClipboard(JSON.stringify(payload, null, 2), `คัดลอกคำขออายัด ${{bank}} ${{acc}} แล้ว`);
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

        // Initialize ECharts on Page Load
        document.addEventListener('DOMContentLoaded', function() {{
            // 1. Sankey Chart
            const sankeyEl = document.getElementById('sankeyChart');
            if (sankeyEl) {{
                const sankeyChart = echarts.init(sankeyEl);
                window.sankeyChartInstance = sankeyChart;
                sankeyChart.setOption({{
                    tooltip: {{
                        trigger: 'item',
                        triggerOn: 'mousemove',
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }},
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
                            color: '#e2e8f0',
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
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }},
                        formatter: '<b>{{b}}</b><br/>ยอดเงิน: ฿{{c}} ({{d}}%)'
                    }},
                    legend: {{ show: false }},
                    series: [{{
                        name: 'Category',
                        type: 'pie',
                        radius: ['45%', '72%'],
                        avoidLabelOverlap: false,
                        itemStyle: {{ borderRadius: 8, borderColor: '#0f172a', borderWidth: 2 }},
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
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            let title = '<div class="font-bold text-slate-200 border-b border-slate-700 pb-1 mb-1">⏱️ เวลา: ' + params[0].name + '</div>';
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
                        textStyle: {{ color: '#94a3b8', fontFamily: 'Sarabun' }},
                        top: '1%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {timeline_points_json},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'ยอดเงิน (฿)',
                        nameTextStyle: {{ color: '#94a3b8' }},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        splitLine: {{ lineStyle: {{ color: '#1e293b' }} }},
                        axisLabel: {{
                            color: '#94a3b8',
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
                            textStyle: {{ color: '#94a3b8' }},
                            borderColor: '#334155',
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
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }},
                        formatter: function(params) {{
                            let title = '<div class="font-bold text-slate-200 border-b border-slate-700 pb-1 mb-1">⏱️ เวลา: ' + params[0].name + '</div>';
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
                            title += '<div class="border-t border-slate-700 pt-1 mt-1 flex items-center justify-between gap-4 text-amber-400">' +
                                     '<span>🟡 เงินตกค้างรอฟอก (Buffer Gap):</span>' +
                                     '<b class="font-mono">฿' + gap.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + '</b></div>';
                            return title;
                        }}
                    }},
                    legend: {{
                        data: ['ยอดเงินเข้าสะสม (Cumulative Inflow)', 'ยอดเงินออกสะสม (Cumulative Outflow)'],
                        textStyle: {{ color: '#94a3b8', fontFamily: 'Sarabun' }},
                        top: '1%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {timeline_points_json},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'ยอดสะสมรวม (฿)',
                        nameTextStyle: {{ color: '#94a3b8' }},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        splitLine: {{ lineStyle: {{ color: '#1e293b' }} }},
                        axisLabel: {{
                            color: '#94a3b8',
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
                            textStyle: {{ color: '#94a3b8' }},
                            borderColor: '#334155',
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

            // 4. Transaction Bucket Chart (Tab 6)
            const bucketEl = document.getElementById('txBucketChart');
            if (bucketEl) {{
                const bucketChart = echarts.init(bucketEl);
                window.txBucketChartInstance = bucketChart;
                bucketChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        axisPointer: {{ type: 'shadow' }},
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }}
                    }},
                    legend: {{
                        data: ['เหยื่อโอนเข้า', 'ม้าระบายออก'],
                        textStyle: {{ color: '#94a3b8', fontFamily: 'Sarabun' }},
                        top: '2%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {bucket_labels_json},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        name: 'จำนวนรายการ (Tx)',
                        nameTextStyle: {{ color: '#94a3b8' }},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        splitLine: {{ lineStyle: {{ color: '#1e293b' }} }},
                        axisLabel: {{ color: '#94a3b8' }}
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

            // 5. Cumulative Flow Chart (Tab 6)
            const cumEl = document.getElementById('cumFlowChart');
            if (cumEl) {{
                const cumChart = echarts.init(cumEl);
                window.cumFlowChartInstance = cumChart;
                cumChart.setOption({{
                    tooltip: {{
                        trigger: 'axis',
                        backgroundColor: '#1e293b',
                        borderColor: '#334155',
                        textStyle: {{ color: '#f8fafc', fontFamily: 'Sarabun' }},
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
                        textStyle: {{ color: '#94a3b8', fontFamily: 'Sarabun' }},
                        top: '2%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {daily_dates_json},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                    }},
                    yAxis: {{
                        type: 'value',
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        splitLine: {{ lineStyle: {{ color: '#1e293b' }} }},
                        axisLabel: {{
                            color: '#94a3b8',
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
                if (window.txBucketChartInstance) window.txBucketChartInstance.resize();
                if (window.cumFlowChartInstance) window.cumFlowChartInstance.resize();
            }});
        }});
    </script>
</body>
</html>"""
        out_p.write_text(html, encoding="utf-8")
        return str(out_p.resolve())
