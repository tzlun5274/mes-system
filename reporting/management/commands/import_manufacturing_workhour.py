# -*- coding: utf-8 -*-
"""
這個指令會將『製造工時單 (回覆).xlsx』的資料一次性匯入 ManufacturingWorkHour 資料表。
執行方式：python manage.py import_manufacturing_workhour
"""
import os
import pandas as pd
from django.core.management.base import BaseCommand
from reporting.models import ManufacturingWorkHour
from django.utils import timezone
import re


class Command(BaseCommand):
    help = "將 Excel 工時單資料匯入 ManufacturingWorkHour"

    def handle(self, *args, **options):
        file_path = "製造工時單 (回覆).xlsx"
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"找不到檔案：{file_path}"))
            return
        # 讀取 Excel
        df = pd.read_excel(file_path)
        # 欄位對應
        mapping = {
            "作業員": "operator",
            "公司別": "company",
            "日期": "date",
            "開始時間": "start_time",
            "完成時間": "end_time",
            "製令號碼": "order_number",
            "機種名稱": "equipment_name",
            "工作內容": "work_content",
            "良品數量(只填數字)": "good_qty",
            "不良品數量(沒有請填0)": "defect_qty",
        }
        # 轉換欄位名稱
        df = df.rename(columns=mapping)
        # 處理日期欄位
        df["date"] = pd.to_datetime(df["date"]).dt.date
        # 匯入資料
        count = 0
        skip = 0
        for idx, row in df.iterrows():

            def safe_get(val, default):
                try:
                    if pd.isna(val) or str(val).strip() == "":
                        return default
                    return val
                except Exception:
                    return default

            good_qty = safe_get(row.get("good_qty", 0), 0)
            defect_qty = safe_get(row.get("defect_qty", 0), 0)
            operator = safe_get(row.get("operator", ""), "")
            company = safe_get(row.get("company", ""), "")
            date = safe_get(row.get("date", ""), "")
            start_time = safe_get(row.get("start_time", ""), "")
            end_time = safe_get(row.get("end_time", ""), "")
            order_number = safe_get(row.get("order_number", ""), "")
            equipment_name = safe_get(row.get("equipment_name", ""), "")
            work_content = safe_get(row.get("work_content", ""), "")

            # 只取數字部分
            def extract_int(val):
                if isinstance(val, str):
                    m = re.search(r"\d+", val)
                    return int(m.group()) if m else 0
                try:
                    return int(val)
                except:
                    return 0

            good_qty = extract_int(good_qty)
            defect_qty = extract_int(defect_qty)
            # 檢查日期格式
            if not date or str(date).strip() == "":
                print(f"略過第{idx+2}行：日期為空")
                skip += 1
                continue
            try:
                # 若不是datetime.date型別則嘗試轉換
                if not hasattr(date, "year"):
                    date = pd.to_datetime(date).date()
            except Exception:
                print(f"略過第{idx+2}行：日期格式錯誤({date})")
                skip += 1
                continue
            ManufacturingWorkHour.objects.create(
                operator=str(operator),
                company=str(company),
                date=date,
                start_time=str(start_time),
                end_time=str(end_time),
                order_number=str(order_number),
                equipment_name=str(equipment_name),
                work_content=str(work_content),
                good_qty=good_qty,
                defect_qty=defect_qty,
            )
            count += 1
        print(f"成功匯入 {count} 筆工時單資料，略過 {skip} 筆無效資料。")
