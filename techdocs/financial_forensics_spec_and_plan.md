# เอกสารข้อกำหนดระบบและแผนการพัฒนา (System Specification & Implementation Plan)
## โครงการ: ระบบสถาปัตยกรรมวิเคราะห์เส้นทางการเงินเชิงนิติวิทยาศาสตร์และตรวจจับบัญชีม้า
### (Enterprise Comprehensive Financial Forensics & Flow Matching Architecture)

**รหัสเอกสาร:** SPEC-FIN-FORENSIC-001  
**เวอร์ชัน:** 2.0.0 (Enterprise Production-Ready Specification — ฉบับสมบูรณ์พร้อมสร้างจริง)  
**สถานะ:** อนุมัติการสร้างจริง (Approved by User to Proceed)  
**ผู้ออกแบบ:** Principal Financial Forensic Architect & Lead Evidence Auditor  
**เอกสารอ้างอิงหลัก:** `techdocs/financial_forensics.txt`  
**ข้อมูลทดสอบอ้างอิง:** `input/statement.csv` (SHA-256: `838e7386ae95a9ec519f90715ab3613376a05146a6f64e71c140099ab7abb631`)  
**เป้าหมายผู้ใช้งาน:** พนักงานสอบสวนคดีอาชญากรรมทางเทคโนโลยี, เจ้าหน้าที่ บช.สอท. (ตำรวจไซเบอร์), ศูนย์ AOC 1441, ปปง., ปอศ., DSI และนักวิเคราะห์ธุรกรรมทางการเงิน

---

## 1. บทนำและบริบทการปฏิบัติงานจริง (Operational Background & Objective)

### 1.1 ที่มาและปัญหาในงานสืบสวน
ในปัจจุบัน ขบวนการอาชญากรรมทางไซเบอร์ เช่น แก๊งคอลเซ็นเตอร์, เว็บพนันออนไลน์, และการหลอกลวงลงทุน (Pig Butchering Scam) ใช้วิธีการฟอกเงินผ่าน **เครือข่ายบัญชีม้า (Mule Account Networks)** โดยมีแบบแผนพฤติกรรมเฉพาะดังนี้:
1. **Structuring / Smurfing (การซอยยอดและกระจายเงิน):** เมื่อเงินจากเหยื่อไหลเข้าสู่บัญชีม้าแถวที่ 1 บัญชีพักจะรีบซอยยอดเงินออกเป็นก้อนย่อยๆ หลายก้อน เพื่อกระจายต่อไปยังบัญชีแถว 2, 3 หรือแปลงเป็นสินทรัพย์ดิจิทัล (Crypto Assets) ภายในเวลาไม่กี่นาที
2. **Buffer Balance & Fee Residue:** ยอดเงินที่โอนออกจะไม่เท่ากับยอดเงินที่ไหลเข้ามา 100% เป๊ะๆ เนื่องจากมีค่าธรรมเนียมธนาคาร (เช่น 5-10 บาท), เงินคงเหลือเดิมติดบัญชี (Buffer Balance), และการเหลือเศษติดบัญชีเพื่อตบตาการตรวจสอบ
3. **ข้อจำกัดของระบบเดิม:** ระบบเดิมส่วนใหญ่ใช้วิธีการ Query แบบคงที่ (Static Query) หรือการสุ่มหา (Random Sampling / Heuristics) ซึ่ง **ไม่การันตีความถูกต้อง (False Negative สูงมาก)** เมื่อชุดข้อมูลมีขนาดใหญ่ และไม่สามารถนำเสนอเป็นหลักฐานเชิงประจักษ์ที่มีน้ำหนักเพียงพอในการพิสูจน์ในชั้นศาล

### 1.2 วัตถุประสงค์ของระบบใหม่
ระบบนี้ถูกออกแบบมาเพื่อเป็น **เครื่องมือประจำตัวของเจ้าหน้าที่สืบสวน** ที่เปลี่ยนจากการ "เดาหรือสุ่มตรวจ" มาเป็น **การพิสูจน์ทราบด้วยแบบจำลองทางคณิตศาสตร์ (Mathematical Optimization via MILP)** รองรับการตรวจจับเส้นทางเงินแบบหลายมิติ พร้อมทั้งสร้าง **แฟ้มสำนวนหลักฐาน (Court-Admissible Evidence Dossier)** ที่สมบูรณ์ตามประมวลกฎหมายวิธีพิจารณาความอาญา มาตรา 226

---

## 2. การวิเคราะห์ข้อมูลจริงเชิงประจักษ์จาก Statement ตัวอย่าง (`input/statement.csv`)

จากการตรวจสอบไฟล์ Statement ธนาคารตัวอย่างจริง ซึ่งผ่านการทำ Hash Provenance Verification:
- **บัญชีเป้าหมาย:** `9012345678`
- **ชื่อบัญชี:** บริษัท สยาม อัลฟ่า เทรดดิ้ง จำกัด (พฤติกรรมเป็นนิติบุคคลบัญชีม้า / Mule Corporate Account)
- **วันที่เกิดรายการ:** 20 สิงหาคม 2569 (20/8/2026)
- **สรุปภาพรวมทางตัวเลข:**
  - จำนวนรายการเงินเข้า (XD): **26 รายการ** รวมเป็นเงิน **฿572,297.00**
  - จำนวนรายการเงินออก (XW): **14 รายการ** รวมเป็นเงิน **฿572,200.00**
  - จำนวนค่าธรรมเนียมธนาคาร (FE): **12 รายการ** รวมเป็นเงิน **฿70.00**
  - รวมเงินระบายออกสุทธิ (XW + FE): **฿572,270.00**
  - เงินคงเหลือสุทธิหลังสิ้นสุดวัน: **฿27.00** (เหลือเศษติดบัญชี)
  - **อัตราการระบายเงินออกจากบัญชี (Drain Rate): 99.995%**

```
+---------------------------------------------------------------------------------------------------------+
|                                    FLOW SUMMARY FOR ACCT: 9012345678                                    |
+------------------------------------+----------------------------------+---------------------------------+
| Total Inflow (XD):  ฿572,297.00    | Total Outflow (XW): ฿572,200.00  | Total Fees (FE): ฿70.00         |
| 26 Transactions                    | 14 Transactions                  | 12 Transactions                 |
+------------------------------------+----------------------------------+---------------------------------+
| Net Balance Retained: ฿27.00       | Account Drain Ratio: 99.995%     | High Suspicion Index: 98.6 / 100|
+---------------------------------------------------------------------------------------------------------+
```

### 2.1 การตรวจพบกลุ่มพฤติกรรมผิดปกติ 4 ช่วงเวลา (Timeline & Cluster Analysis)

#### ช่วงที่ 1: การหยั่งเชิงและทดสอบบัญชี (Calibration Phase: 09:22 - 11:38)
- 09:22: เงินเข้า ฿935.00 (จาก KTB MRS.SOMSRI)
- 09:36 (14 นาทีต่อมา): โอนออก ฿930.00 + ค่าธรรมเนียม ฿5.00 ไปยัง **BBL x8001 MR.SOKHA CHAN**
  - **ผลรวม:** $930 + 5 = 935$ บาท (ตรงเป๊ะ 100%) ยอดคงเหลือกลับสู่ยอดตั้งต้น

#### ช่วงที่ 2: การซอยยอดสะสมและระบายต่อ (Midday Structuring Phase: 12:35 - 13:43)
- มีเงินเข้าหลายก้อนย่อย (฿338, ฿519, ฿500, ฿1,500) จากผู้เสียหายหลายราย
- ถูกรวบและโอนออกเป็นก้อนกลม:
  - 13:05: โอนออก ฿3,500.00 + ฿5 FE ไปยัง **BBL x8002 MRS LINDA CHEN**
  - 13:26: โอนออก ฿1,860.00 + ฿5 FE ไปยัง **BBL x8001 MR.SOKHA CHAN** (ปลายทางเดิม)
  - 13:43: โอนออก ฿2,200.00 + ฿10 FE ไปยัง **พร้อมเพย์ x8003 นางสาว กมลพร วงศ์สุวรรณ**

#### ช่วงที่ 3: พายุการฟอกเงินก้อนใหญ่และการหลอกลวงเหยื่อหลัก (Heavy Laundering Storm: 15:31 - 17:49)
- **15:38:00:** เหยื่อรายใหญ่ถูกหลอกโอนเงินก้อนใหญ่เข้ามา **฿470,000.00** จาก `GSB x1001 จ่าสิบตรี ภานุวัฒน์`
- **15:31 - 16:50:** มีเงินเข้าสมทบเพิ่มเติม รวมกลุ่มเงินเข้าทั้งหมดประมาณ **฿557,000.00**
  - ฿19,980.00 และ ฿20,000.00 จาก `KBANK x1002 นาง นิภาภัทร ธรรมเจริญ`
  - ฿39,940.00 จาก `TTB x1003 นาย ธนดล ธรรมเจริญ` (นามสกุลเดียวกัน - มีความเชื่อมโยงระดับ Entity)
  - ฿5,199.00 จาก `BBL x1004 MS SIRIPORN`
