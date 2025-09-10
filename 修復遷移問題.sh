#!/bin/bash
# 修復遷移問題腳本

echo "🔧 修復 MES 系統遷移問題..."

cd /var/www/mes

echo "📋 步驟 1: 修復 django_celery_beat 遷移問題..."

# 清除有問題的 django_celery_beat 遷移記錄
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"DELETE FROM django_migrations WHERE app = 'django_celery_beat';\")
print('已清除 django_celery_beat 遷移記錄')
"

# 手動標記關鍵遷移為已執行
python3 manage.py migrate django_celery_beat 0001_initial --fake
python3 manage.py migrate django_celery_beat 0021_auto_20250910_1056 --fake

echo "📋 步驟 2: 創建新的遷移檔案..."

# 為 system 模組創建遷移檔案
python3 manage.py makemigrations system --skip-checks

echo "📋 步驟 3: 執行遷移..."

# 執行所有遷移
python3 manage.py migrate --skip-checks

echo "📋 步驟 4: 檢查結果..."

# 檢查資料表數量
table_count=$(python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
print(cursor.fetchone()[0])
" 2>/dev/null)

echo "📊 資料表總數: $table_count"

if [ "$table_count" -gt 50 ]; then
    echo "✅ 遷移修復成功！"
else
    echo "⚠️  遷移可能未完全成功"
fi

echo "修復完成時間: $(date)"
