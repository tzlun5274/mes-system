# MES 系統 Linux 部署指南

## 📋 系統需求

### 硬體需求
- **CPU**: 2 核心以上
- **記憶體**: 4GB 以上
- **硬碟**: 10GB 以上可用空間
- **網路**: 穩定的網路連線

### 作業系統需求
- **Ubuntu 20.04 LTS** 或更新版本
- **CentOS 7** 或更新版本
- **Debian 10** 或更新版本

## 🔧 環境套件需求

### 系統套件
```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝基礎套件
sudo apt install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    build-essential \
    libpq-dev \
    libssl-dev \
    freetds-dev \
    gettext \
    curl \
    wget \
    git \
    unzip \
    lsof \
    net-tools \
    ntpdate \
    dialog \
    apt-utils
```

### 資料庫和快取
```bash
# PostgreSQL 資料庫
sudo apt install -y postgresql postgresql-contrib

# Redis 快取
sudo apt install -y redis-server

# Nginx 網頁伺服器
sudo apt install -y nginx
```

### Python 套件 (requirements.txt)
```txt
django==5.1.8
django-environ==0.12.0
django-import-export==4.3.7
djangorestframework==3.16.0
gunicorn==22.0.0
psycopg2-binary==2.9.10
python-decouple==3.8
celery==5.5.0
redis==5.2.1
pandas==2.2.3
numpy==1.26.4
openpyxl==3.1.5
xlrd==2.0.1
tablib==3.7.0
django-rosetta==0.10.0
django-celery-beat==2.7.0
django-celery-results==2.5.1
pymssql==2.3.4
pytz==2024.2
django-filter==24.3
django-tables2==2.7.0
python-dateutil==2.9.0
plotly==5.24.1
matplotlib==3.9.2
scikit-learn==1.5.2
tensorflow==2.17.0
requests==2.32.3
django-cors-headers==4.4.0
django-storages==1.14.4
pillow==10.4.0
sqlparse>=0.3.1
asgiref<4,>=3.8.1
diff-match-patch==20241021
```

## 🚀 部署步驟

### 步驟 1: 環境檢查
```bash
# 下載並執行環境檢查腳本
chmod +x 環境需求檢查.sh
./環境需求檢查.sh
```

### 步驟 2: 建立系統用戶
```bash
# 建立 mes 用戶
sudo useradd -m -s /bin/bash mes
sudo usermod -aG sudo mes

# 建立 www-data 群組
sudo groupadd www-data
sudo usermod -aG www-data mes

# 設定密碼
sudo passwd mes
```

### 步驟 3: 建立專案目錄
```bash
# 建立專案目錄
sudo mkdir -p /var/www/mes
sudo chown mes:www-data /var/www/mes
sudo chmod 775 /var/www/mes

# 建立日誌目錄
sudo mkdir -p /var/log/mes
sudo chown mes:mes /var/log/mes
sudo chmod 755 /var/log/mes
```

### 步驟 4: 配置 PostgreSQL
```bash
# 切換到 postgres 用戶
sudo -u postgres psql

# 建立資料庫和使用者
CREATE DATABASE mes_db;
CREATE USER mes_user WITH PASSWORD 'mes_password';
GRANT ALL PRIVILEGES ON DATABASE mes_db TO mes_user;
ALTER USER mes_user CREATEDB;
\q

# 啟動 PostgreSQL 服務
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 步驟 5: 配置 Redis
```bash
# 編輯 Redis 配置
sudo nano /etc/redis/redis.conf

# 設定以下參數：
# bind 127.0.0.1
# port 6379
# requirepass mesredis2025
# maxmemory 2147483648
# maxclients 1000

# 啟動 Redis 服務
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 步驟 6: 複製專案檔案
```bash
# 複製專案檔案到 /var/www/mes
sudo cp -r * /var/www/mes/
sudo chown -R mes:www-data /var/www/mes
sudo chmod +x /var/www/mes/manage.py
```

### 步驟 7: 建立環境變數檔案
```bash
# 建立 .env 檔案
sudo -u mes tee /var/www/mes/.env << EOF
DJANGO_SECRET_KEY='your-secret-key-here'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip
HOST_IP=your-server-ip
DATABASE_NAME=mes_db
DATABASE_USER=mes_user
DATABASE_PASSWORD=mes_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_URL=postgresql://mes_user:mes_password@localhost:5432/mes_db
CELERY_BROKER_URL=redis://:mesredis2025@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:mesredis2025@127.0.0.1:6379/0
LOG_FILE=/var/log/mes/django/mes.log
SERVER_NAME=mes
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=mesredis2025
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
PROJECT_DIR=/var/www/mes
LOG_BASE_DIR=/var/log/mes
BACKUP_DIR=/var/www/mes/backups_DB
APP_USER=mes
APP_GROUP=www-data
GUNICORN_PORT=8000
NGINX_PORT=80
GUNICORN_WORKERS=3
DJANGO_PROJECT_NAME=mes_config
LANGUAGE_CODE=zh-hant
TIME_ZONE=Asia/Taipei
SESSION_COOKIE_AGE=259200
STATIC_ROOT=/var/www/mes/static
LOCALE_DIR=/var/www/mes/locale
TEMP_DIR=/tmp
REQUIREMENTS_FILE=/var/www/mes/requirements.txt
EOF

sudo chown mes:www-data /var/www/mes/.env
sudo chmod 640 /var/www/mes/.env
```

