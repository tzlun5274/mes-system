#!/bin/bash

# MES 系統服務重啟腳本
# 用途：重啟所有 MES 相關服務

echo "=== MES 系統服務重啟腳本 ==="

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
LOG_FILE="/var/log/mes/restart_services.log"

# 確保日誌檔案存在
touch $LOG_FILE

echo "開始重啟時間: $(date)" | tee -a $LOG_FILE

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

# 函數：強制停止服務
force_stop_service() {
    local service_name="$1"
    local desc="$2"
    
    echo -e "${YELLOW}🛑 強制停止 $desc...${NC}" | tee -a $LOG_FILE
    
    # 先嘗試正常停止
    systemctl stop $service_name 2>/dev/null
    
    # 等待 3 秒
    sleep 3
    
    # 檢查是否還在運行
    if systemctl is-active --quiet $service_name; then
        echo -e "${YELLOW}⚠️  $desc 仍在運行，強制終止...${NC}" | tee -a $LOG_FILE
        
        # 獲取服務的 PID
        local pids=$(systemctl show $service_name --property=MainPID --value 2>/dev/null | tr '\n' ' ')
        
        if [ ! -z "$pids" ]; then
            # 終止主進程
            for pid in $pids; do
                if [ "$pid" != "0" ] && [ "$pid" != "" ]; then
                    echo "終止進程 PID: $pid" | tee -a $LOG_FILE
                    kill -TERM $pid 2>/dev/null
                    sleep 2
                    
                    # 如果還在運行，強制殺死
                    if kill -0 $pid 2>/dev/null; then
                        echo "強制殺死進程 PID: $pid" | tee -a $LOG_FILE
                        kill -KILL $pid 2>/dev/null
                    fi
                fi
            done
        fi
        
        # 再次嘗試停止服務
        systemctl stop $service_name 2>/dev/null
        sleep 2
    fi
    
    # 最終檢查
    if systemctl is-active --quiet $service_name; then
        echo -e "${RED}❌ 無法停止 $desc${NC}" | tee -a $LOG_FILE
        return 1
    else
        echo -e "${GREEN}✅ $desc 已停止${NC}" | tee -a $LOG_FILE
        return 0
    fi
}

# 函數：強制清理端口
force_clear_port() {
    local port="$1"
    local desc="$2"
    
    echo -e "${YELLOW}🔍 檢查端口 $port 是否被佔用...${NC}" | tee -a $LOG_FILE
    
    if netstat -tlnp | grep -q ":$port "; then
        echo -e "${YELLOW}⚠️  發現端口 $port 被佔用，正在強制清理...${NC}" | tee -a $LOG_FILE
        
        # 獲取佔用端口的進程
        local pids=$(netstat -tlnp | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | tr '\n' ' ')
        
        for pid in $pids; do
            if [ ! -z "$pid" ] && [ "$pid" != "" ]; then
                echo "發現佔用端口的進程 PID: $pid" | tee -a $LOG_FILE
                ps aux | grep $pid | grep -v grep | tee -a $LOG_FILE
                
                # 終止進程
                echo "終止進程 PID: $pid" | tee -a $LOG_FILE
                kill -TERM $pid 2>/dev/null
                sleep 3
                
                # 檢查是否還在運行
                if kill -0 $pid 2>/dev/null; then
                    echo "強制殺死進程 PID: $pid" | tee -a $LOG_FILE
                    kill -KILL $pid 2>/dev/null
                    sleep 2
                fi
            fi
        done
        
        # 再次檢查端口
        if netstat -tlnp | grep -q ":$port "; then
            echo -e "${RED}❌ 無法清理端口 $port${NC}" | tee -a $LOG_FILE
            return 1
        else
            echo -e "${GREEN}✅ 端口 $port 已清理${NC}" | tee -a $LOG_FILE
            return 0
        fi
    else
        echo -e "${GREEN}✅ 端口 $port 未被佔用${NC}" | tee -a $LOG_FILE
        return 0
    fi
}

echo ""
echo -e "${YELLOW}🔧 步驟 0: 強制清理所有服務和端口${NC}"

# 強制清理端口 8000
force_clear_port "8000" "Gunicorn 端口"

# 強制停止所有服務
force_stop_service "gunicorn-mes_config" "Gunicorn 服務"
force_stop_service "celery-mes_config" "Celery Worker 服務"
force_stop_service "celerybeat-mes_config" "Celery Beat 服務"
force_stop_service "nginx" "Nginx 服務"

# 清理 Celery 相關進程
echo -e "${YELLOW}🧹 清理 Celery 相關進程...${NC}" | tee -a $LOG_FILE
pkill -f "celery" 2>/dev/null || true
pkill -f "gunicorn" 2>/dev/null || true
sleep 3

