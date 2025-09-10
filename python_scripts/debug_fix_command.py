#!/usr/bin/env python3
"""
調試修復命令的執行過程
"""

import os
import sys
import django

# 設定Django環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.models import WorkOrder
from workorder.services.workorder_status_service import WorkOrderStatusService

def debug_fix_command(workorder_id):
    """調試修復命令的執行過程"""
    try:
        # 獲取工單
        workorder = WorkOrder.objects.get(id=workorder_id)
        print(f"=== 工單資訊 ===")
        print(f"工單號碼: {workorder.order_number}")
        print(f"當前狀態: {workorder.status}")
        
        # 檢查生產活動
        print(f"\n=== 生產活動檢查 ===")
        has_production_activity = WorkOrderStatusService._check_production_activity(workorder)
        print(f"生產活動檢查結果: {has_production_activity}")
        
        # 判斷應該的狀態
        should_be_in_progress = has_production_activity
        should_be_pending = not has_production_activity
        
        print(f"應該的狀態:")
        print(f"  should_be_in_progress: {should_be_in_progress}")
        print(f"  should_be_pending: {should_be_pending}")
        
        # 檢查狀態是否需要修復
        needs_fix = False
        new_status = workorder.status
        
        if should_be_in_progress and workorder.status == 'pending':
            needs_fix = True
            new_status = 'in_progress'
            print(f"需要修復: pending → in_progress")
        elif should_be_pending and workorder.status == 'in_progress':
            needs_fix = True
            new_status = 'pending'
            print(f"需要修復: in_progress → pending")
        else:
            print(f"不需要修復: 狀態正常")
        
        print(f"\n=== 修復結果 ===")
        print(f"需要修復: {needs_fix}")
        print(f"舊狀態: {workorder.status}")
        print(f"新狀態: {new_status}")
        
        # 實際執行修復（非乾跑模式）
        if needs_fix:
            print(f"\n=== 執行修復 ===")
            from django.db import transaction
            from django.utils import timezone
            
            with transaction.atomic():
                old_status = workorder.status
                workorder.status = new_status
                workorder.updated_at = timezone.now()
                workorder.save()
                
                print(f"處理完成: {old_status} → {workorder.status}")
                
                # 重新查詢確認
                workorder.refresh_from_db()
                print(f"確認狀態: {workorder.status}")
        else:
            print(f"不需要修復")
            
    except WorkOrder.DoesNotExist:
        print(f"工單 {workorder_id} 不存在")
    except Exception as e:
        print(f"錯誤: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        workorder_id = int(sys.argv[1])
    else:
        workorder_id = 8655  # 預設工單ID
    
    debug_fix_command(workorder_id) 