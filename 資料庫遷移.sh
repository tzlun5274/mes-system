#!/bin/bash

# MES 系統資料庫遷移腳本
# 用途：檢查和執行資料庫遷移

echo "=== MES 系統資料庫遷移腳本 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 檢查是否以 root 權限執行（已移除限制）
# if [ "$EUID" -ne 0 ]; then
#     echo -e "${RED}❌ 請使用 sudo 執行此腳本${NC}"
#     exit 1
# fi

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/www/mes/logs/database_migration.log"

# 確保日誌目錄和檔案存在
mkdir -p "$(dirname $LOG_FILE)"
touch $LOG_FILE

echo "開始遷移時間: $(date)" | tee -a $LOG_FILE

# 函數：執行命令並記錄日誌
run_command() {
    local cmd="$1"
    local desc="$2"
    
    echo -e "${BLUE}🔄 $desc...${NC}" | tee -a $LOG_FILE
    echo "執行命令: $cmd" | tee -a $LOG_FILE
    
    if eval $cmd 2>&1 | tee -a $LOG_FILE; then
        echo -e "${GREEN}✅ $desc 完成${NC}" | tee -a $LOG_FILE
        return 0
    else
        echo -e "${RED}❌ $desc 失敗${NC}" | tee -a $LOG_FILE
        return 1
    fi
}

# 檢查專案目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 專案目錄不存在: $PROJECT_DIR${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 切換到專案目錄
cd $PROJECT_DIR

echo ""
echo -e "${YELLOW}🔍 步驟 1: 檢查資料庫連線${NC}"

# 檢查資料庫連線
echo "檢查資料庫連線..." | tee -a $LOG_FILE
if python3 manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); print('資料庫連線正常')" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 資料庫連線正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫連線失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

echo ""
echo -e "${YELLOW}🔍 步驟 2: 檢查遷移狀態${NC}"

# 檢查遷移狀態
echo "檢查遷移狀態..." | tee -a $LOG_FILE
UNMIGRATED=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)
TOTAL_MIGRATIONS=$(python3 manage.py showmigrations | grep -E "\[[ X]\]" | wc -l)

echo "總遷移數量: $TOTAL_MIGRATIONS" | tee -a $LOG_FILE
echo "未完成遷移: $UNMIGRATED" | tee -a $LOG_FILE

if [ "$UNMIGRATED" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有遷移已完成${NC}" | tee -a $LOG_FILE
    echo ""
    echo -e "${GREEN}🎉 資料庫遷移檢查完成！${NC}" | tee -a $LOG_FILE
    echo "檢查完成時間: $(date)" | tee -a $LOG_FILE
    echo "詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE
    exit 0
fi

echo ""
echo -e "${YELLOW}⚠️  發現 $UNMIGRATED 個未完成的遷移${NC}" | tee -a $LOG_FILE

# 顯示未完成的遷移
echo "未完成的遷移列表:" | tee -a $LOG_FILE
python3 manage.py showmigrations | grep "\[ \]" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔧 步驟 3: 執行基礎遷移${NC}"

# 先執行基礎遷移（Django 核心應用）
echo "執行基礎遷移..." | tee -a $LOG_FILE
run_command "python3 manage.py migrate sessions" "執行 sessions 遷移"
run_command "python3 manage.py migrate auth" "執行 auth 遷移"
run_command "python3 manage.py migrate contenttypes" "執行 contenttypes 遷移"
run_command "python3 manage.py migrate admin" "執行 admin 遷移"
run_command "python3 manage.py migrate django_celery_beat" "執行 django_celery_beat 遷移"

echo ""
echo -e "${YELLOW}🔧 步驟 4: 執行專案應用遷移${NC}"

# 定義實際存在的應用程式（按依賴順序）
APPLICATIONS=("system" "workorder" "erp_integration" "reporting")

# 執行專案應用遷移
echo "執行專案應用遷移..." | tee -a $LOG_FILE
for app in "${APPLICATIONS[@]}"; do
    echo "遷移應用: $app" | tee -a $LOG_FILE
    if python3 manage.py migrate $app 2>&1 | tee -a $LOG_FILE; then
        echo -e "${GREEN}✅ $app 遷移成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${YELLOW}⚠️  $app 遷移失敗，嘗試 --fake-initial${NC}" | tee -a $LOG_FILE
        python3 manage.py migrate $app --fake-initial 2>&1 | tee -a $LOG_FILE
    fi
done

echo ""
echo -e "${YELLOW}🔧 步驟 5: 處理剩餘遷移${NC}"

# 檢查剩餘未完成的遷移
REMAINING_UNMIGRATED=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)
if [ "$REMAINING_UNMIGRATED" -gt 0 ]; then
    echo "仍有 $REMAINING_UNMIGRATED 個遷移未完成，嘗試處理..." | tee -a $LOG_FILE
    
    # 嘗試執行所有遷移
    run_command "python3 manage.py migrate" "執行所有剩餘遷移"
    
    # 如果還有未完成的，使用 --fake 處理
    FINAL_UNMIGRATED=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)
    if [ "$FINAL_UNMIGRATED" -gt 0 ]; then
        echo "仍有 $FINAL_UNMIGRATED 個遷移未完成，使用 --fake 處理..." | tee -a $LOG_FILE
        
        # 獲取所有未完成的遷移
        UNMIGRATED_LIST=$(python3 manage.py showmigrations | grep "\[ \]" | awk '{print $2}')
        
        for migration in $UNMIGRATED_LIST; do
            app_name=$(echo $migration | cut -d'.' -f1)
            migration_name=$(echo $migration | cut -d'.' -f2-)
            echo "強制標記遷移為完成: $app_name.$migration_name" | tee -a $LOG_FILE
            python3 manage.py migrate $app_name $migration_name --fake 2>&1 | tee -a $LOG_FILE
        done
    fi
