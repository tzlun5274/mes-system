#!/bin/bash

# MES 系統遷移輔助工具
# 用途：提供遷移狀態檢查、回滾、重置、衝突解決等功能

echo "=== MES 系統遷移輔助工具 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 檢查是否以 mes 用戶執行
if [ "$(whoami)" != "mes" ]; then
    echo -e "${RED}❌ 請以 mes 用戶身份執行此腳本${NC}"
    echo "請執行：su - mes 或 sudo -u mes ./遷移輔助工具.sh"
    exit 1
fi

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/log/mes/migration_helper.log"
BACKUP_DIR="/var/www/mes/backups_DB/migration_backups"

# 檢查日誌目錄是否存在，如果不存在則使用專案目錄
if [ ! -d "/var/log/mes" ]; then
    echo "日誌目錄 /var/log/mes 不存在，使用專案目錄下的日誌"
    LOG_FILE="$PROJECT_DIR/migration_helper.log"
fi

# 確保日誌檔案存在
touch $LOG_FILE
chmod 644 $LOG_FILE

echo "工具啟動時間: $(date)" | tee -a $LOG_FILE

# 函數：顯示選單
show_menu() {
    echo ""
    echo -e "${CYAN}請選擇要執行的功能：${NC}"
    echo "1. 檢查遷移狀態"
    echo "2. 顯示詳細遷移資訊"
    echo "3. 檢查遷移衝突"
    echo "4. 回滾到指定遷移"
    echo "5. 重置應用程式遷移"
    echo "6. 解決遷移衝突"
    echo "7. 創建遷移檔案"
    echo "8. 檢查資料庫表結構"
    echo "9. 清理孤立遷移"
    echo "10. 遷移統計報告"
    echo "11. 備份當前狀態"
    echo "12. 創建超級使用者"
    echo "0. 退出"
    echo ""
}

# 函數：檢查遷移狀態
check_migration_status() {
    echo -e "${YELLOW}🔍 檢查遷移狀態...${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    # 獲取所有應用程式的遷移狀態
    echo "=== 遷移狀態總覽 ===" | tee -a $LOG_FILE
    python3 manage.py showmigrations | tee -a $LOG_FILE
    
    # 統計資訊
    TOTAL_MIGRATIONS=$(python3 manage.py showmigrations | grep -E "\[[ X]\]" | wc -l)
    COMPLETED_MIGRATIONS=$(python3 manage.py showmigrations | grep "\[X\]" | wc -l)
    PENDING_MIGRATIONS=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)
    
    echo "" | tee -a $LOG_FILE
    echo "=== 統計資訊 ===" | tee -a $LOG_FILE
    echo "總遷移數量: $TOTAL_MIGRATIONS" | tee -a $LOG_FILE
    echo "已完成遷移: $COMPLETED_MIGRATIONS" | tee -a $LOG_FILE
    echo "待執行遷移: $PENDING_MIGRATIONS" | tee -a $LOG_FILE
    
    if [ "$PENDING_MIGRATIONS" -eq 0 ]; then
        echo -e "${GREEN}✅ 所有遷移已完成${NC}" | tee -a $LOG_FILE
    else
        echo -e "${YELLOW}⚠️  有 $PENDING_MIGRATIONS 個遷移待執行${NC}" | tee -a $LOG_FILE
    fi
}

