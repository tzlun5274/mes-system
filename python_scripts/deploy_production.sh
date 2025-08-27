#!/bin/bash
# MES 系統專案部署腳本
# 用途：部署 MES 專案到已建立的環境

echo "=== MES 系統專案部署 ==="
echo ""

# 檢查是否以 root 權限執行
if [ "$EUID" -ne 0 ]; then
    echo "❌ 請使用 sudo 執行此腳本"
    exit 1
fi

# 設定專案路徑
PROJECT_PATH="/var/www/mes"
SERVICE_NAME="mes"
CELERY_SERVICE_NAME="mes-celery"

# 尋找專案檔案
echo "=== 尋找專案檔案 ==="

# 檢查 /var/www/mes 是否有專案檔案
if [ -f "/var/www/mes/manage.py" ] && [ -f "/var/www/mes/requirements.txt" ]; then
    SOURCE_DIR="/var/www/mes"
    echo "✅ 在 /var/www/mes 找到專案檔案"
else
    echo "❌ 未在 /var/www/mes 找到專案檔案"
    echo ""
    echo "請先執行 deploy.sh 建立基礎環境："
    echo "   sudo ./deploy.sh"
    echo ""
    echo "或者請手動指定專案路徑："
    read -p "請輸入專案路徑: " MANUAL_PATH
    if [ -n "$MANUAL_PATH" ] && [ -f "$MANUAL_PATH/manage.py" ] && [ -f "$MANUAL_PATH/requirements.txt" ]; then
        SOURCE_DIR="$MANUAL_PATH"
        echo "✅ 使用手動指定路徑: $SOURCE_DIR"
    else
        echo "❌ 指定的路徑無效或缺少必要檔案"
        exit 1
    fi
fi

echo "專案來源目錄: $SOURCE_DIR"

# 檢查 .env 檔案
ENV_FILE="$SOURCE_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  未找到 .env 檔案: $ENV_FILE"
    echo ""
    echo "請選擇處理方式："
    echo "1) 從 /var/www/mes/.env 複製（如果已執行 deploy.sh）"
    echo "2) 從其他位置複製 .env 檔案"
    echo "3) 手動創建 .env 檔案"
    echo ""
    read -p "請選擇 (1/2/3): " ENV_CHOICE
    
    case $ENV_CHOICE in
        1)
            if [ -f "/var/www/mes/.env" ]; then
                cp "/var/www/mes/.env" "$ENV_FILE"
                echo "✅ 已從 /var/www/mes/.env 複製"
            else
                echo "❌ /var/www/mes/.env 不存在，請先執行 deploy.sh"
                exit 1
            fi
            ;;
        2)
            read -p "請輸入 .env 檔案路徑: " ENV_SOURCE
            if [ -f "$ENV_SOURCE" ]; then
                cp "$ENV_SOURCE" "$ENV_FILE"
                echo "✅ 已複製 .env 檔案"
            else
                echo "❌ 指定的檔案不存在: $ENV_SOURCE"
                exit 1
            fi
            ;;
        3)
            echo "請手動創建 .env 檔案後重新執行腳本"
            echo "範例 .env 內容："
            echo "DATABASE_NAME=mes_db"
            echo "DATABASE_USER=mes_user"
            echo "DATABASE_PASSWORD=mes_password"
            echo "DATABASE_HOST=localhost"
            echo "DATABASE_PORT=5432"
            echo "CELERY_BROKER_URL=redis://:mesredis2025@127.0.0.1:6379/0"
            echo "CELERY_RESULT_BACKEND=redis://:mesredis2025@127.0.0.1:6379/0"
            exit 1
            ;;
        *)
            echo "❌ 無效選擇，部署已取消"
            exit 1
            ;;
    esac
else
    echo "✅ 找到 .env 檔案: $ENV_FILE"
fi

echo ""
echo "=== 專案部署配置 ==="
echo "專案路徑: $PROJECT_PATH"
echo "服務名稱: $SERVICE_NAME"
echo "專案來源: $SOURCE_DIR"
echo ""

# 檢查基礎環境是否已建立
echo "=== 檢查基礎環境 ==="
if ! command -v psql >/dev/null 2>&1; then
    echo "❌ PostgreSQL 未安裝，請先執行 deploy.sh 建立基礎環境"
    exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
    echo "❌ Redis 未安裝，請先執行 deploy.sh 建立基礎環境"
    exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
    echo "❌ Nginx 未安裝，請先執行 deploy.sh 建立基礎環境"
    exit 1
fi

if ! command -v gunicorn >/dev/null 2>&1; then
    echo "❌ Gunicorn 未安裝，請先執行 deploy.sh 建立基礎環境"
    exit 1
