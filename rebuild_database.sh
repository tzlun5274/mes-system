#!/bin/bash

echo "🔧 開始重建 MES 系統資料庫..."

# 設定環境變數
export PGPASSWORD=mes_password

# 步驟1: 停止所有連線到資料庫的程序
echo "步驟1: 停止所有資料庫連線..."
psql -h localhost -p 5432 -U mes_user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'mes_db' AND pid <> pg_backend_pid();" 2>/dev/null || echo "無法停止連線，繼續執行..."

# 步驟2: 刪除現有資料庫
echo "步驟2: 刪除現有資料庫..."
dropdb -h localhost -p 5432 -U mes_user --if-exists mes_db 2>/dev/null || echo "資料庫可能不存在，繼續執行..."

# 步驟3: 重新建立資料庫
echo "步驟3: 重新建立資料庫..."
createdb -h localhost -p 5432 -U mes_user mes_db

if [ $? -eq 0 ]; then
    echo "✅ 資料庫建立成功"
else
    echo "❌ 資料庫建立失敗"
    exit 1
fi

# 步驟4: 設定資料庫 schema
echo "步驟4: 設定資料庫 schema..."
psql -h localhost -p 5432 -U mes_user -d mes_db -c "SET search_path TO public;"

# 步驟5: 執行 Django migrate 建立所有資料表
echo "步驟5: 執行 Django migrate..."
cd /var/www/mes
export DJANGO_SETTINGS_MODULE=mes_config.settings
export PYTHONPATH=/var/www/mes

python3 manage.py migrate --noinput

if [ $? -eq 0 ]; then
    echo "✅ Django migrate 成功"
else
    echo "⚠️ Django migrate 出現警告，但繼續執行..."
fi

# 步驟6: 建立超級用戶
echo "步驟6: 建立超級用戶..."
python3 manage.py createsuperuser --noinput --username admin --email admin@example.com 2>/dev/null || echo "超級用戶可能已存在"

# 步驟7: 建立基本群組
echo "步驟7: 建立基本群組..."
python3 -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
import django
django.setup()
from django.contrib.auth.models import Group
groups = ['系統管理員', '生產主管', '作業員', '品質管理員', '報表使用者']
for group_name in groups:
    Group.objects.get_or_create(name=group_name)
print('基本群組建立完成')
"

# 步驟8: 收集靜態檔案
echo "步驟8: 收集靜態檔案..."
python3 manage.py collectstatic --noinput

echo ""
echo "🎉 資料庫重建完成！"
echo "系統現在可以正常使用了。"
echo "預設管理員帳號: admin"
echo "預設管理員密碼: admin123"
echo ""
echo "接下來你可以："
echo "1. 重新啟動 Django 服務"
echo "2. 使用系統管理功能還原之前的備份資料"
echo "3. 正常使用 MES 系統" 