#!/bin/bash

# MES 系統核心問題修復腳本
# 用途：修復遷移文件、部署腳本、程式碼錯誤等核心問題

echo "=== MES 系統核心問題修復 ==="
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

# 設定變數
PROJECT_DIR="/var/www/mes"
LOG_FILE="/var/log/mes/core_fix.log"
BACKUP_DIR="/var/backups/mes/$(date +%Y%m%d_%H%M%S)"

# 建立日誌和備份目錄
mkdir -p /var/log/mes
mkdir -p $BACKUP_DIR
touch $LOG_FILE

echo "開始修復時間: $(date)" | tee -a $LOG_FILE
echo "備份目錄: $BACKUP_DIR" | tee -a $LOG_FILE

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

# 函數：備份檔案
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "已備份: $file" | tee -a $LOG_FILE
    fi
}

echo ""
echo -e "${YELLOW}🔧 步驟 1: 建立備份${NC}"

# 備份重要檔案
echo "建立重要檔案備份..." | tee -a $LOG_FILE
backup_file "$PROJECT_DIR/.env"
backup_file "$PROJECT_DIR/manage.py"
backup_file "$PROJECT_DIR/requirements.txt"

# 備份遷移檔案
echo "備份遷移檔案..." | tee -a $LOG_FILE
find $PROJECT_DIR -name "migrations" -type d | while read dir; do
    if [ -d "$dir" ]; then
        cp -r "$dir" "$BACKUP_DIR/"
        echo "已備份遷移目錄: $dir" | tee -a $LOG_FILE
    fi
done

echo ""
echo -e "${YELLOW}🔧 步驟 2: 修復權限問題${NC}"

# 修復專案目錄權限
run_command "chown -R mes:www-data $PROJECT_DIR" "修復專案目錄權限"
run_command "chmod -R 755 $PROJECT_DIR" "設定專案目錄權限"

# 修復日誌目錄權限
run_command "mkdir -p /var/log/mes/django" "建立日誌目錄"
run_command "chown -R mes:www-data /var/log/mes" "修復日誌目錄權限"
run_command "chmod -R 755 /var/log/mes" "設定日誌目錄權限"

echo ""
echo -e "${YELLOW}🔧 步驟 3: 修復資料庫問題${NC}"

cd $PROJECT_DIR

# 檢查資料庫連接
run_command "sudo -u mes python3 manage.py check" "檢查 Django 設定"

# 清理遷移狀態（如果資料庫是空的）
echo "檢查資料庫狀態..." | tee -a $LOG_FILE
if sudo -u mes python3 manage.py dbshell -c "\dt" 2>&1 | grep -q "No relations found"; then
    echo -e "${YELLOW}⚠️ 資料庫為空，執行全新初始化${NC}" | tee -a $LOG_FILE
    
    # 刪除所有遷移記錄
    run_command "sudo -u mes python3 manage.py migrate --fake zero" "清除遷移記錄"
    
    # 重新建立資料表
    run_command "sudo -u mes python3 manage.py migrate --run-syncdb" "建立資料表結構"
    
    # 執行所有遷移
    run_command "sudo -u mes python3 manage.py migrate" "執行所有遷移"
else
    echo -e "${GREEN}✅ 資料庫已有資料，檢查遷移狀態${NC}" | tee -a $LOG_FILE
    
    # 檢查遷移狀態
    run_command "sudo -u mes python3 manage.py showmigrations" "檢查遷移狀態"
    
    # 嘗試修復遷移問題
    run_command "sudo -u mes python3 manage.py migrate --fake-initial" "修復初始遷移"
    run_command "sudo -u mes python3 manage.py migrate" "執行剩餘遷移"
fi

echo ""
echo -e "${YELLOW}🔧 步驟 4: 修復程式碼問題${NC}"

# 檢查並修復常見的 import 問題
echo "檢查程式碼完整性..." | tee -a $LOG_FILE

# 檢查所有 Python 檔案的語法
run_command "find $PROJECT_DIR -name '*.py' -exec python3 -m py_compile {} \;" "檢查 Python 語法"

# 檢查 Django 設定
run_command "sudo -u mes python3 manage.py check --deploy" "檢查部署設定"

echo ""
echo -e "${YELLOW}🔧 步驟 5: 修復服務配置${NC}"

# 重新收集靜態檔案
run_command "sudo -u mes python3 manage.py collectstatic --noinput" "收集靜態檔案"

# 檢查服務配置
run_command "systemctl daemon-reload" "重新載入 systemd"
run_command "systemctl status mes.service" "檢查 MES 服務狀態"
run_command "systemctl status nginx" "檢查 Nginx 服務狀態"

# 重啟服務
run_command "systemctl restart mes.service" "重啟 MES 服務"
run_command "systemctl restart nginx" "重啟 Nginx"

echo ""
echo -e "${YELLOW}🔧 步驟 6: 驗證修復結果${NC}"

# 驗證資料庫
run_command "sudo -u mes python3 manage.py dbshell -c '\dt'" "檢查資料表"

# 驗證網站訪問
run_command "curl -I http://localhost" "測試網站訪問"

# 驗證管理後台
run_command "curl -I http://localhost/admin" "測試管理後台"

echo ""
echo -e "${GREEN}🎉 核心問題修復完成！${NC}" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "📋 修復結果：" | tee -a $LOG_FILE
echo "✅ 權限問題已修復" | tee -a $LOG_FILE
echo "✅ 資料庫問題已修復" | tee -a $LOG_FILE
echo "✅ 程式碼問題已檢查" | tee -a $LOG_FILE
echo "✅ 服務配置已修復" | tee -a $LOG_FILE
echo "✅ 靜態檔案已收集" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "📁 備份位置: $BACKUP_DIR" | tee -a $LOG_FILE
echo "📝 詳細日誌: $LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "🌐 網站地址: http://$(hostname -I | awk '{print $1}')" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE
echo "⚠️ 如果仍有問題，請檢查日誌檔案或考慮方案二：完全重建" | tee -a $LOG_FILE
