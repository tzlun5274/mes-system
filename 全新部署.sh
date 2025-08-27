#!/bin/bash

# MES 系統全新部署腳本
# 用途：從零開始完整部署 MES 系統（包含系統套件、設定、專案）

echo "=== MES 系統全新部署腳本 ==="
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
LOG_FILE="$LOG_BASE_DIR/deploy.log"
HOST_IP=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -n 1)

# 建立日誌目錄
mkdir -p $LOG_BASE_DIR
touch $LOG_FILE

echo "開始部署時間: $(date)" | tee -a $LOG_FILE
echo "主機 IP: $HOST_IP" | tee -a $LOG_FILE

# 函數：從 .env 檔案讀取配置
load_env_config() {
    # 檢查當前目錄的 .env 檔案
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ 未找到 .env 檔案${NC}" | tee -a $LOG_FILE
        echo "請確保在解壓後的目錄執行此腳本，且 .env 檔案存在" | tee -a $LOG_FILE
        echo "當前目錄: $(pwd)" | tee -a $LOG_FILE
        echo "請檢查 .env 檔案是否存在" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "正在讀取當前目錄的 .env 配置..." | tee -a $LOG_FILE
    echo "當前目錄: $(pwd)" | tee -a $LOG_FILE
    
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
        return 1
    fi
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

# 停止相關服務
echo "停止相關服務..." | tee -a $LOG_FILE
systemctl stop mes 2>/dev/null || true
systemctl stop mes-celery 2>/dev/null || true
systemctl stop celery-beat 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
systemctl stop redis-server 2>/dev/null || true
systemctl stop postgresql 2>/dev/null || true

# 移除舊的服務檔案
echo "移除舊的服務檔案..." | tee -a $LOG_FILE
rm -f /etc/systemd/system/mes.service
rm -f /etc/systemd/system/mes-celery.service
rm -f /etc/systemd/system/celery-beat.service
systemctl daemon-reload

# 清理舊的專案檔案
echo "清理舊的專案檔案..." | tee -a $LOG_FILE
if [ -d "$PROJECT_DIR" ]; then
    rm -rf $PROJECT_DIR
fi

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

# 清理 Redis 資料（可選）
echo "清理 Redis 資料..." | tee -a $LOG_FILE
redis-cli -a $REDIS_PASSWORD FLUSHALL 2>/dev/null || true

echo -e "${GREEN}✅ 清理完成${NC}" | tee -a $LOG_FILE

# 步驟 3: 更新系統套件
echo ""
echo -e "${BLUE}📦 步驟 3: 更新系統套件${NC}"
run_command "apt update && apt upgrade -y" "更新系統套件"

# 步驟 4: 安裝基礎套件
echo ""
echo -e "${BLUE}🔧 步驟 4: 安裝基礎套件${NC}"
run_command "apt install -y python3 python3-pip python3-dev python3-setuptools python3-wheel build-essential libpq-dev libssl-dev freetds-dev gettext curl wget git unzip lsof net-tools ntpdate dialog apt-utils" "安裝基礎套件"

# 步驟 5: 安裝資料庫和服務
echo ""
echo -e "${BLUE}🗄️ 步驟 5: 安裝資料庫和服務${NC}"
run_command "apt install -y postgresql postgresql-contrib redis-server nginx" "安裝資料庫和服務"

# 步驟 6: 建立系統用戶
echo ""
echo -e "${BLUE}👥 步驟 6: 建立系統用戶${NC}"
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

# 步驟 7: 建立專案目錄
echo ""
echo -e "${BLUE}📁 步驟 7: 建立專案目錄${NC}"
run_command "mkdir -p $PROJECT_DIR" "建立專案目錄"
run_command "chown -R mes:www-data $PROJECT_DIR" "設定專案目錄權限"
run_command "chmod -R 775 $PROJECT_DIR" "設定專案目錄權限"

# 步驟 8: 配置 PostgreSQL
echo ""
echo -e "${BLUE}🐘 步驟 8: 配置 PostgreSQL${NC}"
run_command "systemctl enable postgresql" "啟用 PostgreSQL 服務"
run_command "systemctl start postgresql" "啟動 PostgreSQL 服務"

# 建立資料庫和使用者
echo "建立資料庫和使用者..." | tee -a $LOG_FILE

# 檢查資料庫是否已存在
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DATABASE_NAME; then
    echo "資料庫 $DATABASE_NAME 已存在，跳過建立" | tee -a $LOG_FILE
else
    run_command "sudo -u postgres psql -c \"CREATE DATABASE $DATABASE_NAME;\"" "建立資料庫"
fi

# 檢查使用者是否已存在
if sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DATABASE_USER'" | grep -q 1; then
    echo "使用者 $DATABASE_USER 已存在，更新密碼" | tee -a $LOG_FILE
    run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "更新使用者密碼"
else
    run_command "sudo -u postgres psql -c \"CREATE USER $DATABASE_USER WITH PASSWORD '$DATABASE_PASSWORD';\"" "建立使用者"
fi

# 授予權限
run_command "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;\"" "授予資料庫權限"
run_command "sudo -u postgres psql -c \"ALTER USER $DATABASE_USER CREATEDB;\"" "授予建立資料庫權限"

echo "資料庫配置完成" | tee -a $LOG_FILE

# 步驟 9: 配置 Redis
echo ""
echo -e "${BLUE}🔴 步驟 9: 配置 Redis${NC}"
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

# 步驟 10: 驗證專案目錄
echo ""
echo -e "${BLUE}📋 步驟 10: 驗證專案目錄${NC}"

# 檢查當前目錄是否為專案目錄
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ 未找到 manage.py，請確保在 /var/www/mes 專案目錄執行此腳本${NC}"
    echo "當前目錄: $(pwd)" | tee -a $LOG_FILE
    echo "請先執行以下步驟：" | tee -a $LOG_FILE
    echo "1. 解壓縮套件" | tee -a $LOG_FILE
    echo "2. 建立目錄: sudo mkdir -p /var/www/mes" | tee -a $LOG_FILE
    echo "3. 搬移檔案: sudo cp -r 解壓目錄/* /var/www/mes/" | tee -a $LOG_FILE
    echo "4. 設定權限: sudo chown -R mes:www-data /var/www/mes/" | tee -a $LOG_FILE
    echo "5. 進入目錄: cd /var/www/mes" | tee -a $LOG_FILE
    echo "6. 修改配置: nano .env" | tee -a $LOG_FILE
    echo "7. 執行部署: sudo ./全新部署.sh" | tee -a $LOG_FILE
    exit 1
fi

# 檢查是否在正確的目錄
if [ "$(pwd)" != "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 請在 $PROJECT_DIR 目錄執行此腳本${NC}" | tee -a $LOG_FILE
    echo "當前目錄: $(pwd)" | tee -a $LOG_FILE
    echo "請執行: cd $PROJECT_DIR" | tee -a $LOG_FILE
    exit 1
fi

echo -e "${GREEN}✅ 專案目錄驗證通過${NC}" | tee -a $LOG_FILE

# 步驟 11: 建立環境變數檔案
echo ""
echo -e "${BLUE}⚙️ 步驟 11: 建立環境變數檔案${NC}"

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
GUNICORN_PORT=8000
NGINX_PORT=80
GUNICORN_WORKERS=3
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

# 建立必要的目錄
echo "建立必要的目錄..." | tee -a $LOG_FILE
run_command "mkdir -p $LOG_BASE_DIR/django" "建立 Django 日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/workorder" "建立工單日誌目錄"
run_command "mkdir -p $LOG_BASE_DIR/erp_integration" "建立 ERP 整合日誌目錄"
run_command "mkdir -p $PROJECT_DIR/static" "建立靜態檔案目錄"
run_command "mkdir -p $PROJECT_DIR/media" "建立媒體檔案目錄"
run_command "mkdir -p $PROJECT_DIR/tmp" "建立臨時檔案目錄"
run_command "mkdir -p $PROJECT_DIR/logs" "建立專案日誌目錄"
run_command "chown -R mes:www-data $LOG_BASE_DIR" "設定日誌目錄權限"
run_command "chmod -R 755 $LOG_BASE_DIR" "設定日誌目錄權限"
run_command "chown -R mes:www-data $PROJECT_DIR/static $PROJECT_DIR/media $PROJECT_DIR/tmp $PROJECT_DIR/logs" "設定專案目錄權限"
run_command "chmod -R 775 $PROJECT_DIR/static $PROJECT_DIR/media $PROJECT_DIR/tmp $PROJECT_DIR/logs" "設定專案目錄權限"

# 步驟 12: 安裝 Python 套件
echo ""
echo -e "${BLUE}🐍 步驟 12: 安裝 Python 套件${NC}"
run_command "cd $PROJECT_DIR && pip3 install -r requirements.txt" "安裝 Python 套件"

# 步驟 13: 執行資料庫遷移
echo ""
echo -e "${BLUE}🗃️ 步驟 13: 執行資料庫遷移${NC}"
export DJANGO_SETTINGS_MODULE=mes_config.settings

# 初始化資料庫（全新生產環境專用）
echo "初始化資料庫..." | tee -a $LOG_FILE

cd $PROJECT_DIR

# 全新生產主機的資料庫初始化策略
echo "執行全新資料庫初始化..." | tee -a $LOG_FILE

# 執行 Django 遷移
echo "執行 Django 遷移..." | tee -a $LOG_FILE
sudo -u mes python3 manage.py migrate 2>&1 | tee -a $LOG_FILE

# 強制檢查資料庫表是否真的建立
echo "檢查資料庫表是否建立..." | tee -a $LOG_FILE
if sudo -u mes python3 manage.py dbshell -c "\dt auth_user" 2>&1 | grep -q "auth_user"; then
    echo -e "${GREEN}✅ Django 遷移成功，資料表已建立${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ Django 遷移失敗，auth_user 表不存在${NC}" | tee -a $LOG_FILE
    
    # 重新建立資料庫並重試
    echo "重新建立資料庫並重試..." | tee -a $LOG_FILE
    sudo -u postgres dropdb $DATABASE_NAME 2>/dev/null || true
    sudo -u postgres createdb $DATABASE_NAME
    
    # 重新授予權限
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;"
    sudo -u postgres psql -c "ALTER USER $DATABASE_USER CREATEDB;"
    
    # 重新執行遷移
    echo "重新執行遷移..." | tee -a $LOG_FILE
    sudo -u mes python3 manage.py migrate 2>&1 | tee -a $LOG_FILE
    
    # 再次檢查
    if sudo -u mes python3 manage.py dbshell -c "\dt auth_user" 2>&1 | grep -q "auth_user"; then
        echo -e "${GREEN}✅ 重新建立資料庫成功${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ 資料庫建立仍然失敗${NC}" | tee -a $LOG_FILE
        echo "檢查遷移狀態..." | tee -a $LOG_FILE
        sudo -u mes python3 manage.py showmigrations 2>&1 | tee -a $LOG_FILE
        echo "檢查資料庫表..." | tee -a $LOG_FILE
        sudo -u mes python3 manage.py dbshell -c "\dt" 2>&1 | tee -a $LOG_FILE
        exit 1
    fi
fi

# 驗證資料庫初始化狀態
echo "驗證資料庫初始化狀態..." | tee -a $LOG_FILE
sudo -u mes python3 manage.py showmigrations 2>&1 | tee -a $LOG_FILE

# 檢查資料庫表是否正確創建
echo "檢查資料庫表結構..." | tee -a $LOG_FILE
sudo -u mes python3 manage.py dbshell -c "\dt" 2>&1 | tee -a $LOG_FILE

echo -e "${GREEN}✅ 資料庫初始化完成${NC}" | tee -a $LOG_FILE

# 建立超級用戶
echo "建立超級用戶..." | tee -a $LOG_FILE
cd $PROJECT_DIR
sudo -u mes python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='$SUPERUSER_NAME').exists():
    User.objects.create_superuser('$SUPERUSER_NAME', '$SUPERUSER_EMAIL', '$SUPERUSER_PASSWORD')
    print('超級用戶已建立')
else:
    print('超級用戶已存在')
" 2>&1 | tee -a $LOG_FILE

# 收集靜態檔案
run_command "cd $PROJECT_DIR && sudo -u mes python3 manage.py collectstatic --noinput" "收集靜態檔案"

# 步驟 14: 建立系統服務
echo ""
echo -e "${BLUE}🔧 步驟 14: 建立系統服務${NC}"

# 建立 Gunicorn 服務
cat > /etc/systemd/system/mes.service << EOF
[Unit]
Description=MES Gunicorn daemon
After=network.target postgresql.service redis-server.service

[Service]
User=mes
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=mes_config.settings
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 mes_config.wsgi:application
ExecStop=/bin/kill -TERM \$MAINPID
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 建立 Celery Worker 服務
cat > /etc/systemd/system/mes-celery.service << EOF
[Unit]
Description=MES Celery Worker
After=network.target

[Service]
Type=simple
User=mes
Group=www-data
EnvironmentFile=$PROJECT_DIR/.env
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/celery -A mes_config worker --loglevel=INFO --pidfile=/var/run/celery/worker.pid
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 建立 Celery Beat 服務
cat > /etc/systemd/system/celery-beat.service << EOF
[Unit]
Description=MES Celery Beat
After=network.target

[Service]
Type=simple
User=mes
Group=www-data
EnvironmentFile=$PROJECT_DIR/.env
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/celery -A mes_config beat --loglevel=INFO --pidfile=/var/run/celery/beat.pid --schedule=/var/run/celery/celerybeat-schedule
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 步驟 15: 配置 Nginx
echo ""
echo -e "${BLUE}🌐 步驟 15: 配置 Nginx${NC}"

# 建立 Nginx 配置
cat > /etc/nginx/sites-available/mes << EOF
upstream mes_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name $HOST_IP;

    location / {
        proxy_pass http://mes_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /static/ {
        alias $PROJECT_DIR/static/;
    }
}
EOF

