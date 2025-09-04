#!/bin/bash

# ========================================
# Git 強制下載腳本
# 功能：從遠端 Git 倉庫強制下載並覆蓋本機專案
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
echo -e "${BLUE}    Git 強制下載腳本開始執行${NC}"
echo -e "${BLUE}========================================${NC}"

# 檢查是否在 Git 倉庫中
if [ ! -d ".git" ]; then
    echo -e "${RED}錯誤：當前目錄不是 Git 倉庫！${NC}"
    echo -e "${YELLOW}請確保您在正確的專案目錄中執行此腳本${NC}"
    exit 1
fi

# 顯示當前分支
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}當前分支：${CURRENT_BRANCH}${NC}"

# 檢查本機變更
echo -e "${BLUE}1. 檢查本機變更狀態...${NC}"
git status

# 檢查是否有未提交的變更
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}檢測到本機有未提交的變更！${NC}"
    echo -e "${YELLOW}這些變更將在強制下載後丟失！${NC}"
    echo -e "${YELLOW}請確認您要繼續執行強制下載${NC}"
fi

# 確認操作
echo -e "${RED}警告：此操作將完全覆蓋本機專案內容！${NC}"
echo -e "${RED}所有未提交的變更都將丟失！${NC}"
echo -e "${YELLOW}請確認您要從遠端倉庫強制下載 ${CURRENT_BRANCH} 分支${NC}"
read -p "是否繼續？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

# 獲取遠端最新變更
echo -e "${BLUE}2. 獲取遠端最新變更...${NC}"
git fetch origin

# 檢查遠端分支是否存在
if ! git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
    echo -e "${RED}錯誤：遠端倉庫中不存在分支 ${CURRENT_BRANCH}${NC}"
    echo -e "${YELLOW}請檢查分支名稱或遠端倉庫設定${NC}"
    exit 1
fi

# 重置本機分支到遠端狀態
echo -e "${BLUE}3. 重置本機分支到遠端狀態...${NC}"
git reset --hard origin/$CURRENT_BRANCH

# 清理未追蹤的檔案
echo -e "${BLUE}4. 清理未追蹤的檔案...${NC}"
git clean -fd

# 檢查下載結果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    強制下載成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}本機專案已完全同步到遠端 ${CURRENT_BRANCH} 分支${NC}"
    echo -e "${GREEN}所有本機變更已被遠端內容覆蓋${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}    強制下載失敗！${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}請檢查網路連線和遠端倉庫設定${NC}"
    exit 1
fi

# 顯示最終狀態
echo -e "${BLUE}5. 顯示最終狀態...${NC}"
git status

# 顯示最近提交
echo -e "${BLUE}6. 顯示最近提交記錄...${NC}"
git log --oneline -5



echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Git 強制下載腳本執行完成${NC}"
echo -e "${GREEN}========================================${NC}" 