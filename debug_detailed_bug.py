#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細調試派工單統計邏輯
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.fill_work.models import FillWork

def debug_detailed_bug():
    """詳細調試派工單統計邏輯"""
    
    print("🔍 詳細調試派工單統計邏輯...")
    
    # 查找派工單 275
    dispatch = WorkOrderDispatch.objects.get(id=275)
    
    print(f"=== 派工單資訊 ===")
    print(f"  工單號: {dispatch.order_number}")
    print(f"  產品編號: {dispatch.product_code}")
    print(f"  公司代號: {dispatch.company_code}")
    print(f"  公司名稱: {dispatch._get_company_name()}")
    print()
    
    # 模擬派工單統計邏輯的步驟
    print("=== 模擬派工單統計邏輯 ===")
    
    # 步驟1: 基本查詢
    fillwork_reports = FillWork.objects.filter(
        workorder=dispatch.order_number,
        product_id=dispatch.product_code
    )
    print(f"步驟1 - 基本查詢: {fillwork_reports.count()} 筆")
    
    # 步驟2: 按公司名稱過濾
    if dispatch.company_code:
        company_name = dispatch._get_company_name()
        if company_name:
            fillwork_reports = fillwork_reports.filter(company_name=company_name)
            print(f"步驟2 - 按公司名稱 '{company_name}' 過濾: {fillwork_reports.count()} 筆")
        else:
            print("步驟2 - 無法取得公司名稱")
    
    # 步驟3: 已核准記錄
    approved_reports = fillwork_reports.filter(approval_status='approved')
    print(f"步驟3 - 已核准記錄: {approved_reports.count()} 筆")
    
    # 步驟4: 出貨包裝記錄
    packaging_reports = approved_reports.filter(process__name='出貨包裝')
    print(f"步驟4 - 出貨包裝記錄: {packaging_reports.count()} 筆")
    
    for r in packaging_reports:
        print(f"  - {r.operator}: {r.work_quantity} (公司: {r.company_name})")
    
    # 步驟5: 計算數量
    packaging_good_quantity = packaging_reports.aggregate(
        total=Sum('work_quantity')
    )['total'] or 0
    
    packaging_defect_quantity = packaging_reports.aggregate(
        total=Sum('defect_quantity')
    )['total'] or 0
    
    print(f"步驟5 - 計算結果:")
    print(f"  良品數量: {packaging_good_quantity}")
    print(f"  不良品數量: {packaging_defect_quantity}")
    print(f"  總數量: {packaging_good_quantity + packaging_defect_quantity}")
    
    print()
    
    # 實際更新派工單統計
    print("=== 實際更新派工單統計 ===")
    dispatch.update_all_statistics()
    
    print(f"派工單統計結果:")
    print(f"  出貨包裝總數量: {dispatch.packaging_total_quantity}")
    print(f"  出貨包裝良品數量: {dispatch.packaging_good_quantity}")
    print(f"  出貨包裝不良品數量: {dispatch.packaging_defect_quantity}")

if __name__ == '__main__':
    from django.db.models import Sum
    debug_detailed_bug()
