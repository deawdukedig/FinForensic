---
name: questioned-bank-document-coordinator
description: "Coordinate forensic verification of bank statements, payment slips, QR payloads, and transaction receipts for forgery, digital tampering, font inconsistency, and mathematical running-balance discrepancies."
category: financial-forensics
risk: safe
metadata:
  phase: specialist
  jurisdiction: thailand
---

# Questioned Bank Document & Payment Slip Coordinator

Establish rigorous forensic verification workflows to detect manipulated bank statements, fraudulent payment slips (สลิปปลอม), QR payload spoofing, and running balance calculation anomalies before evidence is relied upon in court or investigative decisions.

Before substantive work, review the legal standards under Thai Criminal Procedure Code Section 226 and Electronic Transactions Act B.E. 2544 Section 11.

---

## 1. Intake Requirements

Obtain and inventory:
- Questioned document files (Original PDF, scanned image, screenshot, physical printout).
- Digital metadata (creation date, modification date, authoring software, PDF producer metadata).
- Comparison standards:
  - Genuine bank statement templates from the same financial institution and period.
  - Known authentic transaction reference formats and font sets.
  - Interbank clearing switch logs (ITMX) or official bank counter-statements.
- Specific investigative questions (e.g. "Is the transfer slip genuine?", "Has the balance column in the PDF been edited?", "Does the QR code match the transaction details?").

---

## 2. Core Forensic Examination Methods

### A. การตรวจสอบสลิปโอนเงิน (Payment Slip Verification)
1. **QR Code Payload Extraction & Decoding**:
   - ถอดรหัสข้อมูล PromptPay EMVCo QR Code บนสลิป:
     - Sending Bank Code (เช่น 004 KBANK, 014 SCB, 025 BAY).
     - Transaction Reference ID (ความยาวและโครงสร้างรหัสเฉพาะของแต่ละธนาคาร).
     - Recipient Account & Amount.
   - นำค่าที่ถอดรหัสได้ไปเทียบเคียงกับข้อความที่พิมพ์บนภาพสลิป หากไม่ตรงกัน สันนิษฐานว่ามีการดัดแปลงภาพ (Altered Slip).
2. **Visual & Artifact Tampering Analysis**:
   - ตรวจสอบความสม่ำเสมอของแบบอักษร (Font Consistency): ขนาด, ระยะห่างระหว่างตัวอักษร (Kerning), ความหนาบาง, และรอยหยัก (Anti-aliasing artifacts).
   - ตรวจสอบการซ้อนทับของเลเยอร์ภาพ (Error Level Analysis - ELA) บริเวณชื่อบัญชี, วันเวลา, และจำนวนเงิน เพื่อหาร่องรอยการตัดแปะ (Copy-Paste Forgery).
3. **Contemporaneity Cross-Check**:
   - นำวันเวลาและรหัสอ้างอิงบนสลิปไปตรวจสอบเทียบเคียงกับรายการเดินบัญชี (Statement) ของธนาคารผู้รับเงิน หากมียอดเข้าจริงในเวลาตรงกัน จึงจะถือว่าธุรกรรมเกิดขึ้นจริง.

### B. การตรวจสอบรายการเดินบัญชีปลอมแปลง (Altered Bank Statement Verification)
1. **Mathematical Running-Balance Conservation Audit (สมการคงเหลือทางคณิตศาสตร์)**:
   - ตรวจสอบสมการความสมดุลในทุกแถวธุรกรรม:
     $$\text{Balance}_t = \text{Balance}_{t-1} + \text{Inflow}_t - \text{Outflow}_t$$
   - หากผลลัพธ์ไม่ตรงกับตัวเลขในช่องยอดคงเหลือ แม้เพียงจุดทศนิยมเดียว สันนิษฐานว่าเอกสารดังกล่าวผ่านการแก้ไขตัวเลขหรือลบแถวรายการธุรกรรมออก.
2. **PDF Internal Structure & Metadata Analysis**:
   - ตรวจสอบค่า PDF Producer, ModDate, และ XMP Metadata ว่าผ่านโปรแกรมแก้ไขเอกสาร (เช่น Adobe Photoshop, Canva, PDF Editor) หรือไม่.
   - ตรวจสอบ Embedded Fonts และ Text Stream Object ว่ามีการแยก Object ของตัวเลขในตารางหรือไม่.
3. **Transaction Density & Numbering Sequence**:
   - ตรวจสอบลำดับเลขที่อ้างอิง (Sequence Number) และช่วงเวลาระหว่างธุรกรรม เพื่อตรวจหาการแทรกแถวรายการที่ไม่มีอยู่จริง.

---

## 3. Deliverables

1. **Document Authenticity Assessment Worksheet**: ตารางวิเคราะห์เปรียบเทียบระหว่างเอกสารต้องสงสัยและเอกสารมาตรฐาน.
2. **Mathematical Balance Reconciliation Ledger**: บันทึกการคำนวณพิสูจน์ความสมดุลของยอดเงินในทุกแถวธุรกรรมพร้อมระบุจุดที่พบข้อผิดพลาด.
3. **Tampering Anomaly & Artifact Register**: รายงานระบุจุดพิรุธพร้อมภาพขยายเปรียบเทียบพิกัดจุดที่ถูกดัดแปลง.
4. **Forensic Submission Brief for Central Police Forensic Science (พฐ. / สพฐ.)**: เอกสารสรุปข้อสังเกตและประเด็นคำถามเพื่อส่งต่อกลุ่มงานตรวจพิสูจน์เอกสารและพยานหลักฐานดิจิทัล สำนักงานพิสูจน์หลักฐานตำรวจ.

---

## 4. Hard Boundaries

- ห้ามออกใบรับรองชี้ขาดความเป็นเอกสารแท้หรือเท็จโดยเด็ดขาด การสรุปผลต้องระบุเป็น **"รายงานข้อตรวจพบเบื้องต้นเชิงเทคนิค (Technical Findings)"** เพื่อให้ผู้เชี่ยวชาญลายมือชื่อและเอกสารทางนิติวิทยาศาสตร์เป็นผู้ลงนามรับรอง.
- ห้ามดัดแปลงไฟล์เอกสารต้นฉบับ; ทุกการทดสอบต้องทำบนสำเนาที่ได้จากการ Verify ค่า SHA-256 แล้วเท่านั้น.
- อ้างอิงไฟล์พยานหลักฐานด้วย Relative Paths เสมอ (`output/...`, `input/...`).
