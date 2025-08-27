#!/usr/bin/env python3
"""
檢查有出貨包裝記錄的工單
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db.models import Sum
from workorder.models import WorkOrder
from workorder.production_monitoring.models import ProductionMonitoringData
from workorder.fill_work.models import FillWork

def debug_packaging_workorder():
    """檢查有出貨包裝記錄的工單"""
    print("=== 檢查有出貨包裝記錄的工單 ===")
    
    # 1. 找到有出貨包裝記錄的工單
    packaging_reports = FillWork.objects.filter(
        process__name__exact='出貨包裝',
        approval_status='approved'
    )
    
    print(f"\n1. 有出貨包裝記錄的工單:")
    for report in packaging_reports:
        print(f"   - 工單: {report.workorder}, 產品: {report.product_id}, 公司: {report.company_name}, 數量: {report.work_quantity}")
        
        # 2. 檢查該工單是否存在
        workorder = WorkOrder.objects.filter(order_number=report.workorder).first()
        if workorder:
            print(f"     ✓ 工單存在，狀態: {workorder.status}")
            
            # 3. 建立監控資料
            monitoring_data = ProductionMonitoringData.get_or_create_for_workorder(workorder)
            monitoring_data.update_all_statistics()
            monitoring_data.refresh_from_db()
            
            print(f"     ✓ 監控資料 - 出貨包裝總數量: {monitoring_data.packaging_total_quantity}")
            print(f"     ✓ 監控資料 - 出貨包裝良品: {monitoring_data.packaging_good_quantity}")
            print(f"     ✓ 監控資料 - 出貨包裝不良品: {monitoring_data.packaging_defect_quantity}")
        else:
            print(f"     ✗ 工單不存在")
    
    # 4. 檢查該工單的所有填報記錄
    if packaging_reports.exists():
        test_report = packaging_reports.first()
        print(f"\n2. 工單 {test_report.workorder} 的所有填報記錄:")
        
        all_reports = FillWork.objects.filter(
            workorder=test_report.workorder,
            product_id=test_report.product_id
        )
        
        for report in all_reports:
            print(f"   - 工序: {report.process.name}, 狀態: {report.approval_status}, 數量: {report.work_quantity}")

if __name__ == "__main__":
    debug_packaging_workorder() 