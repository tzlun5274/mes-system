#!/usr/bin/env python3
"""
完整的資料庫初始化腳本
重建所有必要的資料表和初始資料
"""
import os
import sys
import django
import subprocess
from pathlib import Path

def init_database():
    """初始化資料庫"""
    print("開始初始化資料庫...")
    
    # 設定 Django 環境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
    django.setup()
    
    try:
        # 步驟1: 執行 Django migrate 建立所有資料表
        print("步驟1: 執行 Django migrate...")
        result = subprocess.run([
            sys.executable, "manage.py", "migrate", "--noinput"
        ], capture_output=True, text=True, cwd="/var/www/mes")
        
        if result.returncode == 0:
            print("✅ Django migrate 成功")
        else:
            print(f"⚠️ Django migrate 出現警告: {result.stderr}")
        
        # 步驟2: 建立超級用戶
        print("步驟2: 建立超級用戶...")
        from django.contrib.auth.models import User
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("✅ 超級用戶建立成功 (admin/admin123)")
        else:
            print("✅ 超級用戶已存在")
        
        # 步驟3: 建立基本群組
        print("步驟3: 建立基本群組...")
        from django.contrib.auth.models import Group
        
        groups = [
            "系統管理員",
            "生產主管", 
            "作業員",
            "品質管理員",
            "報表使用者"
        ]
        
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                print(f"✅ 建立群組: {group_name}")
            else:
                print(f"✅ 群組已存在: {group_name}")
        
        # 步驟4: 建立基本公司設定
        print("步驟4: 建立基本公司設定...")
        try:
            from erp_integration.models import CompanyConfig
            
            if not CompanyConfig.objects.exists():
                company = CompanyConfig.objects.create(
                    company_code="001",
                    company_name="預設公司",
                    database="mes_db"
                )
                print("✅ 建立預設公司設定")
            else:
                print("✅ 公司設定已存在")
        except Exception as e:
            print(f"⚠️ 建立公司設定時出現警告: {e}")
        
        # 步驟5: 建立基本設備類型
        print("步驟5: 建立基本設備類型...")
        try:
            from equip.models import EquipmentType
            
            equipment_types = [
                "SMT設備",
                "測試設備", 
                "包裝設備",
                "其他設備"
            ]
            
            for type_name in equipment_types:
                equipment_type, created = EquipmentType.objects.get_or_create(name=type_name)
                if created:
                    print(f"✅ 建立設備類型: {type_name}")
                else:
                    print(f"✅ 設備類型已存在: {type_name}")
        except Exception as e:
            print(f"⚠️ 建立設備類型時出現警告: {e}")
        
        print("\n🎉 資料庫初始化完成！")
        print("系統現在可以正常使用了。")
        print("預設管理員帳號: admin")
        print("預設管理員密碼: admin123")
        
        return True
        
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        return False

if __name__ == '__main__':
    init_database() 