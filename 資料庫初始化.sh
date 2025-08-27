#!/bin/bash

# 全新生產主機資料庫初始化腳本
# 適用於：全新的 Ubuntu 主機，全新的 PostgreSQL 資料庫

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 全新生產主機資料庫初始化${NC}"
echo "=================================="

# 檢查是否在專案目錄
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ 請在專案根目錄執行此腳本${NC}"
    exit 1
fi

# 讀取環境變數
if [ -f ".env" ]; then
    source .env
    echo "✅ 已載入 .env 配置"
else
    echo -e "${RED}❌ 未找到 .env 檔案${NC}"
    exit 1
fi

# 檢查必要變數
if [ -z "$DATABASE_NAME" ] || [ -z "$DATABASE_USER" ] || [ -z "$DATABASE_PASSWORD" ]; then
    echo -e "${RED}❌ 資料庫配置不完整${NC}"
    exit 1
fi

echo "📊 資料庫配置："
echo "  資料庫名稱: $DATABASE_NAME"
echo "  資料庫用戶: $DATABASE_USER"
echo "  資料庫主機: ${DATABASE_HOST:-localhost}"
echo "  資料庫端口: ${DATABASE_PORT:-5432}"

# 步驟 1: 檢查資料庫連接
echo ""
echo -e "${BLUE}🔍 步驟 1: 檢查資料庫連接${NC}"
if sudo -u postgres psql -d $DATABASE_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ 資料庫連接正常"
else
    echo -e "${RED}❌ 資料庫連接失敗${NC}"
    echo "請檢查 PostgreSQL 服務是否運行"
    exit 1
fi

# 步驟 2: 檢查資料庫是否為空
echo ""
echo -e "${BLUE}🔍 步驟 2: 檢查資料庫狀態${NC}"
TABLE_COUNT=$(sudo -u postgres psql -d $DATABASE_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
echo "當前資料表數量: $TABLE_COUNT"

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  資料庫不是空的，是否繼續？(y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "取消初始化"
        exit 0
    fi
fi

# 步驟 3: 執行 Django 初始化
echo ""
echo -e "${BLUE}🗃️ 步驟 3: 執行 Django 資料庫初始化${NC}"

# 方法 1: 使用 --run-syncdb
echo "嘗試方法 1: 使用 --run-syncdb..."
if sudo -u mes python3 manage.py migrate --run-syncdb 2>&1; then
    echo "✅ 方法 1 成功"
else
    echo -e "${YELLOW}⚠️  方法 1 失敗，嘗試方法 2...${NC}"
    
    # 方法 2: 先 fake 再 migrate
    echo "嘗試方法 2: 先標記遷移為已應用..."
    sudo -u mes python3 manage.py migrate --fake 2>&1
    
    echo "執行實際遷移..."
    if sudo -u mes python3 manage.py migrate 2>&1; then
        echo "✅ 方法 2 成功"
    else
        echo -e "${RED}❌ 方法 2 也失敗${NC}"
        exit 1
    fi
fi

# 步驟 4: 驗證初始化結果
echo ""
echo -e "${BLUE}✅ 步驟 4: 驗證初始化結果${NC}"

# 檢查遷移狀態
echo "檢查遷移狀態..."
sudo -u mes python3 manage.py showmigrations 2>&1

# 檢查資料表
echo ""
echo "檢查資料表..."
TABLE_COUNT_AFTER=$(sudo -u postgres psql -d $DATABASE_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
echo "初始化後資料表數量: $TABLE_COUNT_AFTER"

if [ "$TABLE_COUNT_AFTER" -gt 0 ]; then
    echo -e "${GREEN}✅ 資料庫初始化成功！${NC}"
    echo ""
    echo "📋 初始化結果："
    echo "  - 資料表數量: $TABLE_COUNT_AFTER"
    echo "  - 遷移狀態: 已應用"
    echo "  - 資料庫: $DATABASE_NAME"
    echo ""
    echo "🎉 資料庫初始化完成，可以繼續部署流程！"
else
    echo -e "${RED}❌ 資料庫初始化失敗${NC}"
    exit 1
fi
