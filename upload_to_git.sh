#!/bin/bash

# MES 系統 Git 重新上傳腳本
# 此腳本會刪除現有的 Git 倉庫並重新上傳到 GitHub

echo "=== MES 系統 Git 重新上傳腳本 ==="
echo "請確保您已經在 GitHub 上建立了新的倉庫"
echo ""

# 設定變數
REPO_NAME="mes-system"  # 請修改為您的倉庫名稱
GITHUB_USERNAME="tzlun5274"  # 請修改為您的 GitHub 使用者名稱

# 1. 刪除現有的 Git 倉庫
echo "1. 刪除現有的 Git 倉庫..."
rm -rf .git

# 2. 重新初始化 Git 倉庫
echo "2. 重新初始化 Git 倉庫..."
git init

# 3. 設定 Git 使用者資訊
echo "3. 設定 Git 使用者資訊..."
git config user.name "MES System"
git config user.email "mes@example.com"

# 4. 添加所有檔案到暫存區
echo "4. 添加所有檔案到暫存區..."
git add .

# 5. 提交初始版本
echo "5. 提交初始版本..."
git commit -m "初始版本：MES 製造執行系統

包含以下模組：
- 工單管理 (workorder)
- 設備管理 (equip)
- 物料管理 (material)
- 製程管理 (process)
- 排程管理 (scheduling)
- 品質管理 (quality)
- 生產管理 (production)
- 看板管理 (kanban)
- 報表管理 (reporting)
- 系統管理 (system)
- AI 功能 (ai)
- ERP 整合 (erp_integration)

技術架構：
- Django 5.1.8
- PostgreSQL
- Bootstrap 5
- Chart.js
- Celery + Redis"

# 6. 添加遠端倉庫
echo "6. 添加遠端倉庫..."
git remote add origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git

# 7. 推送到 GitHub
echo "7. 推送到 GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=== 上傳完成！ ==="
echo "您的專案已成功上傳到：https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo ""
echo "請記得："
echo "1. 檢查 GitHub 上的檔案是否完整"
echo "2. 確認 .env 檔案沒有被上傳（包含敏感資訊）"
echo "3. 更新專案說明文件" 