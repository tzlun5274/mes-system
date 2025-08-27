#!/usr/bin/env python3
"""
清理 CompletedWorkOrderAnalysis 表中的重複記錄
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from reporting.models import CompletedWorkOrderAnalysis
from django.db.models import Count

def cleanup_duplicates():
    """清理重複的記錄"""
    print("開始清理 CompletedWorkOrderAnalysis 表中的重複記錄...")
    
    # 找出重複的記錄
    duplicates = CompletedWorkOrderAnalysis.objects.values('workorder_id', 'company_code').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    print(f"找到 {duplicates.count()} 組重複記錄")
    
    for duplicate in duplicates:
        workorder_id = duplicate['workorder_id']
        company_code = duplicate['company_code']
        count = duplicate['count']
        
        print(f"工單 {workorder_id} (公司 {company_code}) 有 {count} 筆重複記錄")
        
        # 取得該組的所有記錄，按建立時間排序
        records = CompletedWorkOrderAnalysis.objects.filter(
            workorder_id=workorder_id,
            company_code=company_code
        ).order_by('created_at')
        
        # 保留最新的記錄，刪除其他重複記錄
        records_to_keep = records.last()
        records_to_delete = records.exclude(id=records_to_keep.id)
        
        print(f"  保留記錄 ID: {records_to_keep.id} (建立時間: {records_to_keep.created_at})")
        print(f"  刪除 {records_to_delete.count()} 筆重複記錄")
        
        # 刪除重複記錄
        deleted_count = records_to_delete.delete()[0]
        print(f"  實際刪除 {deleted_count} 筆記錄")
    
    print("重複記錄清理完成！")

if __name__ == '__main__':
    cleanup_duplicates()
