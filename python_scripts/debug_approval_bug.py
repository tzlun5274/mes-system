#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
調試批次審核失效問題
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.fill_work.models import FillWork
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig

def debug_approval_bug():
    """調試批次審核失效問題"""
    
    print("🔍 調試批次審核失效問題...")
    
    # 查找待審核記錄
    records = FillWork.objects.filter(
        workorder='331-25102001',
        product_id='PFP-CCTCT180425HFTN_VA-800',
        approval_status='pending'
    )
    
    print(f"=== 待審核記錄 ===")
    print(f"總數: {records.count()}")
    
    for r in records[:3]:
        print(f"ID: {r.id}, 公司名稱: {r.company_name}, 產品編號: {r.product_id}")
    
    # 查找對應的派工單
    dispatch = WorkOrderDispatch.objects.filter(
        order_number='331-25102001',
        product_code='PFP-CCTCT180425HFTN_VA-800'
    ).first()
    
    print(f"\n=== 派工單資訊 ===")
    if dispatch:
        print(f"派工單ID: {dispatch.id}")
        print(f"公司代號: {dispatch.company_code}")
        
        # 查找公司配置
        cc = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
        if cc:
            print(f"派工單公司名稱: {cc.company_name}")
        else:
            print("找不到公司配置")
    else:
        print("找不到對應的派工單")
    
    # 模擬驗證邏輯
    print(f"\n=== 模擬驗證邏輯 ===")
    for r in records[:3]:
        print(f"\n檢查記錄 ID: {r.id}")
        print(f"  填報記錄公司名稱: {r.company_name}")
        print(f"  填報記錄產品編號: {r.product_id}")
        
        if dispatch:
            cc = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
            dispatch_company_name = cc.company_name if cc else None
            
            print(f"  派工單公司名稱: {dispatch_company_name}")
            print(f"  派工單產品編號: {dispatch.product_code}")
            
            # 檢查公司名稱是否一致
            company_match = dispatch_company_name == r.company_name
            print(f"  公司名稱一致: {company_match}")
            
            # 檢查產品編號是否一致
            product_match = dispatch.product_code == r.product_id
            print(f"  產品編號一致: {product_match}")
            
            if not company_match:
                print(f"  ❌ 公司名稱不一致：填報記錄={r.company_name}, 派工單={dispatch_company_name}")
            if not product_match:
                print(f"  ❌ 產品編號不一致：填報記錄={r.product_id}, 派工單={dispatch.product_code}")
        else:
            print(f"  ❌ 找不到對應的派工單")

if __name__ == '__main__':
    debug_approval_bug()
