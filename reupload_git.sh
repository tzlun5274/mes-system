#!/bin/bash

echo "=== MES 系統 Git 重新上傳腳本 ==="
echo "開始重新上傳專案到 GitHub..."
echo ""

# 設定變數
REPO_NAME="mes-system"
GITHUB_USERNAME="tzlun5274"

echo "1. 刪除現有的 Git 倉庫..."
rm -rf .git

echo "2. 重新初始化 Git 倉庫..."
git init

echo "3. 設定 Git 使用者資訊..."
git config user.name "MES System"
git config user.email "mes@example.com"

echo "4. 添加所有檔案到暫存區..."
git add .

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

echo "6. 添加遠端倉庫..."
git remote add origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git

echo "7. 設定主分支並推送到 GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=== 上傳完成！ ==="
echo "請檢查：https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo ""
echo "如果遇到認證問題，請："
echo "1. 前往 GitHub → Settings → Developer settings → Personal access tokens"
echo "2. 生成新的 token"
echo "3. 使用 token 作為密碼" 