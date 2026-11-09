"""
Interactive Multi-Entity Graph & 5-Hop Money Trail Dashboard Generator.
Renders specialized multi-layer visual dashboards with Apache ECharts and Tailwind CSS,
supporting 5-Hop Sankey, Force-directed Syndicate Topology, Device Correlation, and Income Discrepancy.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Union
from src.graph.multi_entity_tracer import MultiEntityTracer


class MultiEntityDashboardGenerator:
    """
    Assembles standalone HTML interactive dashboards for multi-entity syndicate investigations.
    """

    def generate_html(
        self,
        tracer: MultiEntityTracer,
        output_file_path: Union[str, Path],
    ) -> str:
        out_p = Path(output_file_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        summary = tracer.get_summary()

        # 1. Build Sankey Data across the 5 Hops
        # To avoid circularity in Sankey, we qualify node names by their Hop / Role if needed
        nodes_dict: Dict[str, Dict[str, str]] = {}
        for eid, ent in tracer.entities.items():
            nodes_dict[eid] = {
                "name": f"{ent.entity_name} ({eid})",
                "role": ent.role,
            }

        # Aggregate flows between entities
        flow_agg: Dict[tuple, float] = {}
        for e in tracer.edges:
            src = nodes_dict.get(e.source_entity, {}).get("name", e.source_entity)
            tgt = nodes_dict.get(e.target_entity, {}).get("name", e.target_entity)
            if src != tgt:
                flow_agg[(src, tgt)] = flow_agg.get((src, tgt), 0.0) + e.amount_thb

        sankey_nodes = [{"name": n["name"]} for n in nodes_dict.values()]
        sankey_links = [
            {"source": src, "target": tgt, "value": round(amt, 2)}
            for (src, tgt), amt in flow_agg.items()
        ]

        # 2. Build Force-Directed Graph Data
        role_categories = [
            "Victim",
            "Mule Tier-1",
            "Mule Tier-2",
            "Mule Tier-3",
            "Cash Runner",
            "Crypto Broker",
            "Syndicate Treasury",
        ]
        
        def get_cat_idx(role: str) -> int:
            for idx, c in enumerate(role_categories):
                if c in role:
                    return idx
            return len(role_categories) - 1

        graph_nodes = []
        for eid, ent in tracer.entities.items():
            tot_vol = ent.actual_inflow_volume + ent.actual_outflow_volume
            sz = max(20, min(55, int(tot_vol / 2_500_000) + 20))
            graph_nodes.append({
                "id": eid,
                "name": ent.entity_name,
                "value": round(tot_vol, 2),
                "symbolSize": sz,
                "category": get_cat_idx(ent.role),
                "role": ent.role,
                "income": ent.declared_income,
            })

        graph_links = [
            {
                "source": e.source_entity,
                "target": e.target_entity,
                "value": e.amount_thb,
                "hop": e.hop_level,
            }
            for e in tracer.edges[:120]  # top visual edges
        ]

        # 3. Income Discrepancy Data (Declared Income vs Actual Flow)
        discrepancy_data = []
        for eid, ent in tracer.entities.items():
            if "Victim" not in ent.role:
                flow_m = (ent.actual_inflow_volume + ent.actual_outflow_volume) / 1_000_000.0
                income_k = ent.declared_income / 1_000.0
                discrepancy_data.append({
                    "name": ent.entity_name,
                    "role": ent.role,
                    "declared_income_k": round(income_k, 1),
                    "actual_flow_m": round(flow_m, 2),
                })

        # 4. Hop Breakdown Chart Data
        hop_names = sorted(list(summary.hop_volumes.keys()))
        hop_values = [round(summary.hop_volumes[h] / 1_000_000.0, 2) for h in hop_names]

        # 5. Device Clusters Data
        dev_list = [
            {"device": dev, "entities": ents, "count": len(ents)}
            for dev, ents in summary.device_clusters.items()
        ]

        html = f"""<!DOCTYPE html>