# 清理 Celery 檔案
echo -e "${YELLOW}🧹 清理 Celery 檔案...${NC}" | tee -a $LOG_FILE
rm -f /var/run/celery/*.pid 2>/dev/null || true
rm -f /var/log/celery/*.log 2>/dev/null || true

echo ""
echo -e "${YELLOW}🔧 步驟 1: 檢查資料庫遷移${NC}"

# 切換到專案目錄
cd $PROJECT_DIR

# 檢查是否有未完成的遷移
echo "檢查資料庫遷移狀態..." | tee -a $LOG_FILE
UNMIGRATED=$(python3 manage.py showmigrations | grep "\[ \]" | wc -l)

if [ "$UNMIGRATED" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  發現 $UNMIGRATED 個未完成的遷移，正在執行...${NC}" | tee -a $LOG_FILE
    run_command "python3 manage.py migrate" "執行資料庫遷移"
else
    echo -e "${GREEN}✅ 所有遷移已完成${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${YELLOW}🔧 步驟 2: 檢查服務狀態${NC}"

# 檢查服務狀態
echo "檢查服務狀態..." | tee -a $LOG_FILE
systemctl status gunicorn-mes_config --no-pager | tee -a $LOG_FILE
systemctl status celery-mes_config --no-pager | tee -a $LOG_FILE
systemctl status celerybeat-mes_config --no-pager | tee -a $LOG_FILE
systemctl status nginx --no-pager | tee -a $LOG_FILE

echo ""
echo -e "${YELLOW}🔧 步驟 3: 重新啟動所有服務${NC}"

# 重新啟動所有服務
run_command "systemctl start gunicorn-mes_config" "啟動 Gunicorn 服務"
run_command "systemctl start celery-mes_config" "啟動 Celery Worker 服務"
run_command "systemctl start celerybeat-mes_config" "啟動 Celery Beat 服務"
run_command "systemctl start nginx" "啟動 Nginx 服務"

echo ""
echo -e "${YELLOW}🔧 步驟 4: 等待服務啟動${NC}"

# 等待服務啟動
sleep 15

echo ""
echo -e "${YELLOW}🔧 步驟 5: 驗證服務狀態${NC}"

# 檢查所有服務狀態
echo "檢查所有服務狀態..." | tee -a $LOG_FILE

# 檢查 Gunicorn 服務
if systemctl is-active --quiet gunicorn-mes_config; then
    echo -e "${GREEN}✅ Gunicorn 服務運行正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ Gunicorn 服務啟動失敗${NC}" | tee -a $LOG_FILE
    systemctl status gunicorn-mes_config --no-pager | tee -a $LOG_FILE
fi

# 檢查 Celery Worker 服務
if systemctl is-active --quiet celery-mes_config; then
    echo -e "${GREEN}✅ Celery Worker 服務運行正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ Celery Worker 服務啟動失敗${NC}" | tee -a $LOG_FILE
    systemctl status celery-mes_config --no-pager | tee -a $LOG_FILE
fi

# 檢查 Celery Beat 服務
if systemctl is-active --quiet celerybeat-mes_config; then
    echo -e "${GREEN}✅ Celery Beat 服務運行正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ Celery Beat 服務啟動失敗${NC}" | tee -a $LOG_FILE
    systemctl status celerybeat-mes_config --no-pager | tee -a $LOG_FILE
fi

# 檢查 Nginx 服務
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx 服務運行正常${NC}" | tee -a $LOG_FILE
else
    echo -e "${RED}❌ Nginx 服務啟動失敗${NC}" | tee -a $LOG_FILE
    systemctl status nginx --no-pager | tee -a $LOG_FILE
fi

echo ""
echo -e "${YELLOW}🔧 步驟 6: 測試系統連線${NC}"

# 測試網站連線
echo "測試網站連線..." | tee -a $LOG_FILE
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ 網站連線測試成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  網站連線測試失敗，請檢查服務狀態${NC}" | tee -a $LOG_FILE
fi

# 測試登入頁面
echo "測試登入頁面..." | tee -a $LOG_FILE
if curl -s -o /dev/null -w "%{http_code}" http://localhost/accounts/login/ | grep -q "200"; then
    echo -e "${GREEN}✅ 登入頁面測試成功${NC}" | tee -a $LOG_FILE
else
    echo -e "${YELLOW}⚠️  登入頁面測試失敗，請檢查服務狀態${NC}" | tee -a $LOG_FILE
fi

echo ""
echo -e "${GREEN}🎉 系統服務重啟完成！${NC}" | tee -a $LOG_FILE
echo "重啟完成時間: $(date)" | tee -a $LOG_FILE
echo "詳細日誌請查看: $LOG_FILE" | tee -a $LOG_FILE

echo ""
echo -e "${BLUE}📋 服務管理指令：${NC}"
echo "查看 Gunicorn 狀態: sudo systemctl status gunicorn-mes_config"
echo "查看 Celery Worker 狀態: sudo systemctl status celery-mes_config"
echo "查看 Celery Beat 狀態: sudo systemctl status celerybeat-mes_config"
echo "查看 Nginx 狀態: sudo systemctl status nginx"
echo "查看 Gunicorn 日誌: sudo journalctl -u gunicorn-mes_config -f"
echo "查看 Celery 日誌: sudo journalctl -u celery-mes_config -f"
echo "重啟服務: sudo ./重啟服務.sh"