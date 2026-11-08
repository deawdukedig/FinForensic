---
name: digital-evidence-acquisition-planner
description: "Prepare lawful, tool-neutral digital evidence preservation and acquisition plans for financial institutions, payment gateways, ad platforms, crypto VASPs, and telecom operators under Thai CPC Section 132, Cyber Emergency Decree B.E. 2566, and Computer Crime Act B.E. 2550."
category: financial-forensics
risk: safe
metadata:
  phase: planning
  jurisdiction: thailand
---

# Digital Evidence Acquisition Planner

Design lawful, structured, and auditable evidence acquisition plans to gather financial records, clearing pool data, ad campaign identities, and telecommunications logs without legal overreach or procedural contamination.

Before substantive work, consult the statutory authorities in `thai-financial-legal-layer.md` and follow the ISO 21043 lifecycle in `core-forensic-workflow.md`.

---

## 1. Intake & Scope Definition

Identify and record:
- Investigated Case ID, victim details, and reported loss magnitude.
- Dispersal targets identified during preliminary flow matching (commercial banks, payment gateways, ad platforms, VASPs).
- Current procedural phase (Emergency 72-hour hold, formal investigation under CPC, or asset forfeiture under AMLA).
- Specific examination questions (e.g. "Identify beneficiary behind Merchant ID", "Preserve CCTV footage at ATM location", "Freeze destination VASP deposit address").

---

## 2. Multi-Target Acquisition Directives

The acquisition planner routes evidence requests across 5 distinct target sectors:

### A. สถาบันการเงินและธนาคารพาณิชย์ (Commercial Banks)
- **Legal Authority**: ประมวลกฎหมายวิธีพิจารณาความอาญา ม.132 ร่วมกับ พ.ร.ก. มาตรการป้องกันและปราบปรามอาชญากรรมทางเทคโนโลยี พ.ศ. 2566 ม.4/ม.6.
- **Requested Material**:
  - รายการเดินบัญชีฉบับทางการ (Official Bank Statement) พร้อมรับรองความถูกต้องตาม พ.ร.บ.ธุรกรรมอิเล็กทรอนิกส์ ม.11.
  - ข้อมูลเปิดบัญชี (KYC / Customer Due Diligence) รวมถึงภาพถ่ายใบหน้าขณะเปิดบัญชี, สำเนาบัตรประชาชน, หมายเลขโทรศัพท์ และ Device ID.
  - บันทึกการเข้าสู่ระบบ Mobile Banking (IP Address, Port, Timestamp, Geolocation) ตลอดช่วงเวลาเกิดเหตุ.
  - ภาพบันทึกจากกล้องวงจรปิด (CCTV) บริเวณตู้ ATM หรือสาขาที่มีการถอนเงินสด.

### B. ผู้ให้บริการรับชำระเงินและ Payment Gateways (Corporate Clearing Pools)
- **Target Entities**: Omise, 2C2P, GB Prime Pay, KGP (Kasikorn Global Payment), Ksher, TrueMoney Merchant.
- **Legal Authority**: ป.วิ.อ. ม.132 (หมายเรียกพยานเอกสารและข้อมูลจากนิติบุคคล) **ห้ามใช้คำสั่งอายัดบัญชีค้าปลีก AOC 1441 กับบัญชี Clearing Pool ของ Payment Gateway**.
- **Requested Material**:
  - ชื่อร้านค้า (Merchant Name), รหัสร้านค้า (Merchant ID), และเลขจดทะเบียนนิติบุคคลหรือบุคคลธรรมดาที่เป็นเจ้าของร้านค้า.
  - ข้อมูลบัญชีธนาคารปลายทางที่ร้านค้ารับเงินโอนจากการ Settlement.
  - รายละเอียดสินค้า/บริการ และบันทึกคำสั่งซื้อ (Order Logs) ที่ตรงกับยอดเงินของผู้เสียหาย.

