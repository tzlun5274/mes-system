#!/bin/bash

# ========================================
# Git 強制上傳腳本
# 功能：將本機專案強制上傳到遠端 Git 倉庫
# 作者：MES 系統開發團隊
# 日期：$(date +%Y-%m-%d)
# ========================================

# 設定顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定錯誤時退出
set -e

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Git 強制上傳腳本開始執行${NC}"
echo -e "${BLUE}========================================${NC}"

# 檢查是否在 Git 倉庫中
if [ ! -d ".git" ]; then
    echo -e "${RED}錯誤：當前目錄不是 Git 倉庫！${NC}"
    echo -e "${YELLOW}請確保您在正確的專案目錄中執行此腳本${NC}"
    exit 1
fi

# 檢查 Git 狀態
echo -e "${BLUE}1. 檢查 Git 狀態...${NC}"
git status

# 顯示當前分支
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}當前分支：${CURRENT_BRANCH}${NC}"

# 確認操作
echo -e "${YELLOW}警告：此操作將強制覆蓋遠端倉庫的內容！${NC}"
echo -e "${YELLOW}請確認您要將本機的 ${CURRENT_BRANCH} 分支強制推送到遠端${NC}"
read -p "是否繼續？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

# 強制添加所有檔案到暫存區（包括未追蹤的檔案）
echo -e "${BLUE}2. 強制添加所有檔案到暫存區...${NC}"
echo -e "${YELLOW}注意：將添加所有檔案，包括未追蹤的檔案${NC}"

# 添加所有已追蹤的變更
git add .

# 添加所有未追蹤的檔案（除了 .gitignore 中排除的）
echo -e "${BLUE}添加未追蹤的檔案...${NC}"
git add -A

# 顯示暫存區狀態
echo -e "${BLUE}暫存區狀態：${NC}"
git status --porcelain

# 強制提交所有變更
echo -e "${BLUE}3. 強制提交所有變更...${NC}"
COMMIT_MESSAGE="完整專案強制更新 - $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MESSAGE" --allow-empty
echo -e "${GREEN}所有變更已提交：$COMMIT_MESSAGE${NC}"

# 獲取遠端最新變更
echo -e "${BLUE}4. 獲取遠端最新變更...${NC}"
git fetch origin

# 顯示本機與遠端的差異
echo -e "${BLUE}檢查本機與遠端的差異...${NC}"
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/$CURRENT_BRANCH 2>/dev/null || echo "無遠端分支")

echo -e "${YELLOW}本機提交：${LOCAL_COMMIT:0:8}${NC}"
echo -e "${YELLOW}遠端提交：${REMOTE_COMMIT:0:8}${NC}"

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo -e "${YELLOW}檢測到本機與遠端有差異，將執行強制推送${NC}"
else
    echo -e "${GREEN}本機與遠端已同步${NC}"
fi

# 強制推送到遠端
echo -e "${BLUE}5. 強制推送到遠端倉庫...${NC}"
echo -e "${RED}警告：此操作將覆蓋遠端倉庫的內容！${NC}"
read -p "確認強制推送？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}強制推送已取消${NC}"
    exit 0
fi

# 執行強制推送
echo -e "${BLUE}執行強制推送...${NC}"
git push origin $CURRENT_BRANCH --force

# 檢查推送結果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    完整專案強制推送成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}分支 ${CURRENT_BRANCH} 已成功推送到遠端倉庫${NC}"
    echo -e "${GREEN}遠端倉庫內容已被本機完整專案內容覆蓋${NC}"
    echo -e "${GREEN}所有檔案和變更都已上傳${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}    強制推送失敗！${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}請檢查網路連線和遠端倉庫設定${NC}"
    exit 1
fi

# 顯示最終狀態
echo -e "${BLUE}6. 顯示最終狀態...${NC}"
git status

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Git 強制上傳腳本執行完成${NC}"
echo -e "${GREEN}========================================${NC}" 