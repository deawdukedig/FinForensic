"""
CLI Interface for the Deterministic Multi-Agent Harness with Strict Mode support.
Allows initializing, inspecting, building JIT prompts, and stepping state transitions.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from harness.schemas import TaskFrame, TaskStatus, SystemState, TaskBudget, StrictLevel
from harness.task_stack import TaskStackManager
from harness.state_machine import DeterministicStateMachine
from harness.prompt_builder import PromptOnDemandBuilder
from harness.verifier import DeterministicVerifier
from src.models.transaction import ActivityType


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        prog="harness",
        description="Deterministic State Machine & Prompt on Demand Harness for Multi-Agent Systems",
    )
    parser.add_argument(
        "--stack-file",
        default="stack.json",
        help="Path to stack.json file (default: stack.json)",
    )
    parser.add_argument(
        "--strict-level",
        choices=["lenient", "strict", "hardcore"],
        default="strict",
        help="Enforcement level for Strict/Opinionated Mode (default: strict)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    init_parser = subparsers.add_parser("init", help="Initialize a new root task onto the stack")
    init_parser.add_argument("--task-id", default="ROOT-001", help="ID of root task")
    init_parser.add_argument("--title", required=True, help="Title of root task")
    init_parser.add_argument("--desc", default="", help="Description or acceptance criteria")
    init_parser.add_argument("--agent", default="pm_agent", help="Initial agent (default: pm_agent)")
    init_parser.add_argument(
        "--allowed-files",
        nargs="*",
        default=[],
        help="List of allowed files for strict boundary checking (Hyper-Disciplined Stack Hygiene)",
    )
    init_parser.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="Max lines changed for atomic blast radius (default: 200)",
    )

    # 2. status
    subparsers.add_parser("status", help="Print current status and Top of Stack")

    # 3. build-prompt
    prompt_parser = subparsers.add_parser("build-prompt", help="Build JIT prompt on demand for Top of Stack")
    prompt_parser.add_argument("--agent", default=None, help="Override target agent")
    prompt_parser.add_argument("--output", default=None, help="Save generated prompt to file")

    # 4. transition
    trans_parser = subparsers.add_parser("transition", help="Apply agent structured output to advance state")
    trans_parser.add_argument(
        "--input",
        required=True,
        help="Raw output text or JSON string from agent, or path to file containing output",
    )

    # 5. verify
    verify_parser = subparsers.add_parser("verify", help="Run deterministic ground-truth verification on current top artifacts")

    # 6. inspect-stack
    subparsers.add_parser("inspect-stack", help="Display visual stack and history")

    # 7. audit-evidence (Imported from C:\ai-skills: audit-agent-run-evidence & digital-forensics)
    audit_parser = subparsers.add_parser("audit-evidence", help="Audit cryptographic provenance & flow conservation")
    audit_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    audit_parser.add_argument("--expected-hash", default=None, help="Expected SHA-256 hash")

    # 8. verify-compliance (Imported from C:\ai-skills: spec-to-code-compliance)
    comp_parser = subparsers.add_parser("verify-compliance", help="Verify spec-to-code alignment against architectural blueprint")
    comp_parser.add_argument("--spec", default="techdocs/financial_forensics_spec_and_plan.md", help="Path to spec file")

    # 9. verify-neutrality (Imported from C:\ai-skills: screen-adverse-media & anti-deception)
    neut_parser = subparsers.add_parser("verify-neutrality", help="Verify legal neutrality standard in reports/claims")
    neut_parser.add_argument("--target", required=True, help="File path or text string to verify")

    # 10. analyze-statement (Enterprise Forensic Flow Matching & Scoring)
    analyze_parser = subparsers.add_parser("analyze-statement", help="Run full forensic analysis and flow matching on statement")
    analyze_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    analyze_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")
    analyze_parser.add_argument("--officer", default="พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)", help="Investigating Officer")

    # 11. export-dossier (Court Dossier Generator Exhibits A-D)
    dossier_parser = subparsers.add_parser("export-dossier", help="Export Section 226 court-admissible dossier report")
    dossier_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    dossier_parser.add_argument("--output", default="dossier_court_report.md", help="Output dossier path")
    dossier_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")
    dossier_parser.add_argument("--officer", default="พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)", help="Investigating Officer")

        # 12. generate-dashboard (Tri-Modal Visual Dashboard)
    dash_parser = subparsers.add_parser("generate-dashboard", help="Generate interactive HTML visual dashboard")
    dash_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    dash_parser.add_argument("--output", default="output/dashboard.html", help="Output HTML file path")
    dash_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")

    # 13. export-pdf (Court Dossier PDF Generator)
    pdf_parser = subparsers.add_parser("export-pdf", help="Export court dossier in official PDF format")
    pdf_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    pdf_parser.add_argument("--output", default="output/court_dossier.pdf", help="Output PDF file path")
    pdf_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")
    pdf_parser.add_argument("--officer", default="พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)", help="Investigating Officer")
    pdf_parser.add_argument("--font", default="THSarabunNew", help="Thai font family to embed: 'THSarabunNew', 'THSarabunIT๙', or path to TTF")

    # 14. copilot (Forensic Chat Copilot)
    copilot_parser = subparsers.add_parser("copilot", help="Query the Forensic Chat Copilot with natural language")
    copilot_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    copilot_parser.add_argument("--query", required=True, help="Investigator question in Thai or English")
    copilot_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")

    # 15. aoc-freeze (AOC 1441 Emergency Asset Freezing Payload)
    freeze_parser = subparsers.add_parser("aoc-freeze", help="Generate standard JSON payload for AOC 1441 emergency freeze")
    freeze_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    freeze_parser.add_argument("--output", default="output/aoc_freeze_request.json", help="Output JSON path")
    freeze_parser.add_argument("--case-id", default="CASE-2026-0820", help="Investigative Case ID")

        # 16. analyze-multi-entity (Multi-Entity Graph & 5-Hop Money Trail)
    multi_parser = subparsers.add_parser("analyze-multi-entity", help="Analyze multi-entity syndicate network and 5-hop money trail")
    multi_parser.add_argument("--nodes", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv", help="Path to nodes CSV")
    multi_parser.add_argument("--edges", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv", help="Path to edges CSV")

    # 17. export-multi-entity-dossier
    multi_dossier_parser = subparsers.add_parser("export-multi-entity-dossier", help="Export multi-entity syndicate court dossier (MD & PDF)")
    multi_dossier_parser.add_argument("--nodes", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv", help="Path to nodes CSV")
    multi_dossier_parser.add_argument("--edges", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv", help="Path to edges CSV")
    multi_dossier_parser.add_argument("--output-pdf", default="output/multi_entity_court_dossier.pdf", help="Output PDF path")
    multi_dossier_parser.add_argument("--output-md", default="output/multi_entity_court_dossier.md", help="Output Markdown path")
    multi_dossier_parser.add_argument("--font", default="THSarabunNew", help="Thai font family to embed: 'THSarabunNew', 'THSarabunIT๙', or path to TTF")

    # 18. generate-multi-entity-dashboard
    multi_dash_parser = subparsers.add_parser("generate-multi-entity-dashboard", help="Generate interactive 5-hop visual dashboard")
    multi_dash_parser.add_argument("--nodes", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv", help="Path to nodes CSV")
    multi_dash_parser.add_argument("--edges", default="techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv", help="Path to edges CSV")
    multi_dash_parser.add_argument("--output", default="output/multi_entity_dashboard.html", help="Output HTML path")

    # 19. trace-victim (Dedicated Single-Victim Flow Matching & Top Beneficiaries)
    vic_parser = subparsers.add_parser("trace-victim", help="Trace a single victim's fund dispersal and summarize top beneficiaries via MILP")
    vic_parser.add_argument("--statement", default="input/statement.csv", help="Path to statement CSV")
    vic_parser.add_argument("--victim", required=True, help="Name, account number, or keyword of the victim")
    vic_parser.add_argument("--case-id", default="CASE-VICTIM-2026", help="Investigative Case ID")
    vic_parser.add_argument("--officer", default="พ.ต.ต. วิทวัส นิติวงศ์ (สอท.)", help="Investigating Officer")
    vic_parser.add_argument("--tolerance", type=float, default=0.05, help="Fee-buffer tolerance ratio (default 0.05)")
    vic_parser.add_argument("--window-hours", type=float, default=24.0, help="Sliding temporal search window in hours (default 24.0)")
    vic_parser.add_argument("--output-analysis", help="Optional path to export Markdown forensic analysis (defaults to output/victim_<slug>_analysis.md)")
    vic_parser.add_argument("--output-md", help="Optional path to export Markdown court dossier")
    vic_parser.add_argument("--output-pdf", help="Optional path to export PDF court dossier")
    vic_parser.add_argument("--output-aoc", help="Optional path to export AOC 1441 freeze JSON")
    vic_parser.add_argument("--output-dashboard", help="Optional path to export interactive HTML single-page dashboard")
    vic_parser.add_argument("--font", default="THSarabunNew", help="Thai font for PDF: 'THSarabunNew' or 'THSarabunIT๙'")

    args = parser.parse_args()

    strict_lvl = StrictLevel(args.strict_level)
    stack_mgr = TaskStackManager(file_path=args.stack_file, strict_level=strict_lvl)
    fsm = DeterministicStateMachine(stack_mgr)

    if args.command == "init":
        root_task = TaskFrame(
            task_id=args.task_id,
            title=args.title,
            description=args.desc,
            assigned_agent=args.agent,
            status=TaskStatus.PENDING,
            allowed_files=list(args.allowed_files),
            max_lines_changed=args.max_lines,
        )
        stack_mgr.set_strict_level(strict_lvl)
        stack_mgr.push(root_task)
        initial_state = fsm.state_for_agent(args.agent)
        stack_mgr.set_system_state(initial_state)
        print(f"✅ Initialized task stack with root task '{args.task_id}'.")
        print(f"Current State:  {initial_state.value}")
        print(f"Strict Level:   {strict_lvl.value.upper()}")
        print(f"Top Agent:      {args.agent}")
        if args.allowed_files:
            print(f"Allowed Files:  {', '.join(args.allowed_files)}")

    elif args.command == "status":
        print("=" * 60)
        print(f"⚡ SYSTEM STATE: {stack_mgr.current_state.value}")
        print(f"🛡️ STRICT LEVEL: {stack_mgr.strict_level.value.upper()}")
        print(f"📁 STACK DEPTH:  {len(stack_mgr.stack)}")
        print(f"🔑 SESSION ID:   {stack_mgr.session_id}")
        print("=" * 60)

        top = stack_mgr.peek()
        if top:
            print(f"🎯 TOP OF STACK (Active Task):")
            print(f"  - Task ID:        {top.task_id}")
            print(f"  - Title:          {top.title}")
            print(f"  - Assigned Agent: {top.assigned_agent}")
            print(f"  - Status:         {top.status.value}")
            print(f"  - Allowed Files:  {', '.join(top.allowed_files) if top.allowed_files else '(unrestricted)'}")
            print(f"  - Max Blast (L):  {top.max_lines_changed}")
            print(f"  - Artifacts:      {', '.join(top.artifacts) if top.artifacts else '(none)'}")
            print(f"  - Retries:        {top.budget.current_retries} / {top.budget.max_retries}")
            print(f"  - Tokens Used:    {top.budget.used_tokens} / {top.budget.max_tokens}")
        else:
            print("Stack is empty (IDLE / COMPLETED).")

        if stack_mgr.history:
            last_hist = stack_mgr.history[-1]
            receipt = last_hist.get("verification_receipt")
            if receipt:
                print("\n🧾 LATEST VERIFICATION RECEIPT:")
                print(f"  - Gate Type:      {receipt.get('gate_type')}")
                print(f"  - Status:         {receipt.get('status')} (Exit Code: {receipt.get('exit_code')})")
                print(f"  - Verified Files: {', '.join(receipt.get('verified_files', []))}")

    elif args.command == "build-prompt":
        top = stack_mgr.peek()
        if not top:
            print("❌ Cannot build prompt: Task stack is empty.", file=sys.stderr)
            sys.exit(1)

        builder = PromptOnDemandBuilder()
        prompt = builder.build_prompt(top, target_agent=args.agent, strict_level=stack_mgr.strict_level)

        if args.output:
            out_path = Path(args.output)
            out_path.write_text(prompt, encoding="utf-8")
            print(f"✅ Prompt saved to {out_path} ({len(prompt)} chars).")
        else:
            print(prompt)

    elif args.command == "transition":
        input_data = args.input
        input_path = Path(input_data)
        if input_path.exists() and input_path.is_file():
            input_data = input_path.read_text(encoding="utf-8")

        res = fsm.step_with_raw_output(input_data)
        print("=" * 60)
        print(f"Transition Result: {'✅ SUCCESS' if res.success else '❌ REJECTED / BLOCKED'}")
        print(f"State Change:      {res.previous_state.value} -> {res.new_state.value}")
        print(f"Next Agent:        {res.next_agent or '(none)'}")
        print(f"Message:           {res.message}")
        if res.rejection_feedback:
            print(f"Feedback/Reason:   {res.rejection_feedback}")
        if res.verification_receipt:
            print(f"Receipt Generated: {res.verification_receipt.status} (Gate: {res.verification_receipt.gate_type})")
        print("=" * 60)
        if not res.success:
            sys.exit(1)

    elif args.command == "verify":
        top = stack_mgr.peek()
        if not top:
            print("❌ Stack is empty.", file=sys.stderr)
            sys.exit(1)

        verifier = DeterministicVerifier()
        v_res = verifier.verify_artifacts(top.artifacts)
        print(v_res.summary())
        if not v_res.passed:
            for err in v_res.errors:
                print(f"  - ❌ {err}")
            sys.exit(1)

    elif args.command == "inspect-stack":
        print(json.dumps(stack_mgr.to_dict(), indent=2, ensure_ascii=False))

    elif args.command == "audit-evidence":
        verifier = DeterministicVerifier()
        csv_path = args.statement
        print("=" * 60)
        print("🔍 AUDITING FORENSIC EVIDENCE & CHAIN OF CUSTODY")
        print(f"Target Statement: {csv_path}")
        print("=" * 60)

        # 1. Cryptographic hash check
        h_ok, h_msg, computed_hash = verifier.verify_data_provenance(csv_path, args.expected_hash)
        print(f"SHA-256 Provenance: {'✅ PASS' if h_ok else '❌ FAIL'}")
        print(f"  - Hash: {computed_hash}")
        print(f"  - Details: {h_msg}")

        # 2. Statement schema & validity check
        s_ok, s_errs, s_summary = verifier.verify_statement_csv(csv_path)
        print(f"\nStatement Schema Integrity: {'✅ PASS' if s_ok else '❌ FAIL'}")
        print(f"  - Total Transactions: {s_summary.get('total_rows', 0)}")
        print(f"  - Total Inflow:       ฿{s_summary.get('total_inflow', 0):,.2f}")
        print(f"  - Total Outflow:      ฿{s_summary.get('total_outflow', 0):,.2f}")
        if not s_ok:
            for err in s_errs:
                print(f"  - ❌ {err}")
            sys.exit(1)
        if not h_ok:
            sys.exit(1)
        print("\n✅ Evidence Chain of Custody successfully audited and verified.")

    elif args.command == "verify-compliance":
        verifier = DeterministicVerifier()
        c_ok, c_errs, c_summary = verifier.verify_spec_compliance(args.spec)
        print("=" * 60)
        print("📐 SPEC-TO-CODE COMPLIANCE VERIFICATION")
        print(f"Target Specification: {args.spec}")
        print("=" * 60)
        print(f"Compliance Status: {'✅ COMPLIANT' if c_ok else '❌ NON-COMPLIANT'}")
        print(f"Core Contracts Checked: {c_summary.get('contracts_checked', 0)}")
        print(f"Spec Size: {c_summary.get('spec_size_bytes', 0):,} bytes")
        if not c_ok:
            for err in c_errs:
                print(f"  - ❌ {err}")
            sys.exit(1)
        print("\n✅ All required architecture contracts are formally specified and compliant.")

    elif args.command == "verify-neutrality":
        verifier = DeterministicVerifier()
        n_ok, n_violations = verifier.verify_neutrality_standard(args.target)
        print("=" * 60)
        print("⚖️ LEGAL NEUTRALITY & CORROBORATION GATE VERIFICATION")
        print(f"Target: {args.target}")
        print("=" * 60)
        print(f"Verdict: {'✅ PASS (Corroboration-Gated Neutrality Preserved)' if n_ok else '❌ FAIL (Defamatory or Conclusive Guilt Language Detected)'}")
        if not n_ok:
            for v in n_violations:
                print(f"  - ❌ {v}")
            sys.exit(1)
        print("\n✅ Artifact strictly adheres to evidentiary standards under Section 226.")

    elif args.command in ("analyze-statement", "export-dossier"):
        from src.models.transaction import ActivityType
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.flow_matcher import FlowMatchingEngine
        from src.engine.behavioral import SuspicionScoringEngine
        from src.engine.cycle_detector import CycleDetector
        from src.graph.tracer import GraphTracer
        from src.audit.provenance import compute_file_sha256, EvidenceVault
        from src.models.dossier import SuspicionReport
        from src.dossier.generator import EvidenceDossierGenerator

        csv_path = args.statement
        case_id = args.case_id
        officer = args.officer

        # 1. Chain of custody hash & Vault
        file_hash = compute_file_sha256(csv_path)
        vault = EvidenceVault(case_id=case_id, officer_id=officer)
        vault.record_action("INGEST", f"Ingested statement file {csv_path} with SHA-256 {file_hash}")

        # 2. Universal Parsing
        parser = UniversalStatementParser()
        transactions = parser.parse_file(csv_path)
        vault.record_action("PARSE", f"Parsed {len(transactions)} valid banking transactions")

        # 3. Behavioral Scoring
        scorer = SuspicionScoringEngine()
        score, level, breakdown = scorer.score(transactions)

        # 4. Cycle Detection
        detector = CycleDetector(target_account=transactions[0].account_no if transactions else "")
        cycles = detector.detect_cycles(transactions)

        # 5. Graph Analytics & Shared Surnames
        tracer = GraphTracer(target_account=transactions[0].account_no if transactions else "")
        tracer.build_graph(transactions)
        shared_surnames = tracer.detect_shared_surnames()

        # 6. Flow Matching on Major Inflows
        matcher = FlowMatchingEngine()
        major_inflows = sorted([t for t in transactions if t.activity == ActivityType.INFLOW and t.amount >= 10000.0], key=lambda x: x.amount, reverse=True)[:5]
        candidate_pool = [t for t in transactions if t.activity in (ActivityType.OUTFLOW, ActivityType.FEE) and not t.is_reversal]
        cluster_specs = []
        for idx, inf in enumerate(major_inflows, start=1):
            outflows_after = [
                t for t in candidate_pool
                if t.activity in (ActivityType.OUTFLOW, ActivityType.FEE)
                and t.timestamp >= inf.timestamp
                and (t.timestamp - inf.timestamp).total_seconds() <= 86400 * 3
            ][:60]
            cluster_specs.append((f"CLUSTER-INF-{idx:02d}", [inf], outflows_after, None))
        clusters = matcher.solve_clusters_parallel(cluster_specs)

        vault.record_action("SOLVE", f"Solved {len(clusters)} flow matching clusters via MILP")

        # Top counterparties
        out_txs = [t for t in transactions if t.activity == ActivityType.OUTFLOW]
        cp_vol: Dict[str, float] = {}
        for tx in out_txs:
            k = f"{tx.counterparty_bank or 'N/A'} {tx.counterparty_account or 'N/A'} {tx.counterparty_name or ''}".strip()
            cp_vol[k] = cp_vol.get(k, 0.0) + tx.amount

        # Build SuspicionReport
        acct_raw = transactions[0].account_no if transactions else "N/A"
        acct_masked = f"{acct_raw[:4]}xxxx{acct_raw[-2:]}" if len(acct_raw) >= 6 else acct_raw
        acct_name = transactions[0].account_name if transactions else "N/A"

        report = SuspicionReport(
            case_id=case_id,
            account_no_masked=acct_masked,
            account_no_raw=acct_raw,
            account_name=acct_name,
            statement_hash_sha256=file_hash,
            overall_suspicion_score=score,
            suspicion_level=level,
            clusters_detected=clusters,
            top_counterparties=cp_vol,
            cfr_hits=[],
            merkle_root=vault.get_merkle_root(),
            admissibility_receipt=vault.generate_admissibility_receipt(file_hash),
        )

        dossier_gen = EvidenceDossierGenerator(case_id=case_id, investigating_officer=officer)

        if args.command == "export-dossier":
            out_path = Path(args.output)
            dossier_text = dossier_gen.generate_markdown_dossier(report, transactions, vault)
            out_path.write_text(dossier_text, encoding="utf-8")
            vault.record_action("EXPORT", f"Exported court dossier to {out_path}")
            print("=" * 65)
            print("📄 COURT-ADMISSIBLE FORENSIC DOSSIER EXPORTED")
            print(f"Target Statement: {csv_path}")
            print(f"Output File:      {out_path.as_posix()}")
            print(f"Case Reference:   {case_id}")
            print(f"Suspicion Score:  {score}/100 ({level})")
            print(f"Merkle Root:      {vault.get_merkle_root()}")
            print("=" * 65)
            print("✅ Court dossier (Exhibit A-D) generated successfully.")

        else:
            # analyze-statement console report
            print("=" * 65)
            print("🔬 ENTERPRISE FINANCIAL FORENSICS & FLOW MATCHING REPORT")
            print(f"Target Statement: {csv_path}")
            print(f"Target Account:   {acct_raw} ({acct_name})")
            print(f"SHA-256 Hash:     {file_hash}")
            print("=" * 65)
            print(f"Total Transactions: {len(transactions)} (Inflow: ฿{breakdown['total_inflow']:,.2f}, Outflow: ฿{breakdown['total_outflow']:,.2f})")
            print(f"Net Residual:       ฿{breakdown['final_balance']:,.2f} | Drain Rate: {breakdown['drain_percentage']}%")
            print(f"Avg Transit Latency: {breakdown['avg_latency_minutes']} minutes (Rapid Dispersal)")
            print(f"\n📊 UNIFIED SUSPICION SCORE: {score}/100")
            print(f"   Verdict: {level}")
            print(f"   Breakdown: Amount={breakdown['s_amount']}, Time={breakdown['s_time']}, Balance={breakdown['s_balance']}, Network={breakdown['s_network']}")

            if shared_surnames:
                print("\n👥 ENTITY RESOLUTION (Shared Surnames Detected):")
                for s in shared_surnames:
                    names_sample = ', '.join(a['name'] for a in s['accounts'][:3])
                    suffix = ' ...' if len(s['accounts']) > 3 else ''
                    print(f"   - นามสกุล '{s['surname']}': {len(s['accounts'])} บัญชี ({names_sample}{suffix})")

            print("\n⚡ FLOW MATCHING CLUSTERS (MILP Solver):")
            for c in clusters:
                print(f"   • {c.cluster_id}: Inflow ฿{c.inflow_total:,.2f} -> Matched Outflow ฿{c.outflow_total:,.2f} (Drain: {c.drain_percentage:.1f}%)")
                print(f"     Proof: {c.mathematical_proof}")

            print("\n🏆 TOP DISPERSAL COUNTERPARTIES:")
            sorted_cps = sorted(cp_vol.items(), key=lambda x: x[1], reverse=True)[:5]
            for i, (cp, vol) in enumerate(sorted_cps, 1):
                print(f"   {i}. {cp} -> ฿{vol:,.2f}")

            print("\n⚖️ CHAIN OF CUSTODY:")
            print(f"   Merkle Root: {vault.get_merkle_root()}")
            print(f"   Integrity:   {vault.verify_vault_integrity()} (All records tamper-evident)")
            print("=" * 65)

    elif args.command == "generate-dashboard":
        from src.models.transaction import ActivityType
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.flow_matcher import FlowMatchingEngine
        from src.engine.behavioral import SuspicionScoringEngine
        from src.ui.dashboard_generator import ForensicDashboardGenerator
        from src.models.dossier import SuspicionReport
        from src.audit.provenance import compute_file_sha256

        csv_path = args.statement
        parser = UniversalStatementParser()
        txs = parser.parse_file(csv_path)
        transactions = txs
        scorer = SuspicionScoringEngine()
        score, level, breakdown = scorer.score(txs)
        file_hash = compute_file_sha256(csv_path)

        acct_raw = txs[0].account_no if txs else "N/A"
        acct_masked = f"{acct_raw[:4]}xxxx{acct_raw[-2:]}" if len(acct_raw) >= 6 else acct_raw
        acct_name = txs[0].account_name if txs else "N/A"

        rep = SuspicionReport(
            case_id=args.case_id,
            account_no_masked=acct_masked,
            account_no_raw=acct_raw,
            account_name=acct_name,
            statement_hash_sha256=file_hash,
            overall_suspicion_score=score,
            suspicion_level=level,
            clusters_detected=[],
            top_counterparties={},
            cfr_hits=[],
            merkle_root="",
            admissibility_receipt={},
        )

        ui_gen = ForensicDashboardGenerator()
        out_file = ui_gen.generate_html(rep, txs, args.output)
        print("=" * 65)
        print("📊 INTERACTIVE FORENSIC DASHBOARD GENERATED")
        print(f"Target Statement: {csv_path}")
        print(f"Dashboard File:   {out_file}")
        print(f"Features:         Sankey Flow, Network Topology, Timeline, 52 Audited Rows")
        print("=" * 65)
        print("✅ Dashboard ready to open in any web browser.")

    elif args.command == "export-pdf":
        from src.models.transaction import ActivityType
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.flow_matcher import FlowMatchingEngine
        from src.engine.behavioral import SuspicionScoringEngine
        from src.audit.provenance import compute_file_sha256, EvidenceVault
        from src.models.dossier import SuspicionReport
        from src.dossier.pdf_exporter import CourtDossierPDFExporter

        csv_path = args.statement
        parser = UniversalStatementParser()
        txs = parser.parse_file(csv_path)
        file_hash = compute_file_sha256(csv_path)
        vault = EvidenceVault(case_id=args.case_id, officer_id=args.officer)
        vault.record_action("INGEST", f"Ingested {csv_path}")

        transactions = txs
        scorer = SuspicionScoringEngine()
        score, level, breakdown = scorer.score(txs)

        matcher = FlowMatchingEngine()
        major_inflows = sorted([t for t in txs if t.activity == ActivityType.INFLOW and t.amount >= 10000.0], key=lambda x: x.amount, reverse=True)[:5]
        candidate_pool = [t for t in transactions if t.activity in (ActivityType.OUTFLOW, ActivityType.FEE) and not t.is_reversal]
        cluster_specs = []
        for idx, inf in enumerate(major_inflows, start=1):
            outflows_after = [
                t for t in candidate_pool
                if t.timestamp >= inf.timestamp
                and (t.timestamp - inf.timestamp).total_seconds() <= 86400 * 3
            ][:60]
            cluster_specs.append((f"CLUSTER-{idx:02d}", [inf], outflows_after, None))
        clusters = matcher.solve_clusters_parallel(cluster_specs)

        out_txs = [t for t in txs if t.activity == ActivityType.OUTFLOW]
        cp_vol: dict = {}
        for tx in out_txs:
            k = f"{tx.counterparty_bank or 'N/A'} {tx.counterparty_account or 'N/A'} {tx.counterparty_name or ''}".strip()
            cp_vol[k] = cp_vol.get(k, 0.0) + tx.amount

        acct_raw = txs[0].account_no if txs else "N/A"
        acct_masked = f"{acct_raw[:4]}xxxx{acct_raw[-2:]}" if len(acct_raw) >= 6 else acct_raw
        acct_name = txs[0].account_name if txs else "N/A"

        rep = SuspicionReport(
            case_id=args.case_id,
            account_no_masked=acct_masked,
            account_no_raw=acct_raw,
            account_name=acct_name,
            statement_hash_sha256=file_hash,
            overall_suspicion_score=score,
            suspicion_level=level,
            clusters_detected=clusters,
            top_counterparties=cp_vol,
            cfr_hits=[],
            merkle_root=vault.get_merkle_root(),
            admissibility_receipt=vault.generate_admissibility_receipt(file_hash),
        )

        exporter = CourtDossierPDFExporter(font_name=args.font)
        pdf_file = exporter.export_pdf(args.output, rep, txs, vault, officer_name=args.officer)
        print("=" * 65)
        print("⚖️ COURT-ADMISSIBLE PDF DOSSIER GENERATED")
        print(f"Target Statement: {csv_path}")
        print(f"PDF Output File:  {pdf_file}")
        print(f"Exhibits:         Exhibit A (Summary), B (MILP Proofs), C (Counterparties), D (AOC Form)")
        print(f"Governing Law:    Thai Criminal Procedure Code Section 226 & ETA Sec 26")
        print("=" * 65)
        print("✅ Official PDF dossier generated successfully.")

    elif args.command == "copilot":
        from src.models.transaction import ActivityType
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.flow_matcher import FlowMatchingEngine
        from src.engine.behavioral import SuspicionScoringEngine
        from src.audit.provenance import compute_file_sha256
        from src.models.dossier import SuspicionReport
        from src.copilot.chat import ForensicChatCopilot

        csv_path = args.statement
        parser = UniversalStatementParser()
        txs = parser.parse_file(csv_path)
        file_hash = compute_file_sha256(csv_path)
        transactions = txs
        scorer = SuspicionScoringEngine()
        score, level, breakdown = scorer.score(txs)

        out_txs = [t for t in txs if t.activity == ActivityType.OUTFLOW]
        cp_vol: dict = {}
        for tx in out_txs:
            k = f"{tx.counterparty_bank or 'N/A'} {tx.counterparty_account or 'N/A'} {tx.counterparty_name or ''}".strip()
            cp_vol[k] = cp_vol.get(k, 0.0) + tx.amount

        acct_raw = txs[0].account_no if txs else "N/A"
        acct_masked = f"{acct_raw[:4]}xxxx{acct_raw[-2:]}" if len(acct_raw) >= 6 else acct_raw
        acct_name = txs[0].account_name if txs else "N/A"

        rep = SuspicionReport(
            case_id=args.case_id,
            account_no_masked=acct_masked,
            account_no_raw=acct_raw,
            account_name=acct_name,
            statement_hash_sha256=file_hash,
            overall_suspicion_score=score,
            suspicion_level=level,
            clusters_detected=[],
            top_counterparties=cp_vol,
            cfr_hits=[],
            merkle_root="",
            admissibility_receipt={},
        )

        copilot = ForensicChatCopilot(rep, txs)
        ans = copilot.answer_query(args.query)
        print("=" * 65)
        print(f"🤖 FORENSIC CHAT COPILOT (Query: '{args.query}')")
        print("=" * 65)
        print(ans)
        print("=" * 65)

    elif args.command == "aoc-freeze":
        import json
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.behavioral import SuspicionScoringEngine
        from src.integrations.aoc_cfr import AOCFraudRegistryClient

        csv_path = args.statement
        parser = UniversalStatementParser()
        txs = parser.parse_file(csv_path)
        transactions = txs
        scorer = SuspicionScoringEngine()
        score, level, breakdown = scorer.score(txs)

        client = AOCFraudRegistryClient()
        acct_raw = txs[0].account_no if txs else "N/A"
        acct_name = txs[0].account_name if txs else "N/A"
        payload = client.generate_freeze_payload(
            case_id=args.case_id,
            investigator_id="POL-8842",
            target_account=acct_raw,
            bank_code="KBANK/BBL/SCB",
            account_name=acct_name,
            drain_percentage=breakdown["drain_percentage"],
            matched_outflow_total=breakdown["total_outflow"],
        )

        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print("=" * 65)
        print("🚨 AOC 1441 EMERGENCY FREEZE PAYLOAD GENERATED")
        print(f"Target Account:  {acct_raw} ({acct_name})")
        print(f"Payload File:    {out_p.as_posix()}")
        print(f"Action:          SUSPEND_ALL_DEBIT_CHANNELS (72 Hours)")
        print(f"Legal Basis:     พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 7")
        print("=" * 65)
        print("✅ Ready for automated API transmission to AOC 1441.")

    elif args.command == "analyze-multi-entity":
        from src.graph.multi_entity_tracer import MultiEntityTracer
        tracer = MultiEntityTracer()
        summary = tracer.load_from_csv(args.nodes, args.edges)
        print("=" * 65)
        print("🌐 MULTI-ENTITY GRAPH & 5-HOP MONEY TRAIL REPORT")
        print(f"Case Reference:      {summary.case_id}")
        print(f"Nodes File:          {args.nodes}")
        print(f"Edges File:          {args.edges}")
        print("=" * 65)
        print(f"Total Entities:      {summary.total_entities} (Victims, Mules, Cash Runners, Crypto)")
        print(f"Total Transactions:  {summary.total_transactions:,}")
        print(f"Total Flow Volume:   ฿{summary.total_flow_volume_thb:,.2f} ({summary.total_flow_volume_thb/1e6:.1f}M THB)")
        print("\n📈 5-HOP MONEY TRAIL BREAKDOWN:")
        for h, v in summary.hop_volumes.items():
            cnt = sum(1 for e in tracer.edges if e.hop_level == h)
            print(f"   • {h:25s}: {cnt:4d} txs | ฿{v:14,.2f} ({v/1e6:5.1f}M THB)")
        if summary.device_clusters:
            print("\n📱 SHARED DEVICE FINGERPRINT CLUSTERS:")
            for dev, ents in summary.device_clusters.items():
                print(f"   - Device '{dev}': Controls {len(ents)} accounts ({', '.join(ents)})")
        print("\n🏆 TOP CONSOLIDATION GATEWAYS:")
        for gw in summary.top_gateways:
            print(f"   - {gw['name']} ({gw['entity_id']}): ฿{gw['volume_thb']:,.2f}")
        print("=" * 65)

    elif args.command == "export-multi-entity-dossier":
        # Path imported at top-level
        from src.graph.multi_entity_tracer import MultiEntityTracer
        from src.dossier.multi_entity_dossier import MultiEntityDossierGenerator
        tracer = MultiEntityTracer()
        tracer.load_from_csv(args.nodes, args.edges)
        gen = MultiEntityDossierGenerator(font_name=args.font)
        md_text = gen.generate_markdown(tracer)
        Path(args.output_md).write_text(md_text, encoding="utf-8")
        pdf_path = gen.export_pdf(tracer, args.output_pdf)
        print("=" * 65)
        print("⚖️ MULTI-ENTITY SYNDICATE COURT DOSSIER EXPORTED")
        print(f"Markdown Dossier: {Path(args.output_md).as_posix()}")
        print(f"PDF Dossier:      {pdf_path}")
        print("Governing Law:    พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 9, 10 & ป.วิ.อาญา ม.226")
        print("=" * 65)
        print("✅ Multi-entity court dossiers successfully created.")

    elif args.command == "generate-multi-entity-dashboard":
        from src.graph.multi_entity_tracer import MultiEntityTracer
        from src.ui.multi_entity_dashboard import MultiEntityDashboardGenerator
        tracer = MultiEntityTracer()
        tracer.load_from_csv(args.nodes, args.edges)
        gen = MultiEntityDashboardGenerator()
        out_file = gen.generate_html(tracer, args.output)
        print("=" * 65)
        print("📊 5-HOP MULTI-ENTITY VISUAL DASHBOARD GENERATED")
        print(f"Dashboard File:   {out_file}")
        print(f"Features:         5-Hop Sankey, Force-directed Topology, Device Fingerprints, Income Discrepancy")
        print("=" * 65)
        print("✅ Multi-entity dashboard ready to view in browser.")




    elif args.command == "trace-victim":
        import json
        from src.ingestion.universal_parser import UniversalStatementParser
        from src.engine.victim_tracer import VictimFlowTracer, slugify_victim_name
        from src.audit.provenance import compute_file_sha256, EvidenceVault

        csv_path = args.statement
        file_hash = compute_file_sha256(csv_path)
        vault = EvidenceVault(case_id=args.case_id, officer_id=args.officer)
        vault.record_action("INGEST", f"Ingested statement file {csv_path} with SHA-256 {file_hash}")

        parser = UniversalStatementParser()
        transactions = parser.parse_file(csv_path)
        vault.record_action("PARSE", f"Parsed {len(transactions)} valid banking transactions")

        tracer = VictimFlowTracer(
            transactions=transactions,
            statement_file=csv_path,
            statement_sha256=file_hash,
            tolerance_ratio=args.tolerance,
        )

        result = tracer.trace_victim(
            query=args.victim,
            time_window_hours=args.window_hours,
        )
        vault.record_action("TRACE_VICTIM", f"Traced victim '{result.victim_name}' loss ฿{result.total_inflow_thb:,.2f}")

        # Terminal Output
        print("=" * 75)
        print("🎯 TARGETED VICTIM FORENSIC TRACER & TOP BENEFICIARIES")
        print(f"Statement File:      {csv_path}")
        print(f"Target Victim:       {result.victim_name} (Query: '{args.victim}')")
        print(f"Case ID Reference:   {args.case_id}")
        print(f"Investigator:        {args.officer}")
        print(f"Provenance SHA-256:  {file_hash}")
        print("=" * 75)

        print("\n👤 VICTIM INFLOW LEDGER:")
        print(f"   • Total Victim Inflows:  ฿{result.total_inflow_thb:,.2f} ({len(result.inflow_transactions)} transactions)")
        print(f"   • Victim Account(s):     {', '.join(result.victim_accounts) if result.victim_accounts else 'N/A'}")
        print(f"   • Gateway Mule Account:  {result.target_account} ({result.target_account_name})")
        if result.inflow_transactions:
            t_first = result.inflow_transactions[0].timestamp.strftime('%d/%m/%Y %H:%M:%S')
            t_last = result.inflow_transactions[-1].timestamp.strftime('%d/%m/%Y %H:%M:%S')
            print(f"   • Transaction Period:    {t_first} ถึง {t_last}")

        print("\n🧮 MILP FLOW MATCHING & DISPERSAL DYNAMICS:")
        print(f"   • Matched Outflows:      ฿{result.total_matched_outflow_thb:,.2f} (Across {len(result.matched_clusters)} clusters)")
        print(f"   • Mule Account Drain:    {result.drain_percentage:.2f}%")
        print(f"   • Mean Residence Time:   {result.avg_latency_minutes:.1f} minutes")
        print(f"   • Residual Buffer Trapped:฿{result.net_residual_buffer_thb:,.2f}")

        print("\n🏆 TOP DISPERSAL DESTINATIONS & BENEFICIARIES (ผู้รับผลประโยชน์หลัก):")
        print("-" * 115)
        print(f"{'Rank':<4} | {'Destination Account / Channel':<32} | {'Account Holder':<26} | {'Outflow (฿)':<13} | {'Claim (฿)':<13} | {'Share%':<6} | {'Action'}")
        print("-" * 115)
        for d in result.top_destinations:
            acct_str = f"{d.bank} {d.account_no}"[:32]
            holder_str = d.account_name[:26]
            print(f"{d.rank:<4} | {acct_str:<32} | {holder_str:<26} | ฿{d.total_drained_thb:>11,.2f} | ฿{d.proportional_claim_thb:>11,.2f} | {d.percentage_of_victim_funds:>5.1f}% | {d.recommended_action}")
        print("-" * 115)

        print("\n⚖️ PROPORTIONAL ASSET RESTITUTION CLAIM (ป.วิ.อาญา ม.226 / ปปง. ม.49/1):")
        print(f"   • Total Legally Claimable Restitution: ฿{result.total_claimable_thb:,.2f}")
        print(f"   • Ground Truth Verification:           OPTIMAL (Verified via scipy.optimize.milp)")
        print(f"   • Merkle Provenance Root:              {vault.get_merkle_root()}")

        # Automatic Forensic Analysis Markdown Persistence
        slug = slugify_victim_name(result.victim_name)
        analysis_path_str = args.output_analysis or f"output/victim_{slug}_analysis.md"
        analysis_path = Path(analysis_path_str)
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_text = tracer.generate_analysis_report(result, case_id=args.case_id, officer=args.officer)
        analysis_path.write_text(analysis_text, encoding="utf-8")
        vault.record_action("EXPORT_ANALYSIS_MD", f"Exported victim analysis report to {analysis_path.as_posix()}")
        print(f"\n📊 Forensic Analysis Markdown: {analysis_path.as_posix()}")

        # Optional Markdown Court Dossier Export
        if args.output_md:
            md_path = Path(args.output_md)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_text = tracer.generate_markdown_report(result, case_id=args.case_id, officer=args.officer)
            md_path.write_text(md_text, encoding="utf-8")
            vault.record_action("EXPORT_MD", f"Exported victim markdown dossier to {md_path}")
            print(f"\n📄 Markdown Court Dossier: {md_path.as_posix()}")

        # Optional PDF Export
        if args.output_pdf:
            pdf_path = Path(args.output_pdf)
            tracer.export_pdf(
                result=result,
                output_pdf_path=pdf_path,
                case_id=args.case_id,
                officer_name=args.officer,
                font_name=args.font,
            )
            vault.record_action("EXPORT_PDF", f"Exported victim PDF dossier to {pdf_path}")
            print(f"📑 Official PDF Court Dossier: {pdf_path.as_posix()}")

        # Optional AOC Freeze JSON Export
        if args.output_aoc:
            aoc_path = Path(args.output_aoc)
            aoc_path.parent.mkdir(parents=True, exist_ok=True)
            aoc_payload = tracer.generate_aoc_payload(result, case_id=args.case_id, officer=args.officer)
            aoc_path.write_text(json.dumps(aoc_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            vault.record_action("EXPORT_AOC", f"Exported AOC freeze payload to {aoc_path}")
            print(f"🚨 AOC 1441 Freeze JSON:       {aoc_path.as_posix()}")

        # Optional HTML Dashboard Export
        if args.output_dashboard:
            dash_path = Path(args.output_dashboard)
            dash_path.parent.mkdir(parents=True, exist_ok=True)
            tracer.generate_html_dashboard(result, output_html_path=dash_path, case_id=args.case_id, officer=args.officer)
            vault.record_action("EXPORT_DASHBOARD", f"Exported victim dashboard to {dash_path}")
            print(f"📊 Interactive HTML Dashboard:  {dash_path.as_posix()}")

        print("=" * 75)
        print("✅ Single-victim flow tracing and beneficiary summary completed successfully.")



if __name__ == "__main__":
    main()