### C. แพลตฟอร์มโฆษณาออนไลน์ระดับโลก (Global Tech Ad Platforms)
- **Target Entities**: Meta (Facebook/Instagram Ads), Google (YouTube/Search Ads), TikTok Ads, LINE Ads.
- **Legal Authority**: พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ. 2550 ม.18 และหนังสือขอความร่วมมือพยานหลักฐานระหว่างประเทศ (MLAT / Direct Law Enforcement Disclosure Requests).
- **Requested Material**:
  - ข้อมูล Ad Account ID, Page ID, และบัญชีผู้ดูแล (Admin User Profile/Email).
  - ข้อมูลวิธีการชำระเงินค่าโฆษณา (Credit Card BIN, Virtual Card, Bank Transfer).
  - บันทึก IP Address และหมายเลขโทรศัพท์ที่ใช้ในการลงทะเบียนและยิงแคมเปญโฆษณาหลอกลวง.
  - คำร้องขอระงับการเผยแพร่แคมเปญโฆษณาและระงับบัญชีโฆษณาในทันที.

### D. ผู้ประกอบธุรกิจสินทรัพย์ดิจิทัลและศูนย์ซื้อขายคริปโต (VASP & Crypto Exchanges)
- **Target Entities**: Bitkub, Binance TH by Gulf Innova, Orbix, Upbit Thailand, Satang Pro.
- **Legal Authority**: พ.ร.บ.ป้องกันและปราบปรามการฟอกเงิน พ.ศ. 2542 ม.48/ม.57 ร่วมกับกฎกระทรวงว่าด้วยการตรวจสอบข้อเท็จจริงเกี่ยวกับลูกค้า (CDD/KYC Travel Rule).
- **Requested Material**:
  - ประวัติการฝาก-ถอนคริปโต (TxHash, Destination Blockchain Address, Network Chain).
  - ข้อมูล KYC ของเจ้าของกระเป๋าเงินบน Exchange และข้อมูลบัญชีธนาคารผูกมัดสำหรับการซื้อขาย P2P / Fiat On-Off Ramp.
  - คำสั่งระงับการโอนเหรียญ (Asset Hold) ในกระเป๋าเงินเป้าหมาย.

### E. ผู้ให้บริการโทรคมนาคมและอินเทอร์เน็ต (Telco & ISP Operators)
- **Legal Authority**: พ.ร.บ.คอมพิวเตอร์ พ.ศ. 2550 ม.18(2)(3).
- **Requested Material**:
  - ข้อมูลผู้ครอบครองเลขหมายโทรศัพท์ (SIM Registration) และประวัติการเติมเงิน/ชำระค่าบริการ.
  - ข้อมูล Log การใช้งานอินเทอร์เน็ตที่ตรงกับ IP Address และ Port ที่ใช้ทำธุรกรรม Mobile Banking.
  - ข้อมูลตำแหน่งเสาสัญญาณ (Cell Site / Tower Geolocation) ขณะเกิดธุรกรรม.

---

## 3. Deliverables

1. **Subpoena & Acquisition Target Register**: ตารางจำแนกเป้าหมายการออกหมายเรียกพยานเอกสารและหนังสือประสานงาน.
2. **Statutory Justification Brief**: บันทึกข้อกฎหมายรองรับอำนาจหน้าที่ของพนักงานสอบสวนแยกตามประเภทนิติบุคคล.
3. **Evidence Preservation Order Drafts**: ร่างหนังสือขออายัดพยานหลักฐานดิจิทัลเร่งด่วนเพื่อป้องกันการลบทำลาย Log (Preservation Letter).
4. **Acquisition Log & Integrity Tracker**: บันทึกการติดตามความคืบหน้าการส่งมอบเอกสาร พร้อมช่องทางตรวจรับค่า SHA-256.

---

## 4. Hard Boundaries

- ห้ามส่งคำสั่งอายัดบัญชีธนาคาร (Freeze) ไปยังบัญชี Clearing Pool ของ Payment Gateway หรือ Platform โฆษณา โดยเด็ดขาด ให้ใช้เฉพาะหมายเรียก ม.132 เพื่อไม่ให้กระทบระบบการชำระเงินของส่วนรวม.
- ห้ามวางแผนการเข้าถึงข้อมูลโดยมิชอบ เช่น การดักรับข้อมูลลับโดยไม่มีหมายศาล หรือการใช้วิธีการแฮก/เจาะระบบ.
- ใช้ Workspace-Relative Paths เสมอเมื่ออ้างอิงเอกสารหรือไฟล์หลักฐาน (`output/...`, `input/...`).
