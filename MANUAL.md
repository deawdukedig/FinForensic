# ⚡ คู่มือการใช้งาน FinForensic ฉบับเร่งด่วน (Quickstart Manual)
> **สำหรับ:** พนักงานสอบสวน, เจ้าหน้าที่ บช.สอท. (ตำรวจไซเบอร์), ศูนย์ AOC 1441, ปปง., ปอศ., DSI และนักวิเคราะห์เส้นทางการเงิน  
> **CLI Entrypoint:** `python -m harness.cli <command> [options]`

---

## 📑 สรุปคำสั่งด่วน (Command Quick-Reference Cheat Sheet)

| งานที่ต้องการทำ | คำสั่งหลัก (CLI Command) | ผลลัพธ์ที่ได้ (Output) |
| :--- | :--- | :--- |
| **1. แกะรอยเงินเหยื่อเฉพาะราย** | `python -m harness.cli trace-victim --victim "<ชื่อหรือเลขบัญชี>"` | ออก Markdown Report คู่กับ Dashboard HTML เสมอ |
| **2. สร้างคำสั่งอายัดฉุกเฉิน AOC 1441** | `python -m harness.cli aoc-freeze --statement <ไฟล์.csv>` | `output/aoc_freeze_request.json` |
| **3. สร้างสำนวนคดีส่งศาล (PDF ไทย)** | `python -m harness.cli export-pdf --statement <ไฟล์.csv>` | `output/court_dossier.pdf` |
| **4. สร้างแดชบอร์ด Interactive HTML** | `python -m harness.cli generate-dashboard --statement <ไฟล์.csv>` | `output/dashboard.html` |
| **5. แกะรอยเหยื่อครบวงจร (เพิ่ม PDF + AOC)** | `python -m harness.cli trace-victim --victim "<ชื่อ>" --output-pdf <ไฟล์.pdf> --output-aoc <ไฟล์.json>` | ออกทั้ง Report MD, Dashboard HTML, PDF, และ AOC JSON |
| **6. วิเคราะห์เครือข่ายม้า 5 แถว** | `python -m harness.cli analyze-multi-entity` | แผนผังเครือข่าย 5-Hop พร้อมออก MD และ HTML Dashboard |
| **7. ซักถามข้อมูลด้วยภาษาไทย (Copilot)** | `python -m harness.cli copilot --query "<คำถามภาษาไทย>"` | คำตอบวิเคราะห์ทันที |
| **8. ตรวจสอบแฮชและพยานหลักฐาน** | `python -m harness.cli audit-evidence --statement <ไฟล์.csv>` | ยืนยัน SHA-256 Provenance |

---

## 🎯 Case 1: แกะรอยเงินผู้เสียหายเฉพาะราย (Targeted Victim Tracing)

เมื่อมีผู้เสียหายมาแจ้งความ และต้องการทราบว่าเงินที่โอนเข้าบัญชีม้าแถวที่ 1 ถูกซอยและโอนต่อไปยังบัญชีใดบ้าง และต้องอายัดเงินเท่าใด:

### คำสั่งแบบรวดเร็ว (Default: แสดงผลบนหน้าจอ + บันทึก Markdown Report คู่กับ Dashboard HTML เสมอ):
```bash
python -m harness.cli trace-victim --statement input/statement.csv --victim "ภานุวัฒน์"
```
*(ระบบจะสร้างทั้ง `output/victim_panuwat_analysis.md` และ `output/victim_panuwat_dashboard.html` ให้ทันที)*

### คำสั่งแบบครบวงจร (ออกทั้ง PDF ส่งศาล + JSON ส่งศูนย์ AOC 1441 + หน้าเว็บ Dashboard):
```bash
python -m harness.cli trace-victim `
  --statement input/statement.csv `
  --victim "ภานุวัฒน์" `
  --case-id "CASE-2026-สอท-0820" `
  --officer "พ.ต.ต. วิทวัส นิติวงศ์" `
  --output-pdf output/victim_panuwat_dossier.pdf `
  --output-aoc output/victim_panuwat_aoc.json `
  --output-dashboard output/victim_panuwat_dashboard.html
