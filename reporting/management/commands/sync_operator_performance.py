# -*- coding: utf-8 -*-
"""
這個指令會自動同步所有補登紀錄到作業員生產報表：
- 只要補登紀錄已核准、動作為完成，就會依照作業員+設備+日期分組，統計生產數量與設備使用率。
- 自動寫入OperatorPerformance資料表。
"""
from django.core.management.base import BaseCommand
from workorder.models import WorkOrderProcessSupplementLog, WorkOrderProcess, SystemConfig
from equip.models import Equipment
from reporting.models import OperatorPerformance
from django.utils import timezone
from collections import defaultdict

class Command(BaseCommand):
    help = '自動同步所有補登紀錄到作業員生產報表'

    def handle(self, *args, **options):
        # 取得只在最後一天計算產量的工序關鍵字
        try:
            config = SystemConfig.objects.get(key='final_day_only_process_keywords')
            final_day_keywords = [k.strip() for k in config.value.split(',') if k.strip()]
        except SystemConfig.DoesNotExist:
            final_day_keywords = []
        # 先依工序、作業員、設備、工單、產品、工序名稱分組所有補登紀錄
        grouped_logs = defaultdict(list)
        for log in WorkOrderProcessSupplementLog.objects.filter(is_approved=True, action_type='complete'):
            operator = log.operator.name if log.operator else '未指定作業員'
            process = log.workorder_process
            equipment_id = process.assigned_equipment or ''
            equipment_name = ''
            if equipment_id:
                try:
                    equipment_obj = Equipment.objects.filter(id=equipment_id).first()
                    equipment_name = equipment_obj.name if equipment_obj else str(equipment_id)
                except Exception:
                    equipment_name = str(equipment_id)
            else:
                equipment_name = '未分配設備'
            work_order = process.workorder.order_number if hasattr(process, 'workorder') and process.workorder else ''
            product_name = process.workorder.product_code if hasattr(process, 'workorder') and process.workorder else ''
            process_name = process.process_name if hasattr(process, 'process_name') else ''
            key = (operator, equipment_name, work_order, product_name, process_name)
            grouped_logs[key].append(log)
        count = 0
        for (operator, equipment_name, work_order, product_name, process_name), logs in grouped_logs.items():
            # 依日期排序
            logs = sorted(logs, key=lambda l: l.supplement_time)
            # 判斷是否為只在最後一天計算產量的工序
            is_final_day_only = any(kw in process_name for kw in final_day_keywords)
            if is_final_day_only:
                # 只在最後一天計算產量
                for i, log in enumerate(logs):
                    date = log.supplement_time.date()
                    qty = log.completed_quantity if i == len(logs)-1 else 0
                    OperatorPerformance.objects.update_or_create(
                        operator_name=operator,
                        equipment_name=equipment_name,
                        date=date,
                        work_order=work_order,
                        product_name=product_name,
                        process_name=process_name,
                        defaults={
                            'production_quantity': qty,
                            'equipment_usage_rate': 100.0 if qty > 0 else 0.0,
                            'start_time': log.supplement_time,
                            'end_time': log.end_time,
                        }
                    )
                    count += 1
            else:
                # 依工時自動分攤
                total_hours = sum(((l.end_time-l.supplement_time).total_seconds()/3600) if l.end_time and l.supplement_time else 0 for l in logs)
                total_qty = sum(l.completed_quantity or 0 for l in logs)
                # 若只有最後一天有數量，前面天數沒填，則自動分攤
                if total_qty > 0 and any((l.completed_quantity or 0)==0 for l in logs):
                    for log in logs:
                        date = log.supplement_time.date()
                        hours = ((log.end_time-log.supplement_time).total_seconds()/3600) if log.end_time and log.supplement_time else 0
                        qty = int(round(total_qty * hours / total_hours)) if total_hours > 0 else 0
                        OperatorPerformance.objects.update_or_create(
                            operator_name=operator,
                            equipment_name=equipment_name,
                            date=date,
                            work_order=work_order,
                            product_name=product_name,
                            process_name=process_name,
                            defaults={
                                'production_quantity': qty,
                                'equipment_usage_rate': 100.0 if qty > 0 else 0.0,
                                'start_time': log.supplement_time,
                                'end_time': log.end_time,
                            }
                        )
                        count += 1
                else:
                    # 每天有填數量就照原本邏輯
                    for log in logs:
                        date = log.supplement_time.date()
                        qty = log.completed_quantity or 0
                        OperatorPerformance.objects.update_or_create(
                            operator_name=operator,
                            equipment_name=equipment_name,
                            date=date,
                            work_order=work_order,
                            product_name=product_name,
                            process_name=process_name,
                            defaults={
                                'production_quantity': qty,
                                'equipment_usage_rate': 100.0 if qty > 0 else 0.0,
                                'start_time': log.supplement_time,
                                'end_time': log.end_time,
                            }
                        )
                        count += 1
        self.stdout.write(self.style.SUCCESS(f'已同步 {count} 筆作業員生產報表資料（含自訂關鍵字分攤邏輯）')) 