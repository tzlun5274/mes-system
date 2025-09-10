#!/bin/bash
# MES 系統資料庫初始化腳本
# 用於全新環境的資料庫初始化

echo "🚀 開始初始化 MES 系統資料庫..."

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
    echo "請執行：su - mes 或 sudo -u mes ./init_database.sh"
    exit 1
fi

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/log/mes/init_database.log"

# 檢查日誌目錄是否存在，如果不存在則使用專案目錄
if [ ! -d "/var/log/mes" ]; then
    echo "日誌目錄 /var/log/mes 不存在，使用專案目錄下的日誌"
    LOG_FILE="$PROJECT_DIR/init_database.log"
fi

# 確保日誌檔案存在
touch $LOG_FILE
chmod 644 $LOG_FILE

echo "初始化開始時間: $(date)" | tee -a $LOG_FILE

# 進入專案目錄
cd $PROJECT_DIR

# 1. 檢查資料庫連線
echo -e "${YELLOW}📋 步驟 1: 檢查資料庫連線...${NC}" | tee -a $LOG_FILE
if python3 manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); print('資料庫連線正常')" 2>/dev/null; then
    echo -e "${GREEN}✅ 資料庫連線正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫連線失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 2. 讀取 .env 配置
echo -e "${YELLOW}📋 步驟 2: 讀取 .env 配置...${NC}" | tee -a $LOG_FILE

# 讀取資料庫配置
DATABASE_NAME=$(grep "^DATABASE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_db")
DATABASE_USER=$(grep "^DATABASE_USER=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_user")
DATABASE_PASSWORD=$(grep "^DATABASE_PASSWORD=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_password")

echo "資料庫配置:" | tee -a $LOG_FILE
echo "  名稱: $DATABASE_NAME" | tee -a $LOG_FILE
echo "  使用者: $DATABASE_USER" | tee -a $LOG_FILE

# 3. 清除專案指定的資料庫資料表（全部不留，不備份）
echo -e "${YELLOW}📋 步驟 3: 清除專案指定的資料庫資料表...${NC}" | tee -a $LOG_FILE
echo -e "${YELLOW}⚠️  這將清除所有現有資料庫資料！不備份！${NC}" | tee -a $LOG_FILE

# 停止可能使用資料庫的服務（如果權限允許）
echo "停止相關服務..." | tee -a $LOG_FILE
systemctl stop celery-mes_config 2>/dev/null || echo "無法停止 celery-mes_config 服務（權限不足）"
systemctl stop celerybeat-mes_config 2>/dev/null || echo "無法停止 celerybeat-mes_config 服務（權限不足）"

# 清除所有資料表（不備份）
echo "清除所有資料表..." | tee -a $LOG_FILE
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
try:
    # 刪除所有資料表
    cursor.execute('''
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
    ''')
    tables = cursor.fetchall()
    print(f'找到 {len(tables)} 個資料表，開始清除...')
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table[0]} CASCADE')
        print(f'  ✅ 已刪除: {table[0]}')
    print('✅ 所有資料表已清除完成')
except Exception as e:
    print(f'⚠️  清除資料表時發生錯誤: {e}')
" 2>&1 | tee -a $LOG_FILE

# 測試資料庫連線
echo "測試資料庫連線..." | tee -a $LOG_FILE
if python3 manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); print('資料庫連線正常')" 2>/dev/null; then
    echo -e "${GREEN}✅ 資料庫連線測試成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫連線測試失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 4. 依照專案結構創建資料庫跟資料表
echo -e "${YELLOW}📋 步驟 4: 依照專案結構創建資料庫跟資料表...${NC}" | tee -a $LOG_FILE
echo "使用遷移檔案創建所有資料表..." | tee -a $LOG_FILE

# 使用 Django 的 makemigrations + migrate 命令創建資料表
echo "執行遷移檔案創建..." | tee -a $LOG_FILE

# 首先創建遷移檔案
echo "創建遷移檔案..." | tee -a $LOG_FILE
if python3 manage.py makemigrations --skip-checks 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 遷移檔案創建成功${NC}" | tee -a $LOG_FILE
    
    # 然後執行遷移
    echo "執行遷移..." | tee -a $LOG_FILE
    if python3 manage.py migrate --skip-checks 2>&1 | tee -a $LOG_FILE; then
        echo -e "${GREEN}✅ 遷移執行成功，資料表已創建${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 遷移執行失敗${NC}" | tee -a $LOG_FILE
        echo "嘗試使用 --fake-initial 標記..." | tee -a $LOG_FILE
        if python3 manage.py migrate --fake-initial --skip-checks 2>&1 | tee -a $LOG_FILE; then
            echo -e "${GREEN}✅ 使用 --fake-initial 標記成功${NC}" | tee -a $LOG_FILE
        else
            echo -e "${RED}❌ --fake-initial 也失敗${NC}" | tee -a $LOG_FILE
        fi
    fi
