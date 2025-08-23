#!/usr/bin/env python3
"""
手動創建派工單資料表腳本
解決遷移問題，直接創建必要的資料表
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def create_dispatch_tables():
    """創建派工單相關的資料表"""
    
    with connection.cursor() as cursor:
        # 創建 workorder_workorderdispatch 資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workorder_workorderdispatch (
                id BIGSERIAL PRIMARY KEY,
                dispatch_number VARCHAR(20) UNIQUE NOT NULL,
                workorder_id BIGINT NOT NULL,
                priority VARCHAR(10) NOT NULL DEFAULT 'normal',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                dispatch_date DATE NULL,
                planned_start_date DATE NULL,
                planned_end_date DATE NULL,
                actual_start_date TIMESTAMP WITH TIME ZONE NULL,
                actual_completion_date TIMESTAMP WITH TIME ZONE NULL,
                assigned_operator VARCHAR(100) NULL,
                assigned_equipment VARCHAR(100) NULL,
                estimated_hours DECIMAL(10,2) NULL,
                actual_hours DECIMAL(10,2) NULL,
                notes TEXT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                created_by VARCHAR(100) NULL,
                updated_by VARCHAR(100) NULL
            );
        """)
        
        # 創建 workorder_workorderdispatchprocess 資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workorder_workorderdispatchprocess (
                id BIGSERIAL PRIMARY KEY,
                dispatch_workorder_id BIGINT NOT NULL,
                sequence INTEGER NOT NULL,
                process_name VARCHAR(100) NOT NULL,
                process_description TEXT NULL,
                estimated_duration DECIMAL(10,2) NULL,
                actual_duration DECIMAL(10,2) NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                start_time TIMESTAMP WITH TIME ZONE NULL,
                end_time TIMESTAMP WITH TIME ZONE NULL,
                operator VARCHAR(100) NULL,
                equipment VARCHAR(100) NULL,
                notes TEXT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
        """)
        
        # 創建 workorder_workorderdispatchmaterial 資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workorder_workorderdispatchmaterial (
                id BIGSERIAL PRIMARY KEY,
                dispatch_workorder_id BIGINT NOT NULL,
                material_code VARCHAR(50) NOT NULL,
                material_name VARCHAR(100) NOT NULL,
                required_quantity DECIMAL(10,2) NOT NULL,
                issued_quantity DECIMAL(10,2) NULL DEFAULT 0,
                unit VARCHAR(20) NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                issue_date TIMESTAMP WITH TIME ZONE NULL,
                notes TEXT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
        """)
        
        # 創建 workorder_workorderdispatchquality 資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workorder_workorderdispatchquality (
                id BIGSERIAL PRIMARY KEY,
                dispatch_workorder_id BIGINT NOT NULL,
                inspection_type VARCHAR(50) NOT NULL,
                inspection_date TIMESTAMP WITH TIME ZONE NULL,
                inspector VARCHAR(100) NULL,
                result VARCHAR(20) NULL,
                pass_quantity INTEGER NULL,
                fail_quantity INTEGER NULL,
                notes TEXT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
        """)
        
        # 創建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workorder_dispatch_workorder_id 
            ON workorder_workorderdispatch(workorder_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workorder_dispatch_status 
            ON workorder_workorderdispatch(status);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workorder_dispatchprocess_dispatch_id 
            ON workorder_workorderdispatchprocess(dispatch_workorder_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workorder_dispatchmaterial_dispatch_id 
            ON workorder_workorderdispatchmaterial(dispatch_workorder_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workorder_dispatchquality_dispatch_id 
            ON workorder_workorderdispatchquality(dispatch_workorder_id);
        """)
        
        print("✅ 派工單資料表創建完成！")
        
        # 更新遷移記錄
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied) 
            VALUES ('dispatch', '0001_initial', NOW())
            ON CONFLICT DO NOTHING;
        """)
        
        print("✅ 遷移記錄已更新！")

if __name__ == '__main__':
    try:
        create_dispatch_tables()
        print("🎉 所有派工單資料表創建成功！")
    except Exception as e:
        print(f"❌ 創建資料表時發生錯誤: {e}")
        sys.exit(1)
