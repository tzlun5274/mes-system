#!/usr/bin/env python3
"""
更新派工單的公司名稱
"""
import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig

def update_dispatch_company_names():
    """更新派工單的公司名稱"""
    print("=== 更新派工單的公司名稱 ===")
    
    # 取得所有派工單
    dispatches = WorkOrderDispatch.objects.all()
    print(f"找到 {dispatches.count()} 筆派工單")
    
    updated_count = 0
    for dispatch in dispatches:
        if dispatch.company_code:
            try:
                company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
                if company_config:
                    old_name = dispatch.company_name
                    dispatch.company_name = company_config.company_name
                    dispatch.save()
                    updated_count += 1
                    print(f"  更新派工單 ID {dispatch.id}: {old_name} → {dispatch.company_name}")
                else:
                    print(f"  派工單 ID {dispatch.id}: 找不到公司代號 {dispatch.company_code} 的設定")
            except Exception as e:
                print(f"  派工單 ID {dispatch.id}: 更新失敗 - {str(e)}")
        else:
            print(f"  派工單 ID {dispatch.id}: 無公司代號")
    
    print(f"\n更新完成: {updated_count} 筆派工單")

if __name__ == "__main__":
    update_dispatch_company_names() 