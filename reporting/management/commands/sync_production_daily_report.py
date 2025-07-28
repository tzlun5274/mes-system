# -*- coding: utf-8 -*-
"""
這個指令會自動同步作業員績效數據到生產日報表：
- 從 OperatorPerformance 數據中生成 ProductionDailyReport 數據
- 按照日期、作業員/SMT產線、設備分組統計
- 自動計算完成率、效率等指標
"""
from django.core.management.base import BaseCommand
from reporting.models import OperatorPerformance, ProductionDailyReport
from django.utils import timezone
from collections import defaultdict
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "自動同步作業員績效數據到生產日報表"

    def handle(self, *args, **options):
        self.stdout.write("開始同步生產日報表數據...")
        
        # 清除舊的生產日報表數據
        deleted_count = ProductionDailyReport.objects.all().delete()[0]
        self.stdout.write(f"已清除 {deleted_count} 筆舊的生產日報表數據")
        
        # 從 OperatorPerformance 獲取數據
        operator_performances = OperatorPerformance.objects.all()
        
        # 按日期、作業員/SMT產線、設備分組
        grouped_data = defaultdict(lambda: {
            'production_quantity': 0,
            'total_work_hours': 0.0,
            'work_order': '',
            'product_name': '',
            'process_name': '',
            'line': 'SMT1'  # 預設生產線
        })
        
        for performance in operator_performances:
            # 判斷是作業員還是 SMT 產線
            operator_or_line = performance.operator_name
            if 'SMT' in performance.operator_name or '自動化' in performance.operator_name:
                # 如果是 SMT 相關，使用設備名稱作為產線
                if 'P_LINE' in performance.equipment_name:
                    operator_or_line = 'SMT-P_LINE'
                elif 'SMT' in performance.equipment_name:
                    operator_or_line = performance.equipment_name
                else:
                    operator_or_line = performance.operator_name
            
            key = (performance.date, operator_or_line, performance.equipment_name)
            
            grouped_data[key]['production_quantity'] += performance.production_quantity
            
            # 計算每筆記錄的工作時數並累加
            if performance.start_time and performance.end_time:
                duration = performance.end_time - performance.start_time
                work_hours = duration.total_seconds() / 3600
                grouped_data[key]['total_work_hours'] += work_hours
            
            # 記錄工單和產品資訊
            if performance.work_order:
                grouped_data[key]['work_order'] = performance.work_order
            if performance.product_name:
                grouped_data[key]['product_name'] = performance.product_name
            if performance.process_name:
                grouped_data[key]['process_name'] = performance.process_name
        
        # 生成 ProductionDailyReport 記錄
        created_count = 0
        for (date, operator_or_line, equipment_name), data in grouped_data.items():
            # 計算效率 (件/小時)
            efficiency_rate = 0.0
            if data['total_work_hours'] > 0:
                efficiency_rate = (data['production_quantity'] / data['total_work_hours']) * 100
            
            # 計算完成率 (假設為100%，因為這是實際完成的數據)
            completion_rate = 100.0
            
            # 創建 ProductionDailyReport 記錄
            ProductionDailyReport.objects.create(
                date=date,
                operator_or_line=operator_or_line,
                equipment_name=equipment_name,
                line=data['line'],
                production_quantity=data['production_quantity'],
                completed_quantity=data['production_quantity'],  # 假設生產數量等於完成數量
                completion_rate=completion_rate,
                work_hours=data['total_work_hours'],
                efficiency_rate=efficiency_rate,
                process_name=data['process_name']
            )
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"成功同步 {created_count} 筆生產日報表數據")
        ) 