run_command "ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/" "啟用 Nginx 網站"
run_command "rm -f /etc/nginx/sites-enabled/default" "移除預設網站"
run_command "nginx -t" "測試 Nginx 配置"
# 步驟 16: 啟動所有服務
echo ""
echo -e "${BLUE}🚀 步驟 16: 啟動所有服務${NC}"
run_command "mkdir -p /var/run/celery /var/log/celery" "建立 Celery 目錄"
run_command "chown -R mes:www-data /var/run/celery /var/log/celery" "設定 Celery 目錄權限"
run_command "chmod -R 755 /var/run/celery /var/log/celery" "設定 Celery 目錄權限"
run_command "systemctl daemon-reload" "重新載入 systemd"

# 啟動所有服務
run_command "systemctl enable mes.service" "啟用 MES 服務"
run_command "systemctl enable mes-celery.service" "啟用 Celery Worker 服務"
run_command "systemctl enable celery-beat.service" "啟用 Celery Beat 服務"
run_command "systemctl enable nginx" "啟用 Nginx 服務"

# 啟動服務並等待
echo "啟動 MES 服務..." | tee -a $LOG_FILE
run_command "systemctl start mes.service" "啟動 MES 服務"
sleep 5

echo "啟動 Celery Worker 服務..." | tee -a $LOG_FILE
run_command "systemctl start mes-celery.service" "啟動 Celery Worker 服務"
sleep 3

