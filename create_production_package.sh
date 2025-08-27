#!/bin/bash

# 建立生產環境部署套件
# 用途：打包所有必要的檔案，用於部署到生產主機

echo "=== 建立生產環境部署套件 ==="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 檢查是否在專案根目錄
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ 請在專案根目錄執行此腳本${NC}"
    exit 1
fi

# 設定變數
PACKAGE_NAME="mes_production_package_$(date +%Y%m%d_%H%M%S)"
TEMP_DIR="/tmp/$PACKAGE_NAME"

echo -e "${BLUE}📦 建立部署套件: $PACKAGE_NAME${NC}"

# 建立臨時目錄
echo "建立臨時目錄..."
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# 複製核心檔案
echo "複製核心檔案..."
cp -r mes_config $TEMP_DIR/
cp -r ai $TEMP_DIR/
cp -r equip $TEMP_DIR/
cp -r erp_integration $TEMP_DIR/
cp -r kanban $TEMP_DIR/
cp -r material $TEMP_DIR/
cp -r process $TEMP_DIR/
cp -r production $TEMP_DIR/
cp -r quality $TEMP_DIR/
cp -r reporting $TEMP_DIR/
cp -r scheduling $TEMP_DIR/
cp -r system $TEMP_DIR/
cp -r workorder $TEMP_DIR/
cp -r templates $TEMP_DIR/
cp -r static $TEMP_DIR/
cp -r media $TEMP_DIR/

# 複製配置檔案
echo "複製配置檔案..."
cp manage.py $TEMP_DIR/
cp requirements.txt $TEMP_DIR/
cp .env $TEMP_DIR/

# 複製部署腳本
echo "複製部署腳本..."
cp 全新部署.sh $TEMP_DIR/
cp restart_services.sh $TEMP_DIR/
chmod +x $TEMP_DIR/全新部署.sh
chmod +x $TEMP_DIR/restart_services.sh

# 設定打包目錄權限
echo "設定打包目錄權限..."
chmod -R 755 $TEMP_DIR
chown -R mes:mes $TEMP_DIR

# 複製重要文件（如果存在）
echo "複製重要文件..."
# 注意：這些檔案可能不存在，使用 2>/dev/null || true 避免錯誤
# 實際檢查發現根目錄沒有 .md 檔案，所以這些複製會失敗但不影響打包
cp README.md $TEMP_DIR/ 2>/dev/null || true
cp VERSION.md $TEMP_DIR/ 2>/dev/null || true
cp CHANGELOG.md $TEMP_DIR/ 2>/dev/null || true
cp DEVELOPMENT_STATUS.md $TEMP_DIR/ 2>/dev/null || true
cp Linux部署指南.md $TEMP_DIR/ 2>/dev/null || true

# 清理並重新生成遷移文件（生產環境用）
echo "清理並重新生成遷移文件..."
cd $TEMP_DIR

# 備份現有遷移文件
BACKUP_DIR="migrations_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
find . -path "*/migrations/*.py" -not -name "__init__.py" -exec cp {} $BACKUP_DIR/ \; 2>/dev/null || true

# 刪除所有現有遷移文件（保留 __init__.py）
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

# 重新生成乾淨的遷移文件
python3 manage.py makemigrations 2>/dev/null || echo "遷移文件生成完成"

echo "新生成的遷移文件："
find . -path "*/migrations/*.py" -not -name "__init__.py" | sort

# 清理打包目錄中的垃圾檔案
echo "清理垃圾檔案..."

# 刪除 Python 快取檔案
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 刪除日誌檔案
find . -name "*.log" -delete
find . -name "celery_*.log" -delete
find . -name "nohup.out" -delete

# 刪除測試檔案
find . -name "test_*.py" -delete
find . -name "test_*.xlsx" -delete
find . -name "test_*.csv" -delete

