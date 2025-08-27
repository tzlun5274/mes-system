#!/usr/bin/env python3
"""
調試完工判斷邏輯
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch

def debug_completion_logic():
    """調試完工判斷邏輯"""
    order_number = '331-25528002'
    
    print(f"=== 調試工單 {order_number} 完工判斷邏輯 ===")
    
    # 獲取工單和派工單
    workorder = WorkOrder.objects.filter(order_number=order_number).first()
    dispatch = WorkOrderDispatch.objects.filter(order_number=order_number).first()
    
    if not workorder or not dispatch:
        print("工單或派工單不存在")
        return
    
    print(f"計劃數量: {dispatch.planned_quantity}")
    print(f"出貨包裝數量: {dispatch.packaging_total_quantity}")
    print(f"總完成數量: {dispatch.total_quantity}")
    
    # 手動計算完工條件
    packaging_quantity = dispatch.packaging_total_quantity
    planned_quantity = dispatch.planned_quantity
    
    print(f"\n=== 完工條件檢查 ===")
    print(f"出貨包裝數量 >= 計劃數量: {packaging_quantity} >= {planned_quantity} = {packaging_quantity >= planned_quantity}")
    print(f"計劃數量 > 0: {planned_quantity} > 0 = {planned_quantity > 0}")
    
    # 手動設定完工狀態
    if packaging_quantity >= planned_quantity and planned_quantity > 0:
        print(f"✓ 應該設定為可完工")
        dispatch.completion_threshold_met = True
        dispatch.can_complete = True
        dispatch.save()
        print(f"✓ 已手動設定完工狀態")
    else:
        print(f"✗ 不滿足完工條件")
    
    # 重新檢查
    dispatch.refresh_from_db()
    print(f"\n=== 更新後狀態 ===")
    print(f"可完工: {dispatch.can_complete}")
    print(f"達到完工閾值: {dispatch.completion_threshold_met}")

if __name__ == '__main__':
    debug_completion_logic()
