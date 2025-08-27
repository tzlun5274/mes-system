#!/bin/bash

# 清理遷移文件腳本
# 用途：重新生成乾淨的遷移文件，適合生產環境部署

echo "=== 清理遷移文件，重新生成乾淨的遷移 ==="

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

echo -e "${YELLOW}⚠️  這將刪除所有現有的遷移文件並重新生成${NC}"
echo -e "${YELLOW}⚠️  請確保您已經備份了重要資料${NC}"
read -p "確定要繼續嗎？(y/N): " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ 操作已取消${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🔄 步驟 1: 備份現有遷移文件${NC}"
BACKUP_DIR="migrations_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 備份所有遷移文件
find . -path "*/migrations/*.py" -not -name "__init__.py" -exec cp {} $BACKUP_DIR/ \;
echo -e "${GREEN}✅ 遷移文件已備份到 $BACKUP_DIR${NC}"

echo ""
echo -e "${BLUE}🔄 步驟 2: 刪除現有遷移文件${NC}"

# 刪除所有遷移文件（保留 __init__.py）
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
echo -e "${GREEN}✅ 現有遷移文件已刪除${NC}"

echo ""
echo -e "${BLUE}🔄 步驟 3: 重新生成遷移文件${NC}"

# 重新生成遷移文件
python3 manage.py makemigrations
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 遷移文件重新生成成功${NC}"
else
    echo -e "${RED}❌ 遷移文件生成失敗${NC}"
    echo "恢復備份的遷移文件..."
    cp $BACKUP_DIR/* */migrations/ 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${BLUE}🔄 步驟 4: 檢查生成的遷移文件${NC}"

# 檢查生成的遷移文件
echo "新生成的遷移文件："
find . -path "*/migrations/*.py" -not -name "__init__.py" | sort

echo ""
echo -e "${GREEN}🎉 遷移文件清理完成！${NC}"
echo ""
echo -e "${BLUE}📋 下一步：${NC}"
echo "1. 測試遷移是否正常：python3 manage.py migrate --dry-run"
echo "2. 如果測試正常，可以部署到生產環境"
echo "3. 備份目錄：$BACKUP_DIR（可以刪除）"
echo ""
echo -e "${YELLOW}⚠️  注意：新的遷移文件只包含當前的模型狀態${NC}"
echo -e "${YELLOW}⚠️  不包含開發過程中的歷史變更${NC}"
