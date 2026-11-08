---
name: forensic-findings-integrator
description: "Synthesize multi-source investigative findings across financial transaction ledgers, ATM CCTV footage timestamps, mobile banking IP logs, telecommunication cell tower records, and mule KYC profiles without manufacturing artificial certainty."
category: financial-forensics
risk: safe
metadata:
  phase: synthesis
  jurisdiction: thailand
---

# Multi-Source Forensic Findings Integrator

Synthesize independent forensic disciplines and evidence streams into a unified, source-attributed investigative matrix without manufacturing false cumulative certainty or papering over evidentiary gaps.

Before substantive integration, review the 8 discrete evidence states in `core-forensic-workflow.md` and the legal admissibility rules in `thai-financial-legal-layer.md`.

---

## 1. Intake of Independent Evidence Streams

Collect, verify, and index:
1. **Financial Ledger Stream (สายหลักฐานบัญชีการเงิน)**:
   - รายการเดินบัญชี (Bank Statements), ข้อมูลการจับคู่เส้นทางการเงิน MILP, บันทึกการโอนเงิน PromptPay.
2. **Surveillance & Physical Evidence Stream (สายหลักฐานภาพวงจรปิดและกายภาพ)**:
   - บันทึกภาพกล้องวงจรปิดตู้ ATM (CCTV Stills/Video), พิกัดสถานที่ตั้งตู้ ATM (GPS/Address), สลิปการกดเงินสดจริง.
3. **Network & Device Telemetry Stream (สายหลักฐานเครือข่ายและอุปกรณ์)**:
   - บันทึกการเข้าสู่ระบบ Mobile Banking (IP Address, Source Port, ISP, User-Agent, Device ID/UUID).
4. **Telecommunications CDR Stream (สายหลักฐานโทรคมนาคม)**:
   - บันทึกการใช้งานโทรศัพท์ (Call Detail Records), พิกัดเสาสัญญาณ (Cell Site Towers), ข้อมูลการลงทะเบียนซิมการ์ด (IMSI/IMEI).
5. **Subject & KYC Entity Stream (สายหลักฐานการพิสูจน์ตัวตนบุคคล)**:
   - ข้อมูลทะเบียนราษฎร (DOPA Linkage), ข้อมูลการเปิดบัญชีธนาคาร (e-KYC Facial Recognition logs), ประวัติอาชญากรรม.

---

## 2. Integration Method & Corroboration Engine

1. **Multi-Source Timestamp Synchronization & Clock Drift Calibration**:
   - ปรับเทียบเวลามาตรฐาน (NTP Standard Time: Asia/Bangkok UTC+7).
   - ตรวจหาและบันทึกค่าความคลาดเคลื่อนของเวลา (Clock Drift) ระหว่าง Server ของธนาคาร, กล้อง CCTV ประจำตู้ ATM, และระบบบันทึก Log ของค่ายมือถือ.
2. **Unified Event Chronology Matrix**:
   - สร้างตารางเหตุการณ์เรียงลำดับเวลา (Sequence of Events) โดยแสดงพยานหลักฐานที่สนับสนุนเหตุการณ์นั้นๆ จากแต่ละสายงาน:
     | ลำดับ | วันเวลา (UTC+7) | กิจกรรมทางการเงิน | ภาพ CCTV / พิกัดตู้ ATM | ข้อมูล IP / อุปกรณ์ | ข้อมูลโทรคมนาคม / เสาสัญญาณ | สถานะพยานหลักฐาน |
     | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
3. **Cross-Stream Corroboration Mapping**:
   - เชื่อมโยงธุรกรรมการเงินเข้ากับตัวบุคคลที่ปรากฏ:
     - *ตัวอย่าง*: ธุรกรรมถอนเงินสด 20,000 บาท เวลา 14:02:18 สอดคล้องกับภาพ CCTV ตู้ ATM สาขา A เวลา 14:02:22 และสัญญาณโทรศัพท์หมายเลขของผู้ต้องสงสัยเชื่อมต่อกับเสาสัญญาณบริเวณตู้ ATM เวลา 14:01-14:05.
4. **Conflict & Discrepancy Isolation**:
   - หากพยานหลักฐานขัดแย้งกัน (เช่น บัญชีมีการโอนเงินที่กรุงเทพฯ แต่เสาสัญญาณโทรศัพท์และภาพ CCTV ปรากฏว่าเจ้าของบัญชีอยู่ต่างจังหวัดหรือแนวชายแดน):
     - **ห้ามพยายามแต่งเรื่องให้กลมกลืนโดยเด็ดขาด** (Do not force narrative fit).
     - ให้บันทึกเป็นประเด็นความขัดแย้งเชิงนิติวิทยาศาสตร์ (Evidentiary Conflict) ซึ่งชี้ว่าอาจมีการเช่า/ซื้อขายบัญชีม้าให้ขบวนการควบคุมทางไกล (Remote Mule Account Control via Proxy/VPN).

---

## 3. Deliverables

1. **Integrated Master Chronology Matrix**: ตารางลำดับเหตุการณ์ร่วมหลายสายงานพร้อมแหล่งอ้างอิงรายแถว.
2. **Corroboration & Independence Assessment Ledger**: บันทึกการประเมินน้ำหนักพยานหลักฐานที่ไม่พึ่งพากัน.
3. **Evidentiary Conflict & Ambiguity Register**: รายการข้อเท็จจริงที่ยังไม่ลงรอยกัน พร้อมประเด็นที่ต้องสืบสวนเพิ่มเติม.
4. **Specialist Re-Examination Brief**: หัวข้อประเด็นส่งกลับให้ผู้เชี่ยวชาญเฉพาะทาง (เช่น ผู้ตรวจพิสูจน์ภาพ หรือผู้เชี่ยวชาญเครือข่าย) ทำการทดสอบเจาะจง.

---

## 4. Hard Boundaries

- **ห้ามสร้างความแน่นอนเทียม (No Artificial Cumulative Certainty)**: พยานหลักฐานที่อ่อนหลายชิ้นรวมกัน ไม่ได้กลายเป็นพยานหลักฐานที่แน่นอนชี้ขาดได้โดยอัตโนมัติ.
- **ห้ามชี้ขาดเจตนาของผู้ต้องสงสัย**: การที่บัญชีมีเงินผ่านและกดเงินสดออก ไม่เท่ากับการยืนยันเจตนาทุจริตในชั้น AI ต้องให้ศาลหรือพนักงานสอบสวนเป็นผู้ชั่งน้ำหนักพยานหลักฐานตาม ป.วิ.อ. ม.226.
- **ใช้ Relative Paths เท่านั้น**: อ้างอิงไฟล์ผลลัพธ์และพยานหลักฐานด้วย Relative Path เช่น `output/...` เสมอ.
