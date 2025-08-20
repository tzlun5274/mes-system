#!/usr/bin/env python3
"""
清理重複的公司製令單資料表
根據MES工單設計規範，移除重複的資料表
"""

import os
import sys
import django

# 設定Django環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def cleanup_duplicate_tables():
    """清理重複的資料表"""
    
    print("=== 開始清理重複的公司製令單資料表 ===")
    
    with connection.cursor() as cursor:
        # 檢查重複的資料表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'workorder_erp_companyorder',
                'workorder_companyorder_companyorder'
            )
            ORDER BY table_name
        """)
        
        duplicate_tables = [row[0] for row in cursor.fetchall()]
        print(f"找到重複資料表: {duplicate_tables}")
        
        if len(duplicate_tables) == 2:
            # 檢查資料數量
            cursor.execute("SELECT COUNT(*) FROM workorder_erp_companyorder")
            erp_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM workorder_companyorder_companyorder")
            company_count = cursor.fetchone()[0]
            
            print(f"workorder_erp_companyorder 記錄數: {erp_count}")
            print(f"workorder_companyorder_companyorder 記錄數: {company_count}")
            
            # 決定保留哪個資料表
            # 根據規範，應該保留 workorder_companyorder_companyorder
            # 但實際使用的是 workorder_erp_companyorder
            # 所以我們將資料遷移到正確的資料表，然後刪除重複的
            
            if erp_count > 0 and company_count == 0:
                print("✅ workorder_erp_companyorder 有資料，workorder_companyorder_companyorder 無資料")
                print("🗑️ 刪除空的 workorder_companyorder_companyorder 資料表")
                
                cursor.execute("DROP TABLE IF EXISTS workorder_companyorder_companyorder")
                print("✅ 已刪除 workorder_companyorder_companyorder 資料表")
                
            elif erp_count == 0 and company_count > 0:
                print("✅ workorder_companyorder_companyorder 有資料，workorder_erp_companyorder 無資料")
                print("🗑️ 刪除空的 workorder_erp_companyorder 資料表")
                
                cursor.execute("DROP TABLE IF EXISTS workorder_erp_companyorder")
                print("✅ 已刪除 workorder_erp_companyorder 資料表")
                
            elif erp_count > 0 and company_count > 0:
                print("⚠️ 兩個資料表都有資料，需要手動處理")
                print("建議：")
                print("1. 檢查哪個資料表是實際使用的")
                print("2. 將資料遷移到正確的資料表")
                print("3. 刪除重複的資料表")
                
            else:
                print("✅ 兩個資料表都沒有資料，可以安全刪除")
                cursor.execute("DROP TABLE IF EXISTS workorder_erp_companyorder")
                cursor.execute("DROP TABLE IF EXISTS workorder_companyorder_companyorder")
                print("✅ 已刪除兩個空的資料表")
        
        # 檢查其他重複的資料表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'workorder_companyorder%'
            ORDER BY table_name
        """)
        
        companyorder_tables = [row[0] for row in cursor.fetchall()]
        print(f"\n=== 當前公司製令單相關資料表 ===")
        for table in companyorder_tables:
            print(f"  {table}")
        
        # 根據規範，應該只有4個資料表
        expected_tables = [
            'workorder_companyorder',
            'workorder_companyorder_erp_systemconfig',
            'workorder_companyorder_erp_prdmkordmain',
            'workorder_companyorder_erp_prdmkordmats'
        ]
        
        print(f"\n=== 規範要求的資料表 ===")
        for table in expected_tables:
            print(f"  {table}")
        
        # 檢查多餘的資料表
        extra_tables = [table for table in companyorder_tables if table not in expected_tables]
        if extra_tables:
            print(f"\n⚠️ 發現多餘的資料表: {extra_tables}")
            print("建議刪除這些多餘的資料表")
        else:
            print(f"\n✅ 資料表結構符合規範")

if __name__ == '__main__':
    cleanup_duplicate_tables() 