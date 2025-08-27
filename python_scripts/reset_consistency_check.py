#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置相符性檢查結果
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.models import ConsistencyCheckResult
from workorder.services.consistency_check_service import ConsistencyCheckService

def reset_consistency_check():
    """重置相符性檢查結果"""
    
    print("🔄 重置相符性檢查結果...")
    
    # 清除所有舊的檢查結果
    old_count = ConsistencyCheckResult.objects.count()
    ConsistencyCheckResult.objects.all().delete()
    print(f"已清除 {old_count} 筆舊的檢查結果")
    
    # 重新執行相符性檢查
    print("\n🔍 重新執行相符性檢查...")
    service = ConsistencyCheckService()
    
    try:
        results = service.run_all_checks()
        print(f"檢查完成！")
        print(f"  填報異常: {results.get('missing_dispatch', 0)} 筆")
        print(f"  產品編號錯誤: {results.get('wrong_product_code', 0)} 筆")
        print(f"  公司名稱錯誤: {results.get('wrong_company', 0)} 筆")
        print(f"  工單號碼錯誤: {results.get('wrong_workorder', 0)} 筆")
        
        total = sum(results.values())
        print(f"  總計: {total} 筆問題")
        
    except Exception as e:
        print(f"❌ 檢查失敗: {str(e)}")
        return
    
    # 檢查新的結果
    print(f"\n📊 新的檢查結果統計:")
    new_results = ConsistencyCheckResult.objects.values('check_type', 'is_fixed').annotate(
        count=django.db.models.Count('id')
    )
    
    for result in new_results:
        check_type = result['check_type']
        is_fixed = result['is_fixed']
        count = result['count']
        status = "已修復" if is_fixed else "未修復"
        print(f"  {check_type}: {count} 筆 ({status})")

if __name__ == '__main__':
    reset_consistency_check()
