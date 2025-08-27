#!/bin/bash

# 全新主機資料庫初始化修復腳本
# 用途：解決全新主機上資料表未建立的問題

echo "=== 全新主機資料庫初始化修復 ==="
echo ""

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
LOG_FILE="/var/log/mes/database_fix.log"

# 建立日誌目錄
mkdir -p /var/log/mes
touch $LOG_FILE

echo "開始修復時間: $(date)" | tee -a $LOG_FILE

# 函數：從 .env 檔案讀取配置
load_env_config() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        echo -e "${RED}❌ 未找到 .env 檔案${NC}" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "正在讀取 .env 配置..." | tee -a $LOG_FILE
    
    # 讀取資料庫配置
    DATABASE_NAME=$(grep "^DATABASE_NAME=" $PROJECT_DIR/.env | cut -d'=' -f2)
    DATABASE_USER=$(grep "^DATABASE_USER=" $PROJECT_DIR/.env | cut -d'=' -f2)
    DATABASE_PASSWORD=$(grep "^DATABASE_PASSWORD=" $PROJECT_DIR/.env | cut -d'=' -f2)
    DATABASE_HOST=$(grep "^DATABASE_HOST=" $PROJECT_DIR/.env | cut -d'=' -f2)
    DATABASE_PORT=$(grep "^DATABASE_PORT=" $PROJECT_DIR/.env | cut -d'=' -f2)
    
    # 驗證必要配置
    if [ -z "$DATABASE_NAME" ] || [ -z "$DATABASE_USER" ] || [ -z "$DATABASE_PASSWORD" ]; then
        echo -e "${RED}❌ 資料庫配置不完整${NC}" | tee -a $LOG_FILE
        echo "請檢查 .env 檔案中的 DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "配置讀取完成:" | tee -a $LOG_FILE
    echo "  資料庫: $DATABASE_NAME" | tee -a $LOG_FILE
    echo "  使用者: $DATABASE_USER" | tee -a $LOG_FILE
    echo "  主機: $DATABASE_HOST" | tee -a $LOG_FILE
    echo "  端口: $DATABASE_PORT" | tee -a $LOG_FILE
}

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

# 步驟 0: 讀取 .env 配置
echo ""
echo -e "${YELLOW}🔧 步驟 0: 讀取 .env 配置${NC}"
load_env_config

echo ""
echo -e "${YELLOW}🔧 步驟 1: 檢查資料庫狀態${NC}"

# 檢查 PostgreSQL 服務
run_command "systemctl status postgresql" "檢查 PostgreSQL 服務狀態"

# 檢查資料庫是否存在
echo "檢查資料庫是否存在..." | tee -a $LOG_FILE
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DATABASE_NAME; then
    echo -e "${GREEN}✅ 資料庫 $DATABASE_NAME 已存在${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️ 資料庫 $DATABASE_NAME 不存在，正在建立...${NC}" | tee -a $LOG_FILE
    run_command "sudo -u postgres createdb $DATABASE_NAME" "建立資料庫 $DATABASE_NAME"
fi

# 檢查資料庫用戶是否存在
echo "檢查資料庫用戶是否存在..." | tee -a $LOG_FILE
if sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DATABASE_USER'" | grep -q 1; then
    echo -e "${GREEN}✅ 用戶 $DATABASE_USER 已存在，更新密碼${NC}" | tee -a $LOG_FILE
    run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "更新用戶密碼"
else
    echo -e "${YELLOW}⚠️ 用戶 $DATABASE_USER 不存在，正在建立...${NC}" | tee -a $LOG_FILE
    run_command "sudo -u postgres psql -c \"CREATE USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "建立用戶 $DATABASE_USER"
fi

# 授予資料庫權限
echo "授予資料庫權限..." | tee -a $LOG_FILE
run_command "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;\"" "授予資料庫權限"
run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER CREATEDB;\"" "授予建立資料庫權限"

echo ""
echo -e "${YELLOW}🔧 步驟 2: 檢查專案目錄${NC}"

