#!/usr/bin/env python3
"""
重建 MES 系統資料庫
"""
import os
import sys
import subprocess
import django

def rebuild_database():
    """重建資料庫"""
    print("🔧 開始重建 MES 系統資料庫...")
    
    # 設定環境變數
    os.environ['PGPASSWORD'] = 'mes_password'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
    
    try:
        # 步驟1: 停止所有連線
        print("步驟1: 停止所有資料庫連線...")
        subprocess.run([
            "psql", "-h", "localhost", "-p", "5432", "-U", "mes_user", "-d", "postgres",
            "-c", "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'mes_db' AND pid <> pg_backend_pid();"
        ], capture_output=True)
        
        # 步驟2: 刪除資料庫
        print("步驟2: 刪除現有資料庫...")
        subprocess.run([
            "dropdb", "-h", "localhost", "-p", "5432", "-U", "mes_user", "--if-exists", "mes_db"
        ], capture_output=True)
        
        # 步驟3: 重新建立資料庫
        print("步驟3: 重新建立資料庫...")
        result = subprocess.run([
            "createdb", "-h", "localhost", "-p", "5432", "-U", "mes_user", "mes_db"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 資料庫建立失敗: {result.stderr}")
            return False
        
        print("✅ 資料庫建立成功")
        
        # 步驟4: 設定 schema
        print("步驟4: 設定資料庫 schema...")
        subprocess.run([
            "psql", "-h", "localhost", "-p", "5432", "-U", "mes_user", "-d", "mes_db",
            "-c", "SET search_path TO public;"
        ], capture_output=True)
        
        # 步驟5: 初始化 Django
        print("步驟5: 初始化 Django...")
        django.setup()
        
        # 步驟6: 執行 migrate
        print("步驟6: 執行 Django migrate...")
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        
        # 步驟7: 建立超級用戶
        print("步驟7: 建立超級用戶...")
        from django.contrib.auth.models import User
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("✅ 超級用戶建立成功")
        else:
            print("✅ 超級用戶已存在")
        
        # 步驟8: 建立基本群組
        print("步驟8: 建立基本群組...")
        from django.contrib.auth.models import Group
        
        groups = ['系統管理員', '生產主管', '作業員', '品質管理員', '報表使用者']
        for group_name in groups:
            Group.objects.get_or_create(name=group_name)
        
        print("✅ 基本群組建立完成")
        
        # 步驟9: 收集靜態檔案
        print("步驟9: 收集靜態檔案...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        
        print("\n🎉 資料庫重建完成！")
        print("系統現在可以正常使用了。")
        print("預設管理員帳號: admin")
        print("預設管理員密碼: admin123")
        print("\n接下來你可以：")
        print("1. 重新啟動 Django 服務")
        print("2. 使用系統管理功能還原之前的備份資料")
        print("3. 正常使用 MES 系統")
        
        return True
        
    except Exception as e:
        print(f"❌ 資料庫重建失敗: {e}")
        return False

if __name__ == '__main__':
    rebuild_database() 