#!/bin/bash

# 重置遷移腳本
# 用途：刪除所有遷移檔案，重新生成初始遷移

echo "=== 重置遷移腳本 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 檢查是否以 root 權限執行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 請使用 sudo 執行此腳本${NC}"
    exit 1
fi

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/log/mes/reset_migration.log"

# 確保日誌檔案存在
touch $LOG_FILE

echo "開始重置遷移時間: $(date)" | tee -a $LOG_FILE

# 檢查專案目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 專案目錄不存在: $PROJECT_DIR${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 切換到專案目錄
cd $PROJECT_DIR

echo ""
echo -e "${YELLOW}⚠️  警告：此操作將刪除所有遷移檔案！${NC}"
echo -e "${YELLOW}⚠️  請確認您已備份資料庫！${NC}"
echo ""
read -p "確定要繼續嗎？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔍 步驟 1: 備份現有遷移檔案${NC}"

# 創建備份目錄
BACKUP_DIR="migrations_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "創建備份目錄: $BACKUP_DIR" | tee -a $LOG_FILE

# 備份所有遷移檔案
for app in system workorder erp_integration reporting; do
    if [ -d "$app/migrations" ]; then
        echo "備份 $app 遷移檔案..." | tee -a $LOG_FILE
        cp -r $app/migrations $BACKUP_DIR/${app}_migrations
    fi
done

echo -e "${GREEN}✅ 遷移檔案已備份到 $BACKUP_DIR${NC}" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🗑️  步驟 2: 刪除所有遷移檔案${NC}"

# 刪除所有遷移檔案（保留 __init__.py）
for app in system workorder erp_integration reporting; do
    if [ -d "$app/migrations" ]; then
        echo "清理 $app 遷移檔案..." | tee -a $LOG_FILE
        find $app/migrations -name "*.py" -not -name "__init__.py" -delete
        echo "已刪除 $app 的所有遷移檔案" | tee -a $LOG_FILE
    fi
done

echo -e "${GREEN}✅ 所有遷移檔案已刪除${NC}" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔧 步驟 3: 重新生成初始遷移${NC}"

# 重新生成初始遷移
for app in system workorder erp_integration reporting; do
    if [ -d "$app" ]; then
        echo "為 $app 生成初始遷移..." | tee -a $LOG_FILE
        if python3 manage.py makemigrations $app 2>&1 | tee -a $LOG_FILE; then
            echo -e "${GREEN}✅ $app 初始遷移生成成功${NC}" | tee -a $LOG_FILE
        else
            echo -e "${YELLOW}⚠️  $app 沒有模型變更${NC}" | tee -a $LOG_FILE
        fi
    fi
done

echo ""
echo -e "${YELLOW}🔍 步驟 4: 檢查生成的遷移檔案${NC}"

# 檢查生成的遷移檔案
for app in system workorder erp_integration reporting; do
    if [ -d "$app/migrations" ]; then
        MIGRATION_COUNT=$(find $app/migrations -name "*.py" -not -name "__init__.py" | wc -l)
        echo "$app: $MIGRATION_COUNT 個遷移檔案" | tee -a $LOG_FILE
    fi
done

echo ""
echo -e "${YELLOW}🔧 步驟 5: 執行遷移${NC}"

# 執行遷移
echo "執行所有遷移..." | tee -a $LOG_FILE
if python3 manage.py migrate 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 遷移執行成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 遷移執行失敗${NC}" | tee -a $LOG_FILE
    echo "請檢查日誌檔案: $LOG_FILE"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔍 步驟 6: 最終檢查${NC}"

# 最終檢查
FINAL_UNMIGRATED=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)

if [ "$FINAL_UNMIGRATED" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有遷移已完成${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  仍有 $FINAL_UNMIGRATED 個遷移未完成${NC}" | tee -a $LOG_FILE
fi

# 測試 Django 檢查
echo "執行 Django 系統檢查..." | tee -a $LOG_FILE
if python3 manage.py check 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ Django 系統檢查通過${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  Django 系統檢查有警告${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${GREEN}🎉 遷移重置完成！${NC}" | tee -a $LOG_FILE
echo "重置完成時間: $(date)" | tee -a $LOG_FILE
echo "備份目錄: $BACKUP_DIR" | tee -a $LOG_FILE
echo "詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE

echo ""
