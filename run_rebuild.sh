#!/bin/bash

echo "🚀 執行資料庫重建..."

# 設定環境變數
export PGPASSWORD=mes_password
export DJANGO_SETTINGS_MODULE=mes_config.settings
export PYTHONPATH=/var/www/mes

# 切換到專案目錄
cd /var/www/mes

# 執行 Python 重建腳本
echo "執行 Python 重建腳本..."
python3 rebuild_db.py

echo "重建腳本執行完成！" 