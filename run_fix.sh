#!/bin/bash

echo "🔧 修復 MES 系統資料庫..."

# 設定環境變數
export PGPASSWORD=mes_password

# 執行 SQL 修復腳本
echo "執行 SQL 修復腳本..."
psql -h localhost -p 5432 -U mes_user -d mes_db -f fix_db.sql

echo "✅ 資料庫修復完成！"
echo "現在可以重新啟動 Django 服務了。" 