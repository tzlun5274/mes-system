# -*- coding: utf-8 -*-
"""
這個指令會自動同步所有補登紀錄到作業員生產報表：
- 只要補登紀錄已核准、動作為完成，就會依照作業員+設備+日期分組，統計生產數量與設備使用率。
- 自動寫入OperatorPerformance資料表。
"""
from django.core.management.base import BaseCommand
from workorder.models import (
    SMTProductionReport,
    OperatorSupplementReport,
    SupervisorProductionReport,
    WorkOrderProcess,
    SystemConfig,
)
from equip.models import Equipment
from reporting.models import OperatorPerformance
from django.utils import timezone
from collections import defaultdict
from datetime import datetime


class Command(BaseCommand):
    help = "自動同步所有補登紀錄到作業員生產報表"

    def handle(self, *args, **options):
        # 取得只在最後一天計算產量的工序關鍵字
        try:
            config = SystemConfig.objects.get(key="final_day_only_process_keywords")
            final_day_keywords = [
                k.strip() for k in config.value.split(",") if k.strip()
            ]
        except SystemConfig.DoesNotExist:
            final_day_keywords = []
        
        # 先依工序、作業員、設備、工單、產品、工序名稱分組所有報工記錄
        grouped_logs = defaultdict(list)
        
        # 1. 處理作業員補登報工記錄
        for report in OperatorSupplementReport.objects.filter(
            approval_status="approved"
        ):
            operator = report.operator.name if report.operator else "未指定作業員"
            equipment_name = report.equipment.name if report.equipment else "未分配設備"
            work_order = report.workorder.order_number if report.workorder else ""
            product_name = report.product_id
            process_name = report.operation
            
            key = (operator, equipment_name, work_order, product_name, process_name)
            grouped_logs[key].append({
                'type': 'operator',
                'date': report.work_date,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'quantity': report.work_quantity,
                'report': report
            })
        
        # 2. 處理主管生產報工記錄
        for report in SupervisorProductionReport.objects.filter(
            approval_status="approved"
        ):
            operator = report.operator.name if report.operator else "未指定作業員"
            equipment_name = report.equipment.name if report.equipment else "未分配設備"
            work_order = report.workorder.order_number if report.workorder else ""
            product_name = report.workorder.product_code if report.workorder else ""
            process_name = report.process.name if report.process else ""
            
            key = (operator, equipment_name, work_order, product_name, process_name)
            grouped_logs[key].append({
                'type': 'supervisor',
                'date': report.work_date,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'quantity': report.work_quantity,
                'report': report
            })
        
        # 3. 處理 SMT 生產報工記錄（SMT 不需要作業員）
        for report in SMTProductionReport.objects.filter(
            approval_status="approved"
        ):
            operator = "SMT自動化"  # SMT 不需要作業員
            equipment_name = report.equipment.name if report.equipment else "未分配設備"
            work_order = report.workorder.order_number if report.workorder else ""
            product_name = report.product_id
            process_name = report.operation
            
            key = (operator, equipment_name, work_order, product_name, process_name)
            grouped_logs[key].append({
                'type': 'smt',
                'date': report.work_date,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'quantity': report.work_quantity,
                'report': report
            })
        
        count = 0
        for (
            operator,
            equipment_name,
            work_order,
            product_name,
            process_name,
        ), logs in grouped_logs.items():
            # 依日期排序
            logs = sorted(logs, key=lambda l: l['date'])
            # 判斷是否為只在最後一天計算產量的工序
            is_final_day_only = any(kw in process_name for kw in final_day_keywords)
            if is_final_day_only:
                # 只在最後一天計算產量
                for i, log in enumerate(logs):
                    date = log['date']
                    qty = log['quantity'] if i == len(logs) - 1 else 0
                    
                    # 將 TimeField 轉換為 DateTimeField
                    start_datetime = datetime.combine(date, log['start_time']) if log['start_time'] else None
                    end_datetime = datetime.combine(date, log['end_time']) if log['end_time'] else None
                    
                    OperatorPerformance.objects.update_or_create(
                        operator_name=operator,
                        equipment_name=equipment_name,
                        date=date,
                        work_order=work_order,
                        product_name=product_name,
                        process_name=process_name,
                        defaults={
                            "production_quantity": qty,
                            "equipment_usage_rate": 100.0 if qty > 0 else 0.0,
                            "start_time": start_datetime,
                            "end_time": end_datetime,
                        },
                    )
                    count += 1
            else:
                # 依工時自動分攤
                total_hours = sum(
                    (
                        datetime.combine(datetime.today(), log['end_time']) - 
                        datetime.combine(datetime.today(), log['start_time'])
                    ).total_seconds() / 3600
                    for log in logs
                )
                
                if total_hours > 0:
                    total_quantity = sum(log['quantity'] for log in logs)
                    for log in logs:
                        hours = (
                            datetime.combine(datetime.today(), log['end_time']) - 
                            datetime.combine(datetime.today(), log['start_time'])
                        ).total_seconds() / 3600
                        
                        # 按比例分配產量
                        proportion = hours / total_hours
                        allocated_quantity = int(total_quantity * proportion)
                        
                        # 將 TimeField 轉換為 DateTimeField
                        start_datetime = datetime.combine(log['date'], log['start_time']) if log['start_time'] else None
                        end_datetime = datetime.combine(log['date'], log['end_time']) if log['end_time'] else None
                        
                        OperatorPerformance.objects.update_or_create(
                            operator_name=operator,
                            equipment_name=equipment_name,
                            date=log['date'],
                            work_order=work_order,
                            product_name=product_name,
                            process_name=process_name,
                            defaults={
                                "production_quantity": allocated_quantity,
                                "equipment_usage_rate": 100.0 if allocated_quantity > 0 else 0.0,
                                "start_time": start_datetime,
                                "end_time": end_datetime,
                            },
                        )
                        count += 1
                else:
                    # 如果沒有工時記錄，平均分配
                    total_quantity = sum(log['quantity'] for log in logs)
                    avg_quantity = total_quantity // len(logs) if logs else 0
                    
                    for i, log in enumerate(logs):
                        qty = avg_quantity + (total_quantity % len(logs) if i < total_quantity % len(logs) else 0)
                        
                        # 將 TimeField 轉換為 DateTimeField
                        start_datetime = datetime.combine(log['date'], log['start_time']) if log['start_time'] else None
                        end_datetime = datetime.combine(log['date'], log['end_time']) if log['end_time'] else None
                        
                        OperatorPerformance.objects.update_or_create(
                            operator_name=operator,
                            equipment_name=equipment_name,
                            date=log['date'],
                            work_order=work_order,
                            product_name=product_name,
                            process_name=process_name,
                            defaults={
                                "production_quantity": qty,
                                "equipment_usage_rate": 100.0 if qty > 0 else 0.0,
                                "start_time": start_datetime,
                                "end_time": end_datetime,
                            },
                        )
                        count += 1

        self.stdout.write(
            self.style.SUCCESS(f"成功同步 {count} 筆作業員生產報表記錄")
        )
