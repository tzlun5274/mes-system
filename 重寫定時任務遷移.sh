#!/bin/bash
# 重寫定時任務遷移腳本 - 確保遷移編號和依賴關係正確

echo "🚀 開始重寫定時任務遷移..."

# 進入專案目錄
cd /var/www/mes

# 1. 備份現有的 django_celery_beat 遷移檔案
echo "備份現有的 django_celery_beat 遷移檔案..."
BACKUP_DIR="/tmp/django_celery_beat_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r /home/mes/.local/lib/python3.10/site-packages/django_celery_beat/migrations/* "$BACKUP_DIR/"
echo "✅ 備份完成：$BACKUP_DIR"

# 2. 清理資料庫中的 django_celery_beat 遷移記錄
echo "清理資料庫中的 django_celery_beat 遷移記錄..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('DELETE FROM django_migrations WHERE app = %s;', ['django_celery_beat'])
print('已清除 django_celery_beat 遷移記錄')
"

# 3. 刪除 django_celery_beat 的所有遷移檔案（保留 __init__.py）
echo "刪除 django_celery_beat 的所有遷移檔案..."
cd /home/mes/.local/lib/python3.10/site-packages/django_celery_beat/migrations/
rm -f *.py
echo "from django.db import migrations" > __init__.py
echo "✅ 遷移檔案清理完成"

# 4. 重新啟用 django_celery_beat
echo "重新啟用 django_celery_beat..."
cd /var/www/mes

# 修改 settings.py
sed -i 's/# "django_celery_beat"/"django_celery_beat"/g' mes_config/settings.py
sed -i 's/# CELERY_BEAT_SCHEDULER/CELERY_BEAT_SCHEDULER/g' mes_config/settings.py

# 修改 system/views.py
sed -i 's/# from django_celery_beat.models/from django_celery_beat.models/g' system/views.py

echo "✅ django_celery_beat 已重新啟用"

# 5. 為 django_celery_beat 創建新的初始遷移
echo "為 django_celery_beat 創建新的初始遷移..."
python3 manage.py makemigrations django_celery_beat

# 6. 執行 django_celery_beat 的初始遷移
echo "執行 django_celery_beat 的初始遷移..."
python3 manage.py migrate django_celery_beat --fake-initial

# 7. 檢查遷移狀態
echo "檢查遷移狀態..."
python3 manage.py showmigrations django_celery_beat

# 8. 檢查資料表數量
echo "檢查資料表數量..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
table_count = cursor.fetchone()[0]
print(f'📊 資料表總數: {table_count}')
"

echo "🎉 定時任務遷移重寫完成！"
echo "📝 備份位置：$BACKUP_DIR"
echo "💡 如果出現問題，可以從備份恢復："
echo "   cp -r $BACKUP_DIR/* /home/mes/.local/lib/python3.10/site-packages/django_celery_beat/migrations/"
