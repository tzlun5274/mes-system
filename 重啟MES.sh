#!/bin/bash

# MES 系統重啟腳本
# 檢查進程 -> 殺掉進程 -> 確認清理 -> 重新啟動

echo "=========================================="
echo "    MES 系統重啟腳本"
echo "=========================================="

# 設定顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 進入 MES 專案目錄
cd /var/www/mes
echo -e "${GREEN}✓ 進入 MES 專案目錄: $(pwd)${NC}"

# 函數：檢查進程
check_processes() {
    echo -e "\n${BLUE}🔍 檢查相關進程...${NC}"
    
    # 檢查 Django 開發伺服器
    DJANGO_PROCESSES=$(ps aux | grep -E "(python.*manage.py runserver|gunicorn)" | grep -v grep)
    CELERY_PROCESSES=$(ps aux | grep -E "(celery.*worker|celery.*beat)" | grep -v grep)
    
    if [ -n "$DJANGO_PROCESSES" ] || [ -n "$CELERY_PROCESSES" ]; then
        echo -e "${YELLOW}發現相關進程:${NC}"
        [ -n "$DJANGO_PROCESSES" ] && echo "Django 進程:" && echo "$DJANGO_PROCESSES"
        [ -n "$CELERY_PROCESSES" ] && echo "Celery 進程:" && echo "$CELERY_PROCESSES"
        return 1
    else
        echo -e "${GREEN}✓ 沒有發現相關進程${NC}"
        return 0
    fi
}

# 函數：殺掉進程
kill_processes() {
    echo -e "\n${YELLOW}🗡️  正在殺掉相關進程...${NC}"
    
    # 殺掉 Django 進程
    echo "殺掉 Django 進程..."
    pkill -f "manage.py runserver" 2>/dev/null
    pkill -f "gunicorn" 2>/dev/null
    
    # 殺掉 Celery 進程
    echo "殺掉 Celery 進程..."
    pkill -f "celery.*worker" 2>/dev/null
    pkill -f "celery.*beat" 2>/dev/null
    
    # 等待進程完全結束
    sleep 3
    
    # 強制殺掉頑固進程
    echo "強制殺掉頑固進程..."
    pkill -9 -f "manage.py runserver" 2>/dev/null
    pkill -9 -f "gunicorn" 2>/dev/null
    pkill -9 -f "celery.*worker" 2>/dev/null
    pkill -9 -f "celery.*beat" 2>/dev/null
    
    # 再次等待
    sleep 2
    echo -e "${GREEN}✓ 進程清理完成${NC}"
}

# 函數：確認清理
confirm_cleanup() {
    echo -e "\n${BLUE}🧹 確認進程清理狀態...${NC}"
    
    # 檢查是否還有進程殘留
    REMAINING_DJANGO=$(ps aux | grep -E "(python.*manage.py runserver|gunicorn)" | grep -v grep)
    REMAINING_CELERY=$(ps aux | grep -E "(celery.*worker|celery.*beat)" | grep -v grep)
    
    if [ -n "$REMAINING_DJANGO" ] || [ -n "$REMAINING_CELERY" ]; then
        echo -e "${RED}✗ 仍有進程殘留:${NC}"
        [ -n "$REMAINING_DJANGO" ] && echo "Django 進程:" && echo "$REMAINING_DJANGO"
        [ -n "$REMAINING_CELERY" ] && echo "Celery 進程:" && echo "$REMAINING_CELERY"
        echo -e "${YELLOW}嘗試最後一次強制清理...${NC}"
        pkill -9 -f "python.*manage.py runserver" 2>/dev/null
        pkill -9 -f "gunicorn" 2>/dev/null
        pkill -9 -f "celery.*worker" 2>/dev/null
        pkill -9 -f "celery.*beat" 2>/dev/null
        sleep 2
        
        # 最終檢查
        FINAL_DJANGO=$(ps aux | grep -E "(python.*manage.py runserver|gunicorn)" | grep -v grep)
        FINAL_CELERY=$(ps aux | grep -E "(celery.*worker|celery.*beat)" | grep -v grep)
        if [ -n "$FINAL_DJANGO" ] || [ -n "$FINAL_CELERY" ]; then
            echo -e "${RED}✗ 無法完全清理進程，請手動檢查${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}✓ 進程清理確認完成${NC}"
    return 0
}

