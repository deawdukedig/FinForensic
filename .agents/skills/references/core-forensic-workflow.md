# Core Financial Forensic Workflow (ISO 21043 Aligned)

Use this workflow for every financial forensic investigation, evidence ingestion, money trail analysis, and dossier creation.

---

## 1. Operating Model (Lifecycle Stages)

Follow the ISO 21043-aligned lifecycle adapted for financial crimes:

1. **Recognise (การตรวจพบ)**:
   - Identify potentially relevant financial accounts, statements, transaction logs, and victim transfer records without prejudging guilt or intent.
2. **Record (การบันทึก)**:
   - Record contemporaneous observations, raw file hashes (SHA-256), timestamps, account metadata, ingestion parameters, and intake logs.
3. **Recover (การรวบรวม)**:
   - Ingest bank statement CSV/Excel/PDF files, official core banking outputs, payment gateway settlements, and ATM CCTV records under sanctioned procedures.
4. **Preserve (การเก็บรักษา)**:
   - Maintain pristine original statements in read-only condition. Create working memory buffers or working copies for algorithmic processing. Maintain strict Chain of Custody logs.
5. **Analyse (การวิเคราะห์เชิงคำนวณ)**:
   - Execute deterministic flow matching via MILP (`scipy.optimize.milp`), cycle detection, velocity latency analysis, and anomalous structuring heuristics.
6. **Interpret (การแปลความหมายเชิงนิติวิทยาศาสตร์)**:
   - Distinguish mathematical observations ($A \cdot x \approx T$) from investigative interpretations (e.g., mule account clustering vs merchant clearing pool). Maintain alternate hypotheses.
7. **Report (การรายงานผล)**:
   - Generate structured Markdown analytical reports (`output/*_analysis.md`) and interactive HTML dashboards (`output/*_dashboard.html`). State assumptions, fee tolerances, and limitations clearly.
8. **Review (การตรวจสอบรับรอง)**:
   - Conduct technical review (evidence auditor, QA gatekeeper) and legal review (supervisory investigator, public prosecutor) before official court filing.

---

## 2. The 8 Discrete Evidence States (Iron Law)

Never collapse these 8 states into a single subjective narrative:

- **Observed (ข้อเท็จจริงเชิงประจักษ์)**:
  - Directly visible or recorded in raw statement data (e.g., "Account 123 transferred ฿50,000 to Account 456 at 14:02:15 with description 'PromptPay'").
- **Reported (ข้อเท็จจริงตามคำให้การ/บันทึกภายนอก)**:
  - Asserted by victim, complainant, or witness but not yet independently verified by bank core records.
- **Test Result (ผลการคำนวณทางคณิตศาสตร์)**:
  - Output produced by deterministic algorithms (e.g., "MILP optimization identified exact subset match with objective value 0.00 within 45-second latency window").
- **Interpretation (การแปลความหมายเชิงสืบสวน)**:
  - Bounded inference derived from observations and results (e.g., "Transaction sequence is consistent with Layer 1 rapid smurfing behaviour").
- **Hypothesis (สมมติฐานเพื่อการพิสูจน์)**:
  - A plausible explanation being tested (e.g., "Hypothesis A: Account owner is an unwitting mule; Hypothesis B: Account owner actively controlled mobile banking session").
- **Unknown (ข้อมูลที่ยังขาดหายหรือไม่ปรากฏ)**:
  - Material information missing from the file (e.g., "Counterparty citizen ID unknown; core banking KYC log not yet returned under CPC Sec 132").
- **Conflict (ข้อเท็จจริงที่ขัดแย้งกัน)**:
  - Discrepancies between sources (e.g., "Victim reported transfer at 14:00, but statement timestamp records 14:15").
- **Excluded (พยานหลักฐานที่อยู่นอกขอบเขตหรือถูกตัดออก)**:
  - Data outside the authorized judicial scope or tainted by irregular collection.

---

## 3. Output Contract Standards

Every analytical report and court dossier must include:
- Scope, case ID, victim ID, and investigative authority.
- Exact statements reviewed, file names, sizes, and pristine SHA-256 hashes.
- Observations and reported claims segregated into distinct sections.
- Algorithmic results with exact mathematical constraints and parameters.
- Dispersal classification (AOC Retail Mule vs Corporate Clearing Pool vs VASP Crypto vs Cash ATM).
- Missing inputs, unverified counterparties, and operational next steps.
- Workspace-relative file paths only (`output/...`, `input/...`).
