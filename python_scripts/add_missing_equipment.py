#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增缺少的設備
"""

import os
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from equip.models import Equipment

def add_missing_equipment():
    """新增缺少的設備"""
    
    print("=== 新增缺少的設備 ===")
    
    # 需要新增的設備列表
    new_equipments = [
        {'name': '目檢台-01', 'model': '目檢台', 'status': 'idle'},
        {'name': '目檢台-02', 'model': '目檢台', 'status': 'idle'},
        {'name': '電測機-01', 'model': '電測機', 'status': 'idle'},
        {'name': '電測機-02', 'model': '電測機', 'status': 'idle'},
        {'name': '電測機-03', 'model': '電測機', 'status': 'idle'},
        {'name': '包裝機-01', 'model': '包裝機', 'status': 'idle'},
        {'name': '包裝機-02', 'model': '包裝機', 'status': 'idle'},
        {'name': '組合機-01', 'model': '組合機', 'status': 'idle'},
        {'name': '組合機-02', 'model': '組合機', 'status': 'idle'},
        {'name': 'AOI檢測機-01', 'model': 'AOI檢測機', 'status': 'idle'},
        {'name': 'AOI檢測機-02', 'model': 'AOI檢測機', 'status': 'idle'},
        {'name': '補錫機-01', 'model': '補錫機', 'status': 'idle'},
        {'name': '補錫機-02', 'model': '補錫機', 'status': 'idle'},
        {'name': 'Hot Bar機-01', 'model': 'Hot Bar機', 'status': 'idle'},
        {'name': 'Hot Bar機-02', 'model': 'Hot Bar機', 'status': 'idle'},
        {'name': '燒錄機-01', 'model': '燒錄機', 'status': 'idle'},
        {'name': '燒錄機-02', 'model': '燒錄機', 'status': 'idle'},
    ]
    
    created_count = 0
    skipped_count = 0
    
    for eq_data in new_equipments:
        # 檢查設備是否已存在
        existing = Equipment.objects.filter(name=eq_data['name']).exists()
        
        if existing:
            print(f"  ⚠️  {eq_data['name']} 已存在，跳過")
            skipped_count += 1
        else:
            # 新增設備
            equipment = Equipment.objects.create(
                name=eq_data['name'],
                model=eq_data['model'],
                status=eq_data['status']
            )
            print(f"  ✓ 已新增 {eq_data['name']}")
            created_count += 1
    
    print(f"\n=== 新增完成 ===")
    print(f"新增設備數: {created_count}")
    print(f"跳過設備數: {skipped_count}")
    
    # 顯示所有設備
    print(f"\n系統總設備數: {Equipment.objects.count()}")
    print("設備列表:")
    for eq in Equipment.objects.all().order_by('name'):
        print(f"  - {eq.name} ({eq.get_status_display()})")
    
    print(f"\n現在您可以在Excel中填入以下設備名稱:")
    for eq_data in new_equipments:
        print(f"  - {eq_data['name']}")

if __name__ == "__main__":
    add_missing_equipment() 