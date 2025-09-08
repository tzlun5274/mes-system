#!/bin/bash

# MES 系統開發環境部署腳本
# 用途：部署 MES 系統開發環境所需的基礎環境（系統套件、服務配置）
# 注意：此腳本配置為開發環境，使用 Django 開發伺服器而非 Gunicorn

echo "=== MES 系統開發環境部署腳本 ==="
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
LOG_BASE_DIR="/var/log/mes"
LOG_FILE="/var/log/mes_deploy.log"
HOST_IP=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -n 1)

# 建立日誌目錄並設定權限
mkdir -p $LOG_BASE_DIR
touch $LOG_FILE
chown -R mes:www-data $LOG_BASE_DIR
chmod -R 755 $LOG_BASE_DIR
chmod 644 $LOG_FILE

echo "開始部署時間: $(date)" | tee -a $LOG_FILE
echo "主機 IP: $HOST_IP" | tee -a $LOG_FILE

# 函數：從 .env 檔案讀取配置
load_env_config() {
    echo "正在讀取 .env 配置..." | tee -a $LOG_FILE
    
    # 讀取資料庫配置
    DATABASE_NAME=$(grep "^DATABASE_NAME=" .env | cut -d'=' -f2)
    DATABASE_USER=$(grep "^DATABASE_USER=" .env | cut -d'=' -f2)
    DATABASE_PASSWORD=$(grep "^DATABASE_PASSWORD=" .env | cut -d'=' -f2)
    DATABASE_HOST=$(grep "^DATABASE_HOST=" .env | cut -d'=' -f2)
    DATABASE_PORT=$(grep "^DATABASE_PORT=" .env | cut -d'=' -f2)
    
    # 讀取 Redis 配置
    REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" .env | cut -d'=' -f2)
    REDIS_MAXMEMORY=$(grep "^REDIS_MAXMEMORY=" .env | cut -d'=' -f2)
    REDIS_MAXCLIENTS=$(grep "^REDIS_MAXCLIENTS=" .env | cut -d'=' -f2)
    
    # 讀取其他配置
    SUPERUSER_NAME=$(grep "^SUPERUSER_NAME=" .env | cut -d'=' -f2)
    SUPERUSER_EMAIL=$(grep "^SUPERUSER_EMAIL=" .env | cut -d'=' -f2)
    SUPERUSER_PASSWORD=$(grep "^SUPERUSER_PASSWORD=" .env | cut -d'=' -f2)
    
    # 驗證必要配置
    if [ -z "$DATABASE_NAME" ] || [ -z "$DATABASE_USER" ] || [ -z "$DATABASE_PASSWORD" ]; then
        echo -e "${RED}❌ 資料庫配置不完整${NC}" | tee -a $LOG_FILE
        exit 1
    fi
    
    if [ -z "$REDIS_PASSWORD" ]; then
        echo -e "${RED}❌ Redis 配置不完整${NC}" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "配置讀取完成:" | tee -a $LOG_FILE
    echo "  資料庫: $DATABASE_NAME" | tee -a $LOG_FILE
    echo "  使用者: $DATABASE_USER" | tee -a $LOG_FILE
    echo "  Redis 密碼: [隱藏]" | tee -a $LOG_FILE
    echo "  管理員: $SUPERUSER_NAME" | tee -a $LOG_FILE
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
        echo -e "${YELLOW}⚠️  請檢查日誌檔案: $LOG_FILE${NC}" | tee -a $LOG_FILE
        return 1
    fi
}

# 函數：檢查命令是否存在
check_command() {
    local cmd="$1"
    local desc="$2"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $desc 已安裝${NC}" | tee -a $LOG_FILE
        return 0
    else
        echo -e "${RED}❌ $desc 未安裝${NC}" | tee -a $LOG_FILE
        return 1
    fi
}

# 函數：檢查服務狀態
check_service() {
    local service_name="$1"
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if systemctl is-active --quiet $service_name; then
            echo -e "${GREEN}✅ $service_name 服務運行正常${NC}" | tee -a $LOG_FILE
            return 0
        else
            echo -e "${YELLOW}⚠️  $service_name 服務未運行，嘗試重啟 (第 $attempt 次)${NC}" | tee -a $LOG_FILE
            systemctl restart $service_name
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
    
    echo -e "${RED}❌ $service_name 服務啟動失敗${NC}" | tee -a $LOG_FILE
    systemctl status $service_name --no-pager | tee -a $LOG_FILE
    return 1
}

# 步驟 0: 讀取 .env 配置
echo ""
echo -e "${YELLOW}🔧 步驟 0: 讀取 .env 配置${NC}"
load_env_config

# 步驟 1: 確認配置
echo ""
echo -e "${YELLOW}🔧 步驟 1: 確認配置${NC}"
echo -e "${YELLOW}⚠️  請確認以下配置是否正確${NC}"
echo ""
echo "資料庫配置:"
echo "  名稱: $DATABASE_NAME"
echo "  使用者: $DATABASE_USER"
echo "  主機: $DATABASE_HOST"
echo "  端口: $DATABASE_PORT"
echo ""
echo "Redis 配置:"
echo "  密碼: [隱藏]"
echo "  最大記憶體: $REDIS_MAXMEMORY"
echo "  最大連線數: $REDIS_MAXCLIENTS"
echo ""
echo "管理員配置:"
echo "  帳號: $SUPERUSER_NAME"
echo "  郵件: $SUPERUSER_EMAIL"
echo ""
read -p "配置是否正確？(y/N): " config_ok