echo "啟動 Celery Beat 服務..." | tee -a $LOG_FILE
run_command "systemctl start celery-beat.service" "啟動 Celery Beat 服務"
sleep 3

echo "啟動 Nginx 服務..." | tee -a $LOG_FILE
run_command "systemctl start nginx" "啟動 Nginx 服務"
sleep 3

# 最終檢查所有服務
echo "檢查所有服務狀態..." | tee -a $LOG_FILE
for service in mes mes-celery celery-beat nginx; do
    if systemctl is-active --quiet $service.service; then
        echo -e "${GREEN}✅ $service 服務運行正常${NC}" | tee -a $LOG_FILE
    else
        echo -e "${RED}❌ $service 服務啟動失敗${NC}" | tee -a $LOG_FILE
        systemctl status $service.service --no-pager | tee -a $LOG_FILE
        echo "嘗試重新啟動 $service 服務..." | tee -a $LOG_FILE
        systemctl restart $service.service
        sleep 5
    fi
done

# 步驟 17: 驗證部署
echo ""
echo -e "${BLUE}✅ 步驟 17: 驗證部署${NC}"

# 等待服務啟動
sleep 5

# 檢查服務狀態
echo "檢查服務狀態..." | tee -a $LOG_FILE
systemctl status mes.service --no-pager | tee -a $LOG_FILE
systemctl status mes-celery.service --no-pager | tee -a $LOG_FILE
systemctl status celery-beat.service --no-pager | tee -a $LOG_FILE
systemctl status nginx --no-pager | tee -a $LOG_FILE