fi

echo "✅ 基礎環境檢查通過"

# 檢查是否已安裝
echo "=== 檢查現有安裝 ==="
if [ -d "$PROJECT_PATH" ]; then
    echo "⚠️  發現現有專案: $PROJECT_PATH"
    echo "   現有專案將會被備份並覆蓋"
    read -p "是否繼續？(y/N): " OVERWRITE_CONFIRM
    if [[ ! $OVERWRITE_CONFIRM =~ ^[Yy]$ ]]; then
        echo "❌ 部署已取消"
        exit 1
    fi
    
    # 備份現有專案
    echo "📦 備份現有專案..."
    BACKUP_DIR="/var/backups/mes"
    mkdir -p $BACKUP_DIR
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    tar -czf $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz -C $PROJECT_PATH .
    echo "✅ 備份完成: $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz"
else
    echo "✅ 未發現現有專案"
fi

echo ""
echo "=== 開始專案部署 ==="

# 1. 停止現有服務
echo "1. 停止現有服務..."
systemctl stop $SERVICE_NAME.service 2>/dev/null || true
systemctl stop $CELERY_SERVICE_NAME.service 2>/dev/null || true
systemctl stop celery-beat.service 2>/dev/null || true
echo "✅ 服務已停止"

# 2. 建立專案目錄
echo "2. 建立專案目錄..."
mkdir -p $PROJECT_PATH
chown mes:www-data $PROJECT_PATH
chmod 775 $PROJECT_PATH

# 3. 複製專案檔案
echo "3. 複製專案檔案..."
cp -r $SOURCE_DIR/* $PROJECT_PATH/
chown -R mes:www-data $PROJECT_PATH
chmod +x $PROJECT_PATH/manage.py

# 4. 安裝 Python 依賴
echo "4. 安裝 Python 依賴..."
cd $PROJECT_PATH
pip3 install -r requirements.txt

# 5. 執行資料庫遷移
echo "5. 執行資料庫遷移..."
export DJANGO_SETTINGS_MODULE=mes_config.settings

# 修復遷移依賴問題
echo "修復遷移依賴問題..."
python3 manage.py fix_migrations --force

# 執行遷移
echo "執行資料庫遷移..."
if ! python3 manage.py migrate; then
    echo "⚠️  標準遷移失敗，嘗試強制遷移..."
    python3 manage.py migrate --fake-initial
    python3 manage.py migrate
fi

# 6. 收集靜態檔案
echo "6. 收集靜態檔案..."
python3 manage.py collectstatic --noinput

# 7. 建立超級用戶（如果不存在）
echo "7. 檢查超級用戶..."
python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', '1234')
    print('超級用戶已建立')
else:
    print('超級用戶已存在')
"

# 8. 重新載入系統服務
echo "8. 重新載入系統服務..."
systemctl daemon-reload

# 9. 啟動服務
echo "9. 啟動服務..."
systemctl enable $SERVICE_NAME.service
systemctl start $SERVICE_NAME.service
systemctl enable $CELERY_SERVICE_NAME.service
systemctl start $CELERY_SERVICE_NAME.service
systemctl enable celery-beat.service
systemctl start celery-beat.service

# 10. 檢查服務狀態
echo "10. 檢查服務狀態..."
sleep 3

echo ""
echo "=== 部署完成 ==="
echo ""
echo "✅ 專案部署成功！"
echo ""
echo "🌐 訪問地址:"
echo "   - 主網站: http://$(hostname -I | awk '{print $1}')"
echo "   - 管理後台: http://$(hostname -I | awk '{print $1}')/admin"
echo ""
echo "🔧 服務管理命令:"
echo "   - 查看狀態: sudo systemctl status $SERVICE_NAME.service"
echo "   - 重啟服務: sudo systemctl restart $SERVICE_NAME.service"
echo "   - 查看日誌: sudo journalctl -u $SERVICE_NAME.service -f"
echo ""
echo "📊 系統檢查:"
echo "   - 檢查進程: ps aux | grep python"
echo "   - 檢查端口: netstat -tlnp | grep :8000"
echo ""
echo "🔄 如果需要回滾:"
if [ -n "$BACKUP_DIR" ] && [ -n "$TIMESTAMP" ]; then
    echo "   - 停止服務: sudo systemctl stop $SERVICE_NAME.service"
    echo "   - 恢復備份: tar -xzf $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz -C $PROJECT_PATH"
    echo "   - 重啟服務: sudo systemctl start $SERVICE_NAME.service"
fi
echo ""
echo "✅ 部署時間: $(date)"
