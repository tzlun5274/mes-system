#!/bin/bash
# 分階段遷移策略 - 先關閉定時任務模型，讓其他模組先遷移

echo "🚀 開始分階段遷移策略..."

# 進入專案目錄
cd /var/www/mes

# 第一階段：關閉 django_celery_beat，讓其他模組先遷移
echo "📋 第一階段：關閉 django_celery_beat，讓其他模組先遷移"

# 1. 確保 django_celery_beat 被註解掉
echo "確保 django_celery_beat 被註解掉..."
sed -i 's/"django_celery_beat"/# "django_celery_beat"/g' mes_config/settings.py
sed -i 's/CELERY_BEAT_SCHEDULER/# CELERY_BEAT_SCHEDULER/g' mes_config/settings.py

# 2. 註解掉所有 django_celery_beat 的導入
echo "註解掉所有 django_celery_beat 的導入..."
find . -name "*.py" -type f -exec sed -i 's/^from django_celery_beat/# from django_celery_beat/g' {} \;
find . -name "*.py" -type f -exec sed -i 's/^import django_celery_beat/# import django_celery_beat/g' {} \;

echo "✅ django_celery_beat 已完全關閉"

# 3. 清理資料庫中的 django_celery_beat 遷移記錄
echo "清理資料庫中的 django_celery_beat 遷移記錄..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('DELETE FROM django_migrations WHERE app = %s;', ['django_celery_beat'])
print('已清除 django_celery_beat 遷移記錄')
"

# 4. 執行其他模組的遷移
echo "執行其他模組的遷移..."
python3 manage.py migrate --skip-checks

# 5. 檢查其他模組的遷移狀態
echo "檢查其他模組的遷移狀態..."
python3 manage.py showmigrations | grep -v django_celery_beat

echo "✅ 第一階段完成：其他模組遷移成功"

# 第二階段：重新開啟 django_celery_beat，讓系統自動產生遷移
echo "📋 第二階段：重新開啟 django_celery_beat，讓系統自動產生遷移"

# 6. 重新啟用 django_celery_beat
echo "重新啟用 django_celery_beat..."
sed -i 's/# "django_celery_beat"/"django_celery_beat"/g' mes_config/settings.py
sed -i 's/# CELERY_BEAT_SCHEDULER/CELERY_BEAT_SCHEDULER/g' mes_config/settings.py

# 7. 恢復 django_celery_beat 的導入（只恢復必要的）
echo "恢復 django_celery_beat 的導入..."
sed -i 's/# from django_celery_beat.models/from django_celery_beat.models/g' system/views.py
sed -i 's/# from django_celery_beat.models/from django_celery_beat.models/g' erp_integration/views.py

echo "✅ django_celery_beat 已重新啟用"

# 8. 為 django_celery_beat 創建新的遷移（編號會自動往後移）
echo "為 django_celery_beat 創建新的遷移（編號會自動往後移）..."
python3 manage.py makemigrations django_celery_beat

# 9. 檢查新產生的遷移編號
echo "檢查新產生的遷移編號..."
python3 manage.py showmigrations django_celery_beat

# 10. 執行 django_celery_beat 的遷移
echo "執行 django_celery_beat 的遷移..."
python3 manage.py migrate django_celery_beat

# 11. 最終檢查
echo "最終檢查..."
python3 manage.py showmigrations django_celery_beat

# 12. 檢查資料表數量
echo "檢查資料表數量..."
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
table_count = cursor.fetchone()[0]
print(f'📊 資料表總數: {table_count}')
"

echo "🎉 分階段遷移策略完成！"
echo "💡 現在 django_celery_beat 的遷移編號應該會自動往後移，依賴關係也會正確建立"
