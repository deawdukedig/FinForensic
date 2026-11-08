---
name: expert-report-quality-checker
description: "Quality-check financial forensic analysis reports and expert dossiers for methodological completeness, mathematical flow conservation, neutrality standards, XAI proof ledgers, and court admissibility under Thai law."
category: quality-assurance
risk: safe
metadata:
  phase: review
  jurisdiction: thailand
---

# Financial Forensic Expert Report Quality Checker

Execute comprehensive technical and evidentiary audits of financial forensic reports, victim analysis dossiers, and investigative summaries before they are signed by experts or presented in judicial proceedings.

Before substantive audit, review the ISO 21043 reporting standards in `core-forensic-workflow.md` and the legal admissibility rules under Thai Criminal Procedure Code Section 226 in `thai-financial-legal-layer.md`.

---

## 1. Audit Checkpoints & Invariants

The Quality Checker rigorously evaluates 7 mandatory dimensions:

### 1. Mathematical Conservation & MILP Proofs
- [ ] มีสมการและข้อจำกัดเชิงเส้นรองรับผลการจับคู่เส้นทางการเงินชัดเจน ($A \cdot x \approx T$).
- [ ] ยอดเงินรวมฝั่งกระจายออก (Dispersal) ไม่เกินยอดเงินเข้าของผู้เสียหาย (Flow Conservation Invariant).
- [ ] ระบุค่าความคลาดเคลื่อน (Tolerance Buffer / Fees) ไว้อย่างโปร่งใส ไม่ใช้คะแนน Heuristic มโนลอยๆ ที่ตรวจสอบที่มาไม่ได้.

### 2. Neutrality Principle (หลักความเป็นกลางทางนิติวิทยาศาสตร์)
- [ ] ไม่ใช้คำชี้ขาดความผิดทางอาญา เช่น "มีความผิดฐานฟอกเงิน", "เป็นคนร้ายแน่นอน", "ต้องถูกตัดสินจำคุก".
- [ ] ใช้ถ้อยคำทางนิติวิทยาศาสตร์ที่ถูกต้อง เช่น `"พบความผิดปกติในระดับสูง (HIGH SUSPICION)"`, `"มีพฤติการณ์สอดคล้องกับการกระจายยอดบัญชีม้า (Structuring/Smurfing)"`, `"ต้องส่งเรื่องให้พนักงานสอบสวนตรวจสอบข้อเท็จจริงเพิ่มเติม"`.

### 3. Dual Output Persistence Protocol (Iron Law)
- [ ] ตรวจสอบว่ามีไฟล์บันทึกผลลัพธ์ครบทั้ง 2 รูปแบบเสมอ:
  1. Structured Markdown Report ใน `output/` (เช่น `output/victim_<name_slug>_analysis.md`, `output/<statement_name>_analysis.md`)
  2. Interactive Single-Page HTML Dashboard ใน `output/` (เช่น `output/victim_<name_slug>_dashboard.html`, `output/<statement_name>_dashboard.html`)
- [ ] ตรวจสอบการตั้งชื่อแดชบอร์ดภาพรวม: ต้องใช้ `output/<statement_name>_dashboard.html` ตามชื่อไฟล์ Statement เสมอ ห้ามใช้ `output/dashboard.html`.

### 4. On-Demand Legal Artifact Protocol (Strict Opt-In)
- [ ] หากผู้ใช้ **ไม่ได้สั่ง** ให้สร้างสำนวนศาลหรือส่งคำสั่งอายัด:
  - ตรวจสอบว่า **ไม่มี** การสร้างไฟล์ `output/*_dossier.pdf` หรือ `output/*_aoc.json` โดยพลการ.
  - ตรวจสอบว่า **ไม่มี** การอ้างในข้อความแชทว่าได้จัดทำไฟล์ PDF หรือ JSON อายัดเรียบร้อยแล้ว.
- [ ] หากผู้ใช้ **มีคำสั่งชัดเจน** (เช่น "pdf", "dossier", "aoc", "อายัดฉุกเฉิน"):
  - ตรวจสอบความสมบูรณ์ของโครงสร้างเอกสารตามมาตรฐาน Exhibits A-D.

### 5. Relative Path Citation (Iron Law)
- [ ] ตรวจสอบการอ้างอิงไฟล์ทุกตำแหน่งในรายงาน:
  - ต้องขึ้นต้นด้วย Relative Path เท่านั้น (เช่น `output/...`, `input/...`, `src/...`).
  - **ห้ามปรากฏ Absolute Path** (`C:\...`, `/home/...`) ในเนื้อหารายงานหรือผลลัพธ์ที่นำเสนอเด็ดขาด.

### 6. PDPA & Data Privacy Masking
- [ ] ตรวจสอบการปิดบังข้อมูล (Masking) บัญชีคู่กรณีบุคคลภายนอกที่ไม่เกี่ยวข้อง:
  - เลขบัญชีปิดบัง 4-6 หลักกลาง (เช่น `152-x-xxx04-1`).
  - ชื่อบุคคลทั่วไปแสดงเฉพาะชื่อต้นหรือตัวย่อ (เช่น `นาย สม*** ม***`).
  - ยกเว้นบัญชีนิติบุคคลสาธารณะหรือบัญชีที่ถูกแจ้งอายัด AOC อย่างเป็นทางการ.

### 7. Actionable Directives by Target Category
- [ ] แยกแยะมาตรการอย่างถูกต้อง:
  - บัญชีม้าบุคคลธรรมดา -> `AOC 1441 อายัดด่วน`
  - บัญชี Payment Gateway / แพลตฟอร์มโฆษณา -> `หมายเรียกพยานเอกสาร ม.132` (ห้ามสั่งอายัดบัญชี Clearing Pool)
  - รายการถอนเงินสดตู้ ATM -> `ขอภาพ CCTV และพิกัดตู้ ATM`
  - ศูนย์ซื้อขายสินทรัพย์ดิจิทัล -> `ขออายัดกระเป๋าเงิน VASP ตาม พ.ร.บ.ฟอกเงิน ม.48/57`

---

## 2. Deliverables

1. **Expert Report QA Audit Checklist**: ตารางประเมินผลผ่าน/ไม่ผ่านในแต่ละมิติ.
2. **Discrepancy & Hallucination Register**: รายการข้อความที่ขัดต่อหลักความเป็นกลางหรือพบค่าที่ไม่สอดคล้องกัน.
3. **Corrective Remediation Directives**: คำแนะนำการปรับปรุงแก้ไขสำนวนรายงานก่อนเสนอหัวหน้าพนักงานสอบสวนหรือผู้เชี่ยวชาญลงนาม.

Label results: **"Forensic Quality Assurance Audit. Not an Admissibility Ruling."**
