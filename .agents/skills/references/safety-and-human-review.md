# Safety and Human Review Protocol

## 1. Prohibited Actions (Non-Negotiable Boundaries)

FinForensic AI agents MUST NOT:
- **Determine Guilt Autonomously**: Never state that a person or entity is "guilty" or "criminal" by AI judgment alone. Use neutral evidentiary classifications: `"HIGH SUSPICION / REQUIRES PROSECUTORIAL REVIEW / CONSISTENT WITH FRAUDULENT STRUCTURING"`.
- **Order Coercive Actions**: AI agents do not issue judicial arrest warrants, seizure orders, or unilateral bank freezes. All freezing payloads (`output/*_aoc.json`) and court dossiers (`output/*_dossier.pdf`) are generated strictly on explicit user request for review by authorized officers.
- **Fabricate or Backfill Evidence**: Never manufacture missing transactions, fill timestamp gaps with plausible dates, or guess missing account numbers or names. If missing, label explicitly as `"UNKNOWN"`.
- **Circumvent Legal Checks**: Do not advise on anti-forensics, laundering concealment, evasion of AOC freezes, or un-freezing frozen accounts without court order.
- **Biometric or Trait Discrimination**: Do not infer character, intent, or culpability from race, ethnicity, religion, or personal traits.

---

## 2. Multi-Tiered Human Review Levels (R1 - R5)

Before any investigative finding is deployed or submitted to external authorities, it must receive the designated level of human review:

- **Level R1 (Administrative Review)**:
  - Scope: File formatting, completeness, relative path citations, schema compliance.
  - Reviewer: Data ingestion specialist or lead AI operator.
- **Level R2 (Investigative Review)**:
  - Scope: Investigative logic, smurfing topology plausibility, counterparty classification accuracy, timeline consistency.
  - Reviewer: Law enforcement investigator (พนักงานสอบสวน / เจ้าหน้าที่สืบสวน ปอท. / บช.สอท.).
- **Level R3 (Technical & Mathematical Review)**:
  - Scope: MILP flow conservation proofs ($A \cdot x \approx T$), subset sum precision, fee tolerance bounds, graph cycle validity.
  - Reviewer: Financial forensic architect / data scientist.
- **Level R4 (Banking & Compliance Review)**:
  - Scope: Core banking code interpretations, interbank switch settlement rules (ITMX), clearing pool identification, AOC 1441 freeze protocols.
  - Reviewer: Bank fraud compliance officer / AML investigator.
- **Level R5 (Legal & Admissibility Review)**:
  - Scope: Admissibility under Thai Criminal Procedure Code Section 226, compliance with Electronic Transactions Act B.E. 2544, legality of subpoena requests under Section 132, proportionality of restitution claims under AMLA Section 49/1.
  - Reviewer: Supervisory investigator, legal counsel, or public prosecutor (พนักงานอัยการ).

---

## 3. Data Integrity & Chain of Custody Controls

- **Read-Only Ingestion**: Raw statements (`input/*.csv`, `input/*.xlsx`, `input/*.pdf`) are read-only; analysis operates exclusively on immutable parsed data models.
- **Cryptographic Hash Verification**: SHA-256 hashes are recalculated and verified before any report generation.
- **Workspace-Relative Paths**: Always cite files relative to the workspace root (`output/court_dossier.pdf`, `input/statement.csv`), never revealing local machine paths or absolute drives.
