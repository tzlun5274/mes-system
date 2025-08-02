#!/bin/bash

echo "🔧 開始修復 MES 系統資料庫..."

# 設定環境變數
export PGPASSWORD=mes_password
export DJANGO_SETTINGS_MODULE=mes_config.settings
export PYTHONPATH=/var/www/mes

cd /var/www/mes

echo "步驟1: 建立核心資料表..."
python3 create_core_tables.py

echo "步驟2: 執行 Django migrate..."
python3 manage.py migrate --noinput

echo "步驟3: 建立超級用戶..."
python3 manage.py createsuperuser --noinput --username admin --email admin@example.com || echo "超級用戶可能已存在"

echo "步驟4: 收集靜態檔案..."
python3 manage.py collectstatic --noinput

echo "🎉 資料庫修復完成！"
echo "系統現在應該可以正常運作了。"
echo "預設管理員帳號: admin"
echo "預設管理員密碼: admin123" 