# 函數：檢查端口
check_ports() {
    echo -e "\n${BLUE}🔌 檢查端口占用...${NC}"
    
    # 檢查 8000 端口
    PORT_8000=$(netstat -tlnp 2>/dev/null | grep :8000 || ss -tlnp 2>/dev/null | grep :8000)
    if [ -n "$PORT_8000" ]; then
        echo -e "${YELLOW}發現 8000 端口被占用:${NC}"
        echo "$PORT_8000"
        return 1
    else
        echo -e "${GREEN}✓ 8000 端口未被占用${NC}"
        return 0
    fi
}

# 函數：資料庫遷移
database_migration() {
    echo -e "\n${BLUE}🗄️  執行資料庫遷移...${NC}"
    
    # 檢查 Python 環境
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
    else
        echo -e "${RED}✗ 找不到 Python3${NC}"
        return 1
    fi
    
    # 檢查資料庫連接
    echo "檢查資料庫連接..."
    if $PYTHON_CMD manage.py check --database default 2>/dev/null; then
        echo -e "${GREEN}✓ 資料庫連接正常${NC}"
    else
        echo -e "${RED}✗ 資料庫連接失敗${NC}"
        echo "請檢查 PostgreSQL 服務是否運行"
        return 1
    fi
    
    # 自動產生遷移檔案
    echo "自動產生遷移檔案..."
    if $PYTHON_CMD manage.py makemigrations --noinput 2>/dev/null; then
        echo -e "${GREEN}✓ 遷移檔案產生成功${NC}"
    else
        echo -e "${YELLOW}⚠ 沒有新的遷移檔案需要產生${NC}"
    fi
    
    # 檢查是否有待執行的遷移
    echo "檢查遷移狀態..."
    PENDING_MIGRATIONS=$($PYTHON_CMD manage.py showmigrations --list | grep -E "\[ \]" | wc -l)
    
    if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
        echo -e "${YELLOW}發現 $PENDING_MIGRATIONS 個待執行的遷移${NC}"
        
        # 顯示待執行的遷移
        echo "待執行的遷移:"
        $PYTHON_CMD manage.py showmigrations --list | grep -E "\[ \]" || true
        
        # 執行遷移
        echo "執行資料庫遷移..."
        if $PYTHON_CMD manage.py migrate 2>/dev/null; then
            echo -e "${GREEN}✓ 資料庫遷移成功${NC}"
        else
            echo -e "${RED}✗ 資料庫遷移失敗${NC}"
            echo "嘗試執行特定應用的遷移..."
            
            # 嘗試執行各個應用的遷移
            for app in workorder scheduling quality equip material process erp_integration ai kanban reporting; do
                echo "執行 $app 應用遷移..."
                $PYTHON_CMD manage.py migrate $app 2>/dev/null && echo -e "${GREEN}✓ $app 遷移成功${NC}" || echo -e "${YELLOW}⚠ $app 遷移跳過${NC}"
            done
        fi
    else
        echo -e "${GREEN}✓ 沒有待執行的遷移${NC}"
    fi
    
    # 檢查遷移後狀態
    echo "檢查遷移後狀態..."
    FINAL_PENDING=$($PYTHON_CMD manage.py showmigrations --list | grep -E "\[ \]" | wc -l)
    if [ "$FINAL_PENDING" -eq 0 ]; then
        echo -e "${GREEN}✓ 所有遷移已完成${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ 仍有 $FINAL_PENDING 個遷移未完成${NC}"
        return 1
    fi
}