<html lang="th" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Entity Graph & 5-Hop Money Trail Suite - {summary.case_id}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Sarabun', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        body {{
            font-family: 'Sarabun', sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        .tab-btn.active {{ border-bottom: 3px solid #0284c7; color: #0284c7; font-weight: 700; }}
        html.dark .tab-btn.active {{ border-bottom: 3px solid #38bdf8 !important; color: #38bdf8 !important; }}

        /* Light Mode Styles (Default) */
        html:not(.dark) body, html.light body {{
            background-color: #f8fafc;
            color: #0f172a;
        }}
        html:not(.dark) header, html.light header {{
            background-color: #ffffff !important;
            border-color: #e2e8f0 !important;
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05) !important;
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
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05);
        }}
        html:not(.dark) .bg-slate-800,
        html:not(.dark) .bg-slate-800\/80,
        html.light .bg-slate-800,
        html.light .bg-slate-800\/80 {{
            background-color: #ffffff !important;
        }}
        html:not(.dark) .border-slate-800,
        html:not(.dark) .border-slate-700,
        html.light .border-slate-800,
        html.light .border-slate-700 {{
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
        html:not(.dark) .tab-btn, html.light .tab-btn {{
            color: #64748b;
        }}
        html:not(.dark) .tab-btn:hover, html.light .tab-btn:hover {{
            color: #0f172a;
        }}

        /* Dark Mode Overrides */
        html.dark body {{
            background-color: #0b1120 !important;
            color: #f8fafc !important;
        }}
        html.dark header {{
            background-color: rgba(15, 23, 42, 0.9) !important;
            border-color: #1e293b !important;
        }}
        html.dark .bg-slate-800\/80 {{
            background-color: rgba(30, 41, 59, 0.8) !important;
        }}
        html.dark .text-white {{
            color: #ffffff !important;
        }}
        .tab-btn.active {{ border-bottom: 3px solid #38bdf8; color: #38bdf8; font-weight: 700; }}
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center md:justify-between bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-2xl">
            <div>
                <div class="flex items-center gap-3">
                    <span class="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">
                        MULTI-ENTITY 5-HOP SUITE
                    </span>
                    <span class="text-xs text-slate-400 font-mono">CASE: {summary.case_id}</span>
                </div>
                <h1 class="text-2xl font-bold mt-1 text-white">ศูนย์ตรวจพิสูจน์โครงข่ายเส้นทางการเงินหลายทอด (Multi-Layered Money Trail)</h1>
                <p class="text-sm text-slate-400">แกะรอยเครือข่ายบัญชีม้า 5 ลำดับขั้น: ผู้เสียหาย &rarr; ม้ารับยอด &rarr; ม้ากระจาย &rarr; ศูนย์พักเงิน &rarr; ตู้ ATM ชายแดน & คริปโต</p>
            </div>
            <div class="mt-4 md:mt-0 flex gap-3">
                <!-- Light / Dark Theme Toggle Button -->
                <button id="themeToggleBtn" onclick="toggleTheme()" class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-semibold transition flex items-center gap-2 shadow-sm text-slate-800 dark:text-amber-300" title="สลับโหมดสว่าง / โหมดมืด">
                    <span id="themeIcon">🌙</span> <span id="themeText">โหมดมืด</span>
                </button>
                <button onclick="window.print()" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-sm transition border border-slate-300 dark:border-slate-700 shadow-sm" >พิมพ์รายงาน</button>
                <a href="multi_entity_court_dossier.pdf" target="_blank" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm font-semibold transition">ดาวน์โหลดสำนวน PDF</a>
            </div>
        </header>

        <!-- KPI Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">ยอดเงินหมุนเวียนรวมในโครงข่าย</div>
                <div class="text-3xl font-bold mt-2 text-emerald-400">฿{summary.total_flow_volume_thb/1e6:,.1f}M</div>
                <div class="text-xs text-slate-400 mt-1">{summary.total_transactions:,} ธุรกรรม (Hop 1 ถึง Hop 5)</div>
            </div>
            <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">จำนวนเอนทิตีในขบวนการ</div>
                <div class="text-3xl font-bold mt-2 text-sky-400">{summary.total_entities} บุคคล/นิติบุคคล</div>
                <div class="text-xs text-slate-400 mt-1">4 ผู้เสียหาย &bull; 6 บัญชีม้า 3 แถว &bull; 3 ปลายทาง</div>
            </div>
            <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">การกดเงินสดตู้ ATM ชายแดน (Hop 4)</div>
                <div class="text-3xl font-bold mt-2 text-rose-400">฿{summary.hop_volumes.get('Hop-4 (ATM Cash-Out)', 0)/1e6:,.2f}M</div>
                <div class="text-xs text-rose-300 mt-1">150 ครั้ง (ตู้ ATM อรัญประเทศ / แม่สอด)</div>
            </div>
            <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 shadow-md">
                <div class="text-xs text-slate-400 uppercase tracking-wide">แปลงสินทรัพย์คริปโต (Hop 5)</div>
                <div class="text-3xl font-bold mt-2 text-purple-400">฿{summary.hop_volumes.get('Hop-5 (Crypto Off-Ramp)', 0)/1e6:,.2f}M</div>
                <div class="text-xs text-slate-400 mt-1">โอนเข้ากระเป๋าต่างประเทศ (Unhosted Wallet)</div>
            </div>
        </div>

        <!-- Tab Controls -->
        <div class="flex border-b border-slate-800 space-x-6 text-sm">
            <button onclick="switchTab('tab-sankey')" id="btn-tab-sankey" class="tab-btn active pb-3 text-slate-300">
                1. ผังการไหลเวียน 5 ทอด (5-Hop Money Trail)
            </button>
            <button onclick="switchTab('tab-network')" id="btn-tab-network" class="tab-btn pb-3 text-slate-300">
                2. โครงข่ายใยแมงมุม (Syndicate Graph)
            </button>
            <button onclick="switchTab('tab-income')" id="btn-tab-income" class="tab-btn pb-3 text-slate-300">
                3. รายได้แจ้ง vs ยอดเงินผ่าน (Income Discrepancy)
            </button>
            <button onclick="switchTab('tab-devices')" id="btn-tab-devices" class="tab-btn pb-3 text-slate-300">
                4. อุปกรณ์ร่วม & IP สั่งการ (Device Fingerprint)
            </button>
            <button onclick="switchTab('tab-table')" id="btn-tab-table" class="tab-btn pb-3 text-slate-300">
                5. บัญทึกธุรกรรม 5 ลำดับขั้น (Hop Edges Table)
            </button>
        </div>

        <!-- Tab 1: 5-Hop Sankey -->
        <div id="tab-sankey" class="tab-content bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-2">ผังแสดงการส่งต่อเงินจากผู้เสียหายผ่านโครงข่าย 5 ลำดับขั้น (5-Hop End-to-End Money Trail)</h2>
            <p class="text-xs text-slate-400 mb-4">แสดงเส้นทางตั้งแต่เงินออกจากเหยื่อ (Hop 1) ผ่านบัญชีม้า 3 แถว (Hop 2, 3) สู่การกดเงินสดและการซื้อเหรียญคริปโต (Hop 4, 5)</p>
            <div id="chart-sankey" style="width: 100%; height: 550px;"></div>
        </div>

        <!-- Tab 2: Syndicate Network Topology -->
        <div id="tab-network" class="tab-content hidden bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-2">โครงข่ายความสัมพันธ์เครือข่ายขบวนการ (Syndicate Force-Directed Graph)</h2>
            <p class="text-xs text-slate-400 mb-4">ขนาดของ Node แปรผันตามปริมาณเงินหมุนเวียน (ลากโหนดเพื่อจัดผังได้อิสระ)</p>
            <div id="chart-network" style="width: 100%; height: 550px;"></div>
        </div>

        <!-- Tab 3: Income Discrepancy -->
        <div id="tab-income" class="tab-content hidden bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-2">การเปรียบเทียบรายได้ที่แจ้งเปิดบัญชี vs ยอดเงินหมุนเวียนจริง (Declared Income vs Actual Flow)</h2>
            <p class="text-xs text-slate-400 mb-4">พยานหลักฐานมัดตัวบัญชีม้าตาม พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 9 (แจ้งรายได้หลักหมื่น แต่เงินผ่านหลักสิบล้าน)</p>
            <div id="chart-income" style="width: 100%; height: 450px;"></div>
        </div>

        <!-- Tab 4: Device & IP Clusters -->
        <div id="tab-devices" class="tab-content hidden bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-4">การตรวจพบอุปกรณ์สั่งการร่วมกัน (Shared Device Fingerprint Clusters)</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {"".join([f'''
                <div class="bg-slate-800 p-4 rounded-xl border border-amber-500/30">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-mono text-amber-400 font-bold">{d['device']}</span>
                        <span class="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded">ใช้งานร่วม {d['count']} บัญชี</span>
                    </div>
                    <div class="text-xs text-slate-300 mt-2">
                        <b>บัญชีที่ควบคุมผ่านเครื่องเดียวกัน:</b> {", ".join(d['entities'])}
                    </div>
                    <p class="text-[11px] text-slate-400 mt-1">ข้อบ่งชี้: ศูนย์ปฏิบัติการแก๊งคอลเซ็นเตอร์ (Command Hub) ใช้โทรศัพท์เครื่องเดียวควบคุมบัญชีม้าหลายคน</p>
                </div>
                ''' for d in dev_list])}
            </div>
        </div>

        <!-- Tab 5: Hop Edges Table -->
        <div id="tab-table" class="tab-content hidden bg-slate-900/80 p-6 rounded-2xl border border-slate-800 overflow-x-auto">
            <h2 class="text-lg font-bold text-white mb-4">ตารางความสัมพันธ์ธุรกรรม 1,200 รายการ (Hop Transaction Edges)</h2>
            <table class="w-full text-left text-xs border-collapse">
                <thead>
                    <tr class="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <th class="p-3">รหัสเส้นเงิน</th>
                        <th class="p-3">ลำดับทอด (Hop)</th>
                        <th class="p-3">บัญชีต้นทาง (Source)</th>
                        <th class="p-3">บัญชีปลายทาง (Target)</th>
                        <th class="p-3 text-right">จำนวนเงิน (บาท)</th>
                        <th class="p-3">ช่องทาง</th>
                        <th class="p-3">พิกัด / อุปกรณ์</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
                    {"".join([f'''
                    <tr class="hover:bg-slate-800/40">
                        <td class="p-3 font-mono text-sky-400">{e.trace_id}</td>
                        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold {'bg-amber-500/20 text-amber-300' if 'Hop-1' in e.hop_level else ('bg-sky-500/20 text-sky-300' if 'Hop-2' in e.hop_level else ('bg-purple-500/20 text-purple-300' if 'Hop-3' in e.hop_level else 'bg-rose-500/20 text-rose-300'))}">{e.hop_level}</span></td>
                        <td class="p-3">{e.source_entity} ({e.source_account})</td>
                        <td class="p-3">{e.target_entity} ({e.target_account})</td>
                        <td class="p-3 text-right font-mono font-semibold text-emerald-400">฿{e.amount_thb:,.2f}</td>
                        <td class="p-3">{e.channel}</td>
                        <td class="p-3 text-slate-400">{e.geolocation or '-'}</td>
                    </tr>
                    ''' for e in tracer.edges[:150]])}
                </tbody>
            </table>
            <div class="text-center text-xs text-slate-500 py-3">แสดงตัวอย่าง 150 รายการแรกจากทั้งหมด {len(tracer.edges):,} รายการ</div>
        </div>

        <footer class="text-center text-xs text-slate-600 py-4">
            ระบบสืบสวนเครือข่ายเส้นทางการเงินหลายทอด (FinForensic Multi-Entity Suite v2.1.0) | รองรับ พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566
        </footer>
    </div>

    <script>
        const sankeyNodes = {json.dumps(sankey_nodes, ensure_ascii=False)};
        const sankeyLinks = {json.dumps(sankey_links, ensure_ascii=False)};
        const graphNodes = {json.dumps(graph_nodes, ensure_ascii=False)};
        const graphLinks = {json.dumps(graph_links, ensure_ascii=False)};
        const discrepancyData = {json.dumps(discrepancy_data, ensure_ascii=False)};

        let sankeyChart, networkChart, incomeChart;

        function initSankey() {{
            sankeyChart = echarts.init(document.getElementById('chart-sankey'));
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
            networkChart = echarts.init(document.getElementById('chart-network'));
            networkChart.setOption({{
                tooltip: {{}},
                legend: [{{ data: {json.dumps(role_categories, ensure_ascii=False)}, textStyle: {{ color: '#cbd5e1' }} }}],
                series: [{{
                    type: 'graph',
                    layout: 'force',
                    data: graphNodes,
                    links: graphLinks,
                    categories: {json.dumps([{"name": r} for r in role_categories], ensure_ascii=False)},
                    roam: true,
                    label: {{ show: true, position: 'right', color: '#cbd5e1', fontSize: 10 }},
                    force: {{ repulsion: 450, edgeLength: [100, 180] }},
                    lineStyle: {{ color: '#94a3b8', width: 2, curveness: 0.15 }}
                }}]
            }});
        }}

        function initIncome() {{
            incomeChart = echarts.init(document.getElementById('chart-income'));
            const names = discrepancyData.map(d => d.name);
            const incomes = discrepancyData.map(d => d.declared_income_k);
            const flows = discrepancyData.map(d => d.actual_flow_m);

            incomeChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: ['รายได้แจ้งเปิดบัญชี (พันบาท/เดือน)', 'ยอดเงินหมุนเวียนจริง (ล้านบาท)'], textStyle: {{ color: '#cbd5e1' }} }},
                xAxis: {{ type: 'category', data: names, axisLabel: {{ color: '#94a3b8', rotate: 20 }} }},
                yAxis: [
                    {{ type: 'value', name: 'รายได้ (พันบาท)', axisLabel: {{ color: '#94a3b8' }} }},
                    {{ type: 'value', name: 'ยอดเงินจริง (ล้านบาท)', axisLabel: {{ color: '#94a3b8' }} }}
                ],
                series: [
                    {{ name: 'รายได้แจ้งเปิดบัญชี (พันบาท/เดือน)', type: 'bar', data: incomes, itemStyle: {{ color: '#38bdf8' }} }},
                    {{ name: 'ยอดเงินหมุนเวียนจริง (ล้านบาท)', type: 'bar', yAxisIndex: 1, data: flows, itemStyle: {{ color: '#f43f5e' }} }}
                ]
            }});
        }}

        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            document.getElementById('btn-' + tabId).classList.add('active');

            if (tabId === 'tab-sankey' && sankeyChart) sankeyChart.resize();
            if (tabId === 'tab-network') {{
                if (!networkChart) initNetwork();
                networkChart.resize();
            }}
            if (tabId === 'tab-income') {{
                if (!incomeChart) initIncome();
                incomeChart.resize();
            }}
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
        }}

        function updateChartThemes(theme) {{
            const isDark = (theme === 'dark');
            const axisColor = isDark ? '#475569' : '#cbd5e1';
            const labelColor = isDark ? '#94a3b8' : '#64748b';
            const tooltipBg = isDark ? '#1e293b' : '#ffffff';
            const tooltipBorder = isDark ? '#334155' : '#cbd5e1';
            const tooltipText = isDark ? '#f8fafc' : '#0f172a';

            if (window.sankeyChart) {{
                window.sankeyChart.setOption({{
                    tooltip: {{ backgroundColor: tooltipBg, borderColor: tooltipBorder, textStyle: {{ color: tooltipText }} }},
                    series: [{{ label: {{ color: isDark ? '#e2e8f0' : '#1e293b' }} }}]
                }});
            }}
            if (window.incomeChart) {{
                window.incomeChart.setOption({{
                    legend: {{ textStyle: {{ color: labelColor }} }},
                    xAxis: {{ axisLabel: {{ color: labelColor }} }},
                    yAxis: [
                        {{ axisLabel: {{ color: labelColor }} }},
                        {{ axisLabel: {{ color: labelColor }} }}
                    ]
                }});
            }}
        }}

        // Apply theme immediately
        const initialTheme = localStorage.getItem('finforensic_theme') || 'light';
        applyTheme(initialTheme);

        window.addEventListener('DOMContentLoaded', () => {{
            initSankey();
        }});
        window.addEventListener('resize', () => {{
            if (sankeyChart) sankeyChart.resize();
            if (networkChart) networkChart.resize();
            if (incomeChart) incomeChart.resize();
        }});
    </script>
</body>
</html>"""

        out_p.write_text(html, encoding="utf-8")
        try:
            return str(out_p.resolve().relative_to(Path.cwd().resolve()).as_posix())
        except ValueError:
            return str(out_p.as_posix())