if [[ ! $config_ok =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ 請修改 .env 檔案後重新執行部署${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 配置確認完成${NC}"
fi

# 步驟 2: 清理之前的安裝
echo ""
echo -e "${YELLOW}🧹 步驟 2: 清理之前的安裝${NC}"
echo -e "${YELLOW}⚠️  這將停止並清理之前的 MES 系統安裝${NC}"
echo -e "${RED}⚠️  注意：此操作將清除所有資料庫資料！${NC}"
echo ""
read -p "是否要先備份現有資料庫？(y/N): " backup_choice

if [[ $backup_choice =~ ^[Yy]$ ]]; then
    echo "正在備份資料庫..." | tee -a $LOG_FILE
    backup_file="/var/www/mes/backup_$(date +%Y%m%d_%H%M%S).sql"
    sudo -u postgres pg_dump $DATABASE_NAME > $backup_file 2>/dev/null || echo "備份失敗或資料庫不存在"
    echo "備份檔案位置: $backup_file" | tee -a $LOG_FILE
fi

echo ""
read -p "確認要清除所有資料並重新部署嗎？(y/N): " confirm_clear

if [[ ! $confirm_clear =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ 部署已取消${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 確認清除資料，繼續部署${NC}"
fi

# 停止相關服務
echo "停止相關服務..." | tee -a $LOG_FILE
systemctl stop mes 2>/dev/null || true
systemctl stop mes-celery 2>/dev/null || true
systemctl stop celery-beat 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
systemctl stop redis-server 2>/dev/null || true
systemctl stop postgresql 2>/dev/null || true

# 徹底清除資料庫相關資料
echo "徹底清除資料庫相關資料..." | tee -a $LOG_FILE
sudo -u postgres dropdb $DATABASE_NAME 2>/dev/null || true
sudo -u postgres dropuser $DATABASE_USER 2>/dev/null || true

# 清除 Redis 資料
echo "清除 Redis 資料..." | tee -a $LOG_FILE
redis-cli -a $REDIS_PASSWORD FLUSHALL 2>/dev/null || true

    # 移除舊的服務檔案
    echo "移除舊的服務檔案..." | tee -a $LOG_FILE
    rm -f /etc/systemd/system/mes.service
    rm -f /etc/systemd/system/mes-celery.service
    rm -f /etc/systemd/system/celery-beat.service
    rm -f /etc/systemd/system/gunicorn-mes_config.service
    systemctl daemon-reload

# 檢查是否在正確的專案目錄下執行
echo "檢查專案目錄..." | tee -a $LOG_FILE
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 專案目錄 $PROJECT_DIR 不存在${NC}" | tee -a $LOG_FILE
    echo "請確保在 /var/www/mes 目錄下執行此腳本" | tee -a $LOG_FILE
    exit 1
fi

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${RED}❌ 專案目錄 $PROJECT_DIR 中未找到 manage.py${NC}" | tee -a $LOG_FILE
    echo "請確保專案檔案已正確部署到 $PROJECT_DIR" | tee -a $LOG_FILE
    exit 1
fi

# 檢查目錄權限
echo "檢查目錄權限..." | tee -a $LOG_FILE
DIR_OWNER=$(stat -c '%U:%G' "$PROJECT_DIR")
DIR_PERMS=$(stat -c '%a' "$PROJECT_DIR")

echo "當前目錄權限: $DIR_OWNER (權限: $DIR_PERMS)" | tee -a $LOG_FILE

if [ "$DIR_OWNER" != "mes:www-data" ] || [ "$DIR_PERMS" != "755" ]; then
    echo -e "${YELLOW}⚠️  專案目錄權限需要修正${NC}" | tee -a $LOG_FILE
    echo "當前權限: $DIR_OWNER (權限: $DIR_PERMS)" | tee -a $LOG_FILE
    echo "正確權限: mes:www-data (權限: 755)" | tee -a $LOG_FILE
    echo "正在修正權限..." | tee -a $LOG_FILE
    
    # 詳細的權限修正
    run_command "chown -R mes:www-data $PROJECT_DIR" "修正目錄擁有者"
    run_command "chmod -R 755 $PROJECT_DIR" "修正目錄權限"
    
    # 特殊檔案權限設定
    run_command "find $PROJECT_DIR -type f -name '*.py' -exec chmod 644 {} \;" "設定 Python 檔案權限"
    run_command "find $PROJECT_DIR -type f -name '*.sh' -exec chmod 755 {} \;" "設定腳本檔案權限"
    run_command "find $PROJECT_DIR -type f -name '*.conf' -exec chmod 644 {} \;" "設定配置檔案權限"
    run_command "find $PROJECT_DIR -type f -name '.env*' -exec chmod 640 {} \;" "設定環境檔案權限"
    
    # 驗證權限修正
    NEW_OWNER=$(stat -c '%U:%G' "$PROJECT_DIR")
    NEW_PERMS=$(stat -c '%a' "$PROJECT_DIR")
    echo "修正後權限: $NEW_OWNER (權限: $NEW_PERMS)" | tee -a $LOG_FILE
    
    if [ "$NEW_OWNER" = "mes:www-data" ] && [ "$NEW_PERMS" = "755" ]; then
        echo -e "${GREEN}✅ 權限修正完成${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 權限修正失敗${NC}" | tee -a $LOG_FILE
        exit 1
    fi
else
    echo -e "${GREEN}✅ 目錄權限正確${NC}" | tee -a $LOG_FILE
fi

echo -e "${GREEN}✅ 專案目錄檢查通過${NC}" | tee -a $LOG_FILE

# 清理舊的 Nginx 配置
echo "清理舊的 Nginx 配置..." | tee -a $LOG_FILE
rm -f /etc/nginx/sites-available/mes
rm -f /etc/nginx/sites-enabled/mes

# 清理舊的日誌檔案
echo "清理舊的日誌檔案..." | tee -a $LOG_FILE
rm -rf /var/log/mes/* 2>/dev/null || true

# 清理 Python 快取
echo "清理 Python 快取..." | tee -a $LOG_FILE
find /tmp -name "*.pyc" -delete 2>/dev/null || true
find /tmp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find $PROJECT_DIR -name "*.pyc" -delete 2>/dev/null || true
find $PROJECT_DIR -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 清理 Celery 相關檔案
echo "清理 Celery 相關檔案..." | tee -a $LOG_FILE
rm -rf /var/run/celery/* 2>/dev/null || true
rm -rf /var/log/celery/* 2>/dev/null || true

echo -e "${GREEN}✅ 清理完成${NC}" | tee -a $LOG_FILE

# 步驟 3: 清除舊套件
echo ""
echo -e "${BLUE}🗑️ 步驟 3: 清除舊套件${NC}"
echo "清除可能衝突的舊套件..." | tee -a $LOG_FILE

# 停止相關服務
run_command "systemctl stop nginx 2>/dev/null || true" "停止 Nginx 服務"
run_command "systemctl stop postgresql 2>/dev/null || true" "停止 PostgreSQL 服務"
run_command "systemctl stop redis-server 2>/dev/null || true" "停止 Redis 服務"

# 清除舊套件
run_command "apt remove --purge -y nginx nginx-common nginx-core libnginx-mod-* 2>/dev/null || true" "清除舊 Nginx 套件"
run_command "apt remove --purge -y postgresql postgresql-contrib postgresql-* 2>/dev/null || true" "清除舊 PostgreSQL 套件"
run_command "apt remove --purge -y redis-server redis-tools 2>/dev/null || true" "清除舊 Redis 套件"

# 清除配置檔案
run_command "rm -rf /etc/nginx 2>/dev/null || true" "清除 Nginx 配置"
run_command "rm -rf /etc/postgresql 2>/dev/null || true" "清除 PostgreSQL 配置"
run_command "rm -rf /etc/redis 2>/dev/null || true" "清除 Redis 配置"

# 清除日誌檔案
run_command "rm -rf /var/log/nginx 2>/dev/null || true" "清除 Nginx 日誌"
run_command "rm -rf /var/log/postgresql 2>/dev/null || true" "清除 PostgreSQL 日誌"
run_command "rm -rf /var/log/redis 2>/dev/null || true" "清除 Redis 日誌"

# 清除資料目錄
run_command "rm -rf /var/lib/postgresql 2>/dev/null || true" "清除 PostgreSQL 資料"
run_command "rm -rf /var/lib/redis 2>/dev/null || true" "清除 Redis 資料"

# 清理套件快取
run_command "apt autoremove -y" "清理未使用的套件"
run_command "apt clean" "清理套件快取"

echo -e "${GREEN}✅ 舊套件清除完成${NC}" | tee -a $LOG_FILE

# 步驟 4: 更新系統套件
echo ""
echo -e "${BLUE}📦 步驟 4: 更新系統套件${NC}"

# 檢查並修復 dpkg 問題
echo "檢查 dpkg 狀態..." | tee -a $LOG_FILE
if dpkg --audit 2>/dev/null | grep -q "broken"; then
    echo -e "${YELLOW}⚠️  發現 dpkg 問題，正在修復...${NC}" | tee -a $LOG_FILE
    run_command "dpkg --configure -a" "修復 dpkg 配置"
fi

run_command "apt update && apt upgrade -y" "更新系統套件"

# 步驟 5: 安裝基礎套件
echo ""
echo -e "${BLUE}🔧 步驟 5: 安裝基礎套件${NC}"
run_command "apt install -y python3 python3-pip python3-dev python3-setuptools python3-wheel build-essential libpq-dev libssl-dev freetds-dev gettext curl wget git unzip lsof net-tools ntpdate dialog apt-utils" "安裝基礎套件"

# 步驟 6: 安裝資料庫和服務
echo ""
echo -e "${BLUE}🗄️ 步驟 6: 安裝資料庫和服務${NC}"
run_command "apt install -y postgresql postgresql-contrib postgresql-client redis-server nginx" "安裝資料庫和服務"

# 步驟 7: 建立系統用戶
echo ""
echo -e "${BLUE}👥 步驟 7: 建立系統用戶${NC}"
if ! id "mes" >/dev/null 2>&1; then
    run_command "useradd -m -s /bin/bash mes" "建立 mes 用戶"
    run_command "usermod -aG sudo mes" "將 mes 加入 sudo 群組"
    echo -e "${YELLOW}⚠️  請設定 mes 用戶密碼${NC}"
    passwd mes
else
    echo -e "${GREEN}✅ mes 用戶已存在${NC}"
fi

if ! getent group "www-data" >/dev/null 2>&1; then
    run_command "groupadd www-data" "建立 www-data 群組"
fi
run_command "usermod -aG www-data mes" "將 mes 加入 www-data 群組"

# 步驟 8: 專案目錄已確認存在（前面已檢查過）
echo -e "${GREEN}✅ 專案目錄已確認存在${NC}" | tee -a $LOG_FILE

# 步驟 9: 配置 PostgreSQL
echo ""
echo -e "${BLUE}🐘 步驟 9: 配置 PostgreSQL${NC}"

# 檢查 PostgreSQL 版本並啟動正確的服務
echo "檢查 PostgreSQL 版本..." | tee -a $LOG_FILE
if [ -d "/etc/postgresql/14" ]; then
    POSTGRES_SERVICE="postgresql@14-main"
    echo "檢測到 PostgreSQL 14，使用服務: $POSTGRES_SERVICE" | tee -a $LOG_FILE
elif [ -d "/etc/postgresql/13" ]; then
    POSTGRES_SERVICE="postgresql@13-main"
    echo "檢測到 PostgreSQL 13，使用服務: $POSTGRES_SERVICE" | tee -a $LOG_FILE
elif [ -d "/etc/postgresql/12" ]; then
    POSTGRES_SERVICE="postgresql@12-main"
    echo "檢測到 PostgreSQL 12，使用服務: $POSTGRES_SERVICE" | tee -a $LOG_FILE
else
    POSTGRES_SERVICE="postgresql"
    echo "使用預設 PostgreSQL 服務: $POSTGRES_SERVICE" | tee -a $LOG_FILE
fi

run_command "systemctl enable $POSTGRES_SERVICE" "啟用 PostgreSQL 服務"
run_command "systemctl start $POSTGRES_SERVICE" "啟動 PostgreSQL 服務"

# 配置 PostgreSQL 監聽設定
echo "配置 PostgreSQL 監聽設定..." | tee -a $LOG_FILE
if [ -d "/etc/postgresql/14" ]; then
    POSTGRES_CONF="/etc/postgresql/14/main/postgresql.conf"
    POSTGRES_HBA="/etc/postgresql/14/main/pg_hba.conf"
elif [ -d "/etc/postgresql/13" ]; then
    POSTGRES_CONF="/etc/postgresql/13/main/postgresql.conf"
    POSTGRES_HBA="/etc/postgresql/13/main/pg_hba.conf"
elif [ -d "/etc/postgresql/12" ]; then
    POSTGRES_CONF="/etc/postgresql/12/main/postgresql.conf"
    POSTGRES_HBA="/etc/postgresql/12/main/pg_hba.conf"
else
    POSTGRES_CONF="/etc/postgresql/*/main/postgresql.conf"
    POSTGRES_HBA="/etc/postgresql/*/main/pg_hba.conf"
fi

# 備份原始配置
if [ -f "$POSTGRES_CONF" ]; then
    cp "$POSTGRES_CONF" "${POSTGRES_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 已備份 PostgreSQL 配置檔案" | tee -a $LOG_FILE
    
    # 設定監聽地址和端口
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$POSTGRES_CONF"
    sed -i "s/#port = 5432/port = 5432/" "$POSTGRES_CONF"
    
    # 重啟 PostgreSQL 服務以應用新配置
    run_command "systemctl restart $POSTGRES_SERVICE" "重啟 PostgreSQL 服務以應用新配置"
    
    # 等待服務完全啟動
    sleep 5
    
    echo "✅ PostgreSQL 配置更新完成" | tee -a $LOG_FILE
else
    echo "⚠️  無法找到 PostgreSQL 配置檔案" | tee -a $LOG_FILE
fi

# 檢查 PostgreSQL 工具是否安裝
echo "檢查 PostgreSQL 工具..." | tee -a $LOG_FILE
if ! check_command "psql" "PostgreSQL 客戶端工具"; then
    echo -e "${YELLOW}⚠️  安裝 PostgreSQL 客戶端工具...${NC}" | tee -a $LOG_FILE
    run_command "apt install -y postgresql-client" "安裝 PostgreSQL 客戶端工具"
fi

# 建立資料庫和使用者
echo "建立資料庫和使用者..." | tee -a $LOG_FILE

# 確保完全清除舊資料庫並重新建立（全新部署）
echo "確保完全清除舊資料庫並重新建立..." | tee -a $LOG_FILE
sudo -u postgres dropdb $DATABASE_NAME 2>/dev/null || true
sudo -u postgres dropuser $DATABASE_USER 2>/dev/null || true

# 重新建立使用者
run_command "sudo -u postgres psql -c \"CREATE USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "建立資料庫使用者"

# 重新建立資料庫
run_command "sudo -u postgres psql -c \"CREATE DATABASE $DATABASE_NAME OWNER $DATABASE_USER;\"" "建立資料庫"

# 授予權限
run_command "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;\"" "授予資料庫權限"
run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER CREATEDB;\"" "授予建立資料庫權限"

# 測試資料庫連線
echo "測試資料庫連線..." | tee -a $LOG_FILE

# 檢查 PostgreSQL 服務狀態
if systemctl is-active --quiet $POSTGRES_SERVICE; then
    echo "✅ PostgreSQL 服務運行正常" | tee -a $LOG_FILE
else
    echo "❌ PostgreSQL 服務未運行，嘗試重啟..." | tee -a $LOG_FILE
    run_command "systemctl restart $POSTGRES_SERVICE" "重啟 PostgreSQL 服務"
    sleep 3
fi

# 檢查端口監聽
if netstat -tlnp 2>/dev/null | grep -q ":5432 "; then
    echo "✅ PostgreSQL 端口 5432 正在監聽" | tee -a $LOG_FILE
else
    echo "❌ PostgreSQL 端口 5432 未監聽" | tee -a $LOG_FILE
    echo "檢查端口狀態..." | tee -a $LOG_FILE
    netstat -tlnp | grep 5432 | tee -a $LOG_FILE
fi

# 測試資料庫連線
if sudo -u postgres psql -d $DATABASE_NAME -c "SELECT 1;" 2>&1 | grep -q "1 row"; then
    echo -e "${GREEN}✅ 資料庫連線測試成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫連線測試失敗${NC}" | tee -a $LOG_FILE
    echo -e "${YELLOW}⚠️  請檢查以下項目：${NC}" | tee -a $LOG_FILE
    echo "  1. PostgreSQL 服務是否正常運行" | tee -a $LOG_FILE
    echo "  2. psql 命令是否可用" | tee -a $LOG_FILE
    echo "  3. 資料庫使用者權限是否正確" | tee -a $LOG_FILE
    echo "  4. 資料庫是否成功建立" | tee -a $LOG_FILE
    echo "  5. 端口 5432 是否正在監聽" | tee -a $LOG_FILE
    exit 1
fi

echo "資料庫配置完成" | tee -a $LOG_FILE

# 步驟 10: 配置 Redis
echo ""
echo -e "${BLUE}🔴 步驟 10: 配置 Redis${NC}"
run_command "systemctl enable redis-server" "啟用 Redis 服務"

# 配置 Redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
requirepass $REDIS_PASSWORD
maxmemory $REDIS_MAXMEMORY
maxclients $REDIS_MAXCLIENTS
dir /var/lib/redis
appendonly no
save 900 1
save 300 10
save 60 10000
loglevel notice
EOF

run_command "systemctl restart redis-server" "重啟 Redis 服務"

# 設定 vm.overcommit_memory 為 1（Redis 建議值）
echo "設定 vm.overcommit_memory 為 1..." | tee -a $LOG_FILE
if command -v sysctl >/dev/null 2>&1; then
    # 立即設定
    sysctl vm.overcommit_memory=1 2>/dev/null && echo "✅ 立即設定 vm.overcommit_memory=1 成功" | tee -a $LOG_FILE || echo "⚠️  無法立即設定 vm.overcommit_memory" | tee -a $LOG_FILE
    
    # 永久設定
    if ! grep -q "vm.overcommit_memory" /etc/sysctl.conf; then
        echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf && echo "✅ 永久設定 vm.overcommit_memory=1 成功" | tee -a $LOG_FILE || echo "⚠️  無法永久設定 vm.overcommit_memory" | tee -a $LOG_FILE
    else
        sed -i 's/.*vm.overcommit_memory.*/vm.overcommit_memory = 1/' /etc/sysctl.conf && echo "✅ 更新 vm.overcommit_memory=1 成功" | tee -a $LOG_FILE || echo "⚠️  無法更新 vm.overcommit_memory" | tee -a $LOG_FILE
    fi
    
    # 重新載入設定
    sysctl -p /etc/sysctl.conf 2>/dev/null && echo "✅ 重新載入 sysctl 設定成功" | tee -a $LOG_FILE || echo "⚠️  無法重新載入 sysctl 設定" | tee -a $LOG_FILE
    
    # 驗證設定
    CURRENT_VALUE=$(sysctl -n vm.overcommit_memory 2>/dev/null)
    if [ "$CURRENT_VALUE" = "1" ]; then
        echo "✅ vm.overcommit_memory 設定驗證成功: $CURRENT_VALUE" | tee -a $LOG_FILE
    else
        echo "⚠️  vm.overcommit_memory 設定驗證失敗，當前值: $CURRENT_VALUE" | tee -a $LOG_FILE
    fi
else
    echo "⚠️  sysctl 命令不可用，無法設定 vm.overcommit_memory" | tee -a $LOG_FILE
fi

# 步驟 11: 驗證當前工作目錄
echo ""
echo -e "${BLUE}📋 步驟 11: 驗證當前工作目錄${NC}"

# 檢查當前目錄是否為專案目錄
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ 未找到 manage.py，請確保在 /var/www/mes 專案目錄執行此腳本${NC}"
    echo "當前目錄: $(pwd)" | tee -a $LOG_FILE
    exit 1
fi

echo -e "${GREEN}✅ 當前工作目錄驗證通過${NC}" | tee -a $LOG_FILE

# 步驟 12: 建立環境變數檔案
echo ""
echo -e "${BLUE}⚙️ 步驟 12: 建立環境變數檔案${NC}"

# 從原始 .env 檔案讀取配置
if [ -f ".env" ]; then
    echo "從原始 .env 檔案複製配置..." | tee -a $LOG_FILE
    cp .env $PROJECT_DIR/.env
    
    # 更新動態值
    sed -i "s|HOST_IP=.*|HOST_IP=$HOST_IP|g" $PROJECT_DIR/.env
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP|g" $PROJECT_DIR/.env
    sed -i "s|PROJECT_DIR=.*|PROJECT_DIR=$PROJECT_DIR|g" $PROJECT_DIR/.env
    sed -i "s|STATIC_ROOT=.*|STATIC_ROOT=$PROJECT_DIR/static|g" $PROJECT_DIR/.env
    sed -i "s|LOCALE_DIR=.*|LOCALE_DIR=$PROJECT_DIR/locale|g" $PROJECT_DIR/.env
    sed -i "s|BACKUP_DIR=.*|BACKUP_DIR=$PROJECT_DIR/backups_DB|g" $PROJECT_DIR/.env
    sed -i "s|REQUIREMENTS_FILE=.*|REQUIREMENTS_FILE=$PROJECT_DIR/requirements.txt|g" $PROJECT_DIR/.env
    
    # 更新 DATABASE_URL
    DATABASE_URL="postgresql://$DATABASE_USER:$DATABASE_PASSWORD@localhost:5432/$DATABASE_NAME"
    sed -i "s|DATABASE_URL=.*|DATABASE_URL='$DATABASE_URL'|g" $PROJECT_DIR/.env
    
    echo "已從原始 .env 檔案複製並更新配置" | tee -a $LOG_FILE
else
    echo "未找到原始 .env 檔案，建立預設配置..." | tee -a $LOG_FILE
    cat > $PROJECT_DIR/.env << EOF
DJANGO_SECRET_KEY='$(openssl rand -base64 48)'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP
HOST_IP=$HOST_IP
DATABASE_NAME=$DATABASE_NAME
DATABASE_USER=$DATABASE_USER
DATABASE_PASSWORD=$DATABASE_PASSWORD
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_URL='postgresql://$DATABASE_USER:$DATABASE_PASSWORD@localhost:5432/$DATABASE_NAME'
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@127.0.0.1:6379/0
LOG_FILE=$LOG_BASE_DIR/django/mes.log
SERVER_NAME=mes
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_MAXMEMORY=2147483648
REDIS_MAXCLIENTS=1000
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=user@gmail.com
EMAIL_HOST_PASSWORD=user_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=MES@gmail.com
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=1234
PROJECT_DIR=$PROJECT_DIR
LOG_BASE_DIR=/var/log/mes
BACKUP_DIR=$PROJECT_DIR/backups_DB
APP_USER=mes
APP_GROUP=www-data
NGINX_PORT=80
DJANGO_PROJECT_NAME=mes_config
LANGUAGE_CODE=zh-hant
TIME_ZONE=Asia/Taipei
SESSION_COOKIE_AGE=259200
STATIC_ROOT=$PROJECT_DIR/static
LOCALE_DIR=$PROJECT_DIR/locale
TEMP_DIR=/tmp
REQUIREMENTS_FILE=$PROJECT_DIR/requirements.txt
EOF
fi

run_command "chown mes:www-data $PROJECT_DIR/.env" "設定 .env 檔案權限"
run_command "chmod 640 $PROJECT_DIR/.env" "設定 .env 檔案權限"

# 步驟 12.1: 建立所有必要的目錄和檔案
echo ""
echo -e "${BLUE}📁 步驟 12.1: 建立所有必要的目錄和檔案${NC}"
echo "建立所有必要的目錄和檔案..." | tee -a $LOG_FILE

# 建立系統日誌目錄結構
echo "建立系統日誌目錄結構..." | tee -a $LOG_FILE
run_command "mkdir -p $LOG_BASE_DIR/django" "建立 Django 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/workorder" "建立工單日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/erp_integration" "建立 ERP 整合日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/quality" "建立品質管理日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/material" "建立物料管理日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/equip" "建立設備管理日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/reporting" "建立報表系統日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/celery" "建立 Celery 日誌目錄"
    # 跳過 Gunicorn 日誌目錄（開發環境不需要）
    echo "跳過 Gunicorn 日誌目錄建立（開發環境不需要）..." | tee -a $LOG_FILE
run_command "mkdir -p $LOG_BASE_DIR/nginx" "建立 Nginx 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/postgresql" "建立 PostgreSQL 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/redis" "建立 Redis 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/system" "建立系統日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/kanban" "建立看板日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/production" "建立生產日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/ai" "建立 AI 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/scheduling" "建立排程日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/process" "建立製程日誌目錄"



# 建立服務相關目錄
echo "建立服務相關目錄..." | tee -a $LOG_FILE
run_command "mkdir -p /var/run/celery" "建立 Celery 執行目錄"
run_command "mkdir -p /var/log/celery" "建立 Celery 日誌目錄"
run_command "mkdir -p /var/log/nginx" "建立 Nginx 日誌目錄"
run_command "mkdir -p /var/log/postgresql" "建立 PostgreSQL 日誌目錄"
run_command "mkdir -p /var/log/redis" "建立 Redis 日誌目錄"
run_command "mkdir -p /var/lib/postgresql" "建立 PostgreSQL 資料目錄"
run_command "mkdir -p /var/lib/redis" "建立 Redis 資料目錄"

# 建立必要的日誌檔案
echo "建立必要的日誌檔案..." | tee -a $LOG_FILE
# 建立 Django 設定中指定的主要日誌檔案
run_command "touch $LOG_BASE_DIR/mes.log" "建立 Django 主要日誌檔案"
run_command "touch $LOG_BASE_DIR/workorder.log" "建立工單日誌檔案"
# 建立其他服務日誌檔案
run_command "touch $LOG_BASE_DIR/django/mes.log" "建立 Django 日誌檔案"
run_command "touch $LOG_BASE_DIR/celery/celery.log" "建立 Celery 日誌檔案"
    # 跳過 Gunicorn 日誌檔案建立（開發環境不需要）
    echo "跳過 Gunicorn 日誌檔案建立（開發環境不需要）..." | tee -a $LOG_FILE
run_command "touch $LOG_BASE_DIR/nginx/access.log" "建立 Nginx 存取日誌"
run_command "touch $LOG_BASE_DIR/nginx/error.log" "建立 Nginx 錯誤日誌"
run_command "touch $LOG_BASE_DIR/postgresql/postgresql.log" "建立 PostgreSQL 日誌"
run_command "touch $LOG_BASE_DIR/redis/redis.log" "建立 Redis 日誌"

# 建立所有模組日誌檔案
echo "建立所有模組日誌檔案..." | tee -a $LOG_FILE
run_command "touch $LOG_BASE_DIR/workorder/workorder.log" "建立工單模組日誌檔案"
run_command "touch $LOG_BASE_DIR/erp_integration/erp_integration.log" "建立 ERP 整合日誌檔案"
run_command "touch $LOG_BASE_DIR/quality/quality.log" "建立品質管理日誌檔案"
run_command "touch $LOG_BASE_DIR/material/material.log" "建立物料管理日誌檔案"
run_command "touch $LOG_BASE_DIR/equip/equip.log" "建立設備管理日誌檔案"
run_command "touch $LOG_BASE_DIR/reporting/reporting.log" "建立報表系統日誌檔案"
run_command "touch $LOG_BASE_DIR/system/system.log" "建立系統管理日誌檔案"
run_command "touch $LOG_BASE_DIR/kanban/kanban.log" "建立看板日誌檔案"
run_command "touch $LOG_BASE_DIR/production/production.log" "建立生產管理日誌檔案"
run_command "touch $LOG_BASE_DIR/ai/ai.log" "建立 AI 功能日誌檔案"
run_command "touch $LOG_BASE_DIR/scheduling/scheduling.log" "建立排程管理日誌檔案"
run_command "touch $LOG_BASE_DIR/process/process.log" "建立製程管理日誌檔案"

# 設定日誌檔案擁有者和權限
echo "設定日誌檔案權限..." | tee -a $LOG_FILE
    run_command "chown mes:www-data $LOG_BASE_DIR/mes.log $LOG_BASE_DIR/workorder.log $LOG_BASE_DIR/django/mes.log $LOG_BASE_DIR/celery/celery.log" "設定應用日誌檔案擁有者"
run_command "chown www-data:www-data $LOG_BASE_DIR/nginx/access.log $LOG_BASE_DIR/nginx/error.log" "設定 Nginx 日誌檔案擁有者"
run_command "chown postgres:postgres $LOG_BASE_DIR/postgresql/postgresql.log" "設定 PostgreSQL 日誌檔案擁有者"
run_command "chown redis:redis $LOG_BASE_DIR/redis/redis.log" "設定 Redis 日誌檔案擁有者"

    run_command "chmod 644 $LOG_BASE_DIR/mes.log $LOG_BASE_DIR/workorder.log $LOG_BASE_DIR/django/mes.log $LOG_BASE_DIR/celery/celery.log" "設定應用日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/nginx/access.log $LOG_BASE_DIR/nginx/error.log" "設定 Nginx 日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/postgresql/postgresql.log" "設定 PostgreSQL 日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/redis/redis.log" "設定 Redis 日誌檔案權限"



echo -e "${GREEN}✅ 所有目錄和檔案建立完成${NC}" | tee -a $LOG_FILE

# 步驟 12.2: 遞迴設定所有權限
echo ""
echo -e "${BLUE}🔐 步驟 12.2: 遞迴設定所有權限${NC}"
echo "開始遞迴設定所有權限..." | tee -a $LOG_FILE

# 設定系統日誌目錄權限（先設定目錄，再設定檔案）
echo "設定系統日誌目錄權限..." | tee -a $LOG_FILE
run_command "find $LOG_BASE_DIR -type d -exec chown mes:www-data {} \;" "設定日誌目錄擁有者"
run_command "find $LOG_BASE_DIR -type d -exec chmod 755 {} \;" "設定日誌目錄權限"

# 設定日誌檔案權限（分類設定，避免權限衝突）
echo "設定應用日誌檔案權限..." | tee -a $LOG_FILE
run_command "find $LOG_BASE_DIR/django -type f -exec chown mes:www-data {} \;" "設定 Django 日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/workorder -type f -exec chown mes:www-data {} \;" "設定工單日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/erp_integration -type f -exec chown mes:www-data {} \;" "設定 ERP 整合日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/quality -type f -exec chown mes:www-data {} \;" "設定品質管理日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/material -type f -exec chown mes:www-data {} \;" "設定物料管理日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/equip -type f -exec chown mes:www-data {} \;" "設定設備管理日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/reporting -type f -exec chown mes:www-data {} \;" "設定報表系統日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/celery -type f -exec chown mes:www-data {} \;" "設定 Celery 日誌檔案擁有者"
    # 跳過 Gunicorn 日誌檔案權限設定（開發環境不需要）
    echo "跳過 Gunicorn 日誌檔案權限設定（開發環境不需要）..." | tee -a $LOG_FILE
run_command "find $LOG_BASE_DIR/system -type f -exec chown mes:www-data {} \;" "設定系統日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/kanban -type f -exec chown mes:www-data {} \;" "設定看板日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/production -type f -exec chown mes:www-data {} \;" "設定生產日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/ai -type f -exec chown mes:www-data {} \;" "設定 AI 日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/scheduling -type f -exec chown mes:www-data {} \;" "設定排程日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/process -type f -exec chown mes:www-data {} \;" "設定製程日誌檔案擁有者"

# 設定服務日誌檔案權限（使用正確的擁有者）
echo "設定服務日誌檔案權限..." | tee -a $LOG_FILE
run_command "find $LOG_BASE_DIR/nginx -type f -exec chown www-data:www-data {} \;" "設定 Nginx 日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/postgresql -type f -exec chown postgres:postgres {} \;" "設定 PostgreSQL 日誌檔案擁有者"
run_command "find $LOG_BASE_DIR/redis -type f -exec chown redis:redis {} \;" "設定 Redis 日誌檔案擁有者"

# 設定所有日誌檔案權限為 644
echo "設定所有日誌檔案權限..." | tee -a $LOG_FILE
run_command "find $LOG_BASE_DIR -type f -name '*.log' -exec chmod 644 {} \;" "設定所有日誌檔案權限"

# 設定專案目錄權限
echo "設定專案目錄權限..." | tee -a $LOG_FILE
run_command "find $PROJECT_DIR -type d -exec chown mes:www-data {} \;" "設定專案目錄擁有者"
run_command "find $PROJECT_DIR -type f -exec chown mes:www-data {} \;" "設定專案檔案擁有者"
run_command "find $PROJECT_DIR -type d -exec chmod 755 {} \;" "設定專案目錄權限"
run_command "find $PROJECT_DIR -type f -exec chmod 644 {} \;" "設定專案檔案權限"

# 設定服務目錄權限
echo "設定服務目錄權限..." | tee -a $LOG_FILE
run_command "find /var/run/celery /var/log/celery -type d -exec chown mes:www-data {} \;" "設定 Celery 目錄擁有者"
run_command "find /var/run/celery /var/log/celery -type f -exec chown mes:www-data {} \;" "設定 Celery 檔案擁有者"
run_command "find /var/run/celery /var/log/celery -type d -exec chmod 755 {} \;" "設定 Celery 目錄權限"
run_command "find /var/run/celery /var/log/celery -type f -exec chmod 644 {} \;" "設定 Celery 檔案權限"
run_command "find /var/log/nginx -type d -exec chown www-data:www-data {} \;" "設定 Nginx 目錄擁有者"
run_command "find /var/log/nginx -type f -exec chown www-data:www-data {} \;" "設定 Nginx 檔案擁有者"
run_command "find /var/log/nginx -type d -exec chmod 755 {} \;" "設定 Nginx 目錄權限"
run_command "find /var/log/nginx -type f -exec chmod 644 {} \;" "設定 Nginx 檔案權限"
run_command "find /var/log/postgresql -type d -exec chown postgres:postgres {} \;" "設定 PostgreSQL 目錄擁有者"
run_command "find /var/log/postgresql -type f -exec chown postgres:postgres {} \;" "設定 PostgreSQL 檔案擁有者"
run_command "find /var/log/postgresql -type d -exec chmod 755 {} \;" "設定 PostgreSQL 目錄權限"
run_command "find /var/log/postgresql -type f -exec chmod 644 {} \;" "設定 PostgreSQL 檔案權限"
run_command "find /var/log/redis -type d -exec chown redis:redis {} \;" "設定 Redis 目錄擁有者"
run_command "find /var/log/redis -type f -exec chown redis:redis {} \;" "設定 Redis 檔案擁有者"
run_command "find /var/log/redis -type d -exec chmod 755 {} \;" "設定 Redis 目錄權限"
run_command "find /var/log/redis -type f -exec chmod 644 {} \;" "設定 Redis 檔案權限"

# 設定特殊檔案權限
echo "設定特殊檔案權限..." | tee -a $LOG_FILE
run_command "find $PROJECT_DIR -type f -name '*.sh' -exec chmod 755 {} \;" "設定腳本執行權限"
run_command "find $PROJECT_DIR -type f -name '*.py' -exec chmod 644 {} \;" "設定 Python 檔案權限"
run_command "find $PROJECT_DIR -type f -name '*.conf' -exec chmod 644 {} \;" "設定配置檔案權限"
run_command "find $PROJECT_DIR -type f -name '.env*' -exec chmod 640 {} \;" "設定環境檔案權限"
run_command "find $PROJECT_DIR -type f -name '*.log' -exec chmod 644 {} \;" "設定日誌檔案權限"

# 設定敏感檔案權限
echo "設定敏感檔案權限..." | tee -a $LOG_FILE
run_command "chmod 600 $PROJECT_DIR/.env" "設定環境檔案嚴格權限"
run_command "chmod 600 $PROJECT_DIR/*.key 2>/dev/null || true" "設定金鑰檔案權限"
run_command "chmod 600 $PROJECT_DIR/*.pem 2>/dev/null || true" "設定憑證檔案權限"

# 設定可寫入目錄權限
echo "設定可寫入目錄權限..." | tee -a $LOG_FILE
run_command "chmod 775 $PROJECT_DIR/static $PROJECT_DIR/media $PROJECT_DIR/tmp $PROJECT_DIR/logs $PROJECT_DIR/backups_DB $PROJECT_DIR/reports $PROJECT_DIR/staticfiles 2>/dev/null || true" "設定可寫入目錄權限"

echo -e "${GREEN}✅ 所有權限設定完成${NC}" | tee -a $LOG_FILE

# 步驟 12.3: 檢查驗證權限
echo ""
echo -e "${BLUE}🔍 步驟 12.3: 檢查驗證權限${NC}"
echo "開始檢查驗證所有權限..." | tee -a $LOG_FILE

# 函數：檢查目錄權限
check_directory_permissions() {
    local dir_path="$1"
    local expected_owner="$2"
    local expected_perms="$3"
    local description="$4"
    
    if [ -d "$dir_path" ]; then
        local actual_owner=$(stat -c '%U:%G' "$dir_path")
        local actual_perms=$(stat -c '%a' "$dir_path")
        
        if [ "$actual_owner" = "$expected_owner" ] && [ "$actual_perms" = "$expected_perms" ]; then
            echo -e "${GREEN}✅ $description: $actual_owner ($actual_perms)${NC}" | tee -a $LOG_FILE
            return 0
        else
            echo -e "${RED}❌ $description: $actual_owner ($actual_perms) - 期望: $expected_owner ($expected_perms)${NC}" | tee -a $LOG_FILE
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  $description: 目錄不存在${NC}" | tee -a $LOG_FILE
        return 1
    fi
}

# 函數：檢查檔案權限
check_file_permissions() {
    local file_path="$1"
    local expected_owner="$2"
    local expected_perms="$3"
    local description="$4"
    
    if [ -f "$file_path" ]; then
        local actual_owner=$(stat -c '%U:%G' "$file_path")
        local actual_perms=$(stat -c '%a' "$file_path")
        
        if [ "$actual_owner" = "$expected_owner" ] && [ "$actual_perms" = "$expected_perms" ]; then
            echo -e "${GREEN}✅ $description: $actual_owner ($actual_perms)${NC}" | tee -a $LOG_FILE
            return 0
        else
            echo -e "${RED}❌ $description: $actual_owner ($actual_perms) - 期望: $expected_owner ($expected_perms)${NC}" | tee -a $LOG_FILE
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  $description: 檔案不存在${NC}" | tee -a $LOG_FILE
        return 1
    fi
}



# 檢查系統目錄權限
echo "檢查系統目錄權限..." | tee -a $LOG_FILE
PERMISSION_ERRORS=0

check_directory_permissions "$LOG_BASE_DIR" "mes:www-data" "755" "系統日誌根目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_directory_permissions "$LOG_BASE_DIR/django" "mes:www-data" "755" "Django 日誌目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_directory_permissions "$LOG_BASE_DIR/celery" "mes:www-data" "755" "Celery 日誌目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
# 跳過 Gunicorn 日誌目錄權限檢查（開發環境不需要）
echo "跳過 Gunicorn 日誌目錄權限檢查（開發環境不需要）..." | tee -a $LOG_FILE

# 檢查服務目錄權限
echo "檢查服務目錄權限..." | tee -a $LOG_FILE
check_directory_permissions "/var/run/celery" "mes:www-data" "755" "Celery 執行目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_directory_permissions "/var/log/celery" "mes:www-data" "755" "Celery 日誌目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_directory_permissions "/var/log/nginx" "www-data:www-data" "755" "Nginx 日誌目錄" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))

# 檢查重要檔案權限
echo "檢查重要檔案權限..." | tee -a $LOG_FILE
check_file_permissions "$PROJECT_DIR/.env" "mes:www-data" "600" "環境配置檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$PROJECT_DIR/manage.py" "mes:www-data" "644" "Django 管理檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))

# 檢查應用日誌檔案權限
echo "檢查應用日誌檔案權限..." | tee -a $LOG_FILE
check_file_permissions "$LOG_BASE_DIR/mes.log" "mes:www-data" "644" "Django 主要日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/workorder.log" "mes:www-data" "644" "工單日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/django/mes.log" "mes:www-data" "644" "Django 日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/celery/celery.log" "mes:www-data" "644" "Celery 日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
# 跳過 Gunicorn 日誌檔案權限檢查（開發環境不需要）
echo "跳過 Gunicorn 日誌檔案權限檢查（開發環境不需要）..." | tee -a $LOG_FILE
check_file_permissions "$LOG_BASE_DIR/workorder/workorder.log" "mes:www-data" "644" "工單模組日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/erp_integration/erp_integration.log" "mes:www-data" "644" "ERP整合日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/quality/quality.log" "mes:www-data" "644" "品質管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/material/material.log" "mes:www-data" "644" "物料管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/equip/equip.log" "mes:www-data" "644" "設備管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/reporting/reporting.log" "mes:www-data" "644" "報表系統日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/system/system.log" "mes:www-data" "644" "系統管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/kanban/kanban.log" "mes:www-data" "644" "看板日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/production/production.log" "mes:www-data" "644" "生產管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/ai/ai.log" "mes:www-data" "644" "AI功能日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/scheduling/scheduling.log" "mes:www-data" "644" "排程管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/process/process.log" "mes:www-data" "644" "製程管理日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))

# 檢查服務日誌檔案權限
echo "檢查服務日誌檔案權限..." | tee -a $LOG_FILE
check_file_permissions "$LOG_BASE_DIR/nginx/access.log" "www-data:www-data" "644" "Nginx 存取日誌" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/nginx/error.log" "www-data:www-data" "644" "Nginx 錯誤日誌" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/postgresql/postgresql.log" "postgres:postgres" "644" "PostgreSQL 日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
check_file_permissions "$LOG_BASE_DIR/redis/redis.log" "redis:redis" "644" "Redis 日誌檔案" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))

# 檢查腳本檔案權限
echo "檢查腳本檔案權限..." | tee -a $LOG_FILE
for script in $PROJECT_DIR/*.sh; do
    if [ -f "$script" ]; then
        check_file_permissions "$script" "mes:www-data" "755" "腳本檔案: $(basename $script)" || PERMISSION_ERRORS=$((PERMISSION_ERRORS + 1))
    fi
done

# 權限驗證總結
echo ""
echo -e "${BLUE}📊 權限驗證總結${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE

if [ $PERMISSION_ERRORS -gt 0 ]; then
    echo -e "${RED}❌ 發現 $PERMISSION_ERRORS 個權限錯誤${NC}" | tee -a $LOG_FILE
    echo -e "${RED}❌ 權限配置不正確，請檢查上述錯誤並重新執行腳本${NC}" | tee -a $LOG_FILE
    exit 1
else
    echo -e "${GREEN}✅ 所有權限檢查通過${NC}" | tee -a $LOG_FILE
fi

echo -e "${GREEN}✅ 權限設定和驗證完成${NC}" | tee -a $LOG_FILE

# 步驟 13: 安裝 Python 套件
echo ""
echo -e "${BLUE}🐍 步驟 13: 安裝 Python 套件${NC}"

# 檢查 requirements.txt 是否存在
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}⚠️  requirements.txt 不存在，跳過 Python 套件安裝${NC}" | tee -a $LOG_FILE
    echo "請確保 requirements.txt 檔案存在於專案目錄中" | tee -a $LOG_FILE
else
    echo "檢查 Python 環境..." | tee -a $LOG_FILE
    run_command "python3 --version" "檢查 Python 版本"
    run_command "pip3 --version" "檢查 pip 版本"
    
    echo "安裝 Python 套件..." | tee -a $LOG_FILE
    cd $PROJECT_DIR
    
    # 嘗試安裝套件，如果失敗則提供詳細錯誤資訊
    if pip3 install -r requirements.txt 2>&1 | tee -a $LOG_FILE; then
        echo -e "${GREEN}✅ Python 套件安裝成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ Python 套件安裝失敗${NC}" | tee -a $LOG_FILE
        echo -e "${YELLOW}⚠️  請檢查以下項目：${NC}" | tee -a $LOG_FILE
        echo "  1. requirements.txt 檔案格式是否正確" | tee -a $LOG_FILE
        echo "  2. 網路連線是否正常" | tee -a $LOG_FILE
        echo "  3. Python 環境是否正確" | tee -a $LOG_FILE
        echo "  4. 系統權限是否足夠" | tee -a $LOG_FILE
        echo -e "${YELLOW}⚠️  可以嘗試手動安裝：pip3 install -r requirements.txt${NC}" | tee -a $LOG_FILE
    fi
fi

# 步驟 15: 清除並重建資料庫
echo ""
echo -e "${BLUE}🗃️ 步驟 15: 清除並重建資料庫${NC}"
export DJANGO_SETTINGS_MODULE=mes_config.settings

cd $PROJECT_DIR

# 清除現有資料庫（全新部署）
echo "清除現有資料庫..." | tee -a $LOG_FILE
echo -e "${YELLOW}⚠️  這將清除所有現有資料庫資料！${NC}" | tee -a $LOG_FILE

# 停止可能使用資料庫的服務
echo "停止相關服務..." | tee -a $LOG_FILE
systemctl stop celery-mes_config 2>/dev/null || true
systemctl stop celerybeat-mes_config 2>/dev/null || true

# 清除資料庫
echo "清除資料庫..." | tee -a $LOG_FILE
run_command "sudo -u postgres dropdb $DATABASE_NAME 2>/dev/null || true" "清除現有資料庫"
run_command "sudo -u postgres dropuser $DATABASE_USER 2>/dev/null || true" "清除現有資料庫用戶"

# 重新建立資料庫和用戶
echo "重新建立資料庫和用戶..." | tee -a $LOG_FILE
run_command "sudo -u postgres psql -c \"CREATE USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "重新建立資料庫用戶"
run_command "sudo -u postgres psql -c \"CREATE DATABASE $DATABASE_NAME OWNER $DATABASE_USER;\"" "重新建立資料庫"
run_command "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;\"" "授予資料庫權限"
run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER CREATEDB;\"" "授予建立資料庫權限"

# 測試資料庫連線
echo "測試資料庫連線..." | tee -a $LOG_FILE
if sudo -u postgres psql -d $DATABASE_NAME -c "SELECT 1;" 2>&1 | grep -q "1 row"; then
    echo -e "${GREEN}✅ 資料庫重建成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ 資料庫重建失敗${NC}" | tee -a $LOG_FILE
    exit 1
fi

# 步驟 16: 執行資料庫遷移
echo ""
echo -e "${BLUE}🗃️ 步驟 16: 執行資料庫遷移${NC}"

# 初始化資料庫（全新生產環境專用）
echo "初始化資料庫..." | tee -a $LOG_FILE

# 全新生產主機的資料庫初始化策略
echo "執行全新資料庫初始化..." | tee -a $LOG_FILE

# 系統環境部署完成
echo "系統環境部署完成..." | tee -a $LOG_FILE

# 檢查專案是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️ 專案目錄不存在，跳過專案相關步驟${NC}" | tee -a $LOG_FILE
    echo "請先建立專案目錄再執行專案部署" | tee -a $LOG_FILE
else
    echo -e "${GREEN}✅ 專案目錄存在，可以進行專案部署${NC}" | tee -a $LOG_FILE
fi

echo -e "${GREEN}✅ 系統環境部署完成${NC}" | tee -a $LOG_FILE

# 步驟 16: 系統環境部署完成
echo ""
echo -e "${BLUE}✅ 步驟 16: 系統環境部署完成${NC}"

echo -e "${GREEN}🎉 系統環境部署完成！${NC}" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}📋 部署資訊${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "系統套件已安裝：" | tee -a $LOG_FILE
echo "  - PostgreSQL 資料庫" | tee -a $LOG_FILE
echo "  - Redis 快取服務" | tee -a $LOG_FILE
echo "  - Nginx 網頁伺服器" | tee -a $LOG_FILE
echo "  - Python 3 環境" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "系統用戶已建立：" | tee -a $LOG_FILE
echo "  - mes 用戶" | tee -a $LOG_FILE
echo "  - www-data 群組" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "下一步：" | tee -a $LOG_FILE
echo "1. 建立專案目錄" | tee -a $LOG_FILE
echo "2. 部署專案檔案" | tee -a $LOG_FILE
echo "3. 配置專案服務" | tee -a $LOG_FILE
# 步驟 17: 啟動系統服務
echo ""
echo -e "${BLUE}🚀 步驟 17: 啟動系統服務${NC}"

# 啟動系統服務
run_command "systemctl enable postgresql" "啟用 PostgreSQL 服務"
run_command "systemctl enable redis-server" "啟用 Redis 服務"
run_command "systemctl enable nginx" "啟用 Nginx 服務"

run_command "systemctl start postgresql" "啟動 PostgreSQL 服務"
run_command "systemctl start redis-server" "啟動 Redis 服務"
run_command "systemctl start nginx" "啟動 Nginx 服務"

# 檢查系統服務狀態
echo "檢查系統服務狀態..." | tee -a $LOG_FILE
run_command "systemctl status postgresql --no-pager" "檢查 PostgreSQL 狀態"
run_command "systemctl status redis-server --no-pager" "檢查 Redis 狀態"
run_command "systemctl status nginx --no-pager" "檢查 Nginx 狀態"

# 檢查端口
echo "檢查系統端口..." | tee -a $LOG_FILE
run_command "netstat -tlnp | grep -E ':(80|6379|5432)'" "檢查系統端口"

# 系統環境部署完成
echo ""
echo -e "${GREEN}🎉 系統環境部署完成！${NC}" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}📋 系統環境資訊${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "主機 IP: $HOST_IP" | tee -a $LOG_FILE
echo "系統用戶: mes" | tee -a $LOG_FILE
echo "專案目錄: $PROJECT_DIR" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}🔧 系統服務${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "PostgreSQL: systemctl status postgresql" | tee -a $LOG_FILE
echo "Redis: systemctl status redis-server" | tee -a $LOG_FILE
echo "Nginx: systemctl status nginx" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}📊 日誌位置${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "系統日誌: $LOG_FILE" | tee -a $LOG_FILE
echo "Nginx 日誌: /var/log/nginx/" | tee -a $LOG_FILE
echo "PostgreSQL 日誌: /var/log/postgresql/" | tee -a $LOG_FILE
echo "Redis 日誌: /var/log/redis/" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "部署完成時間: $(date)" | tee -a $LOG_FILE

# 部署總結
echo ""
echo -e "${BLUE}📊 系統環境部署總結${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "✅ 系統套件安裝完成" | tee -a $LOG_FILE
echo "✅ 系統用戶建立完成" | tee -a $LOG_FILE
echo "✅ PostgreSQL 配置完成" | tee -a $LOG_FILE
echo "✅ Redis 配置完成" | tee -a $LOG_FILE
echo "✅ Nginx 配置完成" | tee -a $LOG_FILE
echo "✅ 系統服務啟動完成" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${GREEN}🎯 下一步${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "1. 建立專案目錄: sudo mkdir -p /var/www/mes" | tee -a $LOG_FILE
echo "2. 部署專案檔案" | tee -a $LOG_FILE
echo "3. 執行專案部署腳本" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${GREEN}🎉 系統環境部署完成！${NC}" | tee -a $LOG_FILE

# 步驟 18: 配置專案服務
echo ""
echo -e "${BLUE}🔧 步驟 18: 配置專案服務${NC}"

# 檢查專案目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  專案目錄不存在，跳過專案服務配置${NC}" | tee -a $LOG_FILE
    echo "請先部署專案檔案再執行此步驟" | tee -a $LOG_FILE
else
    echo -e "${GREEN}✅ 專案目錄存在，開始配置專案服務${NC}" | tee -a $LOG_FILE
    
    # 動態檢測 celery 路徑（開發環境不需要 gunicorn）
    echo "動態檢測 celery 路徑..." | tee -a $LOG_FILE
    CELERY_PATH=$(which celery)
    
    if [ -z "$CELERY_PATH" ]; then
        echo -e "${RED}❌ 找不到 celery，請先安裝${NC}" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "檢測到的路徑:" | tee -a $LOG_FILE
    echo "  celery: $CELERY_PATH" | tee -a $LOG_FILE

    # 跳過 Gunicorn 服務檔案建立（開發環境使用 Django 開發伺服器）
    echo "跳過 Gunicorn 服務檔案建立（開發環境使用 Django 開發伺服器）..." | tee -a $LOG_FILE

    # 建立 Celery Worker 服務檔案
    echo "建立 Celery Worker 服務檔案..." | tee -a $LOG_FILE
    cat > /etc/systemd/system/celery-mes_config.service << EOF
[Unit]
Description=Celery Worker for MES system
After=network.target

[Service]
Type=forking
User=mes
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=mes_config.settings"
ExecStart=/bin/sh -c '$CELERY_PATH multi start worker1 -A mes_config --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO'
ExecStop=/bin/sh -c '$CELERY_PATH multi stopwait worker1 --pidfile=/var/run/celery/%n.pid'
ExecReload=/bin/sh -c '$CELERY_PATH multi restart worker1 -A mes_config --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 建立 Celery Beat 服務檔案
    echo "建立 Celery Beat 服務檔案..." | tee -a $LOG_FILE
    cat > /etc/systemd/system/celerybeat-mes_config.service << EOF
[Unit]
Description=Celery Beat for MES system
After=network.target

[Service]
Type=simple
User=mes
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=mes_config.settings"
ExecStart=$CELERY_PATH -A mes_config beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 建立 Nginx 配置檔案
    echo "建立 Nginx 配置檔案..." | tee -a $LOG_FILE
    
    # 修復 Nginx proxy_headers_hash 警告
    echo "修復 Nginx proxy_headers_hash 警告..." | tee -a $LOG_FILE
    if [ -f "/etc/nginx/nginx.conf" ]; then
        # 備份原始配置
        cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
        
        # 在 http 區塊中添加 proxy_headers_hash 設定
        if ! grep -q "proxy_headers_hash_max_size" /etc/nginx/nginx.conf; then
            # 找到 http 區塊並在開頭添加設定
            sed -i '/^http {/a\    # 修復 proxy_headers_hash 警告\n    proxy_headers_hash_max_size 512;\n    proxy_headers_hash_bucket_size 64;' /etc/nginx/nginx.conf
            echo "✅ 已添加 proxy_headers_hash 設定到 nginx.conf" | tee -a $LOG_FILE
        else
            echo "✅ proxy_headers_hash 設定已存在" | tee -a $LOG_FILE
        fi
    else
        echo "⚠️  無法找到 nginx.conf 檔案" | tee -a $LOG_FILE
    fi
    
    cat > /etc/nginx/sites-available/mes << EOF
server {
    listen 80;
    server_name $HOST_IP localhost;

    client_max_body_size 100M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        # 開發環境：支援 WebSocket 和長連線
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /admin/ {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }

    # 安全性設定
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

    # 啟用 Nginx 網站
    run_command "ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/" "啟用 Nginx 網站配置"
    run_command "rm -f /etc/nginx/sites-enabled/default" "移除預設網站"

    # 建立必要的目錄（已在前面建立，這裡只設定權限）
run_command "find /var/run/celery /var/log/celery -type d -exec chown mes:www-data {} \;" "設定 Celery 目錄擁有者"
run_command "find /var/run/celery /var/log/celery -type f -exec chown mes:www-data {} \;" "設定 Celery 檔案擁有者"
run_command "find /var/run/celery /var/log/celery -type d -exec chmod 755 {} \;" "設定 Celery 目錄權限"
run_command "find /var/run/celery /var/log/celery -type f -exec chmod 644 {} \;" "設定 Celery 檔案權限"

    # 重新載入 systemd
    run_command "systemctl daemon-reload" "重新載入 systemd"

    echo -e "${GREEN}✅ 專案服務配置完成${NC}" | tee -a $LOG_FILE
fi

# 步驟 19: 部署專案（如果專案目錄存在）
echo ""
echo -e "${BLUE}🚀 步驟 19: 部署專案${NC}"

if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${GREEN}✅ 專案檔案存在，開始部署${NC}" | tee -a $LOG_FILE
    
    cd $PROJECT_DIR
    
    # 安裝 Python 套件
    echo "安裝 Python 套件..." | tee -a $LOG_FILE
    run_command "pip3 install -r requirements.txt" "安裝 Python 套件"
    
    # 執行資料庫遷移
    echo "執行資料庫遷移..." | tee -a $LOG_FILE
    
    # 先清除所有遷移檔案，重新生成（確保依賴順序正確）
    echo "清除舊的遷移檔案..." | tee -a $LOG_FILE
    run_command "find . -path '*/migrations/*.py' -not -name '__init__.py' -delete" "清除舊的遷移檔案"
    run_command "find . -path '*/migrations/__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true" "清除遷移快取"
    
    # 重新生成遷移檔案（按正確順序）
    echo "重新生成遷移檔案..." | tee -a $LOG_FILE
    run_command "python3 manage.py makemigrations" "重新生成遷移檔案"
    
    # 執行資料庫遷移
    echo "執行資料庫遷移..." | tee -a $LOG_FILE
    run_command "python3 manage.py migrate" "執行資料庫遷移"
    
    # 收集靜態檔案
    echo "收集靜態檔案..." | tee -a $LOG_FILE
    run_command "python3 manage.py collectstatic --noinput" "收集靜態檔案"
    
    # 建立超級用戶
    echo "建立超級用戶..." | tee -a $LOG_FILE
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('$SUPERUSER_NAME', '$SUPERUSER_EMAIL', '$SUPERUSER_PASSWORD') if not User.objects.filter(username='$SUPERUSER_NAME').exists() else None" | run_command "python3 manage.py shell" "建立超級用戶"
    
    # 設定檔案權限
echo "設定專案檔案權限..." | tee -a $LOG_FILE
run_command "find $PROJECT_DIR -type d -exec chown mes:www-data {} \;" "設定專案目錄擁有者"
run_command "find $PROJECT_DIR -type f -exec chown mes:www-data {} \;" "設定專案檔案擁有者"
run_command "find $PROJECT_DIR -type d -exec chmod 755 {} \;" "設定專案目錄權限"
run_command "find $PROJECT_DIR -type f -exec chmod 644 {} \;" "設定專案檔案權限"
    
    # 設定特殊檔案權限
    run_command "find $PROJECT_DIR -type f -name '*.sh' -exec chmod 755 {} \;" "設定腳本執行權限"
    run_command "find $PROJECT_DIR -type f -name '*.py' -exec chmod 644 {} \;" "設定 Python 檔案權限"
    run_command "find $PROJECT_DIR -type f -name '*.conf' -exec chmod 644 {} \;" "設定配置檔案權限"
    run_command "find $PROJECT_DIR -type f -name '.env*' -exec chmod 640 {} \;" "設定環境檔案權限"
    run_command "find $PROJECT_DIR -type f -name '*.log' -exec chmod 644 {} \;" "設定日誌檔案權限"
    
    # 設定敏感檔案權限
    run_command "chmod 600 $PROJECT_DIR/.env" "設定環境檔案嚴格權限"
    run_command "chmod 600 $PROJECT_DIR/*.key 2>/dev/null || true" "設定金鑰檔案權限"
    run_command "chmod 600 $PROJECT_DIR/*.pem 2>/dev/null || true" "設定憑證檔案權限"
    
    # 設定可寫入目錄權限
    run_command "chmod 775 $PROJECT_DIR/static $PROJECT_DIR/media $PROJECT_DIR/tmp $PROJECT_DIR/logs $PROJECT_DIR/backups_DB $PROJECT_DIR/reports $PROJECT_DIR/staticfiles" "設定可寫入目錄權限"
    
    echo -e "${GREEN}✅ 專案部署完成${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  專案檔案不存在，跳過專案部署${NC}" | tee -a $LOG_FILE
    echo "請先部署專案檔案再執行此步驟" | tee -a $LOG_FILE
fi

# 步驟 21: 啟動專案服務
echo ""
echo -e "${BLUE}🚀 步驟 21: 啟動專案服務${NC}"

if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    # 啟動專案服務（跳過 Gunicorn，開發環境使用 Django 開發伺服器）
    echo "跳過 Gunicorn 服務啟動（開發環境使用 Django 開發伺服器）..." | tee -a $LOG_FILE
    run_command "systemctl enable celery-mes_config" "啟用 Celery Worker 服務"
    run_command "systemctl enable celerybeat-mes_config" "啟用 Celery Beat 服務"
    
    run_command "systemctl start celery-mes_config" "啟動 Celery Worker 服務"
    run_command "systemctl start celerybeat-mes_config" "啟動 Celery Beat 服務"
    
    # 重啟 Nginx
    run_command "systemctl restart nginx" "重啟 Nginx 服務"
    
    # 檢查專案服務狀態（跳過 Gunicorn）
    echo "檢查專案服務狀態..." | tee -a $LOG_FILE
    echo "跳過 Gunicorn 狀態檢查（開發環境使用 Django 開發伺服器）..." | tee -a $LOG_FILE
    run_command "systemctl status celery-mes_config --no-pager" "檢查 Celery Worker 狀態"
    run_command "systemctl status celerybeat-mes_config --no-pager" "檢查 Celery Beat 狀態"
    
    echo -e "${GREEN}✅ 專案服務啟動完成${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  專案檔案不存在，跳過專案服務啟動${NC}" | tee -a $LOG_FILE
fi

# 步驟 22: 最終檢查
echo ""
echo -e "${BLUE}🔍 步驟 22: 最終檢查${NC}"

# 檢查所有服務狀態
echo "檢查所有服務狀態..." | tee -a $LOG_FILE
run_command "systemctl status postgresql --no-pager" "檢查 PostgreSQL 狀態"
run_command "systemctl status redis-server --no-pager" "檢查 Redis 狀態"
run_command "systemctl status nginx --no-pager" "檢查 Nginx 狀態"

if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "跳過 Gunicorn 狀態檢查（開發環境使用 Django 開發伺服器）..." | tee -a $LOG_FILE
    run_command "systemctl status celery-mes_config --no-pager" "檢查 Celery Worker 狀態"
    run_command "systemctl status celerybeat-mes_config --no-pager" "檢查 Celery Beat 狀態"
fi

# 檢查端口
echo "檢查系統端口..." | tee -a $LOG_FILE
run_command "netstat -tlnp | grep -E ':(80|6379|5432)'" "檢查系統端口"

# 測試網站連線
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "測試網站連線..." | tee -a $LOG_FILE
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        echo -e "${GREEN}✅ 網站連線測試成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${YELLOW}⚠️  網站連線測試失敗，請檢查服務狀態${NC}" | tee -a $LOG_FILE
    fi
fi

echo -e "${GREEN}✅ 最終檢查完成${NC}" | tee -a $LOG_FILE

# 部署完成總結
echo ""
echo -e "${GREEN}🎉 系統環境部署完成！${NC}" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}📋 完整部署資訊${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "主機 IP: $HOST_IP" | tee -a $LOG_FILE
echo "系統用戶: mes" | tee -a $LOG_FILE
echo "專案目錄: $PROJECT_DIR" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}🔧 系統服務${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "PostgreSQL: systemctl status postgresql" | tee -a $LOG_FILE
echo "Redis: systemctl status redis-server" | tee -a $LOG_FILE
echo "Nginx: systemctl status nginx" | tee -a $LOG_FILE
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "Django 開發伺服器: python3 manage.py runserver 0.0.0.0:8000" | tee -a $LOG_FILE
    echo "Celery Worker: systemctl status celery-mes_config" | tee -a $LOG_FILE
    echo "Celery Beat: systemctl status celerybeat-mes_config" | tee -a $LOG_FILE
    echo "" | tee -a $LOG_FILE
    echo -e "${BLUE}🌐 網站資訊${NC}" | tee -a $LOG_FILE
    echo "----------------------------------------" | tee -a $LOG_FILE
    echo "網站地址: http://$HOST_IP" | tee -a $LOG_FILE
    echo "管理員帳號: $SUPERUSER_NAME" | tee -a $LOG_FILE
    echo "管理員郵件: $SUPERUSER_EMAIL" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE
echo -e "${BLUE}📊 日誌位置${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "系統日誌: $LOG_FILE" | tee -a $LOG_FILE
echo "Nginx 日誌: /var/log/nginx/" | tee -a $LOG_FILE
echo "PostgreSQL 日誌: /var/log/postgresql/" | tee -a $LOG_FILE
echo "Redis 日誌: /var/log/redis/" | tee -a $LOG_FILE
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "Celery 日誌: /var/log/celery/" | tee -a $LOG_FILE
    echo "Django 開發伺服器日誌: 直接查看終端輸出" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE
echo "部署完成時間: $(date)" | tee -a $LOG_FILE

# 最終部署總結
echo ""
echo -e "${BLUE}📊 完整部署總結${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
echo "✅ 系統套件安裝完成" | tee -a $LOG_FILE
echo "✅ 系統用戶建立完成" | tee -a $LOG_FILE
echo "✅ PostgreSQL 配置完成" | tee -a $LOG_FILE
echo "✅ Redis 配置完成" | tee -a $LOG_FILE
echo "✅ Nginx 配置完成" | tee -a $LOG_FILE
echo "✅ 系統服務啟動完成" | tee -a $LOG_FILE
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "✅ 專案服務配置完成" | tee -a $LOG_FILE
    echo "✅ 專案部署完成" | tee -a $LOG_FILE
    echo "✅ 專案服務啟動完成" | tee -a $LOG_FILE
    echo "✅ 網站功能測試完成" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE
echo -e "${GREEN}🎯 部署完成！${NC}" | tee -a $LOG_FILE
echo "----------------------------------------" | tee -a $LOG_FILE
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
    echo "🌐 網站地址: http://$HOST_IP" | tee -a $LOG_FILE
    echo "👤 管理員帳號: $SUPERUSER_NAME" | tee -a $LOG_FILE
    echo "📧 管理員郵件: $SUPERUSER_EMAIL" | tee -a $LOG_FILE
    echo "" | tee -a $LOG_FILE
    echo "🚀 啟動 Django 開發伺服器:" | tee -a $LOG_FILE
    echo "   cd $PROJECT_DIR" | tee -a $LOG_FILE
    echo "   python3 manage.py runserver 0.0.0.0:8000" | tee -a $LOG_FILE
else
    echo "📦 請部署專案檔案後重新執行此腳本" | tee -a $LOG_FILE
fi
echo "" | tee -a $LOG_FILE
echo -e "${GREEN}🎉 系統環境部署完成！${NC}" | tee -a $LOG_FILE

# 設定所有模組日誌檔案權限
echo "設定所有模組日誌檔案權限..." | tee -a $LOG_FILE
run_command "chown mes:www-data $LOG_BASE_DIR/workorder/workorder.log" "設定工單模組日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/erp_integration/erp_integration.log" "設定 ERP 整合日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/quality/quality.log" "設定品質管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/material/material.log" "設定物料管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/equip/equip.log" "設定設備管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/reporting/reporting.log" "設定報表系統日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/system/system.log" "設定系統管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/kanban/kanban.log" "設定看板日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/production/production.log" "設定生產管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/ai/ai.log" "設定 AI 功能日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/scheduling/scheduling.log" "設定排程管理日誌檔案擁有者"
run_command "chown mes:www-data $LOG_BASE_DIR/process/process.log" "設定製程管理日誌檔案擁有者"

# 設定所有模組日誌檔案權限
echo "設定所有模組日誌檔案權限..." | tee -a $LOG_FILE
run_command "chmod 644 $LOG_BASE_DIR/workorder/workorder.log" "設定工單模組日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/erp_integration/erp_integration.log" "設定 ERP 整合日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/quality/quality.log" "設定品質管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/material/material.log" "設定物料管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/equip/equip.log" "設定設備管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/reporting/reporting.log" "設定報表系統日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/system/system.log" "設定系統管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/kanban/kanban.log" "設定看板日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/production/production.log" "設定生產管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/ai/ai.log" "設定 AI 功能日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/scheduling/scheduling.log" "設定排程管理日誌檔案權限"
run_command "chmod 644 $LOG_BASE_DIR/process/process.log" "設定製程管理日誌檔案權限"

# 修正可能由 Python/Django 套件安裝創建的 setup_project.log 權限
echo "修正可能由套件安裝創建的日誌檔案權限..." | tee -a $LOG_FILE
if [ -f "$LOG_BASE_DIR/setup_project.log" ]; then
    echo "發現 setup_project.log 檔案，修正權限..." | tee -a $LOG_FILE
    run_command "chown mes:www-data $LOG_BASE_DIR/setup_project.log" "修正 setup_project.log 擁有者"
    run_command "chmod 644 $LOG_BASE_DIR/setup_project.log" "修正 setup_project.log 權限"
    echo -e "${GREEN}✅ setup_project.log 權限修正完成${NC}" | tee -a $LOG_FILE
else
    echo "未發現 setup_project.log 檔案" | tee -a $LOG_FILE
fi

# 檢查並修正所有可能由套件安裝創建的日誌檔案
echo "檢查並修正所有套件安裝創建的日誌檔案..." | tee -a $LOG_FILE
find $LOG_BASE_DIR -name "*.log" -user root -exec chown mes:www-data {} \; 2>/dev/null || true
find $LOG_BASE_DIR -name "*.log" -exec chmod 644 {} \; 2>/dev/null || true
echo -e "${GREEN}✅ 所有日誌檔案權限修正完成${NC}" | tee -a $LOG_FILE