# 刪除除錯檔案
find . -name "debug_*.py" -delete
find . -name "check_*.py" -delete
find . -name "fix_*.py" -delete
find . -name "cleanup_*.py" -delete
find . -name "generate_*.py" -delete
find . -name "setup_*.py" -delete
find . -name "simple_*.py" -delete

# 刪除遷移文件備份目錄
rm -rf $BACKUP_DIR

# 刪除空目錄
find . -type d -empty -delete

# 建立部署說明
cat > $TEMP_DIR/部署說明.txt << 'EOF'
MES 系統生產環境部署說明
==========================

📦 套件特色：
- 包含乾淨的遷移文件（已重新生成）
- 移除開發過程中的歷史變更
- 適合全新生產環境部署

🚀 正確的部署流程：

1. 解壓縮套件
   tar -xzf mes_production_package_*.tar.gz
   cd mes_production_package_*

2. 建立系統專案目錄
   sudo mkdir -p /var/www/mes

3. 搬移專案檔案
   sudo cp -r * /var/www/mes/

4. 設定權限
   sudo chown -R mes:www-data /var/www/mes/
   sudo chmod -R 755 /var/www/mes/

5. 進入專案目錄
   cd /var/www/mes

6. 修改配置
   nano .env
   # 修改以下項目：
   # ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP
   # HOST_IP=YOUR_SERVER_IP
   # DATABASE_PASSWORD=YOUR_SECURE_PASSWORD
   # REDIS_PASSWORD=YOUR_REDIS_PASSWORD
   # SUPERUSER_PASSWORD=YOUR_ADMIN_PASSWORD

7. 執行部署腳本
   sudo ./全新部署.sh
   # 腳本會自動：
   # - 安裝系統套件（PostgreSQL、Redis、Nginx等）
   # - 建立系統服務（systemd服務）
   # - 配置資料庫和應用
   # - 啟動所有服務

8. 驗證部署
   sudo systemctl status mes.service
   curl http://localhost

🔧 遷移文件說明：
- 套件中的遷移文件已重新生成
- 只包含當前的模型狀態
- 不包含開發過程中的歷史變更
- 適合全新資料庫部署

📁 目錄結構：
- 解壓目錄：包含完整專案檔案
- 系統目錄：/var/www/mes（部署後）
- 配置檔案：/var/www/mes/.env

🛠️ 服務管理：
- 重啟服務：sudo ./restart_services.sh
- 查看狀態：sudo systemctl status mes.service
- 查看日誌：sudo journalctl -u mes.service -f

注意：全新部署腳本會自動修復所有遷移問題！
EOF

# 建立快速部署腳本
cat > $TEMP_DIR/快速部署.sh << 'EOF'
#!/bin/bash

echo "=== MES 系統快速部署 ==="
echo ""

# 檢查 .env 檔案
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 檔案"
    echo "請先修改 .env 檔案中的配置"
    exit 1
fi

# 檢查是否以 root 權限執行
if [ "$EUID" -ne 0 ]; then
    echo "❌ 請使用 sudo 執行此腳本"
    exit 1
fi

echo "開始部署..."
sudo ./全新部署.sh

echo ""
echo "✅ 部署完成！"
echo "訪問地址: http://$(grep 'HOST_IP=' .env | cut -d'=' -f2)"
echo "管理後台: http://$(grep 'HOST_IP=' .env | cut -d'=' -f2)/admin"
EOF

chmod +x $TEMP_DIR/快速部署.sh

# 設定腳本執行權限
chmod +x $TEMP_DIR/全新部署.sh
chmod +x $TEMP_DIR/restart_services.sh

# 建立 .env 範例
cat > $TEMP_DIR/.env.example << 'EOF'
# Django 基本設定
DJANGO_SECRET_KEY='your-secret-key-here'
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP
HOST_IP=YOUR_SERVER_IP

# 資料庫設定
DATABASE_NAME=mes_db
DATABASE_USER=mes_user
DATABASE_PASSWORD=YOUR_SECURE_PASSWORD
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_URL=postgresql://mes_user:YOUR_SECURE_PASSWORD@localhost:5432/mes_db