# 函數：檢查系統服務
check_system_services() {
    echo -e "\n${BLUE}🔧 檢查系統服務...${NC}"
    
    # 檢查 PostgreSQL
    if sudo systemctl is-active --quiet postgresql; then
        echo -e "${GREEN}✓ PostgreSQL 服務運行中${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL 服務未運行，嘗試啟動...${NC}"
        if sudo systemctl start postgresql 2>/dev/null; then
            echo -e "${GREEN}✓ PostgreSQL 服務啟動成功${NC}"
        else
            echo -e "${RED}✗ PostgreSQL 服務啟動失敗${NC}"
            return 1
        fi
    fi
    
    # 檢查 Redis
    echo -e "\n${BLUE}檢查 Redis 服務...${NC}"
    
    # 檢查 Redis 是否已安裝
    if ! command -v redis-server &> /dev/null; then
        echo -e "${YELLOW}⚠ Redis 未安裝，嘗試安裝...${NC}"
        if sudo apt update && sudo apt install -y redis-server 2>/dev/null; then
            echo -e "${GREEN}✓ Redis 安裝成功${NC}"
        else
            echo -e "${RED}✗ Redis 安裝失敗${NC}"
            echo -e "${YELLOW}⚠ 繼續執行，但某些功能可能受限${NC}"
        fi
    fi
    
    # 嘗試啟動 Redis
    if command -v redis-server &> /dev/null; then
        # 檢查 Redis 服務狀態
        if sudo systemctl is-active --quiet redis-server 2>/dev/null || sudo systemctl is-active --quiet redis 2>/dev/null; then
            echo -e "${GREEN}✓ Redis 服務運行中${NC}"
        else
            echo -e "${YELLOW}⚠ Redis 服務未運行，嘗試啟動...${NC}"
            
            # 嘗試啟動 redis-server
            if sudo systemctl start redis-server 2>/dev/null; then
                echo -e "${GREEN}✓ Redis 服務啟動成功${NC}"
            elif sudo systemctl start redis 2>/dev/null; then
                echo -e "${GREEN}✓ Redis 服務啟動成功${NC}"
            else
                echo -e "${YELLOW}⚠ 系統服務啟動失敗，嘗試手動啟動...${NC}"
                
                # 檢查是否有 Redis 進程在運行
                if pgrep redis-server > /dev/null; then
                    echo -e "${GREEN}✓ Redis 進程已在運行${NC}"
                else
                    # 嘗試手動啟動 Redis（需要 sudo）
                    if sudo redis-server --daemonize yes 2>/dev/null; then
                        echo -e "${GREEN}✓ Redis 手動啟動成功${NC}"
                        sleep 2
                    else
                        echo -e "${RED}✗ Redis 啟動失敗${NC}"
                        echo -e "${YELLOW}⚠ 請手動檢查 Redis 配置${NC}"
                        echo -e "${YELLOW}  檢查命令: sudo journalctl -u redis-server -n 20${NC}"
                        echo -e "${YELLOW}  手動啟動: sudo systemctl start redis-server${NC}"
                    fi
                fi
            fi
        fi
        
        # 測試 Redis 連接
        if command -v redis-cli &> /dev/null; then
            if redis-cli ping 2>/dev/null | grep -q "PONG"; then
                echo -e "${GREEN}✓ Redis 連接正常${NC}"
            elif redis-cli -a mesredis2025 ping 2>/dev/null | grep -q "PONG"; then
                echo -e "${GREEN}✓ Redis 連接正常（使用密碼）${NC}"
            else
                echo -e "${YELLOW}⚠ Redis 連接測試失敗${NC}"
                echo -e "${YELLOW}  請檢查 Redis 是否正在運行: sudo systemctl status redis-server${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ Redis 未安裝或無法找到${NC}"
        echo -e "${YELLOW}  安裝命令: sudo apt install redis-server${NC}"
    fi
    
    return 0
}

