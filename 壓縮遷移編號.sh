#!/bin/bash
# 使用 Django 官方遷移壓縮功能解決編號問題

echo "🚀 開始使用 Django 遷移壓縮功能..."

# 進入專案目錄
cd /var/www/mes

# 1. 檢查 django_celery_beat 的遷移狀態
echo "📋 步驟 1: 檢查 django_celery_beat 的遷移狀態..."
python3 manage.py showmigrations django_celery_beat

# 2. 壓縮 django_celery_beat 的遷移檔案
echo "📋 步驟 2: 壓縮 django_celery_beat 的遷移檔案..."
echo "這將合併所有遷移檔案並重新編號..."

# 壓縮遷移檔案（從 0001 到最新）
python3 manage.py squashmigrations django_celery_beat 0001 0022

# 3. 檢查壓縮後的遷移檔案
echo "📋 步驟 3: 檢查壓縮後的遷移檔案..."
ls -la /home/mes/.local/lib/python3.10/site-packages/django_celery_beat/migrations/

# 4. 清理資料庫中的遷移記錄
echo "📋 步驟 4: 清理資料庫中的遷移記錄..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('DELETE FROM django_migrations WHERE app = %s;', ['django_celery_beat'])
print('已清除 django_celery_beat 遷移記錄')
"

# 5. 執行壓縮後的遷移
echo "📋 步驟 5: 執行壓縮後的遷移..."
python3 manage.py migrate django_celery_beat

# 6. 檢查最終狀態
echo "📋 步驟 6: 檢查最終狀態..."
python3 manage.py showmigrations django_celery_beat

# 7. 檢查資料表數量
echo "📋 步驟 7: 檢查資料表數量..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
table_count = cursor.fetchone()[0]
print(f'📊 資料表總數: {table_count}')
"

echo "🎉 遷移壓縮完成！"
echo "💡 現在 django_celery_beat 的遷移編號應該已經重新整理，沒有重複編號問題"
