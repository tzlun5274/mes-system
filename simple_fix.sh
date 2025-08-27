#!/bin/bash

# 簡單修復腳本 - 針對全新主機
echo "=== 簡單修復：全新主機問題解決 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 步驟 1: 停止所有服務${NC}"
sudo systemctl stop mes.service nginx postgresql redis-server

echo -e "${BLUE}🔄 步驟 2: 清理資料庫${NC}"
sudo -u postgres dropdb mesdb 2>/dev/null || true
sudo -u postgres createdb mesdb

echo -e "${BLUE}🔄 步驟 3: 重新建立資料表${NC}"
cd /var/www/mes
sudo -u mes python3 manage.py migrate --run-syncdb

echo -e "${BLUE}🔄 步驟 4: 執行遷移${NC}"
sudo -u mes python3 manage.py migrate

echo -e "${BLUE}🔄 步驟 5: 建立超級用戶${NC}"
sudo -u mes python3 manage.py createsuperuser --username admin --email admin@example.com --noinput

echo -e "${BLUE}🔄 步驟 6: 收集靜態檔案${NC}"
sudo -u mes python3 manage.py collectstatic --noinput

echo -e "${BLUE}🔄 步驟 7: 重啟服務${NC}"
sudo systemctl start postgresql redis-server nginx mes.service

echo -e "${BLUE}🔄 步驟 8: 測試網站${NC}"
sleep 5
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 修復成功！網站可以訪問${NC}"
    echo -e "${GREEN}🌐 請訪問: http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "${GREEN}👤 管理員帳號: admin${NC}"
    echo -e "${GREEN}🔑 密碼: 請執行: sudo -u mes python3 manage.py changepassword admin${NC}"
else
    echo -e "${RED}❌ 仍有問題，請檢查日誌${NC}"
    sudo journalctl -u mes.service --no-pager -n 20
fi

echo ""
echo -e "${GREEN}🎉 簡單修復完成！${NC}"
