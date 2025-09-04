#!/bin/bash

# 清理專案遷移腳本
# 用途：完全清理專案的所有遷移相關檔案，準備部署到生產主機

echo "=== 清理專案遷移腳本 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 檢查是否以 mes 用戶執行
if [ "$(whoami)" != "mes" ]; then
    echo -e "${RED}❌ 請以 mes 用戶身份執行此腳本${NC}"
    echo "請執行：su - mes 或 sudo -u mes ./清理專案遷移.sh"
    exit 1
fi

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/log/mes/clean_migrations.log"

# 檢查日誌目錄是否存在，如果不存在則使用專案目錄
if [ ! -d "/var/log/mes" ]; then
    echo "日誌目錄 /var/log/mes 不存在，使用專案目錄下的日誌"
    LOG_FILE="$PROJECT_DIR/clean_migrations.log"
fi

# 確保日誌檔案存在
touch $LOG_FILE
chmod 644 $LOG_FILE

echo "開始清理遷移時間: $(date)" | tee -a $LOG_FILE

# 檢查專案目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 專案目錄不存在: $PROJECT_DIR${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 切換到專案目錄
cd $PROJECT_DIR

echo ""
echo -e "${YELLOW}⚠️  警告：此操作將完全清理所有遷移相關檔案！${NC}"
echo -e "${YELLOW}⚠️  此操作不可逆，請確認您要部署到生產主機！${NC}"
echo ""
read -p "確定要繼續嗎？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🗑️  步驟 1: 刪除所有遷移檔案${NC}"

# 刪除所有遷移檔案（保留 __init__.py）
echo "刪除所有遷移檔案..." | tee -a $LOG_FILE
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
echo -e "${GREEN}✅ 所有遷移檔案已刪除${NC}" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🗑️  步驟 2: 刪除遷移備份目錄${NC}"

# 刪除遷移備份目錄
echo "刪除遷移備份目錄..." | tee -a $LOG_FILE
find . -type d -name "migrations_backup_*" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✅ 遷移備份目錄已刪除${NC}" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🗑️  步驟 3: 清理資料庫遷移記錄${NC}"

# 清理資料庫中的遷移記錄
echo "清理資料庫遷移記錄..." | tee -a $LOG_FILE
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('DELETE FROM django_migrations WHERE app IN (\"system\", \"workorder\", \"erp_integration\", \"reporting\", \"equip\", \"material\", \"process\", \"scheduling\", \"quality\", \"kanban\", \"ai\", \"production\")')
print('資料庫遷移記錄已清理')
" 2>&1 | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔍 步驟 4: 檢查清理結果${NC}"

# 檢查遷移檔案數量
MIGRATION_FILES=$(find . -path "*/migrations/*.py" -not -name "__init__.py" | wc -l)
echo "剩餘遷移檔案數量: $MIGRATION_FILES" | tee -a $LOG_FILE

# 檢查備份目錄數量
BACKUP_DIRS=$(find . -type d -name "migrations_backup_*" | wc -l)
echo "剩餘備份目錄數量: $BACKUP_DIRS" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔧 步驟 5: 重新生成初始遷移${NC}"

# 重新生成初始遷移
echo "重新生成初始遷移..." | tee -a $LOG_FILE
if python3 manage.py makemigrations 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 初始遷移生成成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  初始遷移生成有問題${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${YELLOW}🔍 步驟 6: 最終檢查${NC}"

# 檢查生成的遷移檔案
NEW_MIGRATION_FILES=$(find . -path "*/migrations/*.py" -not -name "__init__.py" | wc -l)
echo "新生成的遷移檔案數量: $NEW_MIGRATION_FILES" | tee -a $LOG_FILE

# 顯示生成的遷移檔案
echo "生成的遷移檔案:" | tee -a $LOG_FILE
find . -path "*/migrations/*.py" -not -name "__init__.py" | tee -a $LOG_FILE

echo ""
echo -e "${GREEN}🎉 專案遷移清理完成！${NC}" | tee -a $LOG_FILE
echo "清理完成時間: $(date)" | tee -a $LOG_FILE
echo "詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE

echo ""
echo -e "${BLUE}📋 部署建議：${NC}"
echo "1. 將清理後的專案打包：tar -czf mes_clean.tar.gz ."
echo "2. 上傳到生產主機"
echo "3. 在生產主機執行：python3 manage.py migrate --fake"
echo "4. 創建超級用戶：python3 manage.py createsuperuser"

echo ""


