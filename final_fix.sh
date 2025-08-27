#!/bin/bash

# 最終修復腳本 - 讓專案真正可用
echo "=== 最終修復：讓專案真正可用 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 步驟 1: 檢查當前狀態${NC}"
echo "檢查 PostgreSQL 服務..."
sudo systemctl status postgresql --no-pager

echo "檢查資料庫..."
sudo -u postgres psql -l | grep mesdb || echo "資料庫不存在"

echo "檢查專案目錄..."
ls -la /var/www/mes/

echo -e "${BLUE}🔄 步驟 2: 建立資料庫${NC}"
sudo -u postgres createdb mesdb 2>/dev/null || echo "資料庫已存在"

echo -e "${BLUE}🔄 步驟 3: 建立資料庫用戶${NC}"
sudo -u postgres psql -c "CREATE USER mes WITH PASSWORD 'mes123';" 2>/dev/null || echo "用戶已存在"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mesdb TO mes;"
sudo -u postgres psql -c "ALTER USER mes CREATEDB;"

echo -e "${BLUE}🔄 步驟 4: 建立資料表${NC}"
cd /var/www/mes
sudo -u mes python3 manage.py migrate --run-syncdb

echo -e "${BLUE}🔄 步驟 5: 執行遷移${NC}"
sudo -u mes python3 manage.py migrate

echo -e "${BLUE}🔄 步驟 6: 建立超級用戶${NC}"
sudo -u mes python3 manage.py createsuperuser --username admin --email admin@example.com --noinput

echo -e "${BLUE}🔄 步驟 7: 設定密碼${NC}"
echo "admin:admin123" | sudo -u mes python3 manage.py changepassword admin

echo -e "${BLUE}🔄 步驟 8: 收集靜態檔案${NC}"
sudo -u mes python3 manage.py collectstatic --noinput

echo -e "${BLUE}🔄 步驟 9: 建立服務${NC}"
cat > /etc/systemd/system/mes.service << EOF
[Unit]
Description=MES Gunicorn daemon
After=network.target postgresql.service

[Service]
User=mes
Group=www-data
WorkingDirectory=/var/www/mes
Environment=DJANGO_SETTINGS_MODULE=mes_config.settings
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 mes_config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo -e "${BLUE}🔄 步驟 10: 重載並啟動服務${NC}"
sudo systemctl daemon-reload
sudo systemctl enable mes.service
sudo systemctl start mes.service

echo -e "${BLUE}🔄 步驟 11: 配置 Nginx${NC}"
cat > /etc/nginx/sites-available/mes << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /static/ {
        alias /var/www/mes/staticfiles/;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo -e "${BLUE}🔄 步驟 12: 測試系統${NC}"
sleep 5

echo "檢查服務狀態..."
sudo systemctl status mes.service --no-pager

echo "檢查網站..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 網站可以訪問！${NC}"
    echo -e "${GREEN}🌐 網站地址: http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "${GREEN}👤 管理員帳號: admin${NC}"
    echo -e "${GREEN}🔑 管理員密碼: admin123${NC}"
    echo -e "${GREEN}📊 管理後台: http://$(hostname -I | awk '{print $1}')/admin${NC}"
else
    echo -e "${RED}❌ 網站無法訪問${NC}"
    echo "查看日誌: sudo journalctl -u mes.service -f"
fi

echo ""
echo -e "${GREEN}🎉 最終修復完成！${NC}"
echo -e "${GREEN}✅ 專案現在應該可以正常使用了！${NC}"
