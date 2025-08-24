#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
調試出貨包裝統計 BUG
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.fill_work.models import FillWork

def debug_packaging_bug():
    """調試出貨包裝統計 BUG"""
    
    print("🐛 調試出貨包裝統計 BUG...")
    
    # 查找派工單 275
    dispatch = WorkOrderDispatch.objects.get(id=275)
    
    print(f"=== 派工單查詢條件 ===")
    print(f"  工單號: {dispatch.order_number}")
    print(f"  產品編號: {dispatch.product_code}")
    print(f"  公司代號: {dispatch.company_code}")
    print(f"  公司名稱: {dispatch._get_company_name()}")
    print()
    
    # 基本查詢
    fillwork_reports = FillWork.objects.filter(
        workorder=dispatch.order_number,
        product_id=dispatch.product_code
    )
    print(f"基本查詢結果: {fillwork_reports.count()} 筆")
    
    # 已核准記錄
    approved_reports = fillwork_reports.filter(approval_status='approved')
    print(f"已核准記錄: {approved_reports.count()} 筆")
    
    # 出貨包裝記錄
    packaging_reports = approved_reports.filter(process__name='出貨包裝')
    print(f"出貨包裝記錄: {packaging_reports.count()} 筆")
    print()
    
    for r in packaging_reports:
        print(f"  - {r.operator}: {r.work_quantity} (公司: {r.company_name})")
    
    print()
    
    # 按公司名稱過濾
    if dispatch.company_code:
        company_name = dispatch._get_company_name()
        if company_name:
            filtered_reports = packaging_reports.filter(company_name=company_name)
            print(f"按公司名稱 '{company_name}' 過濾後: {filtered_reports.count()} 筆")
            
            for r in filtered_reports:
                print(f"  - {r.operator}: {r.work_quantity} (公司: {r.company_name})")
        else:
            print("❌ 無法取得公司名稱")
    
    print()
    
    # 更新派工單統計
    print("=== 更新派工單統計 ===")
    dispatch.update_all_statistics()
    
    print(f"出貨包裝總數量: {dispatch.packaging_total_quantity}")
    print(f"出貨包裝良品數量: {dispatch.packaging_good_quantity}")
    print(f"出貨包裝不良品數量: {dispatch.packaging_defect_quantity}")
    
    # 手動計算
    print()
    print("=== 手動計算 ===")
    manual_total = packaging_reports.aggregate(total=Sum('work_quantity'))['total'] or 0
    print(f"手動計算總數量: {manual_total}")

if __name__ == '__main__':
    from django.db.models import Sum
    debug_packaging_bug()
