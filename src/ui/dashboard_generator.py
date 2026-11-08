"""
Interactive Tri-Modal Forensic Visual Dashboard Generator.
Renders standalone HTML dashboards with Apache ECharts and Tailwind CSS,
supporting 5 specialized forensic tabs:
1. ผังการกระจายเงิน (Sankey Flow)
2. กราฟโครงข่ายเชื่อมโยง (Network Topology)
3. เส้นเวลาและความเร็ว (Timeline & Velocity)
4. รายการธุรกรรมเชิงลึก (Transactions)
5. สถิติเชิงลึกและการวิเคราะห์ข้อมูล (Forensic Data Analytics & FAQ Engine)
"""

from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Union
from src.models.transaction import BankTransaction, ActivityType
from src.models.dossier import SuspicionReport


class ForensicDashboardGenerator:
    """
    Assembles self-contained interactive visual dashboards for investigators.
    """

    def generate_html(
        self,
        report: SuspicionReport,
        transactions: List[BankTransaction],
        output_file_path: Optional[Union[str, Path]] = None,
        statement_name: Optional[str] = None,
    ) -> str:
        """
        Builds and saves the interactive HTML dashboard.
        """
        if output_file_path is None:
            if statement_name:
                out_p = Path(f"output/{statement_name}_dashboard.html")
            else:
                out_p = Path("output/dashboard.html")
        else:
            out_p = Path(output_file_path)

        if not statement_name:
            stem = out_p.stem
            if stem.endswith("_dashboard"):
                statement_name = stem[:-10]
            elif stem != "dashboard":
                statement_name = stem

        out_p.parent.mkdir(parents=True, exist_ok=True)

        inflows = [t for t in transactions if t.activity == ActivityType.INFLOW and not t.is_reversal]
        outflows = [t for t in transactions if t.activity == ActivityType.OUTFLOW and not t.is_reversal]
        fees = [t for t in transactions if t.activity == ActivityType.FEE]

        total_in = sum(t.amount for t in inflows)
        total_out = sum(t.amount for t in outflows)
        total_fee = sum(t.amount for t in fees)
        drain_rate = ((total_out + total_fee) / total_in * 100.0) if total_in > 0 else 0.0

        # Build Sankey Data
        target_name = f"{report.account_name} ({report.account_no_masked})"
        nodes_set = {target_name}
        links = []

        # Top inflows into Target
        for tx in sorted(inflows, key=lambda x: x.amount, reverse=True)[:8]:
            src_name = f"{tx.counterparty_name or 'ผู้เสียหาย/แหล่งเงิน'} ({tx.counterparty_bank or 'N/A'})"
            nodes_set.add(src_name)
            links.append({"source": src_name, "target": target_name, "value": round(tx.amount, 2)})

        # Outflows from Target to Recipients
        cp_out_vol: Dict[str, float] = {}
        for tx in outflows:
            dst = f"{tx.counterparty_name or 'ผู้รับโอน'} ({tx.counterparty_bank or 'N/A'})"
            cp_out_vol[dst] = cp_out_vol.get(dst, 0.0) + tx.amount

        for dst, vol in sorted(cp_out_vol.items(), key=lambda x: x[1], reverse=True)[:8]:
            nodes_set.add(dst)
            links.append({"source": target_name, "target": dst, "value": round(vol, 2)})

        sankey_nodes = [{"name": n} for n in sorted(list(nodes_set))]

        # Build Timeline Data with Inflow/Outflow Separation & Cumulative Trajectory
        sorted_txs = sorted(transactions, key=lambda tx: tx.timestamp)
        timeline_times = []
        timeline_inflows = []
        timeline_outflows = []
        timeline_balances = []
        timeline_cum_in = []
        timeline_cum_out = []
        timeline_data = []

        c_in = 0.0
        c_out = 0.0

        for tx in sorted_txs:
            ts = tx.timestamp
            time_str = tx.timestamp.strftime("%d/%m %H:%M:%S")
            timeline_times.append(time_str)

            in_amt = round(tx.amount, 2) if tx.activity == ActivityType.INFLOW else 0.0
            out_amt = round(tx.amount, 2) if tx.activity in (ActivityType.OUTFLOW, ActivityType.FEE) else 0.0

            timeline_inflows.append(in_amt)
            timeline_outflows.append(out_amt)
            timeline_balances.append(round(tx.balance, 2))

            c_in += in_amt
            c_out += out_amt
            timeline_cum_in.append(round(c_in, 2))
            timeline_cum_out.append(round(c_out, 2))

            act_label = "Inflow (เงินเข้า)" if tx.activity == ActivityType.INFLOW else ("Fee (ค่าธรรมเนียม)" if tx.activity == ActivityType.FEE else "Outflow (เงินออก)")
            timeline_data.append({
                "time": time_str,
                "amount": tx.amount,
                "activity": act_label,
                "desc": tx.description,
                "balance": tx.balance,
            })

        timeline_times_json = json.dumps(timeline_times, ensure_ascii=False)
        timeline_inflows_json = json.dumps(timeline_inflows, ensure_ascii=False)
        timeline_outflows_json = json.dumps(timeline_outflows, ensure_ascii=False)
        timeline_balances_json = json.dumps(timeline_balances, ensure_ascii=False)
        timeline_cum_in_json = json.dumps(timeline_cum_in, ensure_ascii=False)
        timeline_cum_out_json = json.dumps(timeline_cum_out, ensure_ascii=False)

        # Build Force-directed Network Graph
        graph_nodes = [{"id": target_name, "name": target_name, "symbolSize": 50, "category": 0}]
        graph_links = []
        for l in links:
            is_in = (l["target"] == target_name)
            other = l["source"] if is_in else l["target"]
            graph_nodes.append({
                "id": other,
                "name": other,
                "symbolSize": max(20, min(45, int(l["value"] / 10000))),
                "category": 1 if is_in else 2,
            })
            graph_links.append({
                "source": l["source"],
                "target": l["target"],
                "value": l["value"],
            })

        # Remove duplicate graph nodes by id
        unique_graph_nodes = []
        seen_ids = set()
        for gn in graph_nodes:
            if gn["id"] not in seen_ids:
                seen_ids.add(gn["id"])
                unique_graph_nodes.append(gn)

        # ----------------------------------------------------
        # Extended Analytics Data (Section 12 Upgrade Plan)
        # ----------------------------------------------------
        # 1. Top Inflows (up to 20)
        top_inflows_20 = [
            {
                "time": t.timestamp.strftime("%H:%M:%S"),
                "party": t.counterparty_name or "ผู้โอนเข้า",
                "channel": f"{t.counterparty_bank or 'N/A'} {t.counterparty_account or ''}".strip(),
                "detail": t.description or "-",
                "amount": t.amount,
            }
            for t in sorted(inflows, key=lambda x: x.amount, reverse=True)[:20]
        ]

        # 2. Top Outflows (up to 20)
        top_outflows_20 = [
            {
                "time": t.timestamp.strftime("%H:%M:%S"),
                "party": t.counterparty_name or "ผู้รับโอน",
                "channel": f"{t.counterparty_bank or 'N/A'} {t.counterparty_account or ''}".strip(),
                "detail": t.description or "-",
                "amount": t.amount,
            }
            for t in sorted(outflows, key=lambda x: x.amount, reverse=True)[:20]
        ]

        # 3. Frequency Ranking (up to 20)
        freq_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "volume": 0.0, "name": "", "bank": ""})
        for t in outflows:
            k = f"{t.counterparty_bank or ''} {t.counterparty_account or ''}".strip() or "N/A"
            freq_map[k]["count"] += 1
            freq_map[k]["volume"] += t.amount
            freq_map[k]["name"] = t.counterparty_name or "ไม่ระบุชื่อ"
            freq_map[k]["bank"] = t.counterparty_bank or "N/A"

        top_freq_20 = [
            {
                "time": f"{v['count']} ครั้ง",
                "party": v["name"],
                "channel": f"{v['bank']} {k}",
                "detail": f"โอนซ้ำ {v['count']} ธุรกรรม (กระจายยอด)",
                "amount": v["volume"],
            }
            for k, v in sorted(freq_map.items(), key=lambda x: x[1]["count"], reverse=True)[:20]
        ]

        # 4. Velocity Latency Ranking (Fastest transit time after nearest inflow - Linear O(N) scan)
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        velocity_list = []
        latest_in = None
        for t in sorted_txs:
            if t.is_reversal:
                continue
            if t.activity == ActivityType.INFLOW:
                latest_in = t
            elif t.activity == ActivityType.OUTFLOW and latest_in is not None:
                diff_sec = (t.timestamp - latest_in.timestamp).total_seconds()
                if diff_sec >= 0:
                    mins = diff_sec / 60.0
                    ts = t.timestamp
                    velocity_list.append({
                        "time": f"{ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}",
                        "party": t.counterparty_name or "ผู้รับโอน",
                        "channel": f"{t.counterparty_bank or 'N/A'} {t.counterparty_account or ''}".strip(),
                        "detail": f"เงินแช่ {mins:.1f} นาที ({diff_sec:.0f} วินาที)",
                        "amount": t.amount,
                        "latency_sec": diff_sec,
                    })
        top_velocity_20 = sorted(velocity_list, key=lambda x: x["latency_sec"])[:20]

        # 5. Channel & Off-ramp Split
        channels_vol = {"ATM Cash-out / ถอนเงินสด": 0.0, "Crypto Off-ramp / สินทรัพย์ดิจิทัล": 0.0, "Bank Transfer / โอนธนาคาร": 0.0}
        for t in outflows:
            txt = f"{t.description} {t.counterparty_name} {t.counterparty_bank}".lower()
            if any(w in txt for w in ["atm", "cardless", "ถอน", "กดเงิน"]):
                channels_vol["ATM Cash-out / ถอนเงินสด"] += t.amount
            elif any(w in txt for w in ["crypto", "usdt", "bitkub", "binance", "p2p", "satang"]):
                channels_vol["Crypto Off-ramp / สินทรัพย์ดิจิทัล"] += t.amount
            else:
                channels_vol["Bank Transfer / โอนธนาคาร"] += t.amount

        channels_donut = [{"name": k, "value": round(v, 2)} for k, v in channels_vol.items() if v > 0]
        if not channels_donut:
            channels_donut = [{"name": "Bank Transfer / โอนธนาคาร", "value": round(sum(t.amount for t in outflows), 2)}]

        # 6. Hourly 24-Hour Activity
        hourly_hours = [f"{h:02d}:00" for h in range(24)]
        hourly_vols = [0.0] * 24
        hourly_cnts = [0] * 24
        for t in transactions:
            h = t.timestamp.hour
            hourly_vols[h] += t.amount
            hourly_cnts[h] += 1

        # 7. Aggregated Inflows by Counterparty
        inflow_counterparties: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(
            lambda: {"bank": "", "acct": "", "name": "", "total_amount": 0.0, "tx_count": 0, "first_seen": None, "last_seen": None, "channels": set()}
        )
        for t in inflows:
            b = t.counterparty_bank or "N/A"
            a = t.counterparty_account or "N/A"
            n = t.counterparty_name or "ไม่ระบุชื่อ"
            key = (b, a, n)
            entry = inflow_counterparties[key]
            entry["bank"] = b
            entry["acct"] = a
            entry["name"] = n
            entry["total_amount"] += t.amount
            entry["tx_count"] += 1
            if entry["first_seen"] is None or t.timestamp < entry["first_seen"]:
                entry["first_seen"] = t.timestamp
            if entry["last_seen"] is None or t.timestamp > entry["last_seen"]:
                entry["last_seen"] = t.timestamp
            if t.channel:
                entry["channels"].add(t.channel)

        sorted_inflows = sorted(inflow_counterparties.values(), key=lambda x: x["total_amount"], reverse=True)

        # 8. Aggregated Outflows by Counterparty
        outflow_counterparties: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(
            lambda: {"bank": "", "acct": "", "name": "", "total_amount": 0.0, "tx_count": 0, "first_seen": None, "last_seen": None, "channels": set(), "action": "", "badge": ""}
        )
        for t in outflows:
            b = t.counterparty_bank or "N/A"
            a = t.counterparty_account or "N/A"
            n = t.counterparty_name or "ไม่ระบุชื่อ"
            key = (b, a, n)
            entry = outflow_counterparties[key]
            entry["bank"] = b
            entry["acct"] = a
            entry["name"] = n
            entry["total_amount"] += t.amount
            entry["tx_count"] += 1
            if entry["first_seen"] is None or t.timestamp < entry["first_seen"]:
                entry["first_seen"] = t.timestamp
            if entry["last_seen"] is None or t.timestamp > entry["last_seen"]:
                entry["last_seen"] = t.timestamp
            if t.channel:
                entry["channels"].add(t.channel)

        sorted_outflows = sorted(outflow_counterparties.values(), key=lambda x: x["total_amount"], reverse=True)

        for item in sorted_outflows:
            combined = f"{item['bank']} {item['acct']} {item['name']} {' '.join(item['channels'])}".lower()
            if any(w in combined for w in ["atm", "cardless", "ถอนสด", "กดเงิน"]):
                item["action"] = "CCTV_INSPECTION_ATM"
                item["badge"] = '<span class="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-[11px] font-semibold">📹 ภาพ CCTV ATM</span>'
            elif any(w in combined for w in ["p2p", "binance", "bitkub", "crypto", "usdt", "vasp", "satang"]):
                item["action"] = "VASP_WALLET_FREEZE"
                item["badge"] = '<span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded text-[11px] font-semibold">🔒 อายัดกระเป๋า VASP</span>'
            elif any(w in combined for w in [
                "meta ads", "facebook ads", "fb ads", "google ads", "tiktok ads", "line ads", "twitter ads",
                "kgp", "kasikorn global payment", "2c2p", "omise", "opn", "gb prime", "paysolutions",
                "ksher", "truemoney merchant", "payment gateway", "gateway", "merchant pool", "billing"
            ]):
                item["action"] = "PLATFORM_SUBPOENA_EVIDENCE"
                item["badge"] = '<span class="px-2 py-0.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 rounded text-[11px] font-semibold">📋 หมายเรียก ม.132</span>'
            else:
                item["action"] = "AOC_1441_FREEZE_URGENT"
                item["badge"] = '<span class="px-2 py-0.5 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded text-[11px] font-semibold">🚨 AOC 1441 อายัดด่วน</span>'

        # Build Inflow Table Rows HTML
        inflow_table_rows = []
        for idx, row in enumerate(sorted_inflows, 1):
            pct = (row["total_amount"] / total_in * 100.0) if total_in > 0 else 0.0
            avg_amt = row["total_amount"] / row["tx_count"] if row["tx_count"] > 0 else 0.0
            rank_badge = f'<span class="w-6 h-6 rounded-full inline-flex items-center justify-center text-xs font-bold {"bg-amber-500/20 text-amber-300 border border-amber-500/40" if idx == 1 else ("bg-slate-700 text-slate-200" if idx <= 3 else "text-slate-400")}">{idx}</span>'
            clean_name = row["name"].replace('"', '')
            clean_acct = row["acct"].replace('"', '')
            inflow_table_rows.append(f"""
            <tr class="hover:bg-slate-800/60 transition border-b border-slate-700/50 cp-inflow-row" data-bank="{row['bank']}" data-acct="{clean_acct}" data-name="{clean_name}">
                <td class="p-3 text-center">{rank_badge}</td>
                <td class="p-3">
                    <span class="px-2 py-0.5 bg-slate-900 border border-slate-700 rounded text-xs font-mono text-sky-400 font-semibold">{row['bank']}</span>
                    <span class="font-mono text-xs text-slate-200 ml-1.5">{clean_acct}</span>
                </td>
                <td class="p-3 font-semibold text-white">{clean_name}</td>
                <td class="p-3 text-center">
                    <span class="font-mono text-xs text-slate-200 font-bold">{row['tx_count']} ครั้ง</span>
                    <div class="text-[10px] text-slate-400">เฉลี่ย ฿{avg_amt:,.2f}</div>
                </td>
                <td class="p-3 text-right">
                    <div class="font-mono text-xs font-bold text-emerald-400">฿{row['total_amount']:,.2f}</div>
                    <div class="text-[10px] text-sky-400 font-semibold">{pct:.1f}% ของยอดเข้า</div>
                </td>
                <td class="p-3 text-center">
                    <button onclick='navigator.clipboard.writeText("{clean_acct}"); showToast("คัดลอกเลขบัญชี {clean_acct} แล้ว");' class="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 transition">
                        คัดลอก
                    </button>
                </td>
            </tr>
            """)
        inflow_table_rows_html = "".join(inflow_table_rows)

        # Build Outflow Table Rows HTML
        outflow_table_rows = []
        for idx, row in enumerate(sorted_outflows, 1):
            pct = (row["total_amount"] / total_out * 100.0) if total_out > 0 else 0.0
            avg_amt = row["total_amount"] / row["tx_count"] if row["tx_count"] > 0 else 0.0
            rank_badge = f'<span class="w-6 h-6 rounded-full inline-flex items-center justify-center text-xs font-bold {"bg-rose-500/20 text-rose-300 border border-rose-500/40" if idx == 1 else ("bg-slate-700 text-slate-200" if idx <= 3 else "text-slate-400")}">{idx}</span>'
            clean_name = row["name"].replace('"', '')
            clean_acct = row["acct"].replace('"', '')

            btn_action = f"""<button onclick='navigator.clipboard.writeText("{clean_acct}"); showToast("คัดลอกเลขบัญชี {clean_acct} แล้ว");' class="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 transition">คัดลอก</button>"""
            if row["action"] == "AOC_1441_FREEZE_URGENT":
                btn_action = f"""<button onclick='navigator.clipboard.writeText("ขออายัดบัญชี {row['bank']} {clean_acct} ({clean_name}) ยอดเงินรวม ฿{row['total_amount']:,.2f}"); showToast("คัดลอกข้อมูลอายัด AOC แล้ว");' class="px-2.5 py-1 bg-rose-600/80 hover:bg-rose-500 rounded text-xs text-white font-semibold transition">Copy AOC</button>"""
            elif row["action"] == "PLATFORM_SUBPOENA_EVIDENCE":
                btn_action = f"""<button onclick='navigator.clipboard.writeText("หมายเรียก ป.วิ.อ. ม.132: {clean_name} ({row['bank']} {clean_acct}) ยอดเงินรวม ฿{row['total_amount']:,.2f}"); showToast("คัดลอกคำขอ ม.132 แล้ว");' class="px-2.5 py-1 bg-amber-600/80 hover:bg-amber-500 rounded text-xs text-white font-semibold transition">Copy ม.132</button>"""
            elif row["action"] == "CCTV_INSPECTION_ATM":
                btn_action = f"""<button onclick='navigator.clipboard.writeText("ขอภาพ CCTV ตู้ ATM {row['bank']} บัญชี {clean_acct}"); showToast("คัดลอกคำขอ CCTV แล้ว");' class="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-200 transition">Copy CCTV</button>"""
            elif row["action"] == "VASP_WALLET_FREEZE":
                btn_action = f"""<button onclick='navigator.clipboard.writeText("ขออายัดกระเป๋า VASP: {clean_name} ({clean_acct})"); showToast("คัดลอกคำขอ VASP แล้ว");' class="px-2.5 py-1 bg-purple-700/80 hover:bg-purple-600 rounded text-xs text-white transition">Copy VASP</button>"""

            outflow_table_rows.append(f"""
            <tr class="hover:bg-slate-800/60 transition border-b border-slate-700/50 cp-outflow-row" data-bank="{row['bank']}" data-acct="{clean_acct}" data-name="{clean_name}">
                <td class="p-3 text-center">{rank_badge}</td>
                <td class="p-3">
                    <span class="px-2 py-0.5 bg-slate-900 border border-slate-700 rounded text-xs font-mono text-rose-400 font-semibold">{row['bank']}</span>
                    <span class="font-mono text-xs text-slate-200 ml-1.5">{clean_acct}</span>
                </td>
                <td class="p-3 font-semibold text-white">{clean_name}</td>
                <td class="p-3 text-center">
                    <span class="font-mono text-xs text-slate-200 font-bold">{row['tx_count']} ครั้ง</span>
                    <div class="text-[10px] text-slate-400">เฉลี่ย ฿{avg_amt:,.2f}</div>
                </td>
                <td class="p-3 text-right">
                    <div class="font-mono text-xs font-bold text-rose-400">฿{row['total_amount']:,.2f}</div>
                    <div class="text-[10px] text-sky-400 font-semibold">{pct:.1f}% ของยอดออก</div>
                </td>
                <td class="p-3 text-center">
                    <div class="mb-1">{row['badge']}</div>
                    {btn_action}
                </td>
            </tr>
            """)
        outflow_table_rows_html = "".join(outflow_table_rows)

        html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Forensics Dashboard - {statement_name or report.case_id}</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Apache ECharts CDN -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        body {{ font-family: 'Sarabun', sans-serif; background-color: #0f172a; color: #f8fafc; }}
        .tab-btn.active {{ border-bottom: 3px solid #38bdf8; color: #38bdf8; font-weight: 700; }}
        .faq-pill:hover {{ transform: translateY(-1px); }}

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
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Top Navigation & Header -->
        <header class="flex flex-col md:flex-row md:items-center md:justify-between bg-slate-800 p-5 rounded-2xl shadow-xl border border-slate-700">
            <div>
                <div class="flex items-center gap-3">
                    <span class="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">
                        {report.suspicion_level}
                    </span>
                    <span class="text-xs text-slate-400 font-mono">{'STATEMENT: ' + statement_name + ' • ' if statement_name else ''}CASE: {report.case_id}</span>
                </div>
                <h1 class="text-2xl font-bold mt-1 text-white">ศูนย์บัญชาการตรวจพิสูจน์เส้นทางการเงินเชิงนิติวิทยาศาสตร์</h1>
                <p class="text-sm text-slate-400">เป้าหมาย: <span class="text-amber-300 font-semibold">{report.account_name}</span> ({report.account_no_masked}) | SHA-256: <code class="text-xs text-slate-500">{report.statement_hash_sha256[:16]}...</code></p>
            </div>
            <div class="mt-4 md:mt-0 flex gap-3">
                <button onclick="window.print()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition">พิมพ์รายงาน</button>
                <a href="court_dossier.md" target="_blank" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm font-semibold transition">เปิดสำนวนคดี</a>
            </div>
        </header>

        <!-- KPI Cards Row -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">คะแนนความน่าสงสัยรวม</div>
                <div class="text-3xl font-bold mt-2 text-rose-400">{report.overall_suspicion_score}<span class="text-lg text-slate-500">/100</span></div>
                <div class="text-xs text-rose-300 mt-1">ความเสี่ยงสูงมาก (Mule Pattern)</div>
            </div>
            <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">อัตราการกวาดเงินออก (Drain Rate)</div>
                <div class="text-3xl font-bold mt-2 text-amber-400">{drain_rate:.2f}%</div>
                <div class="text-xs text-slate-400 mt-1">คงเหลือติดบัญชีเพียง ฿{total_in - (total_out + total_fee):,.2f}</div>
            </div>
            <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">ยอดเงินเข้าทั้งหมด (Inflow)</div>
                <div class="text-3xl font-bold mt-2 text-emerald-400">฿{total_in:,.2f}</div>
                <div class="text-xs text-slate-400 mt-1">{len(inflows)} ธุรกรรม</div>
            </div>
            <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">ยอดระบายออกสุทธิ (Outflow)</div>
                <div class="text-3xl font-bold mt-2 text-sky-400">฿{total_out:,.2f}</div>
                <div class="text-xs text-slate-400 mt-1">{len(outflows)} ธุรกรรม + ค่าธรรมเนียม ฿{total_fee:,.2f}</div>
            </div>
        </div>

        <!-- Section 12 Upgrade: FAQ Quick-Filter Toolbar (7 Core Judicial Questions) -->
        <div class="bg-slate-850 p-4 rounded-xl border border-slate-700/80 bg-slate-800/80 shadow-md">
            <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <span>⚡</span> ทางลัดตอบคำถามยอดฮิตของพนักงานสอบสวนและศาล (7 Judicial FAQ Quick-Filters)
                </span>
                <span class="text-[11px] text-slate-400">คลิกเพื่อสลับไปยังพยานหลักฐานเชิงประจักษ์ทันที</span>
            </div>
            <div class="flex flex-wrap gap-2 text-xs">
                <button onclick="handleFaq(1)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-sky-950 border border-slate-700 hover:border-sky-500 rounded-lg text-slate-300 transition">
                    💸 FAQ 1: เงินไหลไปหาใครบ้าง?
                </button>
                <button onclick="handleFaq(2)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-rose-950 border border-slate-700 hover:border-rose-500 rounded-lg text-slate-300 transition">
                    🚨 FAQ 2: บัญชีม้าแน่นอนไหม?
                </button>
                <button onclick="handleFaq(3)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-amber-950 border border-slate-700 hover:border-amber-500 rounded-lg text-slate-300 transition">
                    🔒 FAQ 3: ควรอายัดบัญชีไหนก่อน?
                </button>
                <button onclick="handleFaq(4)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-emerald-950 border border-slate-700 hover:border-emerald-500 rounded-lg text-slate-300 transition">
                    ⏱️ FAQ 4: เริ่มก่อเหตุเมื่อไหร่?
                </button>
                <button onclick="handleFaq(5)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-purple-950 border border-slate-700 hover:border-purple-500 rounded-lg text-slate-300 transition">
                    🏧 FAQ 5: เงินสด/คริปโตเท่าไหร่?
                </button>
                <button onclick="handleFaq(6)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-cyan-950 border border-slate-700 hover:border-cyan-500 rounded-lg text-slate-300 transition">
                    🤖 FAQ 6: ใช้บอทโอนเงินหรือไม่?
                </button>
                <button onclick="handleFaq(7)" class="faq-pill px-3 py-1.5 bg-slate-900/80 hover:bg-indigo-950 border border-slate-700 hover:border-indigo-500 rounded-lg text-slate-300 transition">
                    🕸️ FAQ 7: ขบวนการเดียวกันไหม?
                </button>
            </div>
        </div>

        <!-- Tab Controls -->
        <div class="flex border-b border-slate-700 space-x-6 text-sm">
            <button onclick="switchTab('tab-sankey')" id="btn-tab-sankey" class="tab-btn active pb-3 text-slate-300">
                1. ผังการกระจายเงิน (Sankey Flow)
            </button>
            <button onclick="switchTab('tab-network')" id="btn-tab-network" class="tab-btn pb-3 text-slate-300">
                2. กราฟโครงข่ายเชื่อมโยง (Network Topology)
            </button>
            <button onclick="switchTab('tab-timeline')" id="btn-tab-timeline" class="tab-btn pb-3 text-slate-300">
                3. เส้นเวลาและความเร็ว (Timeline & Velocity)
            </button>
            <button onclick="switchTab('tab-table')" id="btn-tab-table" class="tab-btn pb-3 text-slate-300">
                4. จัดอันดับยอดรวมบัญชี โอนเข้า-ออก (Counterparty Ranking)
            </button>
            <button onclick="switchTab('tab-analytics')" id="btn-tab-analytics" class="tab-btn pb-3 text-slate-300 font-semibold text-sky-400">
                5. สถิติเชิงลึก (Forensic Data Analytics)
            </button>
        </div>

        <!-- Tab 1: Sankey Flow -->
        <div id="tab-sankey" class="tab-content bg-slate-800 p-6 rounded-2xl border border-slate-700 flex flex-col">
            <div class="flex items-center justify-between mb-4">
                <div>
                    <h2 class="text-lg font-bold text-white">ผังแสดงการไหลเวียนของเงินจากเหยื่อผ่านบัญชีม้าสู่ปลายทาง (Sankey Flow Diagram)</h2>
                    <p class="text-xs text-slate-400">แสดงเส้นทางตั้งแต่ผู้เสียหาย/แหล่งเงินเข้า เข้าสู่บัญชีเป้าหมาย และการกระจายตัวไปยังบัญชีแถวที่ 2</p>
                </div>
                <button onclick="toggleCardFullscreen('tab-sankey', 'sankeyChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                    <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                </button>
            </div>
            <div id="chart-sankey" class="chart-container" style="width: 100%; height: 500px;"></div>
        </div>

        <!-- Tab 2: Network Topology -->
        <div id="tab-network" class="tab-content hidden bg-slate-800 p-6 rounded-2xl border border-slate-700 flex flex-col">
            <div class="flex items-center justify-between mb-4">
                <div>
                    <h2 class="text-lg font-bold text-white">โครงข่ายความสัมพันธ์หลายมิติ (Multi-Hop Force-Directed Graph)</h2>
                    <p class="text-xs text-slate-400">สามารถคลิกลากจุดเพื่อตรวจสอบศูนย์กลางการรับเงินและการกระจายเงิน</p>
                </div>
                <button onclick="toggleCardFullscreen('tab-network', 'networkChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                    <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                </button>
            </div>
            <div id="chart-network" class="chart-container" style="width: 100%; height: 500px;"></div>
        </div>

        <!-- Tab 3: Timeline & Velocity (2 Stacked Cards) -->
        <div id="tab-timeline" class="tab-content hidden space-y-6">
            <!-- Card 1: Batch Velocity -->
            <div id="card-timeline-velocity" class="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white mb-1">การกระจายตัวตามช่วงเวลาและจังหวะการโอนเงิน (Temporal Velocity Analysis)</h2>
                        <p class="text-xs text-slate-400">เปรียบเทียบขนาดรายการเงินเข้า (Inflow) และเงินออก (Outflow) ในแต่ละช่วงเวลา เพื่อตรวจจับพฤติกรรมการซอยยอด (Structuring)</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-sky-500/20 text-sky-300 border border-sky-500/30 rounded-full text-xs font-semibold">
                            เข้า: ฿{sum(t.amount for t in transactions if t.activity == ActivityType.INFLOW):,.2f}
                        </span>
                        <span class="px-3 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full text-xs font-semibold">
                            ออก: ฿{sum(t.amount for t in transactions if t.activity in (ActivityType.OUTFLOW, ActivityType.FEE)):,.2f}
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline-velocity', 'timelineChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>
                <div id="chart-timeline" class="chart-container" style="width: 100%; height: 450px;"></div>
            </div>

            <!-- Card 2: Cumulative Flow & Running Balance -->
            <div id="card-timeline-cumulative" class="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex flex-col">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white mb-1">ยอดเงินสะสมและยอดเงินคงเหลือในบัญชีตามเวลา (Cumulative Cashflow & Balance Trajectory)</h2>
                        <p class="text-xs text-slate-400">วิเคราะห์เส้นทางยอดเงินเข้าสะสมเทียบกับยอดเงินออกสะสม และทิศทางยอดคงเหลือ (Running Balance) ตลอดช่วงเวลาของบัญชี</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold">
                            ยอดคงเหลือล่าสุด: ฿{transactions[-1].balance if transactions else 0:,.2f}
                        </span>
                        <button onclick="toggleCardFullscreen('card-timeline-cumulative', 'timelineCumChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>
                <div id="chart-timeline-cumulative" class="chart-container" style="width: 100%; height: 450px;"></div>
            </div>
        </div>

        <!-- Tab 4: Aggregated Counterparty Ranking -->
        <div id="tab-table" class="tab-content hidden space-y-6">
            <!-- Header bar with search and presentation mode -->
            <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-md">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xl">🏆</span>
                            <h2 class="text-lg font-bold text-white">ตารางจัดอันดับยอดรวมบัญชีคู่กรณี (Aggregated Counterparty Ledger)</h2>
                        </div>
                        <p class="text-xs text-slate-400 mt-1">สรุปรวมยอดเงิน ความถี่ และจำแนกประเภทบัญชีคู่กรณี แยกฝั่งเงินเข้า (Inflow) และเงินออก (Outflow) สำหรับการสืบสวนและอายัด</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="relative">
                            <input type="text" id="cpSearch" oninput="filterCounterparties()" placeholder="ค้นหา ธนาคาร, เลขบัญชี, ชื่อ..." class="w-64 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition">
                            <span class="absolute right-2.5 top-1.5 text-slate-500 text-xs">🔍</span>
                        </div>
                        <button onclick="toggleCardFullscreen('tab-table', null)" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                </div>

                <!-- Summary Cards Row -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-700/60">
                    <div class="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-3.5 flex items-center justify-between">
                        <div>
                            <div class="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">🟢 แหล่งที่มาเงินเข้า (Inflow Originators)</div>
                            <div class="text-lg font-bold text-white font-mono mt-0.5">{len(sorted_inflows):,} <span class="text-xs font-normal text-slate-400">บัญชีคู่กรณี</span></div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-slate-400">ยอดเงินรวม</div>
                            <div class="text-base font-bold text-emerald-400 font-mono">฿{total_in:,.2f}</div>
                        </div>
                    </div>
                    <div class="bg-rose-950/20 border border-rose-500/30 rounded-xl p-3.5 flex items-center justify-between">
                        <div>
                            <div class="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">🔴 ปลายทางเงินออก (Outflow Beneficiaries)</div>
                            <div class="text-lg font-bold text-white font-mono mt-0.5">{len(sorted_outflows):,} <span class="text-xs font-normal text-slate-400">บัญชีคู่กรณี</span></div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-slate-400">ยอดเงินรวม</div>
                            <div class="text-base font-bold text-rose-400 font-mono">฿{total_out:,.2f}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Two Comparison Tables Side-by-Side (or stacked on smaller screens) -->
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <!-- Inflow Table Card -->
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700 shadow-md flex flex-col">
                    <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-700">
                        <div class="flex items-center gap-2">
                            <span class="w-3 h-3 rounded-full bg-emerald-400"></span>
                            <h3 class="text-sm font-bold text-white">อันดับบัญชีเงินเข้าสูงสุด (Top Inflow Sources)</h3>
                        </div>
                        <span class="text-xs text-slate-400 font-mono" id="inflowCountLabel">{len(sorted_inflows)} บัญชี</span>
                    </div>
                    <div class="overflow-x-auto overflow-y-auto max-h-[600px] border border-slate-700/60 rounded-xl">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead class="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-700 shadow-sm z-10">
                                <tr>
                                    <th class="p-2.5 text-center w-12">#</th>
                                    <th class="p-2.5">ธนาคาร / เลขบัญชี</th>
                                    <th class="p-2.5">ชื่อบัญชี</th>
                                    <th class="p-2.5 text-center">ความถี่</th>
                                    <th class="p-2.5 text-right">ยอดรวม (บาท)</th>
                                    <th class="p-2.5 text-center w-20">คัดลอก</th>
                                </tr>
                            </thead>
                            <tbody id="inflowTableBody" class="divide-y divide-slate-700/40">
                                {inflow_table_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Outflow Table Card -->
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700 shadow-md flex flex-col">
                    <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-700">
                        <div class="flex items-center gap-2">
                            <span class="w-3 h-3 rounded-full bg-rose-400"></span>
                            <h3 class="text-sm font-bold text-white">อันดับบัญชีเงินออกสูงสุด (Top Outflow Destinations)</h3>
                        </div>
                        <span class="text-xs text-slate-400 font-mono" id="outflowCountLabel">{len(sorted_outflows)} บัญชี</span>
                    </div>
                    <div class="overflow-x-auto overflow-y-auto max-h-[600px] border border-slate-700/60 rounded-xl">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead class="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-700 shadow-sm z-10">
                                <tr>
                                    <th class="p-2.5 text-center w-12">#</th>
                                    <th class="p-2.5">ธนาคาร / เลขบัญชี</th>
                                    <th class="p-2.5">ชื่อบัญชี</th>
                                    <th class="p-2.5 text-center">ความถี่</th>
                                    <th class="p-2.5 text-right">ยอดรวม (บาท)</th>
                                    <th class="p-2.5 text-center w-28">มาตรการสืบสวน</th>
                                </tr>
                            </thead>
                            <tbody id="outflowTableBody" class="divide-y divide-slate-700/40">
                                {outflow_table_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 5: Extended Forensic Data Analytics (Section 12 Implementation) -->
        <div id="tab-analytics" class="tab-content hidden space-y-6">
            <!-- Row 1: Interactive Multi-Stat Leaderboard -->
            <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-md">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">ตารางจัดอันดับตัวชี้วัดสำคัญ (Multi-Dimensional Leaderboards)</h2>
                        <p class="text-xs text-slate-400">เลือกมิติข้อมูลเพื่อวิเคราะห์พฤติกรรมและกำหนดเป้าหมายการสืบสวน</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <select id="leaderboard-metric" onchange="renderLeaderboard()" class="bg-slate-900 border border-slate-700 text-sky-400 text-xs font-semibold rounded-lg px-3 py-2 outline-none">
                            <option value="outflow">🔴 ยอดเงินโอนออกสูงสุด (Top Outflows)</option>
                            <option value="inflow">🟢 ยอดเงินโอนเข้าสูงสุด (Top Inflows)</option>
                            <option value="frequency">🔁 อันดับโอนซ้ำบ่อยที่สุด (Top Frequency)</option>
                            <option value="velocity">⚡ อันดับเงินผ่านเร็วที่สุด (Top Velocity Latency)</option>
                        </select>
                        <select id="leaderboard-limit" onchange="renderLeaderboard()" class="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-3 py-2 outline-none">
                            <option value="10">แสดง 10 อันดับแรก</option>
                            <option value="20">แสดง 20 อันดับแรก</option>
                        </select>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-slate-900/60 text-slate-400 border-b border-slate-700">
                                <th class="p-3 w-16">อันดับ</th>
                                <th class="p-3 w-28" id="th-col-time">เวลา / จำนวน</th>
                                <th class="p-3" id="th-col-party">ชื่อบุคคล / คู่ค้า</th>
                                <th class="p-3">ธนาคาร / บัญชี / ช่องทาง</th>
                                <th class="p-3">รายละเอียด / พฤติการณ์</th>
                                <th class="p-3 text-right" id="th-col-amount">ยอดเงิน (บาท)</th>
                            </tr>
                        </thead>
                        <tbody id="leaderboard-tbody" class="divide-y divide-slate-700/50 font-mono">
                            <!-- Populated dynamically via JS -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Row 2: Off-ramp Channels & 24-Hour Nocturnal Heatmap -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Channel & Cash-out Split -->
                <div id="card-analytics-channels" class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-md flex flex-col">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-3">
                            <h3 class="text-base font-bold text-white">สัดส่วนช่องทางการผันเงินออก (Off-ramp Channel Split)</h3>
                            <span class="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">ถอนเงินสด / คริปโต</span>
                        </div>
                        <button onclick="toggleCardFullscreen('card-analytics-channels', 'channelChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                    <p class="text-xs text-slate-400 mb-4">เปรียบเทียบการถอนเงินสดตู้ ATM (Cardless ATM), สินทรัพย์ดิจิทัล (Crypto OTC/P2P) และการโอนธนาคาร</p>
                    <div id="chart-channels" class="chart-container" style="width: 100%; height: 320px;"></div>
                </div>

                <!-- 24-Hour Activity Heatmap -->
                <div id="card-analytics-hourly" class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-md flex flex-col">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-3">
                            <h3 class="text-base font-bold text-white">ความหนาแน่นธุรกรรมรอบ 24 ชั่วโมง (24-Hour Activity Profile)</h3>
                            <span class="text-xs text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">ยามวิกาล 01:00-06:00</span>
                        </div>
                        <button onclick="toggleCardFullscreen('card-analytics-hourly', 'hourlyChart')" class="fullscreen-btn px-2.5 py-1.5 bg-slate-900/90 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:border-sky-500 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm shrink-0" title="ขยายเต็มจอสำหรับนำเสนอ">
                            <span class="fs-icon">⛶</span> <span class="fs-text">ขยายเต็มจอ</span>
                        </button>
                    </div>
                    <p class="text-xs text-slate-400 mb-4">ตรวจหาความผิดปกติของเวลาการโอนยามวิกาล ซึ่งขัดกับวิถีชีวิตผู้ประกอบการหรือคนทั่วไป</p>
                    <div id="chart-hourly" class="chart-container" style="width: 100%; height: 320px;"></div>
                </div>
            </div>
        </div>

        <!-- Toast Notification -->
        <div id="toast" class="fixed bottom-6 right-6 bg-slate-900/95 border border-sky-500/50 text-sky-200 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none z-50 flex items-center gap-2">
            <span>📋</span>
            <span id="toastMsg">คัดลอกข้อมูลแล้ว</span>
        </div>

        <!-- Footer -->
        <footer class="text-center text-xs text-slate-500 py-4">
            ระบบสถาปัตยกรรมวิเคราะห์เส้นทางการเงินเชิงนิติวิทยาศาสตร์ (FinForensic Enterprise v2.1.0) | รองรับ ป.วิ.อาญา ม.226
        </footer>
    </div>

    <!-- Scripts -->
    <script>
        const sankeyNodes = {json.dumps(sankey_nodes, ensure_ascii=False)};
        const sankeyLinks = {json.dumps(links, ensure_ascii=False)};
        const graphNodes = {json.dumps(unique_graph_nodes, ensure_ascii=False)};
        const graphLinks = {json.dumps(graph_links, ensure_ascii=False)};
        const timelineData = {json.dumps(timeline_data, ensure_ascii=False)};

        // Section 12 Extended Analytics Data
        const analyticsData = {{
            top_inflows: {json.dumps(top_inflows_20, ensure_ascii=False)},
            top_outflows: {json.dumps(top_outflows_20, ensure_ascii=False)},
            top_freq: {json.dumps(top_freq_20, ensure_ascii=False)},
            top_velocity: {json.dumps(top_velocity_20, ensure_ascii=False)},
            channels: {json.dumps(channels_donut, ensure_ascii=False)},
            hourly_hours: {json.dumps(hourly_hours)},
            hourly_vols: {json.dumps(hourly_vols)},
            hourly_cnts: {json.dumps(hourly_cnts)}
        }};

        let sankeyChart, networkChart, timelineChart, timelineCumChart, channelChart, hourlyChart;

        function initSankey() {{
            sankeyChart = echarts.init(document.getElementById('chart-sankey')); window.sankeyChart = sankeyChart;
            sankeyChart.setOption({{
                tooltip: {{ trigger: 'item', triggerOn: 'mousemove' }},
                series: [{{
                    type: 'sankey',
                    data: sankeyNodes,
                    links: sankeyLinks,
                    emphasis: {{ focus: 'adjacency' }},
                    lineStyle: {{ color: 'gradient', curveness: 0.5 }},
                    label: {{ color: '#f8fafc', fontSize: 11 }}
                }}]
            }});
        }}

        function initNetwork() {{
            networkChart = echarts.init(document.getElementById('chart-network')); window.networkChart = networkChart;
            networkChart.setOption({{
                tooltip: {{}},
                series: [{{
                    type: 'graph',
                    layout: 'force',
                    data: graphNodes,
                    links: graphLinks,
                    roam: true,
                    label: {{ show: true, position: 'right', color: '#cbd5e1', fontSize: 10 }},
                    force: {{ repulsion: 400, edgeLength: [80, 150] }},
                    lineStyle: {{ color: '#94a3b8', width: 2, curveness: 0.1 }}
                }}]
            }});
        }}

        function initTimeline() {{
            timelineChart = echarts.init(document.getElementById('chart-timeline')); window.timelineChart = timelineChart;
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
                    data: ['เงินเข้า (Inflow)', 'เงินออก / โอนระบาย (Outflow)'],
                    textStyle: {{ color: '#cbd5e1' }},
                    top: '1%'
                }},
                grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {timeline_times_json},
                    axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                    axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                }},
                yAxis: {{
                    type: 'value',
                    name: 'ยอดเงินธุรกรรม (฿)',
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
                        name: 'เงินเข้า (Inflow)',
                        type: 'bar',
                        data: {timeline_inflows_json},
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#38bdf8' }},
                                {{ offset: 1, color: '#0284c7' }}
                            ]),
                            borderRadius: [4, 4, 0, 0]
                        }}
                    }},
                    {{
                        name: 'เงินออก / โอนระบาย (Outflow)',
                        type: 'bar',
                        data: {timeline_outflows_json},
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

            const cumEl = document.getElementById('chart-timeline-cumulative');
            if (cumEl) {{
                timelineCumChart = echarts.init(cumEl); window.timelineCumChart = timelineCumChart;
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
                            let netGap = Math.max(0, inVal - outVal);
                            title += '<div class="border-t border-slate-700 pt-1 mt-1 flex items-center justify-between gap-4 text-amber-400">' +
                                     '<span>🟡 ส่วนต่างสะสม (Inflow - Outflow):</span>' +
                                     '<b class="font-mono">฿' + netGap.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + '</b></div>';
                            return title;
                        }}
                    }},
                    legend: {{
                        data: ['ยอดเงินเข้าสะสม (Cumulative Inflow)', 'ยอดเงินออกสะสม (Cumulative Outflow)', 'ยอดคงเหลือในบัญชี (Running Balance)'],
                        textStyle: {{ color: '#cbd5e1' }},
                        top: '1%'
                    }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', top: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'category',
                        data: {timeline_times_json},
                        axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                        axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
                    }},
                    yAxis: [
                        {{
                            type: 'value',
                            name: 'ยอดสะสม (฿)',
                            nameTextStyle: {{ color: '#94a3b8' }},
                            axisLine: {{ lineStyle: {{ color: '#475569' }} }},
                            splitLine: {{ lineStyle: {{ color: '#1e293b' }} }},
                            axisLabel: {{
                                color: '#94a3b8',
                                formatter: function(val) {{ return '฿' + (val / 1000) + 'k'; }}
                            }}
                        }},
                        {{
                            type: 'value',
                            name: 'ยอดคงเหลือ (฿)',
                            nameTextStyle: {{ color: '#34d399' }},
                            axisLine: {{ lineStyle: {{ color: '#34d399' }} }},
                            splitLine: {{ show: false }},
                            axisLabel: {{
                                color: '#34d399',
                                formatter: function(val) {{ return '฿' + (val / 1000) + 'k'; }}
                            }}
                        }}
                    ],
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
                            data: {timeline_cum_in_json},
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
                            data: {timeline_cum_out_json},
                            lineStyle: {{ width: 3, color: '#f43f5e' }},
                            itemStyle: {{ color: '#f43f5e' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(244, 63, 94, 0.22)' }},
                                    {{ offset: 1, color: 'rgba(244, 63, 94, 0.01)' }}
                                ])
                            }}
                        }},
                        {{
                            name: 'ยอดคงเหลือในบัญชี (Running Balance)',
                            type: 'line',
                            yAxisIndex: 1,
                            smooth: true,
                            showSymbol: false,
                            data: {timeline_balances_json},
                            lineStyle: {{ width: 2, color: '#34d399', type: 'dashed' }},
                            itemStyle: {{ color: '#34d399' }}
                        }}
                    ]
                }});
            }}
        }}

        function initAnalyticsCharts() {{
            if (!channelChart) {{
                channelChart = echarts.init(document.getElementById('chart-channels')); window.channelChart = channelChart;
                channelChart.setOption({{
                    tooltip: {{ trigger: 'item', formatter: '{{b}}: ฿{{c}} ({{d}}%)' }},
                    legend: {{ bottom: 0, textStyle: {{ color: '#cbd5e1', fontSize: 11 }} }},
                    series: [{{
                        type: 'pie',
                        radius: ['45%', '70%'],
                        avoidLabelOverlap: false,
                        itemStyle: {{ borderRadius: 8, borderColor: '#1e293b', borderWidth: 2 }},
                        label: {{ show: false }},
                        data: analyticsData.channels,
                        color: ['#f43f5e', '#a855f7', '#38bdf8', '#34d399']
                    }}]
                }});
            }}

            if (!hourlyChart) {{
                hourlyChart = echarts.init(document.getElementById('chart-hourly')); window.hourlyChart = hourlyChart;
                // Nocturnal hours 01:00 to 06:00 highlighted in amber/rose
                const barColors = analyticsData.hourly_hours.map((_, idx) => (idx >= 1 && idx <= 6) ? '#f43f5e' : '#38bdf8');
                hourlyChart.setOption({{
                    tooltip: {{ trigger: 'axis', formatter: function(p) {{
                        const idx = p[0].dataIndex;
                        const vol = analyticsData.hourly_vols[idx].toLocaleString('en-US', {{ minimumFractionDigits: 2 }});
                        const cnt = analyticsData.hourly_cnts[idx];
                        const note = (idx >= 1 && idx <= 6) ? '<br/><span style="color:#f43f5e;font-weight:bold;">⚠️ ช่วงยามวิกาล (Odd-hours)</span>' : '';
                        return 'เวลา ' + analyticsData.hourly_hours[idx] + '<br/>ยอดเงิน: ฿' + vol + '<br/>จำนวน: ' + cnt + ' รายการ' + note;
                    }} }},
                    xAxis: {{ type: 'category', data: analyticsData.hourly_hours, axisLabel: {{ color: '#94a3b8', fontSize: 10, interval: 2 }} }},
                    yAxis: {{ type: 'value', axisLabel: {{ color: '#94a3b8', fontSize: 10 }} }},
                    series: [{{
                        name: 'ยอดเงินหมุนเวียน (฿)',
                        type: 'bar',
                        data: analyticsData.hourly_vols,
                        itemStyle: {{
                            color: function(params) {{ return barColors[params.dataIndex]; }},
                            borderRadius: [4, 4, 0, 0]
                        }}
                    }}]
                }});
            }}

            channelChart.resize();
            hourlyChart.resize();
        }}

        function renderLeaderboard() {{
            const metric = document.getElementById('leaderboard-metric').value;
            const limit = parseInt(document.getElementById('leaderboard-limit').value, 10);
            const tbody = document.getElementById('leaderboard-tbody');
            tbody.innerHTML = '';

            let data = [];
            if (metric === 'outflow') data = analyticsData.top_outflows;
            else if (metric === 'inflow') data = analyticsData.top_inflows;
            else if (metric === 'frequency') data = analyticsData.top_freq;
            else if (metric === 'velocity') data = analyticsData.top_velocity;

            const sliced = data.slice(0, limit);
            if (sliced.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-slate-500">ไม่พบข้อมูลตามเงื่อนไขที่เลือก</td></tr>';
                return;
            }}

            sliced.forEach((row, i) => {{
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-700/30 transition';
                const rankColor = i === 0 ? 'text-amber-400 font-bold' : (i === 1 ? 'text-slate-300 font-bold' : (i === 2 ? 'text-amber-600 font-bold' : 'text-slate-400'));
                const amountColor = metric === 'inflow' ? 'text-emerald-400' : 'text-rose-400';
                
                tr.innerHTML = `
                    <td class="p-3 ${{rankColor}}">#${{i + 1}}</td>
                    <td class="p-3 text-slate-300 font-mono text-[11px]">${{row.time}}</td>
                    <td class="p-3 font-semibold text-white font-sans">${{row.party}}</td>
                    <td class="p-3 text-slate-400 font-sans">${{row.channel}}</td>
                    <td class="p-3 text-slate-300 font-sans">${{row.detail}}</td>
                    <td class="p-3 text-right font-bold ${{amountColor}}">฿${{row.amount.toLocaleString('en-US', {{ minimumFractionDigits: 2 }})}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            const btn = document.getElementById('btn-' + tabId);
            if (btn) btn.classList.add('active');

            if (tabId === 'tab-sankey' && sankeyChart) sankeyChart.resize();
            if (tabId === 'tab-network') {{
                if (!networkChart) initNetwork();
                networkChart.resize();
            }}
            if (tabId === 'tab-timeline') {{
                if (!timelineChart) initTimeline();
                timelineChart.resize();
                if (timelineCumChart) timelineCumChart.resize();
            }}
            if (tabId === 'tab-analytics') {{
                renderLeaderboard();
                initAnalyticsCharts();
            }}
        }}

        function handleFaq(faqNum) {{
            if (faqNum === 1) {{
                switchTab('tab-sankey');
            }} else if (faqNum === 2) {{
                switchTab('tab-sankey');
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }} else if (faqNum === 3) {{
                switchTab('tab-table');
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }} else if (faqNum === 4) {{
                switchTab('tab-timeline');
            }} else if (faqNum === 5) {{
                switchTab('tab-analytics');
                setTimeout(() => {{
                    const el = document.getElementById('chart-channels');
                    if (el) el.scrollIntoView({{ behavior: 'smooth' }});
                }}, 100);
            }} else if (faqNum === 6) {{
                switchTab('tab-analytics');
                document.getElementById('leaderboard-metric').value = 'velocity';
                renderLeaderboard();
            }} else if (faqNum === 7) {{
                switchTab('tab-network');
            }}
        }}

        function showToast(msg) {{
            const toast = document.getElementById('toast');
            const toastMsg = document.getElementById('toastMsg');
            if (!toast || !toastMsg) return;
            toastMsg.innerText = msg;
            toast.classList.remove('translate-y-20', 'opacity-0');
            toast.classList.add('translate-y-0', 'opacity-100');
            setTimeout(() => {{
                toast.classList.remove('translate-y-0', 'opacity-100');
                toast.classList.add('translate-y-20', 'opacity-0');
            }}, 2500);
        }}

        function filterCounterparties() {{
            const query = (document.getElementById('cpSearch').value || '').trim().toLowerCase();
            let inCount = 0;
            let outCount = 0;

            document.querySelectorAll('.cp-inflow-row').forEach(row => {{
                const bank = (row.getAttribute('data-bank') || '').toLowerCase();
                const acct = (row.getAttribute('data-acct') || '').toLowerCase();
                const name = (row.getAttribute('data-name') || '').toLowerCase();
                const match = bank.includes(query) || acct.includes(query) || name.includes(query);
                row.style.display = match ? '' : 'none';
                if (match) inCount++;
            }});

            document.querySelectorAll('.cp-outflow-row').forEach(row => {{
                const bank = (row.getAttribute('data-bank') || '').toLowerCase();
                const acct = (row.getAttribute('data-acct') || '').toLowerCase();
                const name = (row.getAttribute('data-name') || '').toLowerCase();
                const match = bank.includes(query) || acct.includes(query) || name.includes(query);
                row.style.display = match ? '' : 'none';
                if (match) outCount++;
            }});

            const inLabel = document.getElementById('inflowCountLabel');
            if (inLabel) inLabel.innerText = query ? (inCount + ' บัญชี (กรองแล้ว)') : ('{len(sorted_inflows)} บัญชี');
            const outLabel = document.getElementById('outflowCountLabel');
            if (outLabel) outLabel.innerText = query ? (outCount + ' บัญชี (กรองแล้ว)') : ('{len(sorted_outflows)} บัญชี');
        }}

        // Initial setup
        // Fullscreen Toggle Engine for Overview Dashboard
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
                    if (sankeyChart) sankeyChart.resize();
                    if (networkChart) networkChart.resize();
                    if (timelineChart) timelineChart.resize();
                    if (timelineCumChart) timelineCumChart.resize();
                    if (channelChart) channelChart.resize();
                    if (hourlyChart) hourlyChart.resize();
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
        }}

        document.addEventListener('fullscreenchange', () => {{
            const isFs = !!document.fullscreenElement;
            if (!isFs && currentFullscreenEl) {{
                currentFullscreenEl.classList.remove('fullscreen-active');
                updateFsButtons(false, currentFullscreenEl);
                currentFullscreenEl = null;
            }}
            resizeChart();
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape' && currentFullscreenEl) {{
                exitFullscreenMode(currentFullscreenEl);
            }}
        }});

        window.addEventListener('load', () => {{
            initSankey();
        }});

        window.addEventListener('resize', () => {{
            if (sankeyChart) sankeyChart.resize();
            if (networkChart) networkChart.resize();
            if (timelineChart) timelineChart.resize();
            if (timelineCumChart) timelineCumChart.resize();
            if (channelChart) channelChart.resize();
            if (hourlyChart) hourlyChart.resize();
        }});
    </script>
</body>
</html>
"""
        out_p.write_text(html_content, encoding="utf-8")
        try:
            return str(out_p.resolve().relative_to(Path.cwd().resolve()).as_posix())
        except ValueError:
            return str(out_p.as_posix())
