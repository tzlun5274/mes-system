#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診斷完工判斷問題
檢查為什麼工單無法完工
"""

import os
import sys
import django

# 設定 Django 環境
sys.path.append('/var/www/mes')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.services.completion_service import FillWorkCompletionService
from process.models import ProcessName, ProductProcessRoute

def diagnose_completion_issues():
    """診斷完工判斷問題"""
    print("=== 完工判斷問題診斷 ===\n")
    
    # 1. 檢查生產中工單數量
    production_workorders = WorkOrder.objects.filter(status='in_progress')
    print(f"1. 生產中工單數量: {production_workorders.count()}")
    
    if production_workorders.count() == 0:
        print("❌ 沒有生產中的工單")
        return
    
    # 2. 檢查出貨包裝工序是否存在
    print("\n2. 檢查出貨包裝工序:")
    packaging_process = ProcessName.objects.filter(name="出貨包裝").first()
    if packaging_process:
        print(f"✅ 出貨包裝工序存在: {packaging_process.name}")
    else:
        print("❌ 出貨包裝工序不存在！")
        print("   需要建立「出貨包裝」工序")
        return
    
    # 3. 檢查前5個工單的詳細狀況
    print("\n3. 檢查工單完工條件:")
    for i, workorder in enumerate(production_workorders[:5]):
        print(f"\n--- 工單 {i+1}: {workorder.order_number} ---")
        print(f"目標數量: {workorder.quantity}")
        print(f"產品代碼: {workorder.product_code}")
        
        # 檢查派工單
        dispatch = WorkOrderDispatch.objects.filter(order_number=workorder.order_number).first()
        if dispatch:
            print(f"派工單狀態: {dispatch.status}")
            print(f"計劃數量: {dispatch.planned_quantity}")
            print(f"出貨包裝數量: {dispatch.packaging_total_quantity}")
            print(f"可完工: {dispatch.can_complete}")
            print(f"達到閾值: {dispatch.completion_threshold_met}")
        else:
            print("❌ 沒有對應的派工單")
            continue
        
        # 檢查完工條件
        try:
            summary = FillWorkCompletionService.get_completion_summary(workorder.id)
            print(f"完工判斷結果:")
            print(f"  - 可以完工: {summary.get('can_complete', False)}")
            print(f"  - 出貨包裝數量: {summary.get('packaging_quantity', 0)}")
            print(f"  - 完成率: {summary.get('completion_percentage', 0)}%")
            print(f"  - 原因: {summary.get('reason', '未知')}")
        except Exception as e:
            print(f"❌ 檢查完工條件失敗: {str(e)}")
        
        # 檢查工序路線
        try:
            product_routes = ProductProcessRoute.objects.filter(
                product_id=workorder.product_code,
                process_name=packaging_process
            )
            print(f"產品工序路線: {product_routes.count()} 個")
            if product_routes.count() == 0:
                print("❌ 該產品沒有「出貨包裝」工序路線")
        except Exception as e:
            print(f"❌ 檢查工序路線失敗: {str(e)}")

if __name__ == "__main__":
    diagnose_completion_issues()