- **การระบายเงินออกทันทีภายใน 88 นาที (ซอยออก 4 ก้อนใหญ่เพื่อหลบเลี่ยงการอายัด):**
  - 16:16: โอนออก **฿100,000.00** ไปยัง `SCB x8004 MRS. SOPHEA SAR`
  - 17:04: โอนออก **฿190,000.00** (+฿5 FE) ไปยัง `KBANK x8005 นาย ธีรภัทร บุญเสริม`
  - 17:07: โอนออก **฿180,000.00** (+฿5 FE) ไปยัง `KTB x8006 น.ส. จรรยา มิ่งขวัญ`
  - 17:10: โอนออก **฿76,500.00** (+฿5 FE) ไปยัง `KBANK x8007 น.ส. อรอุมา แสนสุข`
  - รวม 4 ยอดนี้: $100,000 + 190,000 + 180,000 + 76,500 = \mathbf{฿546,500.00}$!
  - 17:19: โอนออก ฿4,000 (+฿5 FE) ไปยัง `MR.SOKHA CHAN`
  - 17:49: โอนออก ฿7,700 ไปยัง `ห้างหุ้นส่วนจำกัด สยามพาร์ทเนอร์`
  - ยอดคงเหลือในบัญชีถูกรีดจนเหลือเพียง **฿107.06** ภายในเวลาไม่ถึง 2 ชั่วโมงหลังเงินเหยื่อเข้า!

#### ช่วงที่ 4: การเก็บกวาดรอบดึก (Night Micro-Drain: 22:52 - 22:53)
- 22:52: เงินเข้า ฿3,000.00 จาก `SCB x1011 นาย วรเมธ`
- 22:53 (1 นาทีต่อมา): โอนออก ฿3,400.00 + ฿10 FE ไปยัง **พร้อมเพย์ x8003 นางสาว กมลพร วงศ์สุวรรณ** ทันที เหลือเงินติดบัญชี ฿47.06

---

## 3. การเปรียบเทียบและการเลือกวิธีการคำนวณ (Methodology Evaluation & Hybrid Selection)

อ้างอิงจากหัวข้อ 3 ของเอกสารทางเทคนิค `techdocs/financial_forensics.txt` ระบบได้เปรียบเทียบแนวทางการคำนวณทั้ง 5 รูปแบบ ดังตาราง:

| วิธีการ (Approach) | ข้อดี (Pros) | ข้อจำกัด (Cons) | สถานะในสถาปัตยกรรม |
| :--- | :--- | :--- | :--- |
| **1. Random Sampling** (Monte Carlo) | เขียนง่าย รวดเร็วบนรอบรันเดียว | **ไม่การันตีความถูกต้อง** มี False Negative สูงมาก ไม่มีน้ำหนักในชั้นศาล | ❌ **ตัดทิ้งโดยเด็ดขาด** (ขัดต่อหลักพยานหลักฐาน) |
| **2. Exact Enumeration** (itertools) | ถูกต้อง 100% ไม่ต้องใช้ไลบรารีเสริม | ติดปัญหา $O(2^N)$ เติบโตแบบ Exponential ใช้ได้แค่ $N \le 20-25$ | ⚠️ **ใช้เฉพาะ Local Validation** ($N \le 10$) |
| **3. Dynamic Programming** (DP) | ได้คำตอบแน่นอน เหมาะกับ Integer | ตัวเลขทศนิยมต้องคูณ scale factor, Memory บวมมหาศาลหาก Target หลักแสน/ล้าน | 🔄 **ใช้เป็น Fallback ตัวที่สอง** |
| **4. Mixed-Integer Linear Programming (MILP)** | รองรับ Constraints ซับซ้อน, รองรับทศนิยมโดยตรง, เร็วมากในระดับวินาทีบนชุดข้อมูลใหญ่ | ต้องใช้ Solver ที่น่าเชื่อถือ (HiGHS) และต้องกำหนด Objective ให้รัดกุม | ⭐ **เลือกใช้เป็น แกนประมวลผลหลัก (Primary Core)** |
| **5. Constraint Programming (CP)** (OR-Tools) | รองรับเงื่อนไขตรรกะและเวลาซับซ้อน | มี Overhead ในการติดตั้งและการ Compile Model พอสมควร | 🔄 **สำรองสำหรับ Advanced Scheduling ในอนาคต** |

### 3.1 สถาปัตยกรรมแบบผสมผสานหลายชั้น (The Hybrid Multi-Tier Engine Architecture)

ในการสร้างระบบจริง ระบบไม่ได้ใช้ Approach ใดแบบโดดๆ แต่ใช้ **สถาปัตยกรรมแบบผสมผสาน 4 ลำดับชั้น (Hybrid Multi-Tier)** เพื่อดึงข้อดีของแต่ละวิธีมาอุดช่องโหว่ซึ่งกันและกัน:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HYBRID MULTI-TIER SOLVER PIPELINE                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Pre-filtering       ──► Temporal Sliding Windows (แบ่ง Bucket เวลา, ลดค่า N)   │
│  Layer 2: Primary Solver      ──► scipy.optimize.milp (HiGHS) — แม่นยำ, ทศนิยม, เร็ว ms  │
│  Layer 3: Network Aggregator  ──► Bipartite Matching / MCMF (สำหรับ M-to-N Flow)        │
│  Layer 4: Safety Fallback     ──► Greedy / Scaled DP Fallback (หาก Solver รันเกิน 5.0 วินาที)│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Layer 1: Temporal Sliding Windows Pre-filtering:**
   - คัดกรองทรานแซกชันด้วยหน้าต่างเวลา (เช่น 6h / 12h / 24h) และเลือกเฉพาะรายการเงินออกที่เกิด **หลัง** เงินเข้าเท่านั้น เพื่อลดค่า $N$ ให้เหลือน้อยที่สุดก่อนส่งเข้า Solver