# 檢查端口
echo "檢查端口..." | tee -a $LOG_FILE
netstat -tlnp | grep -E ':(80|8000|6379|5432)' | tee -a $LOG_FILE

# 測試網站
echo "測試網站..." | tee -a $LOG_FILE
sleep 5
if curl -s -f http://localhost > /dev/null 2>&1; then
    echo "✅ 網站可訪問" | tee -a $LOG_FILE
else
    echo "❌ 網站無法訪問，檢查服務狀態..." | tee -a $LOG_FILE
    systemctl status mes.service --no-pager | tee -a $LOG_FILE
    systemctl status nginx --no-pager | tee -a $LOG_FILE
    echo "嘗試重新啟動服務..." | tee -a $LOG_FILE
    systemctl restart mes.service
    systemctl restart nginx
    sleep 10
    if curl -s -f http://localhost > /dev/null 2>&1; then
        echo "✅ 網站重新啟動後可訪問" | tee -a $LOG_FILE
    else
        echo "❌ 網站仍然無法訪問" | tee -a $LOG_FILE
    fi
fi

# 部署完成
echo ""
echo -e "${GREEN}🎉 MES 系統部署完成！${NC}"
echo ""
echo -e "${BLUE}📋 部署資訊${NC}"
echo "----------------------------------------"
echo "專案目錄: $PROJECT_DIR"
echo "主機 IP: $HOST_IP"
echo "訪問地址: http://$HOST_IP"
echo "管理後台: http://$HOST_IP/admin"
echo "管理員帳號: $SUPERUSER_NAME"
echo "管理員密碼: [已設定]"
echo ""
echo -e "${BLUE}🔧 服務管理${NC}"
echo "----------------------------------------"
echo "查看狀態: sudo systemctl status mes.service"
echo "重啟服務: sudo systemctl restart mes.service"
echo "查看日誌: sudo journalctl -u mes.service -f"
echo ""
echo -e "${BLUE}📊 日誌位置${NC}"
echo "----------------------------------------"
echo "應用程式日誌: $LOG_BASE_DIR/"
echo "Nginx 日誌: /var/log/nginx/"
echo "PostgreSQL 日誌: /var/log/postgresql/"
echo "Redis 日誌: /var/log/redis/"
echo ""
echo "部署完成時間: $(date)" | tee -a $LOG_FILE