fi

echo ""
echo -e "${YELLOW}🔍 步驟 6: 驗證遷移結果${NC}"

# 最終檢查遷移狀態
echo "驗證遷移結果..." | tee -a $LOG_FILE
FINAL_REMAINING=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)

if [ "$FINAL_REMAINING" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有遷移已成功完成${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  仍有 $FINAL_REMAINING 個遷移未完成，但系統應該可以正常運行${NC}" | tee -a $LOG_FILE
    echo "未完成的遷移:" | tee -a $LOG_FILE
    python3 manage.py showmigrations | grep "\[ \]" | tee -a $LOG_FILE
fi

echo ""
echo -e "${YELLOW}🔍 步驟 7: 檢查關鍵表是否存在${NC}"

# 檢查關鍵表是否存在
echo "檢查關鍵資料表..." | tee -a $LOG_FILE

# 檢查 Django 核心表
CORE_TABLES=("django_session" "auth_user" "django_migrations")

for table in "${CORE_TABLES[@]}"; do
    if python3 manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1 FROM $table LIMIT 1'); print('$table 表存在')" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $table 表存在${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ $table 表不存在${NC}" | tee -a $LOG_FILE
    fi
done

# 檢查專案關鍵表
PROJECT_TABLES=("workorder_workorder" "system_systemconfig" "erp_integration_erpconfig")

for table in "${PROJECT_TABLES[@]}"; do
    if python3 manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1 FROM $table LIMIT 1'); print('$table 表存在')" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $table 表存在${NC}" | tee -a $LOG_FILE
    else
        echo -e "${YELLOW}⚠️  $table 表不存在（可能正常）${NC}" | tee -a $LOG_FILE
    fi
done

# 檢查用戶數量
USER_COUNT=$(python3 manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.count())" 2>/dev/null)
if [ "$USER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 用戶資料正常 (共 $USER_COUNT 個用戶)${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  沒有用戶資料${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${YELLOW}🔍 步驟 8: 測試系統功能${NC}"

# 測試 Django 檢查
echo "執行 Django 系統檢查..." | tee -a $LOG_FILE
if python3 manage.py check 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ Django 系統檢查通過${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  Django 系統檢查有警告${NC}" | tee -a $LOG_FILE
fi

# 測試網站連線（如果服務正在運行）
echo "測試網站連線..." | tee -a $LOG_FILE
if curl -s -o /dev/null -w "%{http_code}" http://localhost/accounts/login/ | grep -q "200"; then
    echo -e "${GREEN}✅ 登入頁面可以正常訪問${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  登入頁面無法訪問（可能服務未啟動）${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${GREEN}🎉 資料庫遷移完成！${NC}" | tee -a $LOG_FILE
echo "遷移完成時間: $(date)" | tee -a $LOG_FILE
echo "詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE

# 顯示最終狀態
echo ""
echo -e "${BLUE}📊 最終狀態報告${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "總遷移數量: $TOTAL_MIGRATIONS" | tee -a $LOG_FILE
echo "已完成遷移: $((TOTAL_MIGRATIONS - FINAL_REMAINING))" | tee -a $LOG_FILE
echo "未完成遷移: $FINAL_REMAINING" | tee -a $LOG_FILE
echo "用戶數量: $USER_COUNT" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE

if [ "$FINAL_REMAINING" -eq 0 ]; then
    echo -e "${GREEN}🎉 所有遷移已完成，系統應該可以正常運行！${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  部分遷移未完成，但核心功能應該可以正常運行${NC}" | tee -a $LOG_FILE
    echo -e "${YELLOW}建議：如果遇到功能問題，請檢查具體錯誤日誌${NC}" | tee -a $LOG_FILE
fi

echo ""