# 函數：啟動服務
start_services() {
    echo -e "\n${YELLOW}🚀 啟動 MES 服務...${NC}"
    
    # 檢查 Python 環境
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
    else
        echo -e "${RED}✗ 找不到 Python3${NC}"
        return 1
    fi
    
    echo -e "${GREEN}使用 Python: $($PYTHON_CMD --version)${NC}"
    
    # 檢查系統服務
    if ! check_system_services; then
        echo -e "${RED}✗ 系統服務檢查失敗${NC}"
        return 1
    fi
    
    # 執行資料庫遷移
    if ! database_migration; then
        echo -e "${YELLOW}⚠ 資料庫遷移有問題，但繼續啟動服務${NC}"
    fi
    
    # 檢查 Django 設定
    echo "檢查 Django 設定..."
    if $PYTHON_CMD manage.py check 2>/dev/null; then
        echo -e "${GREEN}✓ Django 設定正確${NC}"
    else
        echo -e "${RED}✗ Django 設定有問題${NC}"
        echo "嘗試執行資料庫遷移..."
        $PYTHON_CMD manage.py migrate 2>/dev/null
    fi
    
    # 啟動 Celery Worker
    echo "啟動 Celery Worker..."
    nohup $PYTHON_CMD -m celery -A mes_config worker --loglevel=info > celery_worker.log 2>&1 &
    sleep 3
    
    # 啟動 Celery Beat (定時任務排程器)
    echo "啟動 Celery Beat (定時任務排程器)..."
    nohup $PYTHON_CMD -m celery -A mes_config beat --loglevel=info > celery_beat.log 2>&1 &
    sleep 3
    
    # 啟動 Django 開發伺服器
    echo "啟動 Django 開發伺服器..."
    nohup $PYTHON_CMD manage.py runserver 0.0.0.0:8000 > nohup.out 2>&1 &
    
    # 等待伺服器啟動
    echo "等待伺服器啟動..."
    sleep 5
    
    # 檢查所有服務是否正常啟動
    echo "檢查服務狀態..."
    
    # 檢查 Celery Worker
    if pgrep -f "celery.*worker" > /dev/null; then
        echo -e "${GREEN}✓ Celery Worker 啟動成功${NC}"
    else
        echo -e "${RED}✗ Celery Worker 啟動失敗${NC}"
    fi
    
    # 檢查 Celery Beat
    if pgrep -f "celery.*beat" > /dev/null; then
        echo -e "${GREEN}✓ Celery Beat 啟動成功${NC}"
    else
        echo -e "${RED}✗ Celery Beat 啟動失敗${NC}"
    fi
    
    # 檢查 Django 伺服器
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Django 伺服器啟動成功${NC}"
        echo -e "${GREEN}✓ MES 系統啟動成功！${NC}"
        return 0
    else
        echo -e "${RED}✗ Django 伺服器啟動失敗${NC}"
        echo "檢查錯誤日誌..."
        tail -10 nohup.out
        return 1
    fi
}

