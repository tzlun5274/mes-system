#!/bin/bash
# MES 系統專案更新腳本
# 用途：更新專案內容、執行資料庫遷移、重啟服務

echo "=== MES 系統專案更新 ==="
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

# 檢查專案是否存在
if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ 未找到 MES 系統目錄: $PROJECT_PATH"
    echo "請先執行 全新部署.sh 部署專案"
    exit 1
fi

echo "=== 專案更新配置 ==="
echo "專案路徑: $PROJECT_PATH"
echo "服務名稱: $SERVICE_NAME"
echo ""
echo "📋 此腳本將執行："
echo "✅ 備份當前專案"
echo "✅ 複製新專案檔案"
echo "✅ 安裝 Python 依賴"
echo "✅ 執行資料庫遷移"
echo "✅ 收集靜態檔案"
echo "✅ 重啟服務"
echo ""

# 確認更新
read -p "確認更新專案內容？(y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "❌ 更新已取消"
    exit 1
fi

echo ""
echo "1. 停止服務..."
systemctl stop $SERVICE_NAME.service
systemctl stop $CELERY_SERVICE_NAME.service
systemctl stop celery-beat.service

echo "✅ 服務已停止"

echo ""
echo "2. 備份當前版本..."
BACKUP_DIR="/var/backups/mes"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz -C $PROJECT_PATH .

echo "✅ 備份完成: $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz"

echo ""
echo "3. 複製新專案檔案..."
CURRENT_DIR=$(pwd)
cp -r $CURRENT_DIR/* $PROJECT_PATH/
chown -R mes:www-data $PROJECT_PATH
chmod +x $PROJECT_PATH/manage.py

echo "✅ 專案檔案複製完成"

echo ""
echo "4. 安裝 Python 依賴..."
cd $PROJECT_PATH
pip3 install -r requirements.txt

echo "✅ Python 依賴安裝完成"

echo ""
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

echo "✅ 資料庫遷移完成"

echo ""
echo "6. 收集靜態檔案..."
python3 manage.py collectstatic --noinput

echo "✅ 靜態檔案收集完成"

echo ""
echo "7. 重新載入系統服務..."
systemctl daemon-reload

echo "✅ 系統服務重新載入完成"

echo ""
echo "8. 啟動服務..."
systemctl start $SERVICE_NAME.service
systemctl start $CELERY_SERVICE_NAME.service
systemctl start celery-beat.service

echo "✅ 服務已啟動"

echo ""
echo "9. 驗證更新..."
sleep 3

# 檢查服務狀態
echo "檢查服務狀態..."
systemctl status $SERVICE_NAME.service --no-pager
systemctl status $CELERY_SERVICE_NAME.service --no-pager
systemctl status celery-beat.service --no-pager

echo ""
echo "🎉 專案更新完成！"
echo ""
echo "📋 更新資訊："
echo "備份位置: $BACKUP_DIR/mes_backup_${TIMESTAMP}.tar.gz"
echo "專案路徑: $PROJECT_PATH"
echo "更新時間: $(date)"
echo ""
echo "💡 如需回滾，請使用備份檔案恢復"
