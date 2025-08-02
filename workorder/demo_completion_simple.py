#!/usr/bin/env python3
"""
工單完工判斷機制簡化演示腳本
"""

import os
import sys
import django

# 設定 Django 環境
sys.path.append('/var/www/mes')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.services.completion_service import WorkOrderCompletionService

def main():
    """主函數"""
    print("🚀 工單完工判斷機制演示")
    print("=" * 50)
    
    print("✅ 完工服務導入成功")
    print(f"📦 出貨包裝工序名稱: {WorkOrderCompletionService.PACKAGING_PROCESS_NAME}")
    
    print("\n📋 完工判斷邏輯:")
    print("1. 統計出貨包裝工序的已核准報工數量")
    print("2. 當數量 >= 工單目標數量時，觸發完工流程")
    print("3. 更新工單狀態為 'completed'")
    print("4. 轉移資料到已完工工單資料表")
    print("5. 清理生產中工單資料")
    
    print("\n🔧 使用方法:")
    print("1. 管理命令: python manage.py check_workorder_completion --dry-run")
    print("2. 網頁介面: /workorder/completion-check/")
    print("3. 自動觸發: 當出貨包裝報工被核准時自動檢查")
    
    print("\n📚 核心方法:")
    print("- WorkOrderCompletionService.check_and_complete_workorder(workorder_id)")
    print("- WorkOrderCompletionService._get_packaging_quantity(workorder)")
    print("- WorkOrderCompletionService.transfer_workorder_to_completed(workorder_id)")
    
    print("\n✅ 演示完成")

if __name__ == "__main__":
    main() 