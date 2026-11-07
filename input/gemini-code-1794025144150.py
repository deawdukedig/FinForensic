import random
from datetime import datetime, timedelta
import pandas as pd

# กำหนด Seed เพื่อให้ผลลัพธ์สามารถทำซ้ำได้
random.seed(42)

# บัญชีเป้าหมาย (ม้านิติบุคคล)
acct_no = 9012345678
acct_name = "บริษัท สยาม อัลฟ่า เทรดดิ้ง จำกัด"

# ผู้เสียหาย 20 ราย
victims = [
    ("GSB", "x1001", "จ่าสิบตรี ภานุวัฒน์"),
    ("KBANK", "x1002", "นาง นิภาภัทร ธรรมเจริญ"),
    ("TTB", "x1003", "นาย ธนดล ธรรมเจริญ"),
    ("BBL", "x1004", "MS SIRIPORN P"),
    ("KTB", "x1005", "MRS.SOMSRI THAISONG"),
    ("SCB", "x1006", "นาง มาลี สุวรรณโชติ"),
    ("BAY", "x1007", "SUPAPORN S"),
    ("KTB", "x1008", "KANYAPAT P"),
    ("SCB", "x1010", "นาง สุภาพร เจริญยิ่ง"),
    ("SCB", "x1011", "นาย วรเมธ กิตติพงษ์"),
    ("BBL", "x1012", "WARUNEE S MRS"),
    ("SCB", "x1013", "นาง สุพัตรา ทวีทรัพย์"),
    ("BBL", "x1014", "MS CHALITA SUKSAWAT"),
    ("KBANK", "x1015", "น.ส. นภาภรณ์ ศ"),
    ("SCB", "x1016", "นาง ปิยะพร อุดมสุข"),
    ("KTB", "x1017", "MRS.PRANEE R"),
    ("KTB", "x1018", "MISSKANYA S"),
    ("TTB", "x1019", "นาง สมพร บุญมี"),
    ("KTB", "x1020", "PIMCHANOK B"),
    ("BAY", "x1021", "นาย ชัยวัฒน์ รัตนศิริ"),
]

# บัญชีรับโอนออก (Mule แถว 2 / ร้านค้าแลกเปลี่ยน / บัญชีรวบรวม)
destinations = [
    ("BBL", "x8001", "MR.SOKHA CHAN", "MR.SOKHA CH", 5),
    ("BBL", "x8002", "MRS LINDA CHEN", "MRS LINDA CHEN", 5),
    ("พร้อมเพย์", "x8003", "นางสาว กมลพร วงศ์สุวรรณ", "นางสาว กมลพร", 10),
    ("SCB", "x8004", "MRS. SOPHEA SAR", "MRS. SOPHEA SAR", 5),
    ("KBANK", "x8005", "นาย ธีรภัทร บุญเสริม", "นาย ธีรภัทร บ", 5),
    ("KTB", "x8006", "น.ส. จรรยา มิ่งขวัญ", "น.ส. จรรยา ม", 5),
    ("KBANK", "x8007", "น.ส. อรอุมา แสนสุข", "น.ส. อรอุมา แ", 5),
    (
        "SCB",
        "x8008",
        "ห้างหุ้นส่วนจำกัด สยามพาร์ทเนอร์",
        "ห้างหุ้นส่วนจำกัด สยามพาร์ทเนอร์",
        5,
    ),
    ("KK", "x1009", "นาง รัตนา วงศ์สวัสดิ์", "นาง รัตนา ว", 5),
]

current_time = datetime(2026, 8, 20, 8, 30, 0)
current_balance = 20.06
rows = []