```

#### สิ่งที่ระบบรายงาน:
1. **Victim Inflow Ledger:** ยอดเงินที่เหยื่อถูกหลอกโอนเข้ามา (เช่น ฿470,000.00)
2. **Top Dispersal Destinations:** บัญชีปลายทางที่เงินถูกกระจายออกไป พร้อมสัดส่วน (%) และยอดที่จัดสรร (Proportional Restitution Claim ตาม ป.วิ.อาญา ม.226 / ปปง. ม.49/1)
3. **Action Target:** แนะนำบัญชีเป้าหมายที่ต้องส่งอายัดทันที (`AOC_1441_FREEZE_URGENT`)

---

## 🚨 Case 2: ออกคำสั่งอายัดฉุกเฉินส่งศูนย์ AOC 1441 (Emergency Freezing)

เมื่อต้องการส่งคำขอระงับธุรกรรมทางการเงินและอายัดบัญชีม้าทุกแถวไปยังศูนย์ AOC 1441 ในรูปแบบ JSON มาตรฐาน:

```bash
python -m harness.cli aoc-freeze `
  --statement input/statement.csv `
  --case-id "CASE-2026-AOC-998" `
  --output output/aoc_freeze_request.json
```

- **ผลลัพธ์:** ไฟล์ `output/aoc_freeze_request.json` สำหรับส่งต่อไปยัง API ของศูนย์ AOC 1441 หรือหน่วยงานรับแจ้งเหตุ

---

## ⚖️ Case 3: สร้างแฟ้มสำนวนคดีส่งศาล (Court-Admissible Dossier PDF)

สร้างรายงานสำนวนคดีฉบับสมบูรณ์ พร้อมแนบเอกสารพยานหลักฐาน Exhibits A-D (ฝังฟอนต์ราชการไทย TH Sarabun New แท้):

```bash
python -m harness.cli export-pdf `
  --statement input/statement.csv `
  --case-id "ดำ.1122/2569" `
  --officer "พ.ต.ท. เอกลักษณ์ สืบสกุล" `
  --font "THSarabunNew" `
  --output output/court_dossier.pdf
```

> **หมายเหตุ:** สามารถเลือกฟอนต์ `--font THSarabunIT๙` หรือระบุเส้นทางไฟล์ `.ttf` ในเครื่องได้

---

## 📊 Case 4: สร้างแดชบอร์ด Interactive HTML เปิดดูผ่านเบราว์เซอร์

ต้องการดูภาพรวมกระแสเงินแบบ Visual Sankey Diagram, ไทม์ไลน์ธุรกรรม และตารางสืบค้น:

```bash
python -m harness.cli generate-dashboard `
  --statement input/statement.csv `
  --case-id "CASE-VISUAL-01" `
  --output output/dashboard.html
```

- หลังจากรันเสร็จ ดับเบิลคลิกเปิดไฟล์ `output/dashboard.html` ด้วย Chrome / Edge / Firefox ได้ทันที (รองรับ Responsive, ไม่ต้องต่ออินเทอร์เน็ต)

---

## 🌐 Case 5: วิเคราะห์เครือข่ายบัญชีม้าหลายระดับ (Multi-Entity 5-Hop Syndicate)

สำหรับคดีเครือข่ายองค์กรอาชญากรรมที่มีบัญชีม้าหลายแถว (Nodes & Edges):

### 1. วิเคราะห์ความเชื่อมโยงในเทอร์มินัล:
```bash
python -m harness.cli analyze-multi-entity `
  --nodes "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv" `
  --edges "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv"
```

### 2. สร้างสำนวนคดีเครือข่ายเป็น PDF และ Markdown:
```bash
python -m harness.cli export-multi-entity-dossier `
  --nodes "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv" `
  --edges "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv" `
  --output-pdf output/multi_entity_court_dossier.pdf `
  --output-md output/multi_entity_court_dossier.md
```

### 3. สร้างแดชบอร์ด Interactive 5-Hop Money Trail:
```bash
python -m harness.cli generate-multi-entity-dashboard `
  --nodes "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_nodes_entities.csv" `
  --edges "techdocs/Multi-Entity Graph & Money Trail Suite/forensic_edges_transactions.csv" `
  --output output/multi_entity_dashboard.html
```

---

## 💬 Case 6: ซักถามข้อมูลด้วยภาษาไทยผ่าน Forensic Copilot

เมื่อต้องการสอบถามข้อมูลธุรกรรมแบบเฉพาะเจาะจงโดยไม่ต้องเปิดดูทีละบรรทัด:

```bash
# ถามหายอดโอนเงินสูงสุด
python -m harness.cli copilot --statement input/statement.csv --query "ยอดเงินโอนออกก้อนใหญ่ที่สุดคือยอดใด โอนไปที่ใคร"

