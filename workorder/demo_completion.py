#!/usr/bin/env python3
"""
工單完工判斷機制演示腳本
展示完工判斷機制的各種功能
"""

import os
import sys
import django

# 設定 Django 環境
import sys
sys.path.append('/var/www/mes')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from workorder.models import WorkOrder, WorkOrderProcess
from workorder.workorder_reporting.models import OperatorSupplementReport
from workorder.services.completion_service import WorkOrderCompletionService


def create_demo_data():
    """建立演示資料"""
    print("=== 建立演示資料 ===")
    
    # 建立測試用戶
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={'password': 'demo123'}
    )
    if created:
        print(f"建立測試用戶: {user.username}")
    
    # 建立測試工單
    workorder, created = WorkOrder.objects.get_or_create(
        order_number='WO-DEMO-001',
        defaults={
            'company_code': '01',
            'product_code': 'DEMO-PRODUCT',
            'quantity': 100,
            'status': 'in_progress'
        }
    )
    if created:
        print(f"建立測試工單: {workorder.order_number}")
    
    # 建立出貨包裝工序
    process, created = WorkOrderProcess.objects.get_or_create(
        workorder=workorder,
        process_name='出貨包裝',
        defaults={
            'step_order': 1,
            'planned_quantity': 100,
            'completed_quantity': 0,
            'status': 'in_progress'
        }
    )
    if created:
        print(f"建立出貨包裝工序")
    
    return workorder, user


def demo_packaging_quantity_calculation(workorder, user):
    """演示包裝數量計算"""
    print("\n=== 演示包裝數量計算 ===")
    
    # 清除現有報工記錄
    OperatorSupplementReport.objects.filter(workorder=workorder).delete()
    
    # 測試1: 沒有報工記錄
    quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"1. 沒有報工記錄時: {quantity}")
    
    # 測試2: 建立未核准的報工記錄
            # 需要先建立或獲取出貨包裝工序
        from process.models import ProcessName
        packaging_process, _ = ProcessName.objects.get_or_create(
            name='出貨包裝',
            defaults={'description': '出貨包裝工序'}
        )
        
        OperatorSupplementReport.objects.create(
            workorder=workorder,
            operator=user,
            process=packaging_process,
            work_date=timezone.now().date(),
            work_quantity=50,
            approval_status='pending'
        )
    quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"2. 只有未核准報工記錄時: {quantity}")
    
    # 測試3: 建立已核准的報工記錄
    OperatorSupplementReport.objects.create(
        workorder=workorder,
        operator=user,
        process=packaging_process,
        work_date=timezone.now().date(),
        work_quantity=30,
        approval_status='approved'
    )
    quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"3. 有已核准報工記錄時: {quantity}")
    
    # 測試4: 建立其他工序的報工記錄
    smt_process, _ = ProcessName.objects.get_or_create(
        name='SMT',
        defaults={'description': 'SMT工序'}
    )
    OperatorSupplementReport.objects.create(
        workorder=workorder,
        operator=user,
        process=smt_process,
        work_date=timezone.now().date(),
        work_quantity=100,
        approval_status='approved'
    )
    quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"4. 有其他工序報工記錄時: {quantity}")
    
    # 測試5: 建立更多出貨包裝報工記錄
    OperatorSupplementReport.objects.create(
        workorder=workorder,
        operator=user,
        process=packaging_process,
        work_date=timezone.now().date(),
        work_quantity=70,
        approval_status='approved'
    )
    quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"5. 累計出貨包裝數量: {quantity}")
    
    return quantity


def demo_completion_condition_check(workorder, current_quantity):
    """演示完工條件檢查"""
    print("\n=== 演示完工條件檢查 ===")
    
    target_quantity = workorder.quantity
    print(f"工單目標數量: {target_quantity}")
    print(f"當前出貨包裝數量: {current_quantity}")
    
    if current_quantity >= target_quantity:
        print("✅ 已達到完工條件")
        return True
    else:
        print("❌ 尚未達到完工條件")
        print(f"還需要: {target_quantity - current_quantity}")
        return False


def demo_completion_process(workorder, user):
    """演示完工流程（乾跑模式）"""
    print("\n=== 演示完工流程（乾跑模式） ===")
    
    # 建立達到完工條件的報工記錄
    OperatorSupplementReport.objects.filter(workorder=workorder).delete()
    OperatorSupplementReport.objects.create(
        workorder=workorder,
        operator=user,
        process='出貨包裝',
        work_date=timezone.now().date(),
        work_quantity=100,
        approval_status='approved'
    )
    
    print("建立達到完工條件的報工記錄")
    
    # 檢查完工條件
    packaging_quantity = WorkOrderCompletionService._get_packaging_quantity(workorder)
    print(f"出貨包裝數量: {packaging_quantity}")
    
    if packaging_quantity >= workorder.quantity:
        print("✅ 工單已達到完工條件")
        print("📋 完工流程將執行以下步驟:")
        print("   1. 更新工單狀態為 'completed'")
        print("   2. 更新生產記錄結束時間")
        print("   3. 更新所有工序狀態為 'completed'")
        print("   4. 轉移資料到已完工工單資料表")
        print("   5. 清理生產中工單資料")
        print("\n💡 實際執行時請使用: WorkOrderCompletionService.check_and_complete_workorder(workorder.id)")
    else:
        print("❌ 工單尚未達到完工條件")


def main():
    """主函數"""
    print("🚀 工單完工判斷機制演示")
    print("=" * 50)
    
    try:
        # 建立演示資料
        workorder, user = create_demo_data()
        
        # 演示包裝數量計算
        current_quantity = demo_packaging_quantity_calculation(workorder, user)
        
        # 演示完工條件檢查
        is_completed = demo_completion_condition_check(workorder, current_quantity)
        
        # 演示完工流程
        demo_completion_process(workorder, user)
        
        print("\n" + "=" * 50)
        print("✅ 演示完成")
        print("\n📚 使用說明:")
        print("1. 管理命令: python manage.py check_workorder_completion --dry-run")
        print("2. 網頁介面: /workorder/completion-check/")
        print("3. 自動觸發: 當出貨包裝報工被核准時自動檢查")
        
    except Exception as e:
        print(f"❌ 演示過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 