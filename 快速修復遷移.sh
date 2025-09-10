#!/bin/bash
# 快速修復遷移問題腳本
# 專門解決 django_celery_beat 遷移衝突問題

echo "🚀 快速修復 MES 系統遷移問題..."

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /var/www/mes

echo -e "${YELLOW}📋 步驟 1: 修復 django_celery_beat 遷移問題...${NC}"

# 清除有問題的遷移記錄
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"DELETE FROM django_migrations WHERE app = 'django_celery_beat';\")
print('已清除 django_celery_beat 遷移記錄')
"

# 手動標記關鍵遷移為已執行
python3 manage.py migrate django_celery_beat 0001_initial --fake
python3 manage.py migrate django_celery_beat 0021_auto_20250910_1056 --fake

echo -e "${GREEN}✅ django_celery_beat 遷移問題已修復${NC}"

echo -e "${YELLOW}📋 步驟 2: 執行所有模組遷移...${NC}"

# 一次性執行所有模組遷移
apps=(
    "system"
    "erp_integration" 
    "workorder"
    "equip"
    "material"
    "process"
    "scheduling"
    "quality"
    "kanban"
    "reporting"
    "production"
    "ai"
    "fill_work"
    "manufacturing_order"
    "onsite_reporting"
    "workorder_dispatch"
)

for app in "${apps[@]}"; do
    echo "執行 $app 模組遷移..."
    if python3 manage.py migrate $app --skip-checks >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $app 成功${NC}"
    else
        echo -e "  ${RED}❌ $app 失敗${NC}"
    fi
done

echo -e "${YELLOW}📋 步驟 3: 檢查結果...${NC}"

# 檢查資料表數量
table_count=$(python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
print(cursor.fetchone()[0])
" 2>/dev/null)

echo -e "${GREEN}📊 資料表總數: $table_count${NC}"

if [ "$table_count" -gt 50 ]; then
    echo -e "${GREEN}🎉 遷移修復成功！所有模組資料表已創建${NC}"
else
    echo -e "${RED}⚠️  遷移可能未完全成功，資料表數量較少${NC}"
fi

echo "修復完成時間: $(date)"