# 函數：顯示詳細遷移資訊
show_detailed_migrations() {
    echo -e "${YELLOW}🔍 顯示詳細遷移資訊...${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    # 獲取所有應用程式
    APPS=$(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('corsheaders') and not app.startswith('django_celery_beat'):
        apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null)
    
    for app in $APPS; do
        echo "" | tee -a $LOG_FILE
        echo "=== $app 應用程式 ===" | tee -a $LOG_FILE
        
        # 檢查應用是否有遷移
        if python3 manage.py showmigrations $app >/dev/null 2>&1; then
            python3 manage.py showmigrations $app | tee -a $LOG_FILE
            
            # 顯示遷移檔案資訊
            MIGRATIONS_DIR="$PROJECT_DIR/$app/migrations"
            if [ -d "$MIGRATIONS_DIR" ]; then
                echo "遷移檔案:" | tee -a $LOG_FILE
                ls -la $MIGRATIONS_DIR/*.py 2>/dev/null | tee -a $LOG_FILE
            fi
        else
            echo "沒有遷移檔案" | tee -a $LOG_FILE
        fi
    done
}

# 函數：檢查遷移衝突
check_migration_conflicts() {
    echo -e "${YELLOW}🔍 檢查遷移衝突...${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    # 檢查是否有衝突的遷移
    CONFLICTS=$(python3 manage.py showmigrations 2>&1 | grep -i "conflict\|error\|exception" || echo "")
    
    if [ -z "$CONFLICTS" ]; then
        echo -e "${GREEN}✅ 未發現遷移衝突${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 發現遷移衝突：${NC}" | tee -a $LOG_FILE
        echo "$CONFLICTS" | tee -a $LOG_FILE
    fi
    
    # 檢查是否有重複的遷移號碼
    echo "" | tee -a $LOG_FILE
    echo "檢查重複遷移號碼..." | tee -a $LOG_FILE
    
    for app in $(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('corsheaders') and not app.startswith('django_celery_beat'):
        apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null); do
        MIGRATIONS_DIR="$PROJECT_DIR/$app/migrations"
        if [ -d "$MIGRATIONS_DIR" ]; then
            DUPLICATES=$(find $MIGRATIONS_DIR -name "*.py" -not -name "__init__.py" | xargs basename -s .py | sort | uniq -d)
            if [ ! -z "$DUPLICATES" ]; then
                echo -e "${RED}⚠️  $app 有重複遷移號碼: $DUPLICATES${NC}" | tee -a $LOG_FILE
            fi
        fi
    done
}

# 函數：回滾到指定遷移
rollback_migration() {
    echo -e "${YELLOW}🔍 回滾遷移功能${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "請輸入要回滾的應用程式名稱："
    read -r app_name
    
    echo "請輸入要回滾到的遷移號碼（例如：0001）："
    read -r migration_number
    
    echo "警告：此操作將回滾 $app_name 到遷移 $migration_number"
    echo "請確認是否繼續？(y/N)"
    read -r confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "執行回滾..." | tee -a $LOG_FILE
        python3 manage.py migrate $app_name $migration_number 2>&1 | tee -a $LOG_FILE
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ 回滾成功${NC}" | tee -a $LOG_FILE
        else
            echo -e "${RED}❌ 回滾失敗${NC}" | tee -a $LOG_FILE
        fi
    else
        echo "取消回滾操作" | tee -a $LOG_FILE
    fi
}

# 函數：重置應用程式遷移
reset_app_migrations() {
    echo -e "${YELLOW}🔍 重置應用程式遷移${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "請選擇重置方式："
    echo "1. 重置單一應用程式"
    echo "2. 重置所有專案應用程式"
    echo "3. 重置所有應用程式（包含 Django 核心）"
    read -r reset_choice
    
    case $reset_choice in
        1)
            reset_single_app_migration
            ;;
        2)
            reset_all_project_apps
            ;;
        3)
            reset_all_apps
            ;;
        *)
            echo -e "${RED}無效選擇${NC}" | tee -a $LOG_FILE
            return 1
            ;;
    esac
}

# 函數：重置單一應用程式遷移
reset_single_app_migration() {
    echo "請輸入要重置的應用程式名稱："
    read -r app_name
    
    echo "警告：此操作將完全重置 $app_name 的遷移狀態"
    echo "請確認是否繼續？(y/N)"
    read -r confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "執行重置..." | tee -a $LOG_FILE
        
        # 先標記所有遷移為未應用
        python3 manage.py migrate $app_name zero --fake 2>&1 | tee -a $LOG_FILE
        
        # 然後重新應用遷移
        python3 manage.py migrate $app_name 2>&1 | tee -a $LOG_FILE
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ 重置成功${NC}" | tee -a $LOG_FILE
        else
            echo -e "${RED}❌ 重置失敗${NC}" | tee -a $LOG_FILE
        fi
    else
        echo "取消重置操作" | tee -a $LOG_FILE
    fi
}

# 函數：重置所有專案應用程式
reset_all_project_apps() {
    echo -e "${RED}⚠️  警告：此操作將重置所有專案應用程式的遷移狀態${NC}" | tee -a $LOG_FILE
    echo "這將影響以下應用程式：" | tee -a $LOG_FILE
    
    # 獲取所有專案應用程式
    PROJECT_APPS=$(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('corsheaders') and not app.startswith('django_celery_beat'):
        apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null)
    
    for app in $PROJECT_APPS; do
        echo "  - $app" | tee -a $LOG_FILE
    done
    
    echo ""
    echo "請確認是否繼續？(y/N)"
    read -r confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "執行全部專案應用程式重置..." | tee -a $LOG_FILE
        
        for app in $PROJECT_APPS; do
            echo "重置 $app..." | tee -a $LOG_FILE
            
            # 先標記所有遷移為未應用
            python3 manage.py migrate $app zero --fake 2>&1 | tee -a $LOG_FILE
            
            # 然後重新應用遷移
            python3 manage.py migrate $app 2>&1 | tee -a $LOG_FILE
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ $app 重置成功${NC}" | tee -a $LOG_FILE
            else
                echo -e "${RED}❌ $app 重置失敗${NC}" | tee -a $LOG_FILE
            fi
        done
        
        echo -e "${GREEN}✅ 所有專案應用程式重置完成${NC}" | tee -a $LOG_FILE
    else
        echo "取消重置操作" | tee -a $LOG_FILE
    fi
}

# 函數：重置所有應用程式（包含 Django 核心）
reset_all_apps() {
    echo -e "${RED}🚨 極度警告：此操作將重置所有應用程式的遷移狀態${NC}" | tee -a $LOG_FILE
    echo "這包括 Django 核心應用程式，可能會導致系統不穩定！" | tee -a $LOG_FILE
    echo ""
    echo "請輸入 'RESET_ALL' 來確認此危險操作："
    read -r danger_confirm
    
    if [ "$danger_confirm" != "RESET_ALL" ]; then
        echo "取消重置操作" | tee -a $LOG_FILE
        return 1
    fi
    
    echo "請再次確認：此操作將重置所有遷移，包括 Django 核心應用程式！"
    echo "輸入 'YES_I_UNDERSTAND' 來最終確認："
    read -r final_confirm
    
    if [ "$final_confirm" != "YES_I_UNDERSTAND" ]; then
        echo "取消重置操作" | tee -a $LOG_FILE
        return 1
    fi
    
    echo "執行全部應用程式重置..." | tee -a $LOG_FILE
    
    # 獲取所有應用程式
    ALL_APPS=$(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null)
    
    for app in $ALL_APPS; do
        echo "重置 $app..." | tee -a $LOG_FILE
        
        # 先標記所有遷移為未應用
        python3 manage.py migrate $app zero --fake 2>&1 | tee -a $LOG_FILE
        
        # 然後重新應用遷移
        python3 manage.py migrate $app 2>&1 | tee -a $LOG_FILE
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ $app 重置成功${NC}" | tee -a $LOG_FILE
        else
            echo -e "${RED}❌ $app 重置失敗${NC}" | tee -a $LOG_FILE
        fi
    done
    
    echo -e "${GREEN}✅ 所有應用程式重置完成${NC}" | tee -a $LOG_FILE
    echo -e "${YELLOW}⚠️  建議重新啟動 Django 服務${NC}" | tee -a $LOG_FILE
}

# 函數：解決遷移衝突
resolve_migration_conflicts() {
    echo -e "${YELLOW}🔍 解決遷移衝突${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "請輸入有衝突的應用程式名稱："
    read -r app_name
    
    echo "請輸入衝突的遷移號碼："
    read -r migration_number
    
    echo "選擇解決方法："
    echo "1. 使用 --fake 標記為已應用"
    echo "2. 使用 --fake-initial 標記初始遷移"
    echo "3. 手動編輯遷移檔案"
    read -r choice
    
    case $choice in
        1)
            echo "使用 --fake 標記..." | tee -a $LOG_FILE
            python3 manage.py migrate $app_name $migration_number --fake 2>&1 | tee -a $LOG_FILE
            ;;
        2)
            echo "使用 --fake-initial 標記..." | tee -a $LOG_FILE
            python3 manage.py migrate $app_name $migration_number --fake-initial 2>&1 | tee -a $LOG_FILE
            ;;
        3)
            echo "請手動編輯遷移檔案：$PROJECT_DIR/$app_name/migrations/${migration_number}_*.py"
            ;;
        *)
            echo "無效選擇" | tee -a $LOG_FILE
            ;;
    esac
}

# 函數：創建遷移檔案
create_migration() {
    echo -e "${YELLOW}🔍 創建遷移檔案${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "請輸入要創建遷移的應用程式名稱："
    read -r app_name
    
    echo "請輸入遷移名稱（可選）："
    read -r migration_name
    
    if [ -z "$migration_name" ]; then
        python3 manage.py makemigrations $app_name 2>&1 | tee -a $LOG_FILE
    else
        python3 manage.py makemigrations $app_name --name "$migration_name" 2>&1 | tee -a $LOG_FILE
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 遷移檔案創建成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 遷移檔案創建失敗${NC}" | tee -a $LOG_FILE
    fi
}

# 函數：檢查資料庫表結構
check_database_structure() {
    echo -e "${YELLOW}🔍 檢查資料庫表結構${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    # 檢查所有表是否存在
    echo "=== 資料庫表檢查 ===" | tee -a $LOG_FILE
    
    # 獲取所有模型對應的表名
    TABLES=$(python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"\"\"
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name
\"\"\")
tables = [row[0] for row in cursor.fetchall()]
print(' '.join(tables))
" 2>/dev/null)
    
    for table in $TABLES; do
        # 檢查表是否有資料
        ROW_COUNT=$(python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM \"$table\"')
print(cursor.fetchone()[0])
" 2>/dev/null)
        
        echo "$table: $ROW_COUNT 筆資料" | tee -a $LOG_FILE
    done
}

# 函數：清理孤立遷移
cleanup_orphaned_migrations() {
    echo -e "${YELLOW}🔍 清理孤立遷移${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "檢查孤立遷移檔案..." | tee -a $LOG_FILE
    
    for app in $(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('corsheaders') and not app.startswith('django_celery_beat'):
        apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null); do
        MIGRATIONS_DIR="$PROJECT_DIR/$app/migrations"
        if [ -d "$MIGRATIONS_DIR" ]; then
            echo "檢查 $app 的遷移檔案..." | tee -a $LOG_FILE
            
            # 檢查是否有未在資料庫中記錄的遷移檔案
            for migration_file in $MIGRATIONS_DIR/*.py; do
                if [ -f "$migration_file" ] && [ "$(basename $migration_file)" != "__init__.py" ]; then
                    migration_name=$(basename $migration_file .py)
                    # 檢查是否在資料庫中有記錄
                    EXISTS=$(python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM django_migrations WHERE app = \"$app\" AND name = \"$migration_name\"')
print(cursor.fetchone()[0])
" 2>/dev/null)
                    
                    if [ "$EXISTS" -eq "0" ]; then
                        echo -e "${YELLOW}⚠️  發現孤立遷移: $app/$migration_name${NC}" | tee -a $LOG_FILE
                    fi
                fi
            done
        fi
    done
}

# 函數：遷移統計報告
migration_statistics() {
    echo -e "${YELLOW}🔍 遷移統計報告${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "=== 遷移統計報告 ===" | tee -a $LOG_FILE
    echo "生成時間: $(date)" | tee -a $LOG_FILE
    echo "" | tee -a $LOG_FILE
    
    # 總體統計
    TOTAL_MIGRATIONS=$(python3 manage.py showmigrations | grep -E "\[[ X]\]" | wc -l)
    COMPLETED_MIGRATIONS=$(python3 manage.py showmigrations | grep "\[X\]" | wc -l)
    PENDING_MIGRATIONS=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)
    
    echo "總體統計:" | tee -a $LOG_FILE
    echo "  總遷移數量: $TOTAL_MIGRATIONS" | tee -a $LOG_FILE
    echo "  已完成遷移: $COMPLETED_MIGRATIONS" | tee -a $LOG_FILE
    echo "  待執行遷移: $PENDING_MIGRATIONS" | tee -a $LOG_FILE
    echo "  完成率: $((COMPLETED_MIGRATIONS * 100 / TOTAL_MIGRATIONS))%" | tee -a $LOG_FILE
    echo "" | tee -a $LOG_FILE
    
    # 按應用程式統計
    echo "按應用程式統計:" | tee -a $LOG_FILE
    
    for app in $(python3 manage.py shell -c "
from django.conf import settings
apps = []
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('corsheaders') and not app.startswith('django_celery_beat'):
        apps.append(app.split('.')[-1])
print(' '.join(apps))
" 2>/dev/null); do
        APP_TOTAL=$(python3 manage.py showmigrations $app 2>/dev/null | grep -E "\[[ X]\]" | wc -l)
        APP_COMPLETED=$(python3 manage.py showmigrations $app 2>/dev/null | grep "\[X\]" | wc -l)
        APP_PENDING=$(python3 manage.py showmigrations $app 2>/dev/null | grep "\[ \]" | wc -l)
        
        if [ "$APP_TOTAL" -gt 0 ]; then
            echo "  $app: $APP_COMPLETED/$APP_TOTAL 完成 ($APP_PENDING 待執行)" | tee -a $LOG_FILE
        fi
    done
}

# 函數：備份當前狀態
backup_current_state() {
    echo -e "${YELLOW}🔍 備份當前狀態${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_NAME="migration_state_backup_${TIMESTAMP}"
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql"
    
    # 創建資料庫備份
    DB_NAME=$(python3 manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])" 2>/dev/null || echo "mesdb")
    DB_USER=$(python3 manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['USER'])" 2>/dev/null || echo "mesuser")
    
    if pg_dump -U $DB_USER -h localhost $DB_NAME > $BACKUP_FILE 2>/dev/null; then
        echo -e "${GREEN}✅ 狀態備份已創建: $BACKUP_FILE${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 狀態備份失敗${NC}" | tee -a $LOG_FILE
    fi
    
    # 創建遷移狀態備份
    MIGRATION_STATE_FILE="${BACKUP_DIR}/${BACKUP_NAME}_migration_state.txt"
    python3 manage.py showmigrations > $MIGRATION_STATE_FILE 2>&1
    echo -e "${GREEN}✅ 遷移狀態備份已創建: $MIGRATION_STATE_FILE${NC}" | tee -a $LOG_FILE
}

# 函數：創建超級使用者
create_superuser() {
    echo -e "${YELLOW}🔍 創建超級使用者${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    echo "=== 超級使用者創建工具 ===" | tee -a $LOG_FILE
    
    # 檢查是否已有超級使用者
    EXISTING_SUPERUSERS=$(python3 manage.py shell -c "
from django.contrib.auth.models import User
superusers = User.objects.filter(is_superuser=True).count()
print(superusers)
" 2>/dev/null)
    
    if [ "$EXISTING_SUPERUSERS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  發現 $EXISTING_SUPERUSERS 個現有超級使用者${NC}" | tee -a $LOG_FILE
        echo "現有超級使用者列表:" | tee -a $LOG_FILE
        python3 manage.py shell -c "
from django.contrib.auth.models import User
for user in User.objects.filter(is_superuser=True):
    print(f'- {user.username} ({user.email})')
" 2>/dev/null | tee -a $LOG_FILE
        echo "" | tee -a $LOG_FILE
    fi
    
    echo "請選擇創建方式：" | tee -a $LOG_FILE
    echo "1. 互動式創建（手動輸入）"
    echo "2. 自動創建（使用 .env 預設值）"
    read -r create_method
    
    case $create_method in
        1)
            create_interactive_superuser
            ;;
        2)
            create_auto_superuser
            ;;
        *)
            echo -e "${RED}無效選擇${NC}" | tee -a $LOG_FILE
            return 1
            ;;
    esac
}

# 函數：互動式創建超級使用者
create_interactive_superuser() {
    echo -e "${CYAN}=== 互動式創建超級使用者 ===${NC}" | tee -a $LOG_FILE
    
    echo "請輸入使用者名稱："
    read -r username
    
    echo "請輸入電子郵件："
    read -r email
    
    echo "請輸入密碼："
    read -s password
    echo ""
    
    echo "請再次輸入密碼確認："
    read -s password_confirm
    echo ""
    
    if [ "$password" != "$password_confirm" ]; then
        echo -e "${RED}❌ 密碼不匹配${NC}" | tee -a $LOG_FILE
        return 1
    fi
    
    echo "請輸入名字（可選）："
    read -r first_name
    
    echo "請輸入姓氏（可選）："
    read -r last_name
    
    echo "創建超級使用者..." | tee -a $LOG_FILE
    
    # 使用 Django shell 創建超級使用者
    python3 manage.py shell -c "
from django.contrib.auth.models import User
try:
    user = User.objects.create_user(
        username='$username',
        email='$email',
        password='$password',
        first_name='$first_name',
        last_name='$last_name',
        is_superuser=True,
        is_staff=True
    )
    print(f'✅ 超級使用者創建成功: {user.username}')
    print(f'   電子郵件: {user.email}')
    print(f'   姓名: {user.first_name} {user.last_name}')
except Exception as e:
    print(f'❌ 創建失敗: {str(e)}')
" 2>&1 | tee -a $LOG_FILE
}

# 函數：自動創建超級使用者
create_auto_superuser() {
    echo -e "${CYAN}=== 自動創建超級使用者 ===${NC}" | tee -a $LOG_FILE
    
    # 從 .env 檔案讀取超級使用者設定
    echo "🔍 從 .env 檔案讀取超級使用者設定..." | tee -a $LOG_FILE
    
    # 讀取 .env 檔案中的設定
    ENV_USERNAME=$(grep "^SUPERUSER_NAME=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    ENV_EMAIL=$(grep "^SUPERUSER_EMAIL=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    ENV_PASSWORD=$(grep "^SUPERUSER_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    
    # 檢查是否讀取到設定
    if [ -z "$ENV_USERNAME" ] || [ -z "$ENV_EMAIL" ] || [ -z "$ENV_PASSWORD" ]; then
        echo -e "${RED}❌ .env 檔案中缺少超級使用者設定${NC}" | tee -a $LOG_FILE
        echo "請確保 .env 檔案包含以下設定：" | tee -a $LOG_FILE
        echo "  SUPERUSER_NAME=admin" | tee -a $LOG_FILE
        echo "  SUPERUSER_EMAIL=admin@example.com" | tee -a $LOG_FILE
        echo "  SUPERUSER_PASSWORD=1234" | tee -a $LOG_FILE
        return 1
    fi
    
    echo "📋 讀取到的設定：" | tee -a $LOG_FILE
    echo "  使用者名稱: $ENV_USERNAME" | tee -a $LOG_FILE
    echo "  電子郵件: $ENV_EMAIL" | tee -a $LOG_FILE
    echo "  密碼: $ENV_PASSWORD" | tee -a $LOG_FILE
    
    echo "請確認是否創建超級使用者？(y/N)"
    read -r confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "取消創建" | tee -a $LOG_FILE
        return 1
    fi
    
    echo "創建超級使用者..." | tee -a $LOG_FILE
    
    # 直接創建超級使用者
    python3 manage.py shell -c "
from django.contrib.auth.models import User
try:
    # 檢查使用者是否已存在
    if User.objects.filter(username='$ENV_USERNAME').exists():
        user = User.objects.get(username='$ENV_USERNAME')
        user.set_password('$ENV_PASSWORD')
        user.email = '$ENV_EMAIL'
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f'✅ 超級使用者已更新: {user.username}')
    else:
        user = User.objects.create_user(
            username='$ENV_USERNAME',
            email='$ENV_EMAIL',
            password='$ENV_PASSWORD',
            first_name='系統',
            last_name='管理員',
            is_superuser=True,
            is_staff=True
        )
        print(f'✅ 超級使用者創建成功: {user.username}')
    print(f'   電子郵件: {user.email}')
except Exception as e:
    print(f'❌ 創建失敗: {str(e)}')
" 2>&1 | tee -a $LOG_FILE
}



# 主選單循環
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            check_migration_status
            ;;
        2)
            show_detailed_migrations
            ;;
        3)
            check_migration_conflicts
            ;;
        4)
            rollback_migration
            ;;
        5)
            reset_app_migrations
            ;;
        6)
            resolve_migration_conflicts
            ;;
        7)
            create_migration
            ;;
        8)
            check_database_structure
            ;;
        9)
            cleanup_orphaned_migrations
            ;;
        10)
            migration_statistics
            ;;
        11)
            backup_current_state
            ;;
        12)
            create_superuser
            ;;
        0)
            echo "退出工具" | tee -a $LOG_FILE
            break
            ;;
        *)
            echo -e "${RED}無效選擇，請重新輸入${NC}" | tee -a $LOG_FILE
            ;;
    esac
    
    echo ""
    echo "按 Enter 鍵繼續..."
    read
done

echo "工具結束時間: $(date)" | tee -a $LOG_FILE
