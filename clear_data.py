#!/usr/bin/env python3
"""
清除 WorkOrderReportData 資料
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from reporting.models import WorkOrderReportData

def clear_data():
    """清除所有報表資料"""
    print("開始清除 WorkOrderReportData 資料...")
    
    # 檢查目前的資料數量
    total_count = WorkOrderReportData.objects.count()
    print(f"目前報表資料總數: {total_count}")
    
    if total_count > 0:
        # 清除所有資料
        deleted_count, _ = WorkOrderReportData.objects.all().delete()
        print(f"已清除 {deleted_count} 筆報表資料")
    else:
        print("沒有資料需要清除")
    
    # 確認清除結果
    remaining_count = WorkOrderReportData.objects.count()
    print(f"剩餘報表資料: {remaining_count}")
    
    if remaining_count == 0:
        print("✅ 資料清除完成！")
    else:
        print("❌ 資料清除失敗！")

if __name__ == "__main__":
    clear_data()
