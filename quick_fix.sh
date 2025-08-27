#!/bin/bash

# 快速修復腳本 - 讓專案立即可用
echo "=== 快速修復：讓專案立即可用 ==="

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 步驟 1: 重啟所有服務${NC}"
sudo systemctl restart postgresql redis-server nginx mes.service

echo -e "${BLUE}🔄 步驟 2: 檢查服務狀態${NC}"
sudo systemctl status mes.service --no-pager
sudo systemctl status nginx --no-pager

echo -e "${BLUE}🔄 步驟 3: 測試網站訪問${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 網站可以訪問！${NC}"
    echo -e "${GREEN}🌐 請在瀏覽器訪問: http://$(hostname -I | awk '{print $1}')${NC}"
else
    echo -e "${RED}❌ 網站無法訪問，執行進一步修復...${NC}"
    
    echo -e "${BLUE}🔄 修復資料庫連接${NC}"
    cd /var/www/mes
    sudo -u mes python3 manage.py migrate --run-syncdb
    
    echo -e "${BLUE}🔄 重新啟動服務${NC}"
    sudo systemctl restart mes.service nginx
    
    echo -e "${BLUE}🔄 再次測試${NC}"
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        echo -e "${GREEN}✅ 修復成功！網站現在可以訪問${NC}"
        echo -e "${GREEN}🌐 請在瀏覽器訪問: http://$(hostname -I | awk '{print $1}')${NC}"
    else
        echo -e "${RED}❌ 需要進一步檢查，請查看日誌${NC}"
        echo "查看日誌: sudo journalctl -u mes.service -f"
    fi
fi

echo ""
echo -e "${GREEN}🎉 快速修復完成！${NC}"
