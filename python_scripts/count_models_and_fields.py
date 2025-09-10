#!/usr/bin/env python3
"""
計算 MES 專案中所有模型的資料表數量和欄位數量
"""

import os
import sys
import django
from django.apps import apps
from django.db import models

# 添加專案路徑到 Python 路徑
sys.path.insert(0, '/var/www/mes')

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

def count_models_and_fields():
    """計算所有模型的資料表數量和欄位數量"""
    
    total_tables = 0
    total_fields = 0
    app_stats = {}
    
    print("=" * 80)
    print("MES 專案模型統計報告")
    print("=" * 80)
    print()
    
    # 遍歷所有已安裝的應用程式
    for app_config in apps.get_app_configs():
        app_name = app_config.name
        
        # 跳過 Django 內建的應用程式
        if app_name.startswith('django.') or app_name in ['contenttypes', 'sessions', 'admin', 'auth']:
            continue
            
        app_models = app_config.get_models()
        if not app_models:
            continue
            
        app_tables = 0
        app_fields = 0
        model_details = []
        
        print(f"📱 應用程式: {app_name}")
        print("-" * 60)
        
        for model in app_models:
            # 取得資料表名稱
            table_name = model._meta.db_table
            
            # 計算欄位數量（排除自動生成的欄位如 id）
            fields = model._meta.get_fields()
            field_count = len([f for f in fields if not f.auto_created])
            
            # 取得欄位詳細資訊
            field_names = [f.name for f in fields if not f.auto_created]
            
            app_tables += 1
            app_fields += field_count
            
            model_details.append({
                'name': model.__name__,
                'table': table_name,
                'fields': field_count,
                'field_names': field_names
            })
            
            print(f"  📋 {model.__name__}")
            print(f"     資料表: {table_name}")
            print(f"     欄位數: {field_count}")
            print(f"     欄位: {', '.join(field_names[:5])}{'...' if len(field_names) > 5 else ''}")
            print()
        
        app_stats[app_name] = {
            'tables': app_tables,
            'fields': app_fields,
            'models': model_details
        }
        
        total_tables += app_tables
        total_fields += app_fields
        
        print(f"  📊 {app_name} 小計: {app_tables} 個資料表, {app_fields} 個欄位")
        print("=" * 60)
        print()
    
    # 顯示總計
    print("🎯 總計統計")
    print("=" * 80)
    print(f"總資料表數量: {total_tables}")
    print(f"總欄位數量: {total_fields}")
    print()
    
    # 顯示各應用程式統計
    print("📈 各應用程式統計")
    print("-" * 80)
    print(f"{'應用程式':<20} {'資料表數':<10} {'欄位數':<10} {'平均欄位/表':<15}")
    print("-" * 80)
    
    for app_name, stats in sorted(app_stats.items()):
        avg_fields = round(stats['fields'] / stats['tables'], 1) if stats['tables'] > 0 else 0
        print(f"{app_name:<20} {stats['tables']:<10} {stats['fields']:<10} {avg_fields:<15}")
    
    print("-" * 80)
    print(f"{'總計':<20} {total_tables:<10} {total_fields:<10} {round(total_fields/total_tables, 1) if total_tables > 0 else 0:<15}")
    
    # 顯示欄位最多的前 10 個模型
    print()
    print("🏆 欄位最多的前 10 個模型")
    print("-" * 80)
    
    all_models = []
    for app_name, stats in app_stats.items():
        for model_detail in stats['models']:
            all_models.append({
                'app': app_name,
                'model': model_detail['name'],
                'fields': model_detail['fields'],
                'table': model_detail['table']
            })
    
    # 按欄位數量排序
    all_models.sort(key=lambda x: x['fields'], reverse=True)
    
    for i, model in enumerate(all_models[:10], 1):
        print(f"{i:2d}. {model['app']}.{model['model']:<25} {model['fields']:3d} 欄位 ({model['table']})")
    
    # 顯示資料表名稱列表
    print()
    print("📋 所有資料表名稱列表")
    print("-" * 80)
    
    all_tables = []
    for app_name, stats in app_stats.items():
        for model_detail in stats['models']:
            all_tables.append(f"{model_detail['table']} ({app_name})")
    
    all_tables.sort()
    for i, table in enumerate(all_tables, 1):
        print(f"{i:3d}. {table}")
    
    return {
        'total_tables': total_tables,
        'total_fields': total_fields,
        'app_stats': app_stats
    }

if __name__ == "__main__":
    try:
        stats = count_models_and_fields()
        print()
        print("✅ 統計完成！")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
