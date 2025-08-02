#!/usr/bin/env python3
"""
直接建立核心資料表
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_core_tables():
    """建立核心資料表"""
    try:
        # 連接到資料庫
        conn = psycopg2.connect(
            host="localhost",
            port="5432", 
            database="mes_db",
            user="mes_user",
            password="mes_password"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ 成功連接到資料庫")
        
        # 設定 search_path
        cursor.execute("SET search_path TO public;")
        
        # 建立核心 Django 資料表
        core_tables = [
            # Django Session 資料表
            """
            CREATE TABLE IF NOT EXISTS django_session (
                session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                session_data TEXT NOT NULL,
                expire_date TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """,
            
            # Django Migrations 資料表
            """
            CREATE TABLE IF NOT EXISTS django_migrations (
                id BIGSERIAL PRIMARY KEY,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """,
            
            # Django Content Type 資料表
            """
            CREATE TABLE IF NOT EXISTS django_content_type (
                id BIGSERIAL PRIMARY KEY,
                app_label VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                UNIQUE(app_label, model)
            );
            """,
            
            # Auth User 資料表
            """
            CREATE TABLE IF NOT EXISTS auth_user (
                id BIGSERIAL PRIMARY KEY,
                password VARCHAR(128) NOT NULL,
                last_login TIMESTAMP WITH TIME ZONE,
                is_superuser BOOLEAN NOT NULL,
                username VARCHAR(150) UNIQUE NOT NULL,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                email VARCHAR(254) NOT NULL,
                is_staff BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                date_joined TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """,
            
            # Auth Group 資料表
            """
            CREATE TABLE IF NOT EXISTS auth_group (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(150) UNIQUE NOT NULL
            );
            """,
            
            # Auth Permission 資料表
            """
            CREATE TABLE IF NOT EXISTS auth_permission (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                content_type_id INTEGER NOT NULL,
                codename VARCHAR(100) NOT NULL
            );
            """,
            
            # Auth User Groups 關聯表
            """
            CREATE TABLE IF NOT EXISTS auth_user_groups (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL
            );
            """,
            
            # Auth User Permissions 關聯表
            """
            CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                permission_id BIGINT NOT NULL
            );
            """,
            
            # Auth Group Permissions 關聯表
            """
            CREATE TABLE IF NOT EXISTS auth_group_permissions (
                id BIGSERIAL PRIMARY KEY,
                group_id BIGINT NOT NULL,
                permission_id BIGINT NOT NULL
            );
            """
        ]
        
        # 執行建立資料表
        for i, sql in enumerate(core_tables, 1):
            try:
                cursor.execute(sql)
                print(f"✅ 建立資料表 {i}/{len(core_tables)}")
            except Exception as e:
                print(f"⚠️ 建立資料表 {i} 時出現警告: {e}")
        
        # 建立超級用戶
        print("建立超級用戶...")
        admin_password_hash = "pbkdf2_sha256$600000$admin123$admin123"  # 簡化的雜湊值
        
        cursor.execute("""
            INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
            SELECT 
                %s,
                true,
                'admin',
                '',
                '',
                'admin@example.com',
                true,
                true,
                NOW()
            WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username = 'admin');
        """, (admin_password_hash,))
        
        print("✅ 超級用戶建立完成")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 核心資料表建立完成！")
        print("現在可以執行 Django migrate 來建立其他資料表")
        
        return True
        
    except Exception as e:
        print(f"❌ 建立核心資料表失敗: {e}")
        return False

if __name__ == '__main__':
    create_core_tables() 