# ถามเกี่ยวกับผู้เสียหายเฉพาะราย
python -m harness.cli copilot --statement input/statement.csv --query "จ่าสิบตรี ภานุวัฒน์ โอนเงินเข้ามาเวลาใด และเงินถูกโอนต่อไปยังบัญชีใดบ้าง"

# ถามเกี่ยวกับบัญชีม้า
python -m harness.cli copilot --statement input/statement.csv --query "บัญชีปลายทางที่ได้รับเงินรวมมากที่สุดคือบัญชีใด"
```

---

## 🔍 Case 7: ตรวจสอบความถูกต้องทางนิติวิทยาศาสตร์และกฎหมาย (Audit & Compliance)

```bash
# 1. ตรวจสอบ SHA-256 Provenance และการอนุรักษ์กระแสเงิน (Flow Conservation)
python -m harness.cli audit-evidence --statement input/statement.csv

# 2. ตรวจสอบความเป็นกลางของสำนวน ไม่ชี้นำหรือปรักปรำเกินพยานหลักฐาน (Legal Neutrality)
python -m harness.cli verify-neutrality --target output/victim_panuwat_analysis.md

# 3. ตรวจสอบความสอดคล้องของโค้ดกับพิมพ์เขียวสถาปัตยกรรม (Spec Compliance)
python -m harness.cli verify-compliance
```

---

## 🛠️ พารามิเตอร์สำคัญสำหรับการปรับจูน (Tuning Flags)

| Flag | คำอธิบาย | ค่าเริ่มต้น | ตัวอย่างการใช้งาน |
| :--- | :--- | :--- | :--- |
| `--statement` | ตำแหน่งไฟล์ Statement (CSV) | `input/statement.csv` | `--statement C:/data/bank_statement.csv` |
| `--victim` | คำค้นหาชื่อ, เลขบัญชี, หรือนามสกุลของเหยื่อ | *(จำเป็น)* | `--victim "นิภาภัทร"` หรือ `--victim "x1002"` |
| `--tolerance` | ค่าความคลาดเคลื่อน Fee-Buffer Tolerance ($\pm\%$) | `0.05` (5%) | `--tolerance 0.08` (อนุญาตคลาดเคลื่อน 8%) |
| `--window-hours` | กรอบเวลาค้นหาการกระจายเงิน (ชั่วโมง) | `24.0` | `--window-hours 48.0` (ค้นหาธุรกรรมใน 48 ชม.) |
| `--case-id` | เลขที่คดี / เลขสำนวน | `CASE-2026-0820` | `--case-id "สอท-คดี-69/001"` |
| `--officer` | ชื่อและตำแหน่งพนักงานสอบสวน | *(พ.ต.ต. วิทวัส)* | `--officer "ร.ต.อ. สมเกียรติ มั่นคง"` |
| `--font` | ฟอนต์ภาษาไทยสำหรับ PDF | `THSarabunNew` | `--font "THSarabunIT๙"` |

---

## 📂 รูปแบบไฟล์ Statement ขาเข้าที่รองรับ (Supported Input Formats)

ระบบรองรับไฟล์ CSV จากธนาคารไทยชั้นนำ (Universal Statement Parser) โดยสามารถตรวจจับ Header ภาษาไทย/อังกฤษ ได้อัตโนมัติ:
- **ฟิลด์วันที่และเวลา:** `Date`, `Time`, `Transaction Date`, `วันที่`, `เวลา`
- **ฟิลด์รหัสรายการ:** `Code`, `Type`, `Description`, `รายละเอียด`, `ช่องทาง`
- **ฟิลด์จำนวนเงิน:** `Inflow`, `Outflow`, `Amount`, `XD`, `XW`, `ถอน/โอนออก`, `ฝาก/รับโอน`
- **ฟิลด์บัญชีต้นทาง/ปลายทาง:** `Account`, `Account Name`, `Target Account`, `ชื่อบัญชี`

หากไฟล์ CSV มีรูปแบบแตกต่าง ระบบ Universal Parser จะทำ Normalized Mapping ให้อัตโนมัติทันที