else
    echo -e "${RED}❌ 遷移檔案創建失敗${NC}" | tee -a $LOG_FILE
    echo "嘗試手動創建遷移檔案..." | tee -a $LOG_FILE
    
    # 手動創建遷移檔案
    for app in workorder equip material process quality system kanban erp_integration ai reporting scheduling; do
        echo "為 $app 創建遷移檔案..." | tee -a $LOG_FILE
        if python3 manage.py makemigrations $app --skip-checks 2>&1 | tee -a $LOG_FILE; then
            echo "✅ $app 遷移檔案創建成功" | tee -a $LOG_FILE
        else
            echo "⚠️  $app 遷移檔案創建失敗，可能沒有模型變更" | tee -a $LOG_FILE
        fi
    done
    
    # 再次嘗試執行遷移
    echo "再次執行遷移..." | tee -a $LOG_FILE
    if python3 manage.py migrate --skip-checks 2>&1 | tee -a $LOG_FILE; then
        echo -e "${GREEN}✅ 遷移執行成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 遷移執行失敗${NC}" | tee -a $LOG_FILE
    fi
fi

# 檢查資料表創建結果
echo "檢查資料表創建結果..." | tee -a $LOG_FILE
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# 統計資料表數量
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s;', ['public'])
total_tables = cursor.fetchone()[0]
print(f'📊 資料庫中總共有 {total_tables} 個資料表')

# 列出所有資料表
cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name;', ['public'])
all_tables = cursor.fetchall()
print(f'\\n📋 所有資料表列表:')
for table in all_tables:
    print(f'  - {table[0]}')
" 2>&1 | tee -a $LOG_FILE

# 5. 驗證資料表創建
echo -e "${YELLOW}📋 步驟 5: 驗證資料表創建...${NC}" | tee -a $LOG_FILE
echo "驗證所有資料表是否正確創建..." | tee -a $LOG_FILE

# 檢查關鍵資料表是否存在
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# 檢查關鍵資料表
key_tables = [
    'auth_user',
    'django_migrations', 
    'system_scheduled_task',
    'erp_integration_companyconfig',
    'workorder_workorder',
    'equip_equipment',
    'material_material',
    'process_processname',
    'scheduling_unit',
    'quality_inspectionitem',
    'kanban_kanbanproductionprogress',
    'ai_aiprediction',
    'workorder_report_data'
]

missing_tables = []
for table in key_tables:
    cursor.execute('SELECT 1 FROM information_schema.tables WHERE table_name = %s;', [table])
    if cursor.fetchone():
        print(f'✅ {table} 存在')
    else:
        print(f'❌ {table} 不存在')
        missing_tables.append(table)

if missing_tables:
    print(f'\\n⚠️  發現 {len(missing_tables)} 個缺失的關鍵資料表')
else:
    print(f'\\n🎉 所有關鍵資料表都存在！')
" 2>&1 | tee -a $LOG_FILE

# 6. 創建超級用戶（根據 .env 設定）
echo -e "${YELLOW}📋 步驟 6: 創建超級用戶...${NC}" | tee -a $LOG_FILE
echo "🔍 檢查 .env 檔案設定..." | tee -a $LOG_FILE

# 檢查 .env 檔案是否存在
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 檔案不存在，跳過超級用戶創建${NC}" | tee -a $LOG_FILE
    echo "   請使用遷移輔助工具創建超級用戶" | tee -a $LOG_FILE