while len(rows) < 2500:
    # สุ่มรูปแบบ: 1=เหยื่อโอนเข้า 1 ยอดแล้วโอนออกทันที, 2=Smurfing เข้า 2-4 ยอดแล้วรวบโอนออก
    mode = random.choices(["single_passthrough", "smurfing_batch"], weights=[0.4, 0.6])[0]

    if mode == "single_passthrough":
        # เงินเข้าจากเหยื่อ
        current_time += timedelta(minutes=random.randint(2, 15), seconds=random.randint(5, 50))
        v_bank, v_acc, v_name = random.choice(victims)
        in_amt = int(random.choice([random.randint(300, 3500), random.randint(10000, 49000), random.randint(50000, 250000)]))
        current_balance += in_amt
        rows.append({
            "ACCT_NO": acct_no,
            "ACCT_NAME": acct_name,
            "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
            "TRAN_TIME": current_time.strftime("%H:%M:%S"),
            "ACTIVITIE": "XD",
            "CHANNEL": "ENET",
            "TRAN_AMT": in_amt,
            "BALANCE": round(current_balance, 2),
            "DESCRIPTION": f"รับโอนจาก {v_bank} {v_acc} {v_name}",
        })

        if len(rows) >= 2500:
            break

        # โอนออกแทบทันที (Holding time < 3 นาที)
        current_time += timedelta(seconds=random.randint(25, 120))
        dst_bank, dst_acc, dst_name, dst_short, fee = random.choice(destinations)
        out_amt = int(in_amt * random.uniform(0.96, 0.99))
        if out_amt <= 0:
            out_amt = in_amt

        current_balance -= out_amt
        rows.append({
            "ACCT_NO": acct_no,
            "ACCT_NAME": acct_name,
            "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
            "TRAN_TIME": current_time.strftime("%H:%M:%S"),
            "ACTIVITIE": "XW",
            "CHANNEL": "BCMS",
            "TRAN_AMT": out_amt,
            "BALANCE": round(current_balance, 2),
            "DESCRIPTION": f"โอนไป {dst_bank} {dst_acc} {dst_name}" if dst_bank != "พร้อมเพย์" else f"โอนไปพร้อมเพย์ {dst_acc} {dst_name}",
        })

        if len(rows) >= 2500:
            break

        # ค่าธรรมเนียม
        current_balance -= fee
        rows.append({
            "ACCT_NO": acct_no,
            "ACCT_NAME": acct_name,
            "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
            "TRAN_TIME": current_time.strftime("%H:%M:%S"),
            "ACTIVITIE": "FE",
            "CHANNEL": "BCMS",
            "TRAN_AMT": fee,
            "BALANCE": round(current_balance, 2),
            "DESCRIPTION": f"ค่าธรรมเนียมโอนไป {dst_bank} {dst_acc} {dst_short}" if dst_bank != "พร้อมเพย์" else f"ค่าธรรมเนียมพร้อมเพย์ {dst_acc} {dst_short}",
        })

    else:
        # Smurfing: รับโอนจากเหยื่อหลายรายติดต่อกัน
        batch_count = random.randint(2, 4)
        batch_sum = 0
        for _ in range(batch_count):
            if len(rows) >= 2500:
                break
            current_time += timedelta(minutes=random.randint(1, 8), seconds=random.randint(5, 45))
            v_bank, v_acc, v_name = random.choice(victims)
            in_amt = int(random.choice([random.randint(338, 2500), random.randint(5000, 39900)]))
            current_balance += in_amt
            batch_sum += in_amt
            rows.append({
                "ACCT_NO": acct_no,
                "ACCT_NAME": acct_name,
                "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
                "TRAN_TIME": current_time.strftime("%H:%M:%S"),
                "ACTIVITIE": "XD",
                "CHANNEL": "ENET",
                "TRAN_AMT": in_amt,
                "BALANCE": round(current_balance, 2),
                "DESCRIPTION": f"รับโอนจาก {v_bank} {v_acc} {v_name}",
            })

        if len(rows) >= 2500:
            break

        # รวบยอดโอนออกก้อนใหญ่ (Consolidation Sweep)
        current_time += timedelta(minutes=random.randint(1, 4))
        dst_bank, dst_acc, dst_name, dst_short, fee = random.choice(destinations)
        out_amt = int(batch_sum * random.uniform(0.97, 0.995))
        current_balance -= out_amt
        rows.append({
            "ACCT_NO": acct_no,
            "ACCT_NAME": acct_name,
            "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
            "TRAN_TIME": current_time.strftime("%H:%M:%S"),
            "ACTIVITIE": "XW",
            "CHANNEL": "BCMS",
            "TRAN_AMT": out_amt,
            "BALANCE": round(current_balance, 2),
            "DESCRIPTION": f"โอนไป {dst_bank} {dst_acc} {dst_name}" if dst_bank != "พร้อมเพย์" else f"โอนไปพร้อมเพย์ {dst_acc} {dst_name}",
        })

        if len(rows) >= 2500:
            break

        current_balance -= fee
        rows.append({
            "ACCT_NO": acct_no,
            "ACCT_NAME": acct_name,
            "TRAN_DATE": current_time.strftime("%d/%m/%Y"),
            "TRAN_TIME": current_time.strftime("%H:%M:%S"),
            "ACTIVITIE": "FE",
            "CHANNEL": "BCMS",
            "TRAN_AMT": fee,
            "BALANCE": round(current_balance, 2),
            "DESCRIPTION": f"ค่าธรรมเนียมโอนไป {dst_bank} {dst_acc} {dst_short}" if dst_bank != "พร้อมเพย์" else f"ค่าธรรมเนียมพร้อมเพย์ {dst_acc} {dst_short}",
        })

df_result = pd.DataFrame(rows[:2500])
df_result.to_csv("statement_mockup_2500.csv", index=False, encoding="utf-8-sig")
print("Export completed: statement_mockup_2500.csv (2,500 rows)")