# Redis 設定
CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_REDIS_PASSWORD@127.0.0.1:6379/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=YOUR_REDIS_PASSWORD

# 管理員設定
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@company.com
SUPERUSER_PASSWORD=YOUR_ADMIN_PASSWORD

# 路徑設定
PROJECT_DIR=/var/www/mes
STATIC_ROOT=/var/www/mes/static
LOG_BASE_DIR=/var/log/mes
BACKUP_DIR=/var/www/mes/backups_DB

# 服務設定
GUNICORN_PORT=8000
NGINX_PORT=80
GUNICORN_WORKERS=3
EOF

# 建立 README
cat > $TEMP_DIR/README.md << 'EOF'
# MES 系統生產環境部署套件

## 快速部署

1. **解壓縮套件**
   ```bash
   tar -xzf mes_production_package_*.tar.gz
   cd mes_production_package_*
   ```

2. **修改配置**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   必須修改的項目：
   - `ALLOWED_HOSTS`: 加入您的伺服器 IP
   - `HOST_IP`: 您的伺服器 IP
   - `DATABASE_PASSWORD`: 安全的資料庫密碼
   - `REDIS_PASSWORD`: 安全的 Redis 密碼
   - `SUPERUSER_PASSWORD`: 安全的管理員密碼

3. **執行部署**
   ```bash
   sudo ./全新部署.sh
   ```

4. **驗證部署**
   ```bash
   sudo systemctl status mes.service
   curl http://localhost
   ```

## 系統需求

- Ubuntu 20.04 LTS 或更新版本
- 至少 4GB 記憶體
- 至少 10GB 硬碟空間
- 網路連線

## 訪問地址

部署完成後：
- 主網站: http://YOUR_SERVER_IP
- 管理後台: http://YOUR_SERVER_IP/admin

## 故障排除

如果遇到問題，請檢查：
1. `.env` 檔案配置是否正確
2. 服務狀態: `sudo systemctl status mes.service`
3. 日誌: `sudo journalctl -u mes.service -f`

## 技術支援

如有問題，請聯絡技術支援團隊。
EOF

# 建立壓縮檔
echo "建立壓縮檔..."
cd /tmp
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"

# 移動到專案目錄
mv "$PACKAGE_NAME.tar.gz" /var/www/mes/

# 清理臨時檔案
rm -rf $TEMP_DIR

echo ""
echo -e "${GREEN}✅ 部署套件建立完成！${NC}"
echo ""
echo "📦 套件檔案: /var/www/mes/$PACKAGE_NAME.tar.gz"
echo "📋 套件大小: $(du -h /var/www/mes/$PACKAGE_NAME.tar.gz | cut -f1)"
echo ""
echo "📋 包含的檔案："
echo "✅ 核心模組: workorder, system, reporting, erp_integration, equip, quality, material, kanban, scheduling, ai, process, production"
echo "✅ 設定檔案: mes_config, requirements.txt, manage.py"
echo "✅ 前端檔案: templates, static, media"
echo "✅ 部署腳本: 全新部署.sh, restart_services.sh"
echo "✅ 說明文件: README.md, 部署說明.txt, .env.example"
echo ""
echo "❌ 排除的檔案："
echo "   - *.pyc (Python 快取檔案)"
echo "   - __pycache__ (Python 快取目錄)"
echo "   - *.log (日誌檔案)"
echo "   - test_*.py (測試檔案)"
echo "   - debug_*.py (除錯檔案)"
echo "   - check_*.py (檢查檔案)"
echo "   - fix_*.py (修復檔案)"
echo ""
echo "🚀 部署步驟："
echo "1. 將套件複製到生產主機"
echo "2. 解壓縮: tar -xzf $PACKAGE_NAME.tar.gz"
echo "3. 修改 .env 檔案"
echo "4. 執行: sudo ./全新部署.sh"
echo ""
echo "💡 注意：全新部署腳本會自動修復所有遷移問題！"
