#!/usr/bin/env python3
"""
智能遷移腳本
自動處理常見的遷移問題
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

# 添加專案路徑到 Python 路徑
sys.path.insert(0, '/var/www/mes')

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

def smart_migrate():
    """智能遷移處理"""
    print("=" * 60)
    print("🧠 智能遷移處理")
    print("=" * 60)
    print()
    
    try:
        # 1. 嘗試創建遷移
        print("1. 嘗試創建遷移...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        print("   ✅ 遷移創建成功")
        
    except Exception as e:
        print(f"   ❌ 遷移創建失敗: {e}")
        
        # 檢查是否是 nullable 欄位問題
        if "nullable field" in str(e) and "non-nullable" in str(e):
            print("   🔍 檢測到 nullable 欄位問題")
            handle_nullable_field_issue()
        else:
            print("   ❓ 未知錯誤，請手動處理")
            return
    
    try:
        # 2. 應用遷移
        print("2. 應用遷移...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("   ✅ 遷移應用成功")
        
    except Exception as e:
        print(f"   ❌ 遷移應用失敗: {e}")
        print("   💡 建議：檢查資料庫狀態或使用重置腳本")

def handle_nullable_field_issue():
    """處理 nullable 欄位問題"""
    print("   🔧 處理 nullable 欄位問題...")
    
    # 這裡可以添加自動修復邏輯
    # 例如：自動為欄位添加 null=True, blank=True
    
    print("   💡 建議解決方案：")
    print("      1. 在模型中為問題欄位添加 null=True, blank=True")
    print("      2. 或者提供合理的預設值")
    print("      3. 或者使用重置腳本重新開始")

def check_database_status():
    """檢查資料庫狀態"""
    print("🔍 檢查資料庫狀態...")
    
    cursor = connection.cursor()
    
    # 檢查資料表數量
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    table_count = cursor.fetchone()[0]
    
    # 檢查遷移狀態
    cursor.execute("SELECT COUNT(*) FROM django_migrations")
    migration_count = cursor.fetchone()[0]
    
    print(f"   資料表數量: {table_count}")
    print(f"   遷移記錄數: {migration_count}")
    
    # 檢查是否有未應用的遷移
    try:
        execute_from_command_line(['manage.py', 'showmigrations', '--plan'])
    except:
        pass

if __name__ == "__main__":
    check_database_status()
    print()
    smart_migrate()
