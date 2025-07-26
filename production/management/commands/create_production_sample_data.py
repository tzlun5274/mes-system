# 產線管理範例資料建立命令
# 此檔案用於建立產線管理模組的範例資料，包含產線類型、產線和排程記錄

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time, timedelta
import random
from production.models import ProductionLineType, ProductionLine, ProductionLineSchedule


class Command(BaseCommand):
    help = "建立產線管理模組的範例資料"

    def handle(self, *args, **options):
        self.stdout.write("開始建立產線管理範例資料...")

        # 建立產線類型
        line_types = self.create_line_types()

        # 建立產線
        production_lines = self.create_production_lines(line_types)

        # 建立排程記錄
        self.create_schedules(production_lines)

        self.stdout.write(self.style.SUCCESS("產線管理範例資料建立完成！"))

    def create_line_types(self):
        """建立產線類型"""
        line_types_data = [
            {
                "type_code": "SMT",
                "type_name": "SMT產線",
                "description": "表面黏著技術產線，用於電子元件的自動化組裝",
            },
            {
                "type_code": "ASSY",
                "type_name": "組裝產線",
                "description": "產品組裝產線，用於最終產品的組裝和測試",
            },
            {
                "type_code": "TEST",
                "type_name": "測試產線",
                "description": "產品測試產線，用於品質檢驗和功能測試",
            },
            {
                "type_code": "PACK",
                "type_name": "包裝產線",
                "description": "產品包裝產線，用於最終包裝和出貨準備",
            },
        ]

        line_types = []
        for data in line_types_data:
            line_type, created = ProductionLineType.objects.get_or_create(
                type_code=data["type_code"], defaults=data
            )
            if created:
                self.stdout.write(f"建立產線類型：{line_type.type_name}")
            line_types.append(line_type)

        return line_types

    def create_production_lines(self, line_types):
        """建立產線"""
        lines_data = [
            {
                "line_code": "SMT01",
                "line_name": "SMT產線1",
                "line_type": line_types[0],  # SMT
                "description": "主要SMT產線，負責高精度電子元件組裝",
                "work_start_time": time(8, 0),
                "work_end_time": time(17, 0),
                "lunch_start_time": time(12, 0),
                "lunch_end_time": time(13, 0),
                "overtime_start_time": time(17, 0),
                "overtime_end_time": time(20, 0),
                "has_lunch_break": True,
            },
            {
                "line_code": "SMT02",
                "line_name": "SMT產線2",
                "line_type": line_types[0],  # SMT
                "description": "備用SMT產線，支援產能擴充",
                "work_start_time": time(8, 30),
                "work_end_time": time(17, 30),
                "lunch_start_time": None,
                "lunch_end_time": None,
                "overtime_start_time": time(17, 30),
                "overtime_end_time": time(21, 0),
                "has_lunch_break": False,
            },
            {
                "line_code": "ASSY01",
                "line_name": "組裝產線1",
                "line_type": line_types[1],  # ASSY
                "description": "主要組裝產線，負責產品最終組裝",
                "work_start_time": time(7, 30),
                "work_end_time": time(16, 30),
                "lunch_start_time": time(11, 30),
                "lunch_end_time": time(12, 30),
                "overtime_start_time": time(16, 30),
                "overtime_end_time": time(19, 30),
                "has_lunch_break": True,
            },
            {
                "line_code": "TEST01",
                "line_name": "測試產線1",
                "line_type": line_types[2],  # TEST
                "description": "品質測試產線，確保產品品質",
                "work_start_time": time(9, 0),
                "work_end_time": time(18, 0),
                "lunch_start_time": time(12, 30),
                "lunch_end_time": time(13, 30),
                "overtime_start_time": None,
                "overtime_end_time": None,
                "has_lunch_break": True,
            },
            {
                "line_code": "PACK01",
                "line_name": "包裝產線1",
                "line_type": line_types[3],  # PACK
                "description": "包裝出貨產線，負責最終包裝",
                "work_start_time": time(8, 0),
                "work_end_time": time(17, 0),
                "lunch_start_time": None,
                "lunch_end_time": None,
                "overtime_start_time": None,
                "overtime_end_time": None,
                "has_lunch_break": False,
            },
        ]

        production_lines = []
        for data in lines_data:
            line, created = ProductionLine.objects.get_or_create(
                line_code=data["line_code"],
                defaults={
                    "line_name": data["line_name"],
                    "line_type": data["line_type"],
                    "description": data["description"],
                    "work_start_time": data["work_start_time"],
                    "work_end_time": data["work_end_time"],
                    "lunch_start_time": data["lunch_start_time"],
                    "lunch_end_time": data["lunch_end_time"],
                    "overtime_start_time": data["overtime_start_time"],
                    "overtime_end_time": data["overtime_end_time"],
                    "is_active": True,
                },
            )

            # 設定工作日
            work_days = ["1", "2", "3", "4", "5"]  # 週一到週五
            line.set_work_days_list(work_days)
            line.save()

            if created:
                self.stdout.write(f"建立產線：{line.line_name}")
            production_lines.append(line)

        return production_lines

    def create_schedules(self, production_lines):
        """建立排程記錄"""
        # 建立未來30天的排程
        start_date = timezone.now().date()

        for line in production_lines:
            for i in range(30):
                schedule_date = start_date + timedelta(days=i)

                # 跳過週末
                if schedule_date.weekday() >= 5:  # 週六、週日
                    continue

                # 決定是否為假日
                is_holiday = random.random() < 0.1  # 10%機率為假日

                if is_holiday:
                    # 假日排程
                    schedule, created = ProductionLineSchedule.objects.get_or_create(
                        production_line=line,
                        schedule_date=schedule_date,
                        defaults={
                            "work_start_time": time(0, 0),
                            "work_end_time": time(0, 0),
                            "lunch_start_time": None,
                            "lunch_end_time": None,
                            "overtime_start_time": None,
                            "overtime_end_time": None,
                            "is_holiday": True,
                            "holiday_reason": random.choice(
                                ["國定假日", "設備維護", "停電", "特殊假日"]
                            ),
                            "work_days": "[]",
                        },
                    )
                else:
                    # 正常工作日排程
                    # 根據產線設定決定是否有午休時間
                    has_lunch_break = (
                        line.lunch_start_time is not None
                        and line.lunch_end_time is not None
                    )

                    schedule, created = ProductionLineSchedule.objects.get_or_create(
                        production_line=line,
                        schedule_date=schedule_date,
                        defaults={
                            "work_start_time": line.work_start_time,
                            "work_end_time": line.work_end_time,
                            "lunch_start_time": (
                                line.lunch_start_time if has_lunch_break else None
                            ),
                            "lunch_end_time": (
                                line.lunch_end_time if has_lunch_break else None
                            ),
                            "overtime_start_time": line.overtime_start_time,
                            "overtime_end_time": line.overtime_end_time,
                            "is_holiday": False,
                            "holiday_reason": "",
                            "work_days": '["1", "2", "3", "4", "5"]',
                        },
                    )

                if created:
                    self.stdout.write(f"建立排程：{line.line_name} - {schedule_date}")

        self.stdout.write("排程記錄建立完成")
