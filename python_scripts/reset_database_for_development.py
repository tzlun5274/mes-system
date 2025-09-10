#!/usr/bin/env python3
"""
開發階段資料庫重置腳本
用於解決遷移衝突問題
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# 添加專案路徑到 Python 路徑
sys.path.insert(0, '/var/www/mes')

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

def reset_database():
    """重置資料庫用於開發"""
    print("=" * 60)
    print("🔄 開發階段資料庫重置")
    print("=" * 60)
    print()
    
    print("⚠️  警告：此操作將清除所有資料！")
    print("   僅適用於開發階段，請勿在生產環境使用！")
    print()
    
    # 確認操作
    confirm = input("確定要重置資料庫嗎？(輸入 'YES' 確認): ")
    if confirm != 'YES':
        print("❌ 操作已取消")
        return
    
    print()
    print(" 開始重置資料庫...")
    
    try:
        # 1. 刪除所有遷移檔案（保留 __init__.py）
        print("1. 清理遷移檔案...")
        import glob
        migration_files = glob.glob("*/migrations/0*.py")
        for file in migration_files:
            os.remove(file)
            print(f"   刪除: {file}")
        
        # 2. 重新創建遷移
        print("2. 重新創建遷移...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        # 3. 應用遷移
        print("3. 應用遷移...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        # 4. 創建超級用戶（可選）
        print("4. 創建超級用戶...")
        execute_from_command_line(['manage.py', 'createsuperuser', '--noinput', '--username', 'admin', '--email', 'admin@example.com'])
        
        print()
        print("✅ 資料庫重置完成！")
        print("   現在可以正常進行開發了")
        
    except Exception as e:
        print(f"❌ 重置過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_database()