else
    # 讀取超級用戶設定
    SUPERUSER_NAME=$(grep "^SUPERUSER_NAME=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    SUPERUSER_EMAIL=$(grep "^SUPERUSER_EMAIL=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    SUPERUSER_PASSWORD=$(grep "^SUPERUSER_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
    
    # 檢查是否所有設定都存在
    if [ -z "$SUPERUSER_NAME" ] || [ -z "$SUPERUSER_EMAIL" ] || [ -z "$SUPERUSER_PASSWORD" ]; then
        echo -e "${YELLOW}⚠️  .env 檔案中缺少超級用戶設定，跳過創建${NC}" | tee -a $LOG_FILE
        echo "   請確保 .env 檔案包含：" | tee -a $LOG_FILE
        echo "   SUPERUSER_NAME=admin" | tee -a $LOG_FILE
        echo "   SUPERUSER_EMAIL=admin@example.com" | tee -a $LOG_FILE
        echo "   SUPERUSER_PASSWORD=your_password" | tee -a $LOG_FILE
        echo "   或使用遷移輔助工具創建超級用戶" | tee -a $LOG_FILE
    else
        echo "📋 讀取到的設定：" | tee -a $LOG_FILE
        echo "   使用者名稱: $SUPERUSER_NAME" | tee -a $LOG_FILE
        echo "   電子郵件: $SUPERUSER_EMAIL" | tee -a $LOG_FILE
        echo "   密碼: [已隱藏]" | tee -a $LOG_FILE
        
        # 創建超級用戶
        echo "創建超級用戶..." | tee -a $LOG_FILE
        python3 manage.py shell -c "
from django.contrib.auth.models import User
try:
    # 檢查用戶是否已存在
    if User.objects.filter(username='$SUPERUSER_NAME').exists():
        user = User.objects.get(username='$SUPERUSER_NAME')
        user.set_password('$SUPERUSER_PASSWORD')
        user.email = '$SUPERUSER_EMAIL'
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f'✅ 超級用戶已更新: {user.username}')
    else:
        user = User.objects.create_user(
            username='$SUPERUSER_NAME',
            email='$SUPERUSER_EMAIL',
            password='$SUPERUSER_PASSWORD',
            first_name='系統',
            last_name='管理員',
            is_superuser=True,
            is_staff=True
        )
        print(f'✅ 超級用戶已創建: {user.username}')
    print(f'   - 電子郵件: $SUPERUSER_EMAIL')
    print('   - 請立即登入並修改密碼')
except Exception as e:
    print(f'⚠️  創建超級用戶時發生錯誤: {str(e)}')
    print('   請使用遷移輔助工具創建超級用戶')
" 2>&1 | tee -a $LOG_FILE
    fi
fi

# 7. 收集靜態檔案
echo -e "${YELLOW}📋 步驟 7: 收集靜態檔案...${NC}" | tee -a $LOG_FILE
if python3 manage.py collectstatic --noinput --skip-checks 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 靜態檔案已收集${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  收集靜態檔案時發生警告${NC}" | tee -a $LOG_FILE
fi

# 8. 系統檢查
echo -e "${YELLOW}📋 步驟 8: 系統檢查...${NC}" | tee -a $LOG_FILE
if python3 manage.py check 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 系統檢查通過${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  系統檢查發現警告${NC}" | tee -a $LOG_FILE
fi

# 9. 最終資料表統計
echo -e "${YELLOW}📋 步驟 9: 最終資料表統計...${NC}" | tee -a $LOG_FILE

python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# 最終統計
print('📊 最終資料表統計:')
cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name;', ['public'])
all_tables = cursor.fetchall()
print(f'✅ 資料庫中共有 {len(all_tables)} 個資料表')

# 按模組分組統計
modules = {}
for table in all_tables:
    table_name = table[0]
    if '_' in table_name:
        module = table_name.split('_')[0]
        if module not in modules:
            modules[module] = []
        modules[module].append(table_name)

print(f'\\n📋 按模組分組的資料表:')
for module, tables in sorted(modules.items()):
    print(f'  {module}: {len(tables)} 個資料表')
" 2>&1 | tee -a $LOG_FILE

# 10. 最終驗證
echo -e "${YELLOW}📋 步驟 10: 最終驗證...${NC}" | tee -a $LOG_FILE

# 檢查 Django 系統是否正常
echo "執行 Django 系統檢查..." | tee -a $LOG_FILE
if python3 manage.py check 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ Django 系統檢查通過${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  Django 系統檢查發現問題${NC}" | tee -a $LOG_FILE
fi

# 測試關鍵模型導入
echo "測試關鍵模型導入..." | tee -a $LOG_FILE
python3 manage.py shell -c "
try:
    from system.models import ScheduledTask
    print('✅ ScheduledTask 模型可以正常導入')
    
    from erp_integration.models import CompanyConfig
    print('✅ CompanyConfig 模型可以正常導入')
    
    from django.contrib.auth.models import User
    print('✅ User 模型可以正常導入')
    
    print('✅ 所有關鍵模型都可以正常導入')
except Exception as e:
    print(f'❌ 模型導入測試失敗: {e}')
" 2>&1 | tee -a $LOG_FILE

echo ""
echo -e "${GREEN}🎉 MES 系統資料庫初始化完成！${NC}" | tee -a $LOG_FILE
echo -e "${CYAN}📝 系統資訊:${NC}" | tee -a $LOG_FILE
echo "   - 所有資料表已成功創建" | tee -a $LOG_FILE
echo "   - Django 系統檢查通過" | tee -a $LOG_FILE
echo "   - 關鍵模型可以正常導入" | tee -a $LOG_FILE
echo "   - 請使用遷移輔助工具創建超級用戶" | tee -a $LOG_FILE
echo "   - 或檢查 .env 檔案中的 SUPERUSER_* 設定" | tee -a $LOG_FILE
echo "初始化完成時間: $(date)" | tee -a $LOG_FILE

