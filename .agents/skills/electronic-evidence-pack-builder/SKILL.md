---
name: electronic-evidence-pack-builder
description: "Organise electronic financial evidence provenance, acquisition manifests, SHA-256 hashes, transformation logs, court dossiers, and witness records under Thai Criminal Procedure Code Section 226 and Electronic Transactions Act B.E. 2544."
category: financial-forensics
risk: safe
metadata:
  phase: specialist
  jurisdiction: thailand
---

# Electronic Financial Evidence Pack Builder

Produce a legally admissible, traceable electronic evidence index and pack that enables technical, investigative, and judicial reviewers to test evidence authenticity, integrity, and statutory compliance.

Before substantive work, read [Discipline guidance](references/core-forensic-workflow.md), [Safety and human review](references/safety-and-human-review.md), and [Thai Financial Legal Layer](references/thai-financial-legal-layer.md).

---

## 1. Intake Requirements

Obtain or verify the following materials:
- Raw bank statement files (CSV, XLSX, PDF) or digital core banking exports.
- Source institution, victim account, and acquiring officer details.
- Statutory authority basis (e.g. Complaint filing, AOC 1441 freeze ticket, CPC Section 132 subpoena).
- Pristine file hashes (SHA-256) computed at the moment of intake.
- Transformation manifest (parser normalization rules, encoding conversions, date-time parsing logs).
- Applicable statutory requirements under Thai law (CPC Sec 226/132, Electronic Transactions Act B.E. 2544 Sec 11, AMLA Sec 49/1).

> [!NOTE]
> If any material input is absent, mark it explicitly as **UNKNOWN**. Never reconstruct missing facts, accounts, or timestamps from narrative fit.

---

## 2. Core Method

1. **Provenance & Derivative Mapping**:
   - Trace the original statement source (commercial bank, victim mobile export, payment gateway) and every generated derivative (parsed JSON, analysis Markdown, HTML visual dashboard, PDF court dossier).
2. **Metadata & Record Separation**:
   - Distinguish bank system-generated metadata (transaction ref, posting time, core channel code), victim-reported facts, and AI-computed optimization results (`scipy.optimize.milp`).
3. **Cryptographic Reconcilation**:
   - Reconcile SHA-256 hashes, timestamp offsets, time zones (UTC+7 Asia/Bangkok), and transformation histories for all ingested statements.
4. **Witness & Custodian Register**:
   - Map each bank statement and exhibit to the bank compliance officer, victim complainant, forensic analyst, and investigating officer required to authenticate it in court.
5. **Actionable Classification**:
   - Partition counterparties into lawful action categories:
     - `AOC_1441_FREEZE_URGENT`: Retail mule accounts subject to rapid 72-hour freeze.
     - `PLATFORM_SUBPOENA_EVIDENCE`: Corporate payment gateways / tech ad platforms requiring CPC Section 132 summons.
     - `CCTV_INSPECTION_ATM`: Cash withdrawal points requiring surveillance footage preservation.
     - `VASP_WALLET_FREEZE`: Digital asset exchanges requiring wallet hold under AMLA Section 48/57.
6. **Relative Path Citations (Iron Law)**:
   - Cite all pack contents using workspace-relative paths (e.g. `output/statement_dashboard.html`, `output/court_dossier.pdf`, `input/statement.csv`). Never emit absolute paths (`C:\...`).

---

## 3. Deliverables

An Electronic Financial Evidence Pack must contain:
1. **Evidence Pack Index & Provenance Matrix**: Master table of all ingested and generated exhibits with dates, sizes, and SHA-256 hashes.
2. **Chain of Custody & Transformation Manifest**: Step-by-step audit record from raw statement intake through parser normalization to mathematical flow matching.
3. **Restitution Claims Ledger**: Proportional victim asset allocation calculated under Section 226 and AMLA Section 49/1.
4. **Investigative Directive Schedule**: Partitioned action list for AOC rapid freezes vs Section 132 subpoenas.
5. **Court Admissibility Checklist**: Statutory compliance audit under Section 226 of the Criminal Procedure Code.

Label all draft deliverables: **"AI-assisted forensic evidence draft. Subject to R5 Legal and Investigative Review."**

---

## 4. Hard Boundaries

- **No Self-Certification of Admissibility**: The pack organizes evidence for judicial review; it does not promise or certify court admissibility.
- **On-Demand Court Dossier Protocol**: Generate official PDF dossiers (`output/*_dossier.pdf`) or AOC JSON payloads (`output/*_aoc.json`) ONLY upon explicit user opt-in prompt.
- **No Guilt Determinations**: Document observations and mathematical proofs; leave legal guilt adjudication to the competent court.

---

## 5. Required Review

- **Reviewers**: Lead Evidence Auditor, Supervisory Investigator (พนักงานสอบสวน), and Public Prosecutor (พนักงานอัยการ) prior to formal court submission.