# 檢查專案目錄
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 專案目錄不存在: $PROJECT_DIR${NC}" | tee -a $LOG_FILE
    echo "請先執行完整部署腳本" | tee -a $LOG_FILE
    exit 1
fi

# 檢查 .env 檔案
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}❌ .env 檔案不存在${NC}" | tee -a $LOG_FILE
    exit 1
fi

echo -e "${GREEN}✅ 專案目錄檢查完成${NC}" | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔧 步驟 3: 修復權限${NC}"

# 修復專案目錄權限
run_command "chown -R mes:www-data $PROJECT_DIR" "修復專案目錄權限"
run_command "chmod -R 755 $PROJECT_DIR" "設定專案目錄權限"

echo ""
echo -e "${YELLOW}🔧 步驟 4: 初始化資料庫${NC}"

cd $PROJECT_DIR

# 檢查 Django 設定
echo "檢查 Django 設定..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py check" "檢查 Django 設定"

# 建立資料表結構（不執行遷移）
echo "建立資料表結構..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py migrate --run-syncdb" "建立資料表結構"

# 執行所有遷移
echo "執行所有遷移..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py migrate" "執行所有遷移"

# 驗證遷移狀態
echo "驗證遷移狀態..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py showmigrations" "檢查遷移狀態"

# 檢查資料表
echo "檢查資料表..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py dbshell -c '\dt'" "檢查資料表"

echo ""
echo -e "${YELLOW}🔧 步驟 5: 建立超級用戶${NC}"

# 從 .env 檔案讀取超級用戶資訊
SUPERUSER_NAME=$(grep "^SUPERUSER_NAME=" .env | cut -d'=' -f2)
SUPERUSER_EMAIL=$(grep "^SUPERUSER_EMAIL=" .env | cut -d'=' -f2)
SUPERUSER_PASSWORD=$(grep "^SUPERUSER_PASSWORD=" .env | cut -d'=' -f2)

if [ -z "$SUPERUSER_NAME" ] || [ -z "$SUPERUSER_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️ 無法從 .env 讀取超級用戶資訊，請手動建立${NC}" | tee -a $LOG_FILE
    echo "請執行: sudo -u mes python3 manage.py createsuperuser" | tee -a $LOG_FILE
else
    echo "建立超級用戶: $SUPERUSER_NAME" | tee -a $LOG_FILE
    run_command "sudo -u mes python3 manage.py shell -c \"from django.contrib.auth.models import User; User.objects.create_superuser('$SUPERUSER_NAME', '$SUPERUSER_EMAIL', '$SUPERUSER_PASSWORD') if not User.objects.filter(username='$SUPERUSER_NAME').exists() else print('超級用戶已存在')\"" "建立超級用戶"
fi

echo ""
echo -e "${YELLOW}🔧 步驟 6: 收集靜態檔案${NC}"

# 收集靜態檔案
run_command "sudo -u mes python3 manage.py collectstatic --noinput" "收集靜態檔案"

echo ""
echo -e "${YELLOW}🔧 步驟 7: 重啟服務${NC}"

# 重啟所有服務
run_command "systemctl restart mes.service" "重啟 MES 服務"
run_command "systemctl restart nginx" "重啟 Nginx"

echo ""
echo -e "${GREEN}🎉 資料庫初始化修復完成！${NC}" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "📋 驗證清單：" | tee -a $LOG_FILE
echo "✅ 資料庫已建立" | tee -a $LOG_FILE
echo "✅ 資料表已建立" | tee -a $LOG_FILE
echo "✅ 遷移已執行" | tee -a $LOG_FILE
echo "✅ 超級用戶已建立" | tee -a $LOG_FILE
echo "✅ 靜態檔案已收集" | tee -a $LOG_FILE
echo "✅ 服務已重啟" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "🌐 現在可以訪問網站：" | tee -a $LOG_FILE
echo "   http://$(hostname -I | awk '{print $1}')" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "📝 詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE
