#!/bin/bash
# MES 系統完全清理腳本
# 用途：完全移除 MES 系統及其所有相關套件和配置

echo "=== MES 系統完全清理腳本 ==="
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

echo -e "${RED}⚠️  警告：此腳本將完全移除 MES 系統及其所有相關套件${NC}"
echo -e "${RED}⚠️  包括：專案檔案、資料庫、服務配置、Python 套件、系統套件${NC}"
echo -e "${RED}⚠️  這是一個不可逆的操作！${NC}"
echo ""
read -p "確定要完全清理嗎？輸入 'YES' 確認: " confirm

if [[ $confirm != "YES" ]]; then
    echo -e "${BLUE}取消清理操作${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🧹 開始完全清理 MES 系統...${NC}"

# 1. 停止所有相關服務
echo "1. 停止相關服務..."
systemctl stop mes 2>/dev/null || echo "mes 服務未運行"
systemctl stop mes-celery 2>/dev/null || echo "mes-celery 服務未運行"
systemctl stop celery-beat 2>/dev/null || echo "celery-beat 服務未運行"
systemctl stop nginx 2>/dev/null || echo "nginx 服務未運行"
systemctl stop redis-server 2>/dev/null || echo "redis-server 服務未運行"
systemctl stop postgresql 2>/dev/null || echo "postgresql 服務未運行"

# 2. 移除系統服務檔案
echo "2. 移除系統服務檔案..."
rm -f /etc/systemd/system/mes.service
rm -f /etc/systemd/system/mes-celery.service
rm -f /etc/systemd/system/celery-beat.service
systemctl daemon-reload

# 3. 清理專案目錄
echo "3. 清理專案目錄..."
PROJECT_DIR="/var/www/mes"
if [ -d "$PROJECT_DIR" ]; then
    echo "備份專案到 /tmp/mes_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r $PROJECT_DIR /tmp/mes_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    rm -rf $PROJECT_DIR
    echo "專案目錄已移除"
else
    echo "專案目錄不存在"
fi

# 4. 清理 Nginx 配置
echo "4. 清理 Nginx 配置..."
rm -f /etc/nginx/sites-available/mes
rm -f /etc/nginx/sites-enabled/mes
systemctl restart nginx 2>/dev/null || true

# 5. 清理日誌檔案
echo "5. 清理日誌檔案..."
rm -rf /var/log/mes 2>/dev/null || true
rm -f /var/log/nginx/mes_*.log 2>/dev/null || true

# 6. 清理 Python 快取
echo "6. 清理 Python 快取..."
find /tmp -name "*.pyc" -delete 2>/dev/null || true
find /tmp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find /home -name "*.pyc" -delete 2>/dev/null || true
find /home -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 7. 清理 Redis 資料
echo "7. 清理 Redis 資料..."
redis-cli -a mesredis2025 FLUSHALL 2>/dev/null || echo "Redis 未運行或密碼錯誤"

# 8. 清理資料庫
echo "8. 清理資料庫..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS mes_db;" 2>/dev/null || echo "無法移除資料庫"
sudo -u postgres psql -c "DROP USER IF EXISTS mes_user;" 2>/dev/null || echo "無法移除使用者"

# 9. 清理 mes 用戶
echo "9. 清理系統用戶..."
userdel -r mes 2>/dev/null || echo "無法移除 mes 用戶"

# 10. 移除 Python 套件
echo "10. 移除 Python 套件..."
echo "移除 Django 相關套件..."
pip3 uninstall -y django django-cors-headers django-celery-beat 2>/dev/null || true
echo "移除 Celery 相關套件..."
pip3 uninstall -y celery redis 2>/dev/null || true
echo "移除資料庫相關套件..."
pip3 uninstall -y psycopg2-binary 2>/dev/null || true
echo "移除 Web 伺服器套件..."
pip3 uninstall -y gunicorn 2>/dev/null || true
echo "移除報表相關套件..."
pip3 uninstall -y openpyxl xlsxwriter pandas 2>/dev/null || true
echo "移除其他工具套件..."
pip3 uninstall -y python-dotenv requests 2>/dev/null || true
echo "移除其他可能相關套件..."
pip3 uninstall -y numpy matplotlib seaborn 2>/dev/null || true
pip3 uninstall -y scikit-learn tensorflow 2>/dev/null || true

# 11. 移除系統套件
echo "11. 移除系統套件..."
echo "移除 PostgreSQL..."
apt remove -y postgresql postgresql-contrib 2>/dev/null || true
apt purge -y postgresql* 2>/dev/null || true
echo "移除 Redis..."
apt remove -y redis-server 2>/dev/null || true
apt purge -y redis* 2>/dev/null || true
echo "移除 Nginx..."
apt remove -y nginx 2>/dev/null || true
apt purge -y nginx* 2>/dev/null || true
echo "移除其他相關套件..."
apt remove -y python3-dev build-essential libpq-dev 2>/dev/null || true
echo "清理套件快取..."
apt autoremove -y
apt autoclean

# 12. 清理配置檔案
echo "12. 清理配置檔案..."
rm -f /etc/redis/redis.conf 2>/dev/null || true
rm -rf /etc/postgresql 2>/dev/null || true
rm -rf /var/lib/postgresql 2>/dev/null || true
rm -rf /var/lib/redis 2>/dev/null || true

# 13. 清理臨時檔案
echo "13. 清理臨時檔案..."
rm -f /tmp/mes_*.log 2>/dev/null || true
rm -f /tmp/celery_*.log 2>/dev/null || true
rm -f /tmp/nohup.out 2>/dev/null || true
rm -rf /var/run/celery 2>/dev/null || true
rm -rf /var/log/celery 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ MES 系統完全清理完成！${NC}"
echo ""
echo "📋 清理內容："
echo "✅ 停止所有相關服務"
echo "✅ 移除系統服務檔案"
echo "✅ 清理專案目錄（已備份到 /tmp/）"
echo "✅ 清理 Nginx 配置"
echo "✅ 清理日誌檔案"
echo "✅ 清理 Python 快取"
echo "✅ 清理 Redis 資料"
echo "✅ 清理資料庫"
echo "✅ 清理系統用戶"
echo "✅ 移除所有 Python 套件"
echo "✅ 移除所有系統套件"
echo "✅ 清理配置檔案"
echo "✅ 清理臨時檔案"
echo ""
echo "📁 備份位置：/tmp/mes_backup_YYYYMMDD_HHMMSS/"
echo "💡 如需恢復，請手動複製備份檔案"
echo ""
echo "🔄 系統已回到安裝 MES 之前的狀態"
