#!/bin/bash

# 真正修復腳本 - 解決 500 錯誤和資料庫問題
echo "=== 真正修復：解決 500 錯誤和資料庫問題 ==="

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

echo -e "${BLUE}🔄 步驟 1: 停止所有服務${NC}"
sudo systemctl stop mes.service nginx postgresql redis-server

echo -e "${BLUE}🔄 步驟 2: 完全清理資料庫${NC}"
sudo -u postgres dropdb mesdb 2>/dev/null || true
sudo -u postgres createdb mesdb

echo -e "${BLUE}🔄 步驟 3: 檢查 Django 設定${NC}"
cd /var/www/mes
sudo -u mes python3 manage.py check

echo -e "${BLUE}🔄 步驟 4: 重新建立所有資料表${NC}"
sudo -u mes python3 manage.py migrate --run-syncdb

echo -e "${BLUE}🔄 步驟 5: 執行所有遷移${NC}"
sudo -u mes python3 manage.py migrate

echo -e "${BLUE}🔄 步驟 6: 驗證資料表是否建立${NC}"
sudo -u mes python3 manage.py dbshell -c "\dt"

echo -e "${BLUE}🔄 步驟 7: 建立超級用戶${NC}"
sudo -u mes python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('超級用戶已建立: admin/admin123')
else:
    print('超級用戶已存在')
"

echo -e "${BLUE}🔄 步驟 8: 收集靜態檔案${NC}"
sudo -u mes python3 manage.py collectstatic --noinput

echo -e "${BLUE}🔄 步驟 9: 重啟服務${NC}"
sudo systemctl start postgresql redis-server nginx mes.service

echo -e "${BLUE}🔄 步驟 10: 等待服務啟動${NC}"
sleep 10

echo -e "${BLUE}🔄 步驟 11: 測試網站${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 修復成功！網站可以訪問${NC}"
    echo -e "${GREEN}🌐 請訪問: http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "${GREEN}👤 管理員帳號: admin${NC}"
    echo -e "${GREEN}🔑 密碼: admin123${NC}"
else
    echo -e "${RED}❌ 仍有問題，檢查日誌${NC}"
    sudo journalctl -u mes.service --no-pager -n 20
    echo -e "${YELLOW}⚠️ 請檢查 Django 錯誤日誌${NC}"
    sudo tail -n 20 /var/log/mes/django/mes.log 2>/dev/null || echo "日誌檔案不存在"
fi

echo ""
echo -e "${GREEN}🎉 真正修復完成！${NC}"
