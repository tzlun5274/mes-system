#!/bin/bash

# 正確部署腳本 - 完全遵循 .env 配置
echo "=== 正確部署：完全遵循 .env 配置 ==="

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
LOG_FILE="/var/log/mes/deploy.log"

# 建立日誌目錄
mkdir -p /var/log/mes
touch $LOG_FILE

echo "開始部署時間: $(date)" | tee -a $LOG_FILE

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
    
    # 讀取 Redis 配置
    REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" $PROJECT_DIR/.env | cut -d'=' -f2)
    
    # 讀取超級用戶配置
    SUPERUSER_NAME=$(grep "^SUPERUSER_NAME=" $PROJECT_DIR/.env | cut -d'=' -f2)
    SUPERUSER_EMAIL=$(grep "^SUPERUSER_EMAIL=" $PROJECT_DIR/.env | cut -d'=' -f2)
    SUPERUSER_PASSWORD=$(grep "^SUPERUSER_PASSWORD=" $PROJECT_DIR/.env | cut -d'=' -f2)
    
    # 讀取主機配置
    HOST_IP=$(grep "^HOST_IP=" $PROJECT_DIR/.env | cut -d'=' -f2)
    ALLOWED_HOSTS=$(grep "^ALLOWED_HOSTS=" $PROJECT_DIR/.env | cut -d'=' -f2)
    
    # 驗證必要配置
    if [ -z "$DATABASE_NAME" ] || [ -z "$DATABASE_USER" ] || [ -z "$DATABASE_PASSWORD" ]; then
        echo -e "${RED}❌ 資料庫配置不完整${NC}" | tee -a $LOG_FILE
        echo "請檢查 .env 檔案中的 DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD" | tee -a $LOG_FILE
        exit 1
    fi
    
    echo "配置讀取完成:" | tee -a $LOG_FILE
    echo "  資料庫名稱: $DATABASE_NAME" | tee -a $LOG_FILE
    echo "  資料庫用戶: $DATABASE_USER" | tee -a $LOG_FILE
    echo "  資料庫主機: $DATABASE_HOST" | tee -a $LOG_FILE
    echo "  資料庫端口: $DATABASE_PORT" | tee -a $LOG_FILE
    echo "  主機 IP: $HOST_IP" | tee -a $LOG_FILE
    echo "  允許主機: $ALLOWED_HOSTS" | tee -a $LOG_FILE
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
echo -e "${YELLOW}🔧 步驟 1: 檢查系統服務${NC}"

# 檢查 PostgreSQL 服務
run_command "systemctl status postgresql" "檢查 PostgreSQL 服務狀態"

# 檢查 Redis 服務
run_command "systemctl status redis-server" "檢查 Redis 服務狀態"

echo ""
echo -e "${YELLOW}🔧 步驟 2: 建立資料庫（使用 .env 配置）${NC}"

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
echo -e "${YELLOW}🔧 步驟 3: 初始化資料庫（使用 .env 配置）${NC}"

cd $PROJECT_DIR

# 檢查 Django 設定
echo "檢查 Django 設定..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py check" "檢查 Django 設定"

# 執行遷移建立資料表
echo "執行遷移建立資料表..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py migrate" "執行遷移建立資料表"

# 驗證遷移狀態
echo "驗證遷移狀態..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py showmigrations" "檢查遷移狀態"

# 檢查資料表
echo "檢查資料表..." | tee -a $LOG_FILE
run_command "sudo -u mes python3 manage.py dbshell -c '\dt'" "檢查資料表"

echo ""
echo -e "${YELLOW}🔧 步驟 4: 建立超級用戶（使用 .env 配置）${NC}"