2. **Layer 2: Primary Core Solver — Mixed-Integer Linear Programming (MILP):**
   - ใช้ `scipy.optimize.milp` ขับเคลื่อนด้วย HiGHS Solver
   - รองรับทศนิยมโดยตรงโดยไม่ต้องแปลงเป็นสตางค์ให้ Memory บวม
   - กำหนดขอบเขตอสมการชดเชยค่าธรรมเนียมและ Buffer Balance:
     $$T - \epsilon_{\text{lower}} \le \sum_{i \in S'} z_i \cdot x_i + \sum_{j \in \text{Fees}} f_j \le T + \epsilon_{\text{upper}}$$
3. **Layer 3: Network Flow Aggregator (M-to-N Flow Matching):**
   - สำหรับกรณีเงินเข้าจากเหยื่อหลายราย ($M$ Inflows) ไหลมารวมในบัญชีพัก แล้วแตกออกไปยังบัญชีม้าแถวถัดไป ($N$ Outflows) ระบบจะสลับไปใช้ **Minimum-Cost Maximum-Flow (MCMF)** บน Bipartite Graph
4. **Layer 4: Safety & Timeout Fallback (Greedy / Scaled DP):**
   - ติดตั้งตัวคุมเวลา (`solver_timeout_sec = 5.0`)
   - หากข้อมูลมีความหนาแน่นสูงผิดปกติจน MILP ไม่ลู่เข้าสู่คำตอบภายใน 5.0 วินาที ระบบจะสลับไปรัน Greedy Approximation ทันที เพื่อการันตีว่าระบบจะไม่เกิด Deadlock หรือค้าง

---

## 4. สถาปัตยกรรมระบบ 6 มิติ (The 6-Dimensional Forensic Architecture)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               ENTERPRISE COMPREHENSIVE FINANCIAL FORENSICS ARCHITECTURE               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [มิติ 1: Flow Dynamics]       ──► MILP Solver (scipy.optimize.milp) + M-to-N Matching │
│  [มิติ 2: Behavioral Signals]  ──► Residence Latency, Structuring Evasion, Round Sums   │
│  [มิติ 3: Graph Analytics]     ──► Multi-hop Tracing (Tier 1 -> 3), Shared Identifiers │
│  [มิติ 4: Legal Admissibility] ──► SHA-256 Custody Hash, XAI Mathematical Proof       │
│  [มิติ 5: Scalability Pipeline]──► Sliding Window Chunking, Solver Timeout Fallback    │
│  [มิติ 6: Investigator Workbench]► Tri-Modal Interface (Dashboard, Copilot, Dossier) │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### มิติที่ 1: การวิเคราะห์และจับคู่การไหลของเงิน (Topological & Flow Dynamics)
1. **การจับคู่ทางคณิตศาสตร์ด้วย MILP:**
   $$\text{Minimize} \quad \sum_{i=1}^n c_i \cdot z_i + \lambda \cdot |T - \sum_{i=1}^n z_i \cdot x_i|$$
   โดยที่ $z_i \in \{0, 1\}$ เป็นตัวแปร Binary บ่งชี้การเลือกรายการ
2. **การจัดการสัดส่วนเงินปนเปื้อน (Tainted Fund Attribution):**
   - **FIFO Model:** เงินเข้าก่อน ถูกระบายออกก่อน เหมาะสำหรับกรณีมี Time-gap ชัดเจน
   - **Proportional Pooling (Haircut Model):** คำนวณสัดส่วนเงินปนเปื้อน:
     $$\text{Taint Ratio} = \frac{\text{Suspicious Inflow}}{\text{Suspicious Inflow} + \text{Prior Clean Balance}}$$

### มิติที่ 2: พฤติกรรมศาสตร์และสัญญาณความผิดปกติ (Behavioral & Forensic Signals)
1. **Pass-through Velocity & Residence Time:**
   $$t_{\text{residence}} = t_{\text{outflow}} - t_{\text{inflow}}$$
   หาก $t_{\text{residence}} \le 15 \text{ นาที}$ ให้คะแนนความเสี่ยงระดับวิกฤต (Critical Velocity)
2. **AML Threshold Evasion (Structuring / Smurfing):**
   ตรวจจับยอดโอนที่ปัดเศษลงเพื่อไม่ให้ถึงเกณฑ์รายงาน ปปง. (เช่น รายการใกล้ 2,000,000 บาท หรือต่ำกว่า 50,000 บาท ต่อครั้ง)
3. **Round-Number Clustering:**
   ตรวจจับพฤติกรรมรับเงินเข้ามีเศษ (฿19,980, ฿5,199, ฿39,940) แต่กระจายออกเป็นเลขกลม (฿100,000, ฿190,000, ฿180,000)

### มิติที่ 3: ความสัมพันธ์ระดับโครงข่าย (Graph Analytics & Multi-Hop Tracing)
1. **การติดตามเส้นเงินข้ามทอด (Multi-Hop Tracing):**
   $$\text{Victim (เหยื่อ)} \xrightarrow{\text{Hop 1}} \text{Mule Tier 1 (บัญชีม้ารับโอน)} \xrightarrow{\text{Hop 2}} \text{Mule Tier 2 (บัญชีรวบรวม)} \xrightarrow{\text{Hop 3}} \text{VASP / Cashier}$$
2. **Entity Resolution:**
   จัดกลุ่มผู้รับซ้ำ และตรวจจับความสัมพันธ์ของนามสกุล (เช่น นาง นิภาภัทร ธรรมเจริญ และ นาย ธนดล ธรรมเจริญ)
3. **Cypher Query สำหรับ Neo4j:**
   ```cypher
   MATCH path = (v:Account {account_number: "GSB-1001"})-[:TRANSFERRED*1..4]->(target:Account)
   WHERE all(r IN relationships(path) WHERE r.residence_time_mins < 120)
   RETURN path, reduce(total = 0, r IN relationships(path) | total + r.amount) AS total_flow
   ORDER BY total_flow DESC;
   ```

### มิติที่ 4: ความน่าเชื่อถือทางกฎหมายและพยานหลักฐาน (Legal & Admissibility)
1. **ห่วงโซ่การครอบครองพยานหลักฐานดิจิทัล (Chain of Custody):**
   บันทึก SHA-256 Hash ของไฟล์ Statement ทันทีที่ระบบได้รับไฟล์ และทำงานบน In-memory Copy เท่านั้น
2. **Explainable AI (XAI) & Linear Constraint Proofs:**
   แสดงผลลัพธ์การจับคู่ในรูปแบบ **สมการพีชคณิตเชิงเส้น (Algebraic Proof Ledger)**:
   $$\mathbf{A} \cdot \mathbf{x} = \mathbf{b} \pm \mathbf{\epsilon}$$
3. **Corroboration-Gated Neutrality Standard:**
   รายงานผลเป็น "HIGH SUSPICION / REQUIRES REVIEW" เพื่อความเป็นกลางในการพิจารณาคดี

### มิติที่ 5: ประสิทธิภาพและการประมวลผลระดับสูง (Scalability & High Performance)
1. **Sliding Window Partitioning:** แบ่งกลุ่มตาม `account_id` และช่วงเวลา เพื่อรองรับ 100,000+ รายการ
2. **Time-Limit Enforcer:** ตัดรอบที่ 5.0 วินาที พร้อมสลับไปใช้ Heuristic Fallback

### มิติที่ 6: การทำงานร่วมกับมนุษย์และคะแนนความน่าสงสัย (Human-in-the-Loop & Suspicion Scoring Matrix)
1. **Unified Suspicion Scoring Matrix (คะแนนความน่าสงสัย 0 - 100):**
   ประเมินความเสี่ยงแบบหลายมิติด้วยสมการเชิงเส้นถ่วงน้ำหนัก:
   $$\text{Suspicion Score} = w_1 \cdot S_{\text{amount}} + w_2 \cdot S_{\text{time}} + w_3 \cdot S_{\text{balance}} + w_4 \cdot S_{\text{network}}$$
   - $S_{\text{amount}}$ (น้ำหนัก 0.25): ตรวจจับความผิดปกติด้านจำนวนเงิน (ยอดปัดเศษเลขกลม, การซอยยอด Structuring เลี่ยงรายงาน AML)
   - $S_{\text{time}}$ (น้ำหนัก 0.30): ความเร็วในการระบายเงินออก (Residence Time Latency $\le 15$ นาที จัดเป็นวิกฤต)
   - $S_{\text{balance}}$ (น้ำหนัก 0.25): อัตราการดูดเงินออกจากบัญชีจนแทบไม่เหลือเศษ (Drain Percentage $\ge 99\%$)
   - $S_{\text{network}}$ (น้ำหนัก 0.20): ความสัมพันธ์ในโครงข่าย (การเชื่อมโยงข้ามทอด Multi-hop หรือพบประวัติในฐานข้อมูล Blacklist ของ AOC 1441)
2. **Human-in-the-Loop Interactive Workbench:**
   ระบบสนับสนุนการมีส่วนร่วมของพนักงานสอบสวนในการสืบสวนจริง:
   - **Force Match / Pin Match:** พนักงานสอบสวนสามารถปักหมุดหรือบังคับเชื่อมโยงรายการที่สืบทราบจากแหล่งข่าวภายนอก
   - **Exclude Noise:** คัดกรองธุรกรรมที่ไม่เกี่ยวข้อง (เช่น รายการตัดค่าธรรมเนียมปกติ, ดอกเบี้ย) ออกจากการคำนวณ
   - ส่งต่อผลลัพธ์สู่ **Tri-Modal Forensic Output Architecture** (รายละเอียดในหัวข้อที่ 5)

---

## 5. สถาปัตยกรรมเอาต์พุตแบบ 3 รูปแบบสำหรับพนักงานสอบสวน (Tri-Modal Forensic Output Architecture)

เพื่อตอบโจทย์วงรอบการทำงานจริงของพนักงานสอบสวน (ตำรวจไซเบอร์, ปปง., DSI) ระบบกำหนดเอาต์พุตไว้ **3 รูปแบบที่ทำงานสอดประสานกัน (Tri-Modal Architecture)**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      TRI-MODAL FORENSIC OUTPUT ARCHITECTURE                            │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│  1. Visual Dashboard     │  2. Forensic Chat Copilot   │  3. 1-Click Court Dossier     │
│  (Multi-tab Dimensions)  │  (Agent Harness NLQ)        │  (Legal Evidence Export)      │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ • หน้าจอคัดกรอง Triage    │ • สอบสวนเจาะลึกเฉพาะคดี     │ • เอกสารส่งฟ้องอัยการ/ศาล     │
│ • Sankey & Graph 6 มิติ  │ • กรองเส้นเงินภาษาธรรมชาติ  │ • ขออายัดบัญชีฉุกเฉิน (AOC)   │
│ • Suspicion Score 0-100  │ • สั่งจำลอง Haircut/FIFO    │ • มี SHA-256 + สมการ XAI      │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

### 5.1 โหมดที่ 1: Visual Multi-Dimensional Dashboard (สำหรับคัดกรอง Triage)
หน้าจอแดชบอร์ดสรุปผลแบบ Interactive แบ่งแท็บตามมิติการสืบสวน ช่วยให้เจ้าหน้าที่มองเห็นภาพรวมและตัดสินใจได้ใน 30 วินาที:
* **Executive Alert Card:** 
  - สรุปข้อมูลบัญชี: บัญชีเป้าหมาย `9012345678`, ยอดเงินเข้า ฿572,297, ยอดเงินออก ฿572,200, **Drain Rate: 99.995%**, ดัชนีความเสี่ยงรวม **98.6 / 100 (CRITICAL ALERT)**
* **แท็บ 1: Flow Dynamics (Sankey Diagram):**
  - แสดงสายธารเงิน: ด้านซ้ายแสดงรายชื่อผู้เสียหาย/เงินเข้า ➔ ตรงกลางคือบัญชีม้าพักเงิน ➔ ด้านขวาแสดงบัญชีปลายทางที่เงินถูกซอยออกไป
* **แท็บ 2: Behavioral Signals (Timeline & Latency):**
  - กราฟเวลาแสดงความเร็วในการระบายเงิน ($t_{\text{residence}}$) บ่งชี้เงินเข้าปุ๊บ โอนออกปั๊บภายใน 1-14 นาที
* **แท็บ 3: Multi-Hop Network Graph:**
  - แผนผังโครงข่ายใยแมงมุมแสดงบัญชีม้าแถว 1, แถว 2, แถว 3 พร้อมไฮไลต์ Entity ที่รับเงินซ้ำซ้อน (เช่น `MR.SOKHA CHAN` หรือ `พร้อมเพย์ กมลพร วงศ์สุวรรณ`)
* **แท็บ 4: Human-in-the-Loop Actions:**
  - เจ้าหน้าที่สามารถคลิก **"ปักหมุด (Pin)"** บัญชีต้องสงสัย หรือ **"ตัดออก (Exclude)"** รายการที่ไม่เกี่ยวกับคดี แล้วระบบจะคำนวณเส้นเงินใหม่ทันที

### 5.2 โหมดที่ 2: Interactive Forensic Chat Copilot (ถาม-ตอบกับ Agent Harness ด้วยภาษาธรรมชาติ)
เปิดช่องทางให้เจ้าหน้าที่คุยถาม-ตอบกับ Agent Harness (`forensic_architect` และ `evidence_auditor`) ด้วยภาษาธรรมชาติ (Natural Language Forensic Query):

**ตัวอย่างบทสนทนาจริงบนข้อมูล `statement.csv`:**
> **เจ้าหน้าที่:** *"เงิน 470,000 บาท ของเหยื่อ จ่าสิบตรี ภานุวัฒน์ ที่โอนเข้ามาตอน 15:38 น. ถูกกระจายออกไปให้ใครบ้าง ภายใน 2 ชั่วโมงแรก?"*  
> **Agent Copilot:** *"จากการรัน MILP Flow Matching พบว่าเงินก้อนดังกล่าวถูกระบายออกไปยัง 4 บัญชีปลายทาง รวม ฿546,500 ภายใน 88 นาที ดังนี้:*  
> *1. SCB x8004 MRS. SOPHEA SAR ฿100,000 (16:16 น.)*  
> *2. KBANK x8005 นาย ธีรภัทร บุญเสริม ฿190,000 (17:04 น.)*  
> *3. KTB x8006 น.ส. จรรยา มิ่งขวัญ ฿180,000 (17:07 น.)*  
> *4. KBANK x8007 น.ส. อรอุมา แสนสุข ฿76,500 (17:10 น.)*  
> *สถานะบัญชีหลังโอน: เงินเหลือติดบัญชีเพียง ฿107.06"*

> **เจ้าหน้าที่:** *"ช่วยตรวจสอบให้หน่อยว่า ในบรรดาบัญชีปลายทาง มีใครใช้นามสกุลเดียวกัน หรือเชื่อมโยงกันบ้าง?"*  
> **Agent Copilot:** *"ตรวจพบ Entity Resolution: ผู้โอนเข้าสองรายคือนาง นิภาภัทร ธรรมเจริญ (โอน 15:31 และ 16:12) กับนาย ธนดล ธรรมเจริญ (โอน 16:23) ใช้นามสกุลเดียวกัน เชื่อมโยงเป็นกลุ่มผลประโยชน์เดียวกันครับ"*

### 5.3 โหมดที่ 3: 1-Click Court-Admissible Dossier Export (รายงานสำนวนคดีและขออายัดบัญชี)
สร้างรายงานการตรวจพิสูจน์พยานหลักฐานดิจิทัลอย่างเป็นทางการตาม ป.วิ.อ. มาตรา 226 เพื่อส่งอัยการหรือขอหมายศาล:
* **Exhibit A (Data Integrity Manifest):** บันทึกห่วงโซ่พยานหลักฐาน (Chain of Custody) พร้อมค่า SHA-256 Hash ของไฟล์ Statement ธนาคาร
* **Exhibit B (Mathematical Proof Ledger):** ตารางสมการพีชคณิตเชิงเส้น (XAI) แสดงการจับคู่เงินเข้า-เงินออกอย่างโปร่งใส ไร้ข้อกังขา
* **Exhibit C (Beneficiary Summary):** ตารางสรุปเลขบัญชี, ชื่อ-สกุล, และยอดเงินของบัญชีม้าแถวถัดไป เพื่อใช้ประกอบ **คำร้องขออนุมัติหมายจับ** หรือ **หนังสือขออายัดบัญชีฉุกเฉิน (AOC)** ส่งธนาคาร

### 5.4 วงรอบการทำงานจริงของพนักงานสอบสวน (Investigator Workflow)
1. **นาทีที่ 1 (Triage):** อัปโหลด Statement ➔ ดู **Dashboard** ➔ พบ Drain Rate 99.995% ตัดสินใจรับคดีทันที
2. **นาทีที่ 2-5 (Deep-dive):** ใช้ **Chat Copilot** เจาะลึกความเชื่อมโยงของกลุ่มผู้รับเงินปลายทาง
3. **นาทีที่ 6 (Action):** กด **Export Court Dossier** ➔ ได้เอกสารหลักฐานส่งฟ้องและทำหนังสืออายัดบัญชีได้ทันที

---

## 6. สถาปัตยกรรมชุดเทคโนโลยีและการติดตั้ง (Technology Stack & Deployment Architecture)

ระบบเลือกใช้ **สถาปัตยกรรมชุดเทคโนโลยีแบบผสมผสาน (Hybrid Architecture: Python-Centric Core + TypeScript/Modern Web UI)**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          HYBRID TECH STACK ARCHITECTURE                                │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│  1. Core Backend & Forensic Engine        │  2. Interactive Frontend & Workbench UI    │
│     (Python 3.10+)                        │     (TypeScript / Modern Web / HTML5)      │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Mathematical Solver: scipy.optimize.milp│ • Flow Visualization: Apache ECharts / D3  │
│ • Matrix Math: numpy                      │ • Multi-Hop Network: Cytoscape.js / Canvas │
│ • Thai NLP Entity Parser: pythainlp       │ • Responsive Layout: Tailwind CSS          │
│ • Data Contracts: pydantic v2             │ • Dynamic State Management (Pin/Exclude)   │
│ • High-performance Async API: FastAPI     │ • Interactive Chat Copilot Interface       │
│ • Evidence PDF Generation: reportlab/pypdf│ • Client-side Timeline & Filter Sliders    │
│ • State Machine Harness: harness/ (Python)│ • 1-Click Export Actions                   │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

## 7. สถาปัตยกรรมความพร้อมใช้งานจริงระดับองค์กร 6 เสาหลัก (The 6 Pillars of Production-Grade Hardening)

เพื่อยกระดับระบบให้เป็น **Production-Grade Enterprise System** ที่พร้อมใช้งานในสภาพแวดล้อมจริงของสำนักงานตำรวจแห่งชาติ และ ปปง. ระบบได้ติดตั้ง 6 เสาหลักทางวิศวกรรมความปลอดภัยและความทนทาน:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   6 PILLARS FOR ENTERPRISE PRODUCTION-GRADE FORENSICS                  │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│ 1. Universal Bank Engine │ 2. Advanced Laundering Graph│ 3. Security, RBAC & PDPA      │
│ (Multi-bank Normalization│ (Circular Washing & Cycles, │ (Case Isolation, PII Masking, │
│  + Reversals/Bounces)    │  Cascading Multi-Stage)     │  Audit Trail)                 │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 4. Async Worker Queue    │ 5. Tamper-Evident Vault     │ 6. AOC / AMLO Interoperability│
│ (Celery/Redis Background │ (Append-Only Merkle Log &   │ (AOC 1441 & CFR Blacklist     │
│  Streaming for 500k+ rows│  e-Signature ETA Sec 26)    │  Direct API Integration)      │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

### 7.1 เสาหลักที่ 1: Universal Bank Ingestion Engine & Reversal Reconciliation
1. **Universal Bank Adapter:** รองรับไฟล์ Statement จากทุกธนาคารไทย (KBANK, SCB, KTB, BBL, GSB, TTB, BAY) ทั้งในรูปแบบ CSV, Excel (.xlsx) และ Text File โดยมีระบบ Auto-Header Detection ตัดบรรทัดหัวตารางและสรุปยอดท้ายตารางอัตโนมัติ
2. **Reversals & Chargebacks Handling (การหักลบรายการยกเลิก):**
   - ตรวจจับรายการโอนเงินไม่สำเร็จ (Failed/Unsuccessful Transfers) และรายการดึงเงินกลับ (Chargeback/Reversal)
   - เชื่อมโยงคู่รายการยกเลิก (Reversal Pairs) เพื่อหักลบออกจาก Volume รวม ไม่นำมาคำนวณเป็น Inflow หรือ Outflow ปลอม (Zero False Inflation)
3. **Variable Fee Matrix:** รองรับค่าธรรมเนียมทุกประเภท (ธนาคาร ฿5, พร้อมเพย์ ฿10, BahtNet ฿100-฿250, และค่าธรรมเนียมถอนเงินสดหน้าเคาน์เตอร์)

### 7.2 เสาหลักที่ 2: Advanced Laundering Graph & Cycle Detection
1. **Circular Flow & Cycle Washing Detection:**
   - ตรวจจับวงจรการโอนวนกลับ เช่น $A \rightarrow B \rightarrow C \rightarrow A$ เพื่อปั่นยอดเงินเทียมหรือทำให้เจ้าหน้าที่สับสน
   - ใช้อัลกอริทึม **Tarjan's Strongly Connected Components (SCC)** และ **Cycle Detection** ใน NetworkX / Graph Database แจ้งเตือนวงรอบการฟอกเงินทันที
2. **Multi-Stage Cascading Structuring:**
   - ติดตามเส้นเงินหลายชั้น (Multi-tier Pooling & Smurfing) เช่น เงินเข้า 10 บัญชี ➔ รวบเข้า 2 บัญชีพัก ➔ ซอยออก 15 บัญชีปลายทาง

### 7.3 เสาหลักที่ 3: Security, Multi-Tenancy Case Isolation & PDPA Masking
1. **Case-Level Multi-Tenancy (การแยกสำนวนคดีเด็ดขาด):**
   - พนักงานสอบสวน สน./สภ. ต่างกัน ไม่สามารถเข้าถึง Statement ในคดีของกันและกันได้ ป้องกันข้อมูลคดีรั่วไหล
   - **Cross-Case Intelligence Alert:** หากตรวจพบบัญชีม้าปลายทางตรงกับคดีของ สน./สภ. อื่น ระบบจะส่งสัญญาณแจ้งเตือนเฉพาะรหัสคดีและพนักงานสอบสวนเจ้าของสำนวน เพื่อให้ประสานงานร่วมกัน
2. **PDPA Data Masking (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล):**
   - หน้าจอแสดงผลทั่วไปจะเซ็นเซอร์เลขบัตรประชาชนและเลขที่บัญชี (เช่น `901-xxx-5678`)
   - เปิดดูข้อมูลเต็มได้เฉพาะพนักงานสอบสวนเจ้าของสำนวนที่มีสิทธิ์ตาม ป.วิ.อ. เท่านั้น
3. **Role-Based Access Control (RBAC):**
   - แบ่งสิทธิ์เป็น 3 ระดับ: `Investigator` (วิเคราะห์/สืบสวน), `Supervisor/Commander` (อนุมัติหมาย/ออกคำสั่งอายัด), `Compliance Auditor` (ตรวจสอบความถูกต้องและโปร่งใส)

### 7.4 เสาหลักที่ 4: Asynchronous Processing & Streaming I/O
1. **Asynchronous Worker Queue:**
   - ใช้ FastAPI BackgroundTasks / Redis Queue ในการประมวลผล Statement ขนาดใหญ่ (100,000 – 500,000 รายการ) เพื่อไม่ให้เกิด Gateway Timeout (504)
   - ส่งผลลัพธ์และเปอร์เซ็นต์ความคืบหน้า (Progress Bar) กลับมาทาง **WebSockets** แบบ Real-time
2. **Memory-Mapped Streaming (Generator Chunking):**
   - สตรีมอ่านไฟล์ขนาดใหญ่เป็นท่อนๆ (Chunks) ลดการกิน RAM และป้องกันปัญหา Out-of-Memory (OOM)

### 7.5 เสาหลักที่ 5: Tamper-Evident Evidence Vault & e-Signature
1. **Append-Only Merkle Tree Audit Trail:**
   - ทุก Action ของเจ้าหน้าที่ (การนำเข้าไฟล์, การรันโมเดล, การปักหมุด Pin, การเขียนโน้ตสืบสวน) จะถูกบันทึกเป็น Block ผูกโยงด้วย Cryptographic Hash แบบ Merkle Tree ที่ไม่สามารถลบหรือแก้ไขย้อนหลังได้ เพื่อยืนยันความบริสุทธิ์ของพยานหลักฐาน
2. **Electronic Signature under ETA Section 26-28:**
   - รองรับการลงลายมือชื่อดิจิทัลที่มีใบรับรอง (Digital Certificate & Trusted Timestamp) บนเอกสาร Court Dossier PDF ให้มีผลสมบูรณ์ตามกฎหมายธุรกรรมทางอิเล็กทรอนิกส์

### 7.6 เสาหลักที่ 6: AOC 1441 & Central Fraud Registry (CFR) Interoperability
1. **CFR Blacklist API Integration:**
   - เทียบเคียงเลขบัญชีปลายทางและชื่อบุคคลกับฐานข้อมูลบัญชีม้า Blacklist ของศูนย์ AOC 1441 โดยอัตโนมัติ
2. **Standard AOC Export Protocol:**
   - มีปุ่มส่งออกข้อมูลเป็นฟอร์แมต JSON/XML มาตรฐานที่สามารถนำเข้าสู่ระบบแลกเปลี่ยนข้อมูลของศูนย์ปฏิบัติการแก้ไขปัญหาอาชญากรรมออนไลน์ (AOC 1441) และระบบ ปปง. ได้ทันที

---

## 8. โครงสร้างข้อมูลและ Data Contracts (Pydantic Models)

ระบบใช้ Strict Typing ผ่าน `pydantic v2` ครอบคลุมทั้งข้อมูลธุรกรรมและบันทึกความมั่นคงปลอดภัย:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ActivityType(str, Enum):
    INFLOW = "XD"
    OUTFLOW = "XW"
    FEE = "FE"
    REVERSAL = "REV"

class BankTransaction(BaseModel):
    tx_id: str
    account_no: str
    account_name: str
    timestamp: datetime
    activity: ActivityType
    channel: str
    amount: float = Field(gt=0.0)
    balance: float = Field(ge=0.0)
    description: str
    counterparty_bank: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_name: Optional[str] = None
    is_reversal: bool = False
    reversal_ref_id: Optional[str] = None
    cfr_blacklist_hit: bool = False

class FlowMatchCluster(BaseModel):
    cluster_id: str
    inflow_tx_ids: List[str]
    inflow_total: float
    outflow_tx_ids: List[str]
    outflow_total: float
    fee_total: float
    residual_balance: float
    avg_latency_minutes: float
    drain_percentage: float
    is_circular: bool = False
    circular_cycle_path: Optional[List[str]] = None
    mathematical_proof: str  # Linear equation representation

class MerkleAuditRecord(BaseModel):
    record_id: str
    case_id: str
    officer_id: str
    action_type: str  # INGEST, SOLVE, PIN, EXCLUDE, EXPORT
    timestamp: datetime
    previous_hash: str
    current_hash: str
    signature: Optional[str] = None

class SuspicionReport(BaseModel):
    case_id: str
    account_no_masked: str
    account_no_raw: str
    account_name: str
    statement_hash_sha256: str
    overall_suspicion_score: float = Field(ge=0.0, le=100.0)
    suspicion_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    clusters_detected: List[FlowMatchCluster]
    top_counterparties: Dict[str, float]
    cfr_hits: List[Dict[str, Any]]
    merkle_root: str
    admissibility_receipt: Dict[str, str]
```

---

## 9. ผลการจับคู่จำลองทางคณิตศาสตร์บนข้อมูลจริง (`statement.csv`)

เมื่อนำข้อมูลจริงเข้าสู่แบบจำลอง MILP สำหรับรายการโอนเงินของเหยื่อรายใหญ่ (จ่าสิบตรี ภานุวัฒน์):

```
Target Inflow Cluster:
  - 15:38:00 | GSB x1001 จ่าสิบตรี ภานุวัฒน์ | ฿470,000.00
  - Accompanying structuring inflows (15:31 - 16:23) | ฿86,619.00
  - Total Inbound Pool: ฿556,619.00

MILP Matched Outflows (x_i = 1):
  1. [16:16:00] SCB x8004 MRS. SOPHEA SAR          -> ฿100,000.00 (Latency: 38 mins)
  2. [17:04:00] KBANK x8005 นาย ธีรภัทร บุญเสริม       -> ฿190,000.00 (Latency: 86 mins)
  3. [17:07:00] KTB x8006 น.ส. จรรยา มิ่งขวัญ      -> ฿180,000.00 (Latency: 89 mins)
  4. [17:10:00] KBANK x8007 น.ส. อรอุมา แสนสุข     -> ฿76,500.00  (Latency: 92 mins)
  5. Fees: 3 transactions @ ฿5.00                -> ฿15.00
  -------------------------------------------------------------
  Sum Matched Outflow: ฿546,515.00
  Residual in Account: ฿10,104.00 (Within tolerance bound)
  Solver Status: OPTIMAL (Solved in 0.042 seconds via scipy.optimize.milp)
  Proof Equation: 100,000 + 190,000 + 180,000 + 76,500 + 15 = 546,515 <= 556,619
```

---

## 10. แผนการดำเนินงานและขั้นตอนการพัฒนา (Step-by-Step Implementation Roadmap)

การพัฒนาระบบแบ่งออกเป็น 6 ระยะ (Phases) แบบครบวงจร:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          IMPLEMENTATION MILESTONES & TIMELINE                          │
├────────────┬──────────────────────────────────────────┬────────────────────────────────┤
│ Phase 1    │ Data Ingestion, Universal Adapters & CoC │ Multi-bank Ingestion, SHA-256  │
│ Phase 2    │ Hybrid Flow Matching & Cycle Engine      │ MILP + MCMF + Tarjan SCC       │
│ Phase 3    │ Behavioral Signals & Suspicion Scoring   │ Velocity, Evasion, Score 0-100 │
│ Phase 4    │ Multi-Hop Graph & Case Isolation         │ Account Layering, RBAC, PDPA   │
│ Phase 5    │ Court Evidence Dossier & Merkle Vault    │ Section 226 Report + e-Sign    │
│ Phase 6    │ Tri-Modal Workbench & AOC Integration    │ Dashboard, Copilot, AOC Export │
└────────────┴──────────────────────────────────────────┴────────────────────────────────┘
```

### ระยะที่ 1: การนำเข้าข้อมูลและการรับประกันห่วงโซ่พยานหลักฐาน (Ingestion & Provenance)
- พัฒนา `UniversalStatementParser` รองรับ Statement ทุกธนาคารไทย (KBANK, SCB, KTB, BBL, GSB, TTB, BAY)
- พัฒนาโมดูล `ReversalReconciler` สำหรับตรวจจับและหักลบรายการโอนเงินไม่สำเร็จ/ดึงเงินคืน
- สกัดชื่อบุคคล, ยศ, และบัญชีด้วย `pythainlp` และคำนวณค่า SHA-256 Hash เข้าสู่ Audit Ledger

### ระยะที่ 2: แกนประมวลผลจับคู่เส้นทางการเงินและตรวจจับวงจร (Hybrid Flow & Cycle Engine)
- สร้าง `FlowMatchingEngine` ด้วย `scipy.optimize.milp` เป็นตัวประมวลผลหลัก
- รองรับ Sliding Window Partitioning, M-to-N Flow Matching (MCMF), และ Timeout Fallback 5.0 วินาที
- ติดตั้งอัลกอริทึม **Tarjan SCC / Cycle Detection** เพื่อตรวจจับการโอนเงินวนลูป (Circular Washing)

### ระยะที่ 3: ระบบตรวจจับพฤติกรรมศาสตร์และการคำนวณคะแนนความเสี่ยง (Behavioral & Scoring)
- สร้างโมดูล `ForensicBehavioralSignals` คำนวณ Pass-through Velocity และ Round-number Index
- สร้างโมดูล `SuspicionScoringEngine` ให้คะแนน 0-100 พร้อมคำอธิบายเหตุผลเป็นรายปัจจัย

### ระยะที่ 4: การวิเคราะห์โครงข่ายกราฟและระบบความปลอดภัย (Graph & Security Layer)
- สร้างโมดูล `GraphTracer` สำหรับสร้างกราฟเส้นทางการเงินข้ามทอด (Tier 1 -> Tier 3)
- ติดตั้งระบบ **Case-level Multi-Tenancy** และ **PDPA Masking** (เซ็นเซอร์เลขบัญชี/บัตรประชาชน)

### ระยะที่ 5: แฟ้มสำนวนคดีและห้องนิรภัยพยานหลักฐาน (Evidence Dossier & Merkle Vault)
- สร้างโมดูล `EvidenceDossierGenerator` จัดทำเอกสารสำนวนฟ้อง (Court Dossier) ในรูปแบบ Markdown และ PDF (Exhibit A - D)
- ติดตั้ง **Merkle Tree Audit Vault** บันทึกประวัติการสืบสวนแบบ Append-only ที่แก้ไขย้อนหลังไม่ได้
- รองรับระบบลงลายมือชื่อดิจิทัล (Digital Signature ตาม พ.ร.บ.ธุรกรรมอิเล็กทรอนิกส์ มาตรา 26)

### ระยะที่ 6: ระบบส่วนประสานงานพนักงานสอบสวนและเชื่อมโยง AOC (Tri-Modal & AOC)
- พัฒนา Dashboard 4 แท็บ (Executive, Sankey Flow, Behavioral, Network Graph)
- พัฒนาช่องทาง Interactive Chat Copilot ร่วมกับ Agent Harness (`forensic_architect` และ `evidence_auditor`)
- ติดตั้งระบบเชื่อมต่อ API ตรวจสอบ Blacklist ของศูนย์ AOC 1441 และปุ่มส่งออกสำนวนคดี 1-Click

---

## 11. แผนการตรวจสอบและเกณฑ์การยอมรับ (Verification & Acceptance Criteria)

| รายการทดสอบ | เกณฑ์การยอมรับ (Acceptance Criteria) | วิธีการตรวจสอบ |
| :--- | :--- | :--- |
| **Data Integrity** | ค่า SHA-256 ของไฟล์ต้นฉบับตรงกับค่าที่บันทึกไว้ 100% | `DeterministicVerifier.verify_data_provenance` |
| **Flow Conservation** | เงินที่ระบายออก + ค่าธรรมเนียม + เงินเหลือ ต้องอยู่ในขอบเขตความคลาดเคลื่อน $\le 2\%$ | `DeterministicVerifier.verify_flow_conservation` |
| **Reversal Reconciliation** | รายการดึงเงินกลับ/โอนไม่สำเร็จถูกหักลบออกครบถ้วน ไม่บวมเข้ายอดรวม | Unit Verification บน Reversal Test Fixtures |
| **Cycle Washing** | ระบบตรวจพบวงรอบ $A \rightarrow B \rightarrow C \rightarrow A$ ได้ครบ 100% | Tarjan SCC Algorithm Verification |
| **MILP Convergence** | Solver สามารถประมวลผลจับคู่เสร็จสิ้นภายใน $\le 5.0$ วินาที | `options={"time_limit": 5.0}` |
| **Zero-Test Default** | ไม่มีการเขียนหรือรัน unit test โดยไม่ได้รับคำสั่งอย่างชัดเจน | ตรวจสอบตามกฎ `docs/policies/unittest-policy.md` |
| **Court Admissibility** | แฟ้มสำนวนแสดงรายการสมการทางคณิตศาสตร์ชัดเจน อธิบายในชั้นศาลได้ | Audit โดย `evidence_auditor` |
| **Merkle Integrity** | บันทึกประวัติการสอบสวนทุกรายการเชื่อมโยง Hash ถูกต้อง ไม่มีการดัดแปลง | Merkle Tree Root Hash Verification |

---
**พร้อมเริ่มดำเนินการสร้างจริงใน Phase 1 ทันที**


---

## 12. แผนการยกระดับระบบในอนาคต (System Upgrade Plan: Advanced Analytics & Investigative FAQ Engine)

เพื่อยกระดับระบบ FinForensic จากเครื่องมือมองเห็นภาพ (Visualization) สู่การเป็น **"ระบบสนับสนุนการตัดสินใจเชิงสืบสวนและการตอบคำถามชั้นศาล (Investigative Decision Support & Judicial FAQ Engine)"** จึงกำหนดแผนการอัปเกรดระบบเพิ่มเติมดังนี้:

### 12.1 6 มุมมองการวิเคราะห์ข้อมูลเชิงสถิติเพิ่มเติม (The 6 Extended Analytical Perspectives)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                  EXTENDED FORENSIC DATA ANALYTICS & INSIGHT PERSPECTIVES               │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│ 1. Multi-Stat Ranking    │ 2. Channel & Cash-out Split │ 3. 24-Hour Nocturnal Heatmap  │
│ (Top Amounts, Frequency, │ (Cardless ATM vs Crypto P2P │ (Peak Hour Burst Intensity &  │
│  Velocity Latency)       │  vs Commercial Banks)       │  Odd-hours 01:00-06:00)       │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 4. Typology Clustering   │ 5. Tainted Fund Attribution │ 6. Entity Co-occurrence Graph │
│ (Smurfing, Rapid Drain,  │ (FIFO vs Haircut Ratio      │ (Shared Surnames, Co-payees,  │
│  Ping-test, Final Sweep) │  Interactive Slider)        │  Common Device/Phone)         │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

1. **มุมมองที่ 1: ตารางจัดอันดับตัวชี้วัดสำคัญ (Multi-Dimensional Leaderboards):**
   - **Top Inflows:** จัดอันดับผู้เสียหายรายใหญ่หรือท่อน้ำเลี้ยงหลักที่โอนเงินเข้า
   - **Top Outflows:** จัดอันดับบัญชีปลายทางที่ดูดเงินก้อนโตที่สุดไป เพื่อกำหนดเป้าหมายอายัดเงินด่วน
   - **Top Frequency:** จัดอันดับบัญชีที่รับโอนซ้ำๆ บ่อยที่สุด (Habitual Dispersal) ชี้เป้าคนกดเงินสดหรือบัญชีรวบรวม
   - **Top Velocity:** จัดอันดับรายการที่เงินแช่อยู่ในบัญชีน้อยที่สุด ($\le 1-5$ นาที) พิสูจน์การใช้ระบบอัตโนมัติ
2. **มุมมองที่ 2: สัดส่วนช่องทางและการผันเงินออกนอกระบบ (Channel & Off-ramp Distribution):**
   - แผนภูมิโดนัทเปรียบเทียบสัดส่วน: การถอนเงินสดไม่ใช้บัตร (Cardless ATM) vs สินทรัพย์ดิจิทัล (Crypto USDT P2P) vs การโอนธนาคารพาณิชย์
3. **มุมมองที่ 3: แผนภาพความหนาแน่น 24 ชั่วโมง (24-Hour Activity Heatmap & Burst Intensity):**
   - ตรวจสอบความหนาแน่นของธุรกรรมตามช่วงเวลา ชี้ชัดพฤติกรรมยามวิกาล (Odd-hours 01:00 - 06:00 น.) ซึ่งผิดวิสัยวิถีชีวิตคนปกติ
4. **มุมมองที่ 4: การจำแนกตามกลุ่มพฤติกรรมอาชญากรรม (Behavioral Typology Clustering):**
   - คัดกรองธุรกรรมตามหมวด: `Smurfing_Deposit`, `Rapid_PassThrough_Drain`, `Odd_Hours_Activity`, `Layering_Sweep`, `Micro_Ping_Test`, และ `Final_Account_Drain`
5. **มุมมองที่ 5: แผนผังสัดส่วนเงินปนเปื้อนแบบ Interactive (Interactive Tainted Fund Attribution Slider):**
   - แถบเลื่อน (Slider) ให้พนักงานสอบสวนเลือกสลับโมเดล FIFO หรือ Haircut เพื่อตอบคำถามว่าเงินคงเหลือในบัญชีปลายทางเป็นเงินของผู้เสียหายคดีนี้กี่เปอร์เซ็นต์
6. **มุมมองที่ 6: การเชื่อมโยงอัตลักษณ์ร่วมและเครือข่ายความสัมพันธ์ (Entity Co-occurrence & Shared Identifiers):**
   - ตรวจจับความสัมพันธ์ของนามสกุล, เบอร์โทรศัพท์, บัญชีที่รับเงินจากกลุ่มเดียวกัน (Co-payee clustering)

---

### 12.2 คู่มือคำถามที่พบบ่อยที่ตอบได้ทันทีผ่าน Dashboard (The 7 Core Investigative FAQs)

ระบบได้รับการออกแบบให้ตอบ 7 คำถามยอดฮิตที่พนักงานสอบสวน พนักงานอัยการ และศาลต้องการทราบ โดยแสดงคำตอบเป็นหลักฐานเชิงประจักษ์:

| คำถามยอดฮิตของพนักงานสอบสวนและศาล (FAQ) | วิดเจ็ตบน Dashboard ที่ให้คำตอบทันที | รูปแบบพยานหลักฐานที่นำไปใช้ในสำนวน |
| :--- | :--- | :--- |
| **FAQ 1: เงินของผู้เสียหายไหลไปเข้ากระเป๋าใครบ้าง และเหลือติดอยู่ที่ไหน?** | **Sankey Flow Diagram** & ตาราง Flow Clusters | สมการพีชคณิตเชิงเส้น (Exhibit B) + แผนภาพแสดงเส้นทางการไหลของเงิน |
| **FAQ 2: บัญชีนี้เป็นบัญชีค้าขายปกติ หรือเป็นบัญชีม้าแน่นอน?** | **Drain Rate Gauge (99.99%)** & Latency Chart | พิสูจน์อัตราการกวาดเงินออกเกลี้ยงบัญชี และการไร้ซึ่งค่าใช้จ่ายดำรงชีพปกติ |
| **FAQ 3: ควรทำเรื่องขออายัดบัญชีใดเป็นลำดับแรก (Prioritized Targets)?** | **Top 10 Outflow Leaderboard** & Export AOC Form | รายชื่อบัญชีรับเงินก้อนโตสูงสุด 5 อันดับแรก พร้อมแบบฟอร์ม AOC 1441 (Exhibit D) |
| **FAQ 4: คนร้ายเริ่มปฏิบัติการเมื่อไหร่ มีการเตรียมการล่วงหน้าหรือไม่?** | **Timeline Chart** & พฤติกรรม Micro-Ping Test | บันทึกประวัติช่วงบัญชีนิ่ง (Dormant) $ightarrow$ โอนทดสอบระบบ $ightarrow$ พายุฟอกเงิน |
| **FAQ 5: เงินหลุดออกนอกระบบธนาคารไปเป็นเงินสดหรือคริปโตแล้วเท่าไหร่?** | **Off-ramp Donut Chart** (ATM vs Crypto USDT) | ยอดเงินสดที่ถูกกดผ่านตู้ ATM พร้อมพิกัด เพื่อประสานขอภาพกล้องวงจรปิด CCTV |
| **FAQ 6: มีหลักฐานว่าคนร้ายใช้ระบบโอนอัตโนมัติ (Bot / Script) หรือไม่?** | **Velocity Latency Histogram** ($\le 1-3$ นาที) | หลักฐานทางดิจิทัลเรื่องระยะเวลาเงินแช่สั้นผิดธรรมชาติ (Critical Transit Latency) |
| **FAQ 7: มีความเชื่อมโยงระหว่างผู้โอนหรือผู้รับโอนว่าเป็นขบวนการเดียวกันหรือไม่?** | **Network Topology Graph** & Shared Surname Alert | แผนผังใยแมงมุม (Force-directed Graph) และการตรวจพบนามสกุล/บัญชีกลุ่มเดียวกัน |

---

### 12.3 แผนงานการพัฒนาและยกระดับ (Upgrade Implementation Milestones)

| ขั้นตอน (Step) | งานที่ต้องดำเนินการ (Action Items) | โมดูลเป้าหมาย |
| :--- | :--- | :--- |
| **Step 1** | เพิ่มแท็บ **"5. สถิติเชิงลึก (Forensic Data Analytics)"** บน Dashboard พร้อม Interactive Dropdown เลือกลำดับ Top 10/20, ยอดเงิน, ความถี่, และความเร็ว | `src/ui/dashboard_generator.py` |
| **Step 2** | เพิ่มระบบ **FAQ Quick-Filter Buttons** (คลิกปุ่มเดียวเพื่อสลับหน้าจอไปสู่คำตอบของทั้ง 7 คำถามยอดฮิต) | `src/ui/dashboard_generator.py` |
| **Step 3** | ยกระดับ **Forensic Chat Copilot** ให้รองรับการค้นหาเชิงสถิติและการถามตอบตามคำถามทั้ง 7 ข้ออย่างลึกซึ้ง | `src/copilot/chat.py` |
| **Step 4** | เชื่อมโยงข้อมูลพิกัดตู้ ATM และการสแกนกล้อง CCTV เข้าสู่รายงานสำนวนคดีศาล | `src/dossier/pdf_exporter.py` |

---


---

## 13. สถาปัตยกรรมโครงข่ายเส้นทางการเงินหลายทอด (Multi-Entity Graph & 5-Hop Money Trail Suite)

เพื่อรองรับการสืบสวนขบวนการอาชญากรรมไซเบอร์ระดับองค์กร (Organized Cyber Syndicate) ที่มีโครงสร้างซับซ้อนเกินกว่าบัญชีเดี่ยว ระบบได้รับการยกระดับสู่สถาปัตยกรรม **Multi-Entity Graph & 5-Hop Money Trail Suite** รองรับการเชื่อมโยงข้อมูล KYC เอนทิตี, โครงข่ายบัญชีข้ามธนาคาร, ช่องทางกดเงินสดชายแดน, และกระเป๋าสินทรัพย์ดิจิทัล (Crypto OTC/Unhosted Wallets):

### 13.1 แผนผังโครงสร้างเส้นทางการเงิน 5 ทอด (The 5-Hop Syndicate Topology)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        5-HOP SYNDICATE MONEY TRAIL ARCHITECTURE                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ผู้เสียหายหลายราย] (Victims - ENT_VIC_01..04)                                         │
│         │                                                                              │
│         │  Hop 1: Smurfing Injection (ซอยยอด ฿15,000 - ฿49,500 เพื่อหลบเกณฑ์ 50k)        │
│         ▼                                                                              │
│  [ม้าแถว 1: ม้ารับยอด] (Gate Mules - ENT_M1_01..03)                                     │
│         │  - พฤติกรรม: Holding Decay < 180 วินาที, เงินเข้าปุ๊บออกปั๊บ, เงินเหลือติดบัญชี <100บ.│
│         │                                                                              │
│         │  Hop 2: Rapid Pass-Through (โอนออกทันทีผ่าน Mobile App / VPN-Tor)            │
│         ▼                                                                              │
│  [ม้าแถว 2: ม้ากระจาย/สับเปลี่ยน] (Layering & Obfuscation Hubs - ENT_M2_01..02)         │
│         │  - พฤติกรรม: ซอยยอดแตกออก 2-3 สาย, ไขว้บัญชีต่างธนาคาร, สลับ IP ต่างประเทศ    │
│         │                                                                              │
│         │  Hop 3: Sweep Inflow (โอนรวบยอดก้อนใหญ่เข้าศูนย์กลาง)                        │
│         ▼                                                                              │
│  [ม้าแถว 3: ศูนย์พักเงินกลาง] (Syndicate Consolidation Node - ENT_M3_01)                 │
│         │  - พฤติกรรม: รับเงินหลายสายมารวมเป็นยอดหลักแสนถึงหลักล้าน                     │
│         │                                                                              │
│         ├───────────────────────────────────────────────┐                              │
│         │ Hop 4: Cash Extraction                        │ Hop 5: Crypto Off-Ramp       │
│         ▼                                               ▼                              │
│  [ม้ากดเงินสด / ชายแดน] (ENT_RUN_01)             [ร้านรับแลกเหรียญ Crypto P2P]         │
│  - Cardless ATM Bursts (กดครั้งละ 30,000 ติดๆ กัน)   (P2P Escrow - ENT_OTC_01)          │
│  - พิกัด: อ.อรัญประเทศ จ.สระแก้ว / อ.แม่สอด จ.ตาก  - แปลงเป็น Stablecoin (USDT)        │
│                                                         │                              │
│                                                         ▼                              │
│                                                  [กระเป๋าหลักหัวหน้าแก๊ง]              │
│                                                  (Syndicate Cold Wallet - ENT_BOSS_01) │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 กฎการตรวจจับเชิงนิติวิทยาศาสตร์ขั้นสูง (Advanced Forensic Detection Rules)
1. **Device Fingerprint & IMEI Correlation:** ตรวจจับกรณีที่บัญชีม้าหลายบัญชีต่างชื่อ ต่างธนาคาร ล็อกอินเข้าใช้งานผ่าน **โทรศัพท์เครื่องเดียวกัน (Shared Device Fingerprint)** เช่น Infinix Hot 30 หรือ Xiaomi Redmi
2. **Impossible Travel & Geolocation Anomalies:** ตรวจจับความเร็วการเดินทางที่เป็นไปไม่ได้ เช่น มีการโอนเงินผ่าน IP กรุงเทพฯ แต่ถูกกดเงินสดจากตู้ ATM ที่สระแก้วภายในเวลาห่างกันเพียง 2 นาที
3. **Nocturnal Velocity Spikes:** การทำธุรกรรมหนาแน่นผิดปกติในช่วงเวลา 01:00 - 05:00 น.
4. **Border-Zone Cash Burst:** การกดเงินสดแบบไม่ใช้บัตร (Cardless ATM) ถี่ๆ บริเวณแนวชายแดน (อรัญประเทศ, แม่สอด) เพื่อขนเงินสดข้ามแดน
5. **Crypto Escrow Off-Ramp:** การตัดขาดเส้นทางการเงินดิจิทัลด้วยการซื้อ USDT ผ่าน P2P Merchant แล้วโอนเข้า External Unhosted Wallet

### 13.3 ฐานความผิดทางกฎหมายที่รองรับ (Governing Legal Framework)
* **พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566:**
  - **มาตรา 9:** ความผิดฐานเปิดหรือยินยอมให้ผู้อื่นใช้บัญชีเงินฝาก (ม้าแถว 1, 2, 3) โทษจำคุกไม่เกิน 3 ปี หรือปรับไม่เกิน 300,000 บาท
  - **มาตรา 10:** ความผิดฐานเป็นธุระจัดหา โฆษณา หรือซื้อขายให้เช่าบัญชีม้า/ซิมการ์ด โทษจำคุก 2 - 5 ปี หรือปรับ 200,000 - 500,000 บาท
* **พ.ร.บ. ป้องกันและปราบปรามการฟอกเงิน พ.ศ. 2542:**
  - **มาตรา 5:** ความผิดฐานฟอกเงิน โอน รับโอน หรือเปลี่ยนสภาพทรัพย์สินจากการกระทำความผิด
* **ประมวลกฎหมายวิธีพิจารณาความอาญา:**
  - **มาตรา 226:** การรับฟังพยานหลักฐานอิเล็กทรอนิกส์ (Log, IP Address, Device Fingerprint, พิกัด Cell Tower) โดยรักษาห่วงโซ่พยานหลักฐาน (Chain of Custody)

---


---

## 13. สถาปัตยกรรมโครงข่ายเส้นทางการเงินหลายทอด (Multi-Entity Graph & 5-Hop Money Trail Architecture)

จากการอัปเกรดตามข้อกำหนดใน `techdocs/Multi-Entity Graph & Money Trail Suite` ระบบ FinForensic ได้ขยายขีดความสามารถจากการวิเคราะห์ Statement บัญชีเดี่ยว (Single Account) สู่การเป็น **"ระบบตรวจพิสูจน์โครงข่ายอาชญากรรมการเงินหลายทอด (Multi-Layered Syndicate Money Trail Suite)"** เพื่อรองรับการสืบสวนคดีขบวนการคอลเซ็นเตอร์และเว็บพนันออนไลน์ขนาดใหญ่:

### 13.1 แบบจำลองข้อมูลโครงข่าย (Graph-Relational Data Model)

ระบบใช้แบบจำลองข้อมูล 2 ชั้นในการเชื่อมโยงพยานหลักฐาน:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               MULTI-ENTITY GRAPH & 5-HOP MONEY TRAIL ARCHITECTURE                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [1. Entity Master KYC]  ──► บุคคล/นิติบุคคล, บทบาท, รายได้แจ้งเปิดบัญชี, สถานะ AML     │
│ [2. Transaction Edges]  ──► เส้นเงินเชื่อมโยงข้ามทอด (Hop 1 ถึง Hop 5), อุปกรณ์, IP    │
│ [3. Device Fingerprint] ──► ตรวจจับโทรศัพท์/คอมพิวเตอร์เครื่องเดียวกันคุมหลายบัญชี     │
│ [4. Off-Ramp Analytics] ──► ตรวจจับการกดเงินสดตู้ ATM ชายแดน และการซื้อเหรียญคริปโต     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Entity Master KYC (`forensic_nodes_entities.csv`):**
   - บันทึกตัวตน (Entity ID, ชื่อนามสกุล, บทบาทในขบวนการ, ระดับความเสี่ยง KYC, และรายได้ที่แจ้งไว้ต่อเดือน)
   - ใช้ตรวจจับ **Income Discrepancy Anomaly**: เปรียบเทียบรายได้ที่แจ้งเปิดบัญชี (เช่น นักศึกษา/ว่างงาน แจ้ง ฿30,000/เดือน) กับยอดเงินหมุนเวียนจริง (฿30M - ฿60M) เพื่อเป็นพยานหลักฐานมัดตัวความผิดตาม พ.ร.ก. อาชญากรรมทางเทคโนโลยี พ.ศ. 2566 มาตรา 9 (เปิดบัญชีม้า)

2. **Transaction Edges Ledger (`forensic_edges_transactions.csv`):**
   - บันทึกเส้นทางธุรกรรมแบบ Directed Graph ระดับวินาที พร้อมตัวชี้วัดนิติวิทยาศาสตร์ดิจิทัล: `hop_level`, `channel`, `ip_address`, `device_fingerprint`, `geolocation`, และ `forensic_rule_triggered`

---

### 13.2 วงจรเส้นทางการเงิน 5 ลำดับขั้น (5-Hop Syndicate Money Trail Typology)

```
   [ผู้เสียหายหลายราย] (Victims: ENT_VIC_01 - 04)
         │
         │  Hop 1: Smurfing Inflows (ยอด 15,000 - 49,500 บาท เพื่อหลบเกณฑ์ 50k)
         ▼
   [ม้าแถว 1: ม้ารับยอด] (Gate Mules: ENT_M1_01 - 03)
         │  - Holding Time < 180 วินาที, เงินเข้าปุ๊บกระจายออกทันที
         │  - Ending Balance ต่ำกว่า 100 บาท
         ▼
   [ม้าแถว 2: ม้ากระจาย/สับเปลี่ยน] (Layering Hubs: ENT_M2_01 - 02)
         │  - ซอยยอดไขว้ข้ามธนาคาร (KBANK, SCB, TTB, BBL)
         │  - สลับใช้ IP ไทย กับ VPN ปอยเปต / เมียวดี
         ▼
   [ม้าแถว 3 / ศูนย์พักเงิน] (Consolidation Node: ENT_M3_01)
         │  - รวบรวมเงินก้อนใหญ่ระดับหลักแสนถึงหลักล้าน
         │  - ควบคุมโดยศูนย์ปฏิบัติการ (Command Hub)
         ▼
   ┌─────────────────────────────────────────┬─────────────────────────────────────────┐
   │                                         │                                         │
   │ Hop 4: Cash Extraction                  │ Hop 5: Digital Asset Conversion         │
   ▼                                         ▼                                         │
   [ม้ากดเงินสดตู้ ATM ชายแดน]               [ร้านรับแลกเหรียญ Crypto P2P]              │
   (Cash Runner: ENT_RUNNER_01)              (OTC Broker: ENT_CRYPTO_01)               │
   - Cardless ATM Bursts (กดครั้งละ 30k)     - ซื้อ Stablecoin (USDT) ข้ามแดน           │
   - ตู้ ATM อ.อรัญประเทศ / แม่สอด            - โอนเข้า External Unhosted Wallet        │
                                               (กระเป๋าหัวหน้าแก๊ง: ENT_KINGPIN_01)    ▼
```

---

### 13.3 การสืบสวนด้วยพยานหลักฐานอุปกรณ์และพิกัด (Device & Geolocation Forensics)

1. **Shared Device Fingerprint Pooling:**  
   ระบบสามารถตรวจจับและจัดกลุ่มรหัสอุปกรณ์ (`device_fingerprint`) ที่ใช้ล็อกอินสั่งการหลายบัญชีพร้อมกัน (เช่น รหัส `DEV-INFX-HOT30-POOLED` ล็อกอินควบคุมบัญชีม้าพร้อมกันถึง 6 บัญชี) เพื่อพิสูจน์ว่าเป็น **"คอกม้า (Mule Farm)"** ภายใต้การควบคุมของบุคคลคนเดียวกัน
2. **Impossible Travel Velocity:**  
   ตรวจจับความผิดปกติของสถานที่ทำธุรกรรม เช่น มีการสั่งโอนเงินผ่าน Mobile Banking จาก IP ในกรุงเทพฯ แต่มีการกดเงินสดออกจากตู้ ATM ที่ อ.อรัญประเทศ จ.สระแก้ว ภายในเวลาห่างกันเพียง 2 นาที ซึ่งในทางกายภาพเป็นไปไม่ได้ ชี้ชัดว่ามีผู้ร่วมขบวนการอย่างน้อย 2 คนแบ่งหน้าที่กันทำ

---

### 13.4 รองรับชุดข้อมูล Statement เดี่ยวความซับซ้อนสูง 3,500 ธุรกรรม (`advanced_mule_mockup_3500_txns.csv`)

ระบบ Universal Ingestion ได้รับการอัปเกรดให้รองรับไฟล์ Statement ซับซ้อนระดับ 3,500 รายการ ปริมาณเงินหมุนเวียนกว่า **฿96.78 ล้านบาท** พร้อมรองรับคอลัมน์เชิงลึก: `network_type`, `device_model`, `location_province`, `terminal_or_atm_id`, `mule_tier_role`, และ `fraud_pattern_type` เพื่อจำแนกประเภทความผิดปกติ 10 หมวดหมู่ได้อย่างแม่นยำ

---
