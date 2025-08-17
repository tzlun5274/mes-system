#!/usr/bin/env python3
"""
出貨包裝填報記錄除錯腳本
檢查填報記錄的資料結構和計算邏輯
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db.models import Sum
from workorder.fill_work.models import FillWork
from workorder.models import WorkOrder
from erp_integration.models import CompanyConfig

def debug_packaging_records():
    """除錯出貨包裝填報記錄"""
    print("=== 出貨包裝填報記錄除錯 ===")
    
    # 1. 檢查所有出貨包裝填報記錄
    print("\n1. 所有出貨包裝填報記錄:")
    packaging_reports = FillWork.objects.filter(
        process__name__exact='出貨包裝'
    )
    print(f"總記錄數: {packaging_reports.count()}")
    
    for report in packaging_reports:
        print(f"  - 工單號: {report.workorder}, 產品: {report.product_id}, 公司: {report.company_name}, 數量: {report.work_quantity}, 狀態: {report.approval_status}")
    
    # 2. 檢查已核准的出貨包裝填報記錄
    print("\n2. 已核准的出貨包裝填報記錄:")
    approved_packaging_reports = FillWork.objects.filter(
        process__name__exact='出貨包裝',
        approval_status='approved'
    )
    print(f"已核准記錄數: {approved_packaging_reports.count()}")
    
    for report in approved_packaging_reports:
        print(f"  - 工單號: {report.workorder}, 產品: {report.product_id}, 公司: {report.company_name}, 數量: {report.work_quantity}")
    
    # 3. 檢查公司配置
    print("\n3. 公司配置:")
    company_configs = CompanyConfig.objects.all()
    for config in company_configs:
        print(f"  - 代號: {config.company_code}, 名稱: {config.company_name}")
    
    # 4. 檢查工單資料
    print("\n4. 工單資料:")
    workorders = WorkOrder.objects.all()[:5]  # 只顯示前5個
    for workorder in workorders:
        print(f"  - 工單號: {workorder.order_number}, 產品: {workorder.product_code}, 公司代號: {workorder.company_code}")
    
    # 5. 測試特定工單的出貨包裝計算
    print("\n5. 測試特定工單的出貨包裝計算:")
    if workorders.exists():
        test_workorder = workorders.first()
        print(f"測試工單: {test_workorder.order_number}")
        
        # 計算填報記錄數量
        fillwork_reports = FillWork.objects.filter(
            workorder=test_workorder.order_number,
            process__name__exact="出貨包裝",
            approval_status='approved'
        )
        
        print(f"  找到填報記錄: {fillwork_reports.count()} 筆")
        for report in fillwork_reports:
            print(f"    - 公司: {report.company_name}, 數量: {report.work_quantity}")
        
        # 按公司分離
        if test_workorder.company_code:
            company_config = CompanyConfig.objects.filter(
                company_code=test_workorder.company_code
            ).first()
            
            if company_config:
                fillwork_reports_filtered = fillwork_reports.filter(
                    company_name=company_config.company_name
                )
                print(f"  按公司 '{company_config.company_name}' 過濾後: {fillwork_reports_filtered.count()} 筆")
                
                total_quantity = fillwork_reports_filtered.aggregate(
                    total=Sum('work_quantity')
                )['total'] or 0
                print(f"  總數量: {total_quantity}")
            else:
                print(f"  找不到公司配置: {test_workorder.company_code}")
        else:
            print("  工單沒有公司代號")

if __name__ == '__main__':
    debug_packaging_records() 