if [ -z "$SUPERUSER_NAME" ] || [ -z "$SUPERUSER_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️ 無法從 .env 讀取超級用戶資訊，請手動建立${NC}" | tee -a $LOG_FILE
    echo "請執行: sudo -u mes python3 manage.py createsuperuser" | tee -a $LOG_FILE
else
    echo "建立超級用戶: $SUPERUSER_NAME" | tee -a $LOG_FILE
    run_command "sudo -u mes python3 manage.py shell -c \"from django.contrib.auth.models import User; User.objects.create_superuser('$SUPERUSER_NAME', '$SUPERUSER_EMAIL', '$SUPERUSER_PASSWORD') if not User.objects.filter(username='$SUPERUSER_NAME').exists() else print('超級用戶已存在')\"" "建立超級用戶"
fi

echo ""
echo -e "${YELLOW}🔧 步驟 5: 收集靜態檔案${NC}"

# 收集靜態檔案
run_command "sudo -u mes python3 manage.py collectstatic --noinput" "收集靜態檔案"

echo ""
echo -e "${YELLOW}🔧 步驟 6: 建立系統服務${NC}"

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
After=network.target postgresql.service redis-server.service

[Service]
User=mes
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=mes_config.settings
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=/usr/local/bin/celery -A mes_config worker --loglevel=info
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
After=network.target postgresql.service redis-server.service

[Service]
User=mes
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=mes_config.settings
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=/usr/local/bin/celery -A mes_config beat --loglevel=info
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo -e "${YELLOW}🔧 步驟 7: 配置 Nginx（使用 .env 配置）${NC}"

# 建立 Nginx 配置
cat > /etc/nginx/sites-available/mes << EOF
server {
    listen 80;
    server_name $HOST_IP $ALLOWED_HOSTS;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
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
}
EOF

# 啟用 Nginx 配置
run_command "ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/" "啟用 Nginx 配置"
run_command "rm -f /etc/nginx/sites-enabled/default" "移除預設配置"

echo ""
echo -e "${YELLOW}🔧 步驟 8: 重載並啟動服務${NC}"

# 重載 systemd
run_command "systemctl daemon-reload" "重載 systemd"

# 啟用並啟動服務
run_command "systemctl enable mes.service" "啟用 MES 服務"
run_command "systemctl enable mes-celery.service" "啟用 Celery Worker 服務"
run_command "systemctl enable celery-beat.service" "啟用 Celery Beat 服務"

run_command "systemctl start mes.service" "啟動 MES 服務"
run_command "systemctl start mes-celery.service" "啟動 Celery Worker 服務"
run_command "systemctl start celery-beat.service" "啟動 Celery Beat 服務"
run_command "systemctl restart nginx" "重啟 Nginx"

echo ""
echo -e "${YELLOW}🔧 步驟 9: 驗證部署${NC}"

# 等待服務啟動
sleep 10

# 檢查服務狀態
echo "檢查服務狀態..." | tee -a $LOG_FILE
run_command "systemctl status mes.service" "檢查 MES 服務狀態"
run_command "systemctl status nginx" "檢查 Nginx 服務狀態"

# 測試網站訪問
echo "測試網站訪問..." | tee -a $LOG_FILE
if curl -s -o /dev/null -w "%{http_code}" http://$HOST_IP | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 網站可以訪問！${NC}" | tee -a $LOG_FILE
    echo -e "${GREEN}🌐 網站地址: http://$HOST_IP${NC}" | tee -a $LOG_FILE
    echo -e "${GREEN}📊 管理後台: http://$HOST_IP/admin${NC}" | tee -a $LOG_FILE
    if [ ! -z "$SUPERUSER_NAME" ]; then
        echo -e "${GREEN}👤 管理員帳號: $SUPERUSER_NAME${NC}" | tee -a $LOG_FILE
    fi
else
    echo -e "${RED}❌ 網站無法訪問${NC}" | tee -a $LOG_FILE
    echo "查看日誌: sudo journalctl -u mes.service -f" | tee -a $LOG_FILE
fi

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}" | tee -a $LOG_FILE
echo -e "${GREEN}✅ 所有配置都遵循 .env 檔案${NC}" | tee -a $LOG_FILE
echo -e "${GREEN}📝 詳細日誌請查看: $LOG_FILE${NC}" | tee -a $LOG_FILE
