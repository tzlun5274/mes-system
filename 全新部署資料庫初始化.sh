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

# 2. 清除並重建資料庫
echo -e "${YELLOW}📋 步驟 2: 清除並重建資料庫...${NC}" | tee -a $LOG_FILE
echo -e "${YELLOW}⚠️  這將清除所有現有資料庫資料！${NC}" | tee -a $LOG_FILE

# 停止可能使用資料庫的服務
echo "停止相關服務..." | tee -a $LOG_FILE
systemctl stop celery-mes_config 2>/dev/null || true
systemctl stop celerybeat-mes_config 2>/dev/null || true

# 讀取資料庫配置
DATABASE_NAME=$(grep "^DATABASE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_db")
DATABASE_USER=$(grep "^DATABASE_USER=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_user")
DATABASE_PASSWORD=$(grep "^DATABASE_PASSWORD=" .env | cut -d'=' -f2 2>/dev/null || echo "mes_password")

echo "資料庫配置:" | tee -a $LOG_FILE
echo "  名稱: $DATABASE_NAME" | tee -a $LOG_FILE
echo "  使用者: $DATABASE_USER" | tee -a $LOG_FILE

# 清除資料庫
echo "清除資料庫..." | tee -a $LOG_FILE
sudo -u postgres dropdb $DATABASE_NAME 2>/dev/null || true
sudo -u postgres dropuser $DATABASE_USER 2>/dev/null || true

# 重新建立資料庫和用戶
echo "重新建立資料庫和用戶..." | tee -a $LOG_FILE
sudo -u postgres psql -c "CREATE USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE $DATABASE_NAME OWNER $DATABASE_USER;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER $DATABASE_USER CREATEDB;" 2>/dev/null || true

# 測試資料庫連線
echo "測試資料庫連線..." | tee -a $LOG_FILE
if sudo -u postgres psql -d $DATABASE_NAME -c "SELECT 1;" 2>&1 | grep -q "1 row"; then
    echo -e "${GREEN}✅ 資料庫連線測試成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫連線測試失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 3. 清理所有遷移檔案（保留 __init__.py）
echo -e "${YELLOW}📋 步驟 3: 清理遷移檔案...${NC}" | tee -a $LOG_FILE
echo "清除舊的遷移檔案..." | tee -a $LOG_FILE
find . -path '*/migrations/*.py' -not -name '__init__.py' -delete 2>/dev/null || true
find . -path '*/migrations/__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

echo -e "${GREEN}✅ 遷移檔案已清理${NC}" | tee -a $LOG_FILE

# 4. 生成初始遷移（按正確順序）
echo -e "${YELLOW}📋 步驟 4: 生成初始遷移...${NC}" | tee -a $LOG_FILE
echo "重新生成遷移檔案（按正確順序）..." | tee -a $LOG_FILE
if python3 manage.py makemigrations 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 初始遷移已生成${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 生成初始遷移失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 5. 執行遷移
echo -e "${YELLOW}📋 步驟 5: 執行遷移...${NC}" | tee -a $LOG_FILE
if python3 manage.py migrate 2>&1 | tee -a $LOG_FILE; then
    echo -e "${GREEN}✅ 遷移已執行${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 執行遷移失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 6. 創建超級用戶（根據 .env 設定）
echo -e "${YELLOW}📋 步驟 6: 創建超級用戶...${NC}" | tee -a $LOG_FILE
create_superuser_from_env

# 7. 收集靜態檔案
echo -e "${YELLOW}📋 步驟 7: 收集靜態檔案...${NC}" | tee -a $LOG_FILE
if python3 manage.py collectstatic --noinput 2>&1 | tee -a $LOG_FILE; then
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

# 9. 驗證關鍵資料表
echo -e "${YELLOW}📋 步驟 9: 驗證關鍵資料表...${NC}" | tee -a $LOG_FILE
python3 manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    # 檢查 system_user_permission_detail 資料表
    cursor.execute('SELECT tablename FROM pg_tables WHERE tablename = %s;', ['system_user_permission_detail'])
    result = cursor.fetchall()
    if result:
        print('✅ system_user_permission_detail 資料表存在')
    else:
        print('❌ system_user_permission_detail 資料表不存在')
        
    # 檢查所有 system 相關資料表
    cursor.execute('SELECT tablename FROM pg_tables WHERE tablename LIKE %s ORDER BY tablename;', ['system_%'])
    tables = cursor.fetchall()
    print(f'✅ 找到 {len(tables)} 個 system 相關資料表:')
    for table in tables:
        print(f'   - {table[0]}')
" 2>&1 | tee -a $LOG_FILE

echo -e "${GREEN}🎉 MES 系統資料庫初始化完成！${NC}" | tee -a $LOG_FILE
echo -e "${CYAN}📝 系統資訊:${NC}" | tee -a $LOG_FILE
echo "   - 請使用遷移輔助工具創建超級用戶" | tee -a $LOG_FILE
echo "   - 或檢查 .env 檔案中的 SUPERUSER_* 設定" | tee -a $LOG_FILE
echo "初始化完成時間: $(date)" | tee -a $LOG_FILE

# 函數：根據 .env 檔案創建超級用戶
create_superuser_from_env() {
    echo "🔍 檢查 .env 檔案設定..." | tee -a $LOG_FILE
    
    # 檢查 .env 檔案是否存在
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  .env 檔案不存在，跳過超級用戶創建${NC}" | tee -a $LOG_FILE
        echo "   請使用遷移輔助工具創建超級用戶" | tee -a $LOG_FILE
        return
    fi
    
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
        return
    fi
    
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
}