### 步驟 8: 安裝 Python 套件
```bash
# 切換到專案目錄
cd /var/www/mes

# 安裝 Python 套件
sudo pip3 install -r requirements.txt
```

### 步驟 9: 執行資料庫遷移
```bash
# 設定 Django 設定
export DJANGO_SETTINGS_MODULE=mes_config.settings

# 執行遷移
sudo -u mes python3 manage.py migrate

# 建立超級用戶
sudo -u mes python3 manage.py createsuperuser

# 收集靜態檔案
sudo -u mes python3 manage.py collectstatic --noinput
```

### 步驟 10: 建立系統服務

#### Gunicorn 服務
```bash
sudo tee /etc/systemd/system/mes.service << EOF
[Unit]
Description=MES Gunicorn daemon
After=network.target

[Service]
User=mes
Group=www-data
WorkingDirectory=/var/www/mes
Environment=DJANGO_SETTINGS_MODULE=mes_config.settings
EnvironmentFile=/var/www/mes/.env
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 mes_config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
```

#### Celery Worker 服務
```bash
sudo tee /etc/systemd/system/mes-celery.service << EOF
[Unit]
Description=MES Celery Worker
After=network.target

[Service]
Type=forking
User=mes
Group=www-data
EnvironmentFile=/var/www/mes/.env
WorkingDirectory=/var/www/mes
ExecStart=/usr/local/bin/celery multi start worker1 -A mes_config --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO
ExecStop=/usr/local/bin/celery multi stopwait worker1 --pidfile=/var/run/celery/%n.pid
ExecReload=/usr/local/bin/celery multi restart worker1 -A mes_config --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

#### Celery Beat 服務
```bash
sudo tee /etc/systemd/system/celery-beat.service << EOF
[Unit]
Description=MES Celery Beat
After=network.target

[Service]
Type=simple
User=mes
Group=www-data
EnvironmentFile=/var/www/mes/.env
WorkingDirectory=/var/www/mes
ExecStart=/usr/local/bin/celery -A mes_config beat --loglevel=INFO --pidfile=/var/run/celery/beat.pid --schedule=/var/run/celery/celerybeat-schedule
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 步驟 11: 配置 Nginx
```bash
# 建立 Nginx 配置
sudo tee /etc/nginx/sites-available/mes << EOF
upstream mes_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-server-ip;

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
        alias /var/www/mes/static/;
    }
}
EOF

# 啟用網站
sudo ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 測試 Nginx 配置
sudo nginx -t

# 啟動 Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 步驟 12: 啟動所有服務
```bash
# 建立必要目錄
sudo mkdir -p /var/run/celery /var/log/celery
sudo chown -R mes:www-data /var/run/celery /var/log/celery

# 重新載入 systemd
sudo systemctl daemon-reload

# 啟動服務
sudo systemctl enable mes.service
sudo systemctl start mes.service
sudo systemctl enable mes-celery.service
sudo systemctl start mes-celery.service
sudo systemctl enable celery-beat.service
sudo systemctl start celery-beat.service
```

### 步驟 13: 驗證部署
```bash
# 檢查服務狀態
sudo systemctl status mes.service
sudo systemctl status mes-celery.service
sudo systemctl status celery-beat.service
sudo systemctl status nginx

# 檢查端口
sudo netstat -tlnp | grep -E ':(80|8000|6379|5432)'

# 測試網站
curl http://localhost
```

## 🔍 故障排除

### 常見問題

#### 1. 服務無法啟動
```bash
# 檢查日誌
sudo journalctl -u mes.service -f
sudo journalctl -u mes-celery.service -f
sudo journalctl -u celery-beat.service -f
```

#### 2. 資料庫連線問題
```bash
# 測試資料庫連線
sudo -u mes psql -h localhost -U mes_user -d mes_db
```

#### 3. Redis 連線問題
```bash
# 測試 Redis 連線
redis-cli -h 127.0.0.1 -p 6379 -a mesredis2025 ping
```

#### 4. 權限問題
```bash
# 修正權限
sudo chown -R mes:www-data /var/www/mes
sudo chmod -R 755 /var/www/mes
```

## 📊 監控和維護

### 日誌位置
- **應用程式日誌**: `/var/log/mes/`
- **Nginx 日誌**: `/var/log/nginx/`
- **PostgreSQL 日誌**: `/var/log/postgresql/`
- **Redis 日誌**: `/var/log/redis/`

### 備份
```bash
# 資料庫備份
sudo -u postgres pg_dump mes_db > /var/backups/mes_db_$(date +%Y%m%d).sql

# 專案檔案備份
sudo tar -czf /var/backups/mes_files_$(date +%Y%m%d).tar.gz /var/www/mes
```

### 更新
```bash
# 停止服務
sudo systemctl stop mes.service mes-celery.service celery-beat.service

# 更新程式碼
cd /var/www/mes
sudo -u mes git pull

# 更新資料庫
sudo -u mes python3 manage.py migrate

# 重新啟動服務
sudo systemctl start mes.service mes-celery.service celery-beat.service
```

## 🌐 訪問地址

部署完成後，您可以通過以下地址訪問：

- **主網站**: http://your-server-ip
- **管理後台**: http://your-server-ip/admin
- **API 文檔**: http://your-server-ip/api/

## 📞 支援

如果遇到問題，請檢查：
1. 系統日誌
2. 服務狀態
3. 網路連線
4. 防火牆設定

---

**注意**: 請將 `your-server-ip` 替換為您的實際伺服器 IP 地址。