# 函數：顯示狀態
show_status() {
    echo -e "\n${BLUE}📊 系統狀態報告${NC}"
    
    # 顯示進程
    echo -e "\n${YELLOW}當前 Django 進程:${NC}"
    ps aux | grep -E "(python.*manage.py runserver|gunicorn)" | grep -v grep || echo "沒有發現 Django 進程"
    
    echo -e "\n${YELLOW}當前 Celery 進程:${NC}"
    ps aux | grep -E "(celery.*worker|celery.*beat)" | grep -v grep || echo "沒有發現 Celery 進程"
    
    # 顯示端口
    echo -e "\n${YELLOW}端口占用情況:${NC}"
    netstat -tlnp 2>/dev/null | grep :8000 || ss -tlnp 2>/dev/null | grep :8000 || echo "8000 端口未被占用"
    
    # 顯示系統服務狀態
    echo -e "\n${YELLOW}系統服務狀態:${NC}"
    if sudo systemctl is-active --quiet postgresql; then
        echo -e "${GREEN}✓ PostgreSQL: 運行中${NC}"
    else
        echo -e "${RED}✗ PostgreSQL: 未運行${NC}"
    fi
    
    if command -v redis-server &> /dev/null; then
        if sudo systemctl is-active --quiet redis-server 2>/dev/null || sudo systemctl is-active --quiet redis 2>/dev/null; then
            echo -e "${GREEN}✓ Redis: 運行中${NC}"
        else
            echo -e "${RED}✗ Redis: 未運行${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Redis: 未安裝${NC}"
    fi
    
    # 顯示資料庫遷移狀態
    echo -e "\n${YELLOW}資料庫遷移狀態:${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
    else
        echo -e "${RED}✗ Python: 未找到${NC}"
        return
    fi
    
    # 檢查遷移狀態
    PENDING_COUNT=$($PYTHON_CMD manage.py showmigrations --list 2>/dev/null | grep -E "\[ \]" | wc -l)
    if [ "$PENDING_COUNT" -eq 0 ]; then
        echo -e "${GREEN}✓ 所有遷移已完成${NC}"
    else
        echo -e "${YELLOW}⚠ 有 $PENDING_COUNT 個待執行的遷移${NC}"
        echo "待執行的遷移:"
        $PYTHON_CMD manage.py showmigrations --list 2>/dev/null | grep -E "\[ \]" | head -5 || true
        if [ "$PENDING_COUNT" -gt 5 ]; then
            echo "... 還有 $((PENDING_COUNT - 5)) 個遷移"
        fi
    fi
    
    # 顯示系統資源
    echo -e "\n${YELLOW}系統資源使用:${NC}"
    echo "記憶體使用:"
    free -h | head -2
    echo -e "\n磁碟使用:"
    df -h /var/www | head -2
    
    # 顯示最近錯誤日誌
    echo -e "\n${YELLOW}最近錯誤日誌 (最後 5 行):${NC}"
    if [ -f "nohup.out" ]; then
        tail -5 nohup.out | grep -i error || echo "沒有發現錯誤"
    else
        echo "沒有錯誤日誌檔案"
    fi
}

# 主程序
main() {
    echo -e "${BLUE}開始執行 MES 系統重啟流程...${NC}"
    # 步驟 1: 檢查進程
    if check_processes; then
        echo -e "${GREEN}✓ 沒有需要清理的進程${NC}"
    else
        # 步驟 2: 殺掉進程
        kill_processes
        # 步驟 3: 確認清理
        if ! confirm_cleanup; then
            echo -e "${RED}✗ 進程清理失敗，停止重啟${NC}"
            exit 1
        fi
    fi
    # 最終確認沒有 runserver 進程
    echo "最終確認沒有 runserver 0.0.0.0:8000 進程..."
    ps aux | grep "manage.py runserver 0.0.0.0:8000" | grep -v grep && pkill -9 -f "manage.py runserver 0.0.0.0:8000" 2>/dev/null
    sleep 2
    ps aux | grep "manage.py runserver 0.0.0.0:8000" | grep -v grep || echo "沒有 runserver 0.0.0.0:8000 進程"
    # 步驟 4: 檢查端口
    if ! check_ports; then
        echo -e "${RED}✗ 端口被占用，停止重啟${NC}"
        exit 1
    fi
    # 步驟 5: 啟動服務
    if start_services; then
        echo -e "\n${GREEN}=========================================="
        echo "    MES 系統重啟成功！"
        echo "==========================================${NC}"
        echo -e "${GREEN}✓ 可以通過以下網址訪問：${NC}"
        echo -e "${GREEN}  本地: http://localhost:8000${NC}"
        echo -e "${GREEN}  網路: http://192.168.1.21:8000${NC}"
    else
        echo -e "\n${RED}=========================================="
        echo "    MES 系統重啟失敗！"
        echo "==========================================${NC}"
        echo -e "${YELLOW}請檢查錯誤日誌: tail -f nohup.out${NC}"
        exit 1
    fi
    # 步驟 6: 顯示最終狀態
    show_status
}

# 執行主程序
main "$@" 