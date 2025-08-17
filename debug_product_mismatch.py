#!/usr/bin/env python3
"""
檢查產品代碼不匹配的問題
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db.models import Sum
from workorder.models import WorkOrder
from workorder.fill_work.models import FillWork

def debug_product_mismatch():
    """檢查產品代碼不匹配的問題"""
    print("=== 檢查產品代碼不匹配的問題 ===")
    
    # 1. 檢查出貨包裝記錄
    packaging_reports = FillWork.objects.filter(
        process__name__exact='出貨包裝',
        approval_status='approved'
    )
    
    print(f"\n1. 出貨包裝記錄:")
    for report in packaging_reports:
        print(f"   - 工單: {report.workorder}")
        print(f"   - 產品代碼: {report.product_id}")
        print(f"   - 公司: {report.company_name}")
        print(f"   - 數量: {report.work_quantity}")
        
        # 2. 檢查對應的工單
        workorder = WorkOrder.objects.filter(order_number=report.workorder).first()
        if workorder:
            print(f"   - 工單產品代碼: {workorder.product_code}")
            print(f"   - 產品代碼匹配: {report.product_id == workorder.product_code}")
        else:
            print(f"   - 工單不存在")
        print()
    
    # 3. 檢查工單的產品代碼
    workorder = WorkOrder.objects.filter(order_number='331-25220001').first()
    if workorder:
        print(f"\n2. 工單 {workorder.order_number} 的產品代碼:")
        print(f"   - 工單產品代碼: {workorder.product_code}")
        
        # 4. 檢查該工單的所有填報記錄
        all_reports = FillWork.objects.filter(workorder=workorder.order_number)
        print(f"\n3. 該工單的所有填報記錄:")
        for report in all_reports:
            print(f"   - 填報產品代碼: {report.product_id}")
            print(f"   - 工序: {report.process.name}")
            print(f"   - 狀態: {report.approval_status}")
            print(f"   - 數量: {report.work_quantity}")
            print()

if __name__ == "__main__":
    debug_product_mismatch() 