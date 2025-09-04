# MES 製造執行系統

## 📋 專案概述

MES (Manufacturing Execution System) 是一個完整的製造執行系統，提供工單管理、設備監控、品質控制、報表分析等功能。

## 🚀 快速開始

### 開發環境設定
```bash
# 1. 克隆專案
git clone [專案地址]

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env 檔案

# 4. 執行遷移
python3 manage.py migrate

# 5. 創建超級用戶
python3 manage.py createsuperuser

# 6. 啟動開發伺服器
python3 manage.py runserver
```

## 📚 文件清單

### 部署相關文件
- **`MES系統部署指南.md`** - 完整的部署指南，包含詳細步驟和故障排除
- **`腳本清單.md`** - 所有腳本檔案的使用說明

### 核心腳本
- **`合併遷移檔案.sh`** - 合併 Django 遷移檔案，解決依賴問題
- **`創建部署包.sh`** - 創建生產環境部署包
- **`全新部署.sh`** - 完整系統部署腳本

### 系統管理腳本
- **`重啟MES.sh`** - 重啟 MES 系統服務
- **`重啟服務.sh`** - 重啟所有相關服務
- **`Celery管理.sh`** - 管理 Celery 背景任務

## 🔧 部署流程

詳細的部署流程請參考 `MES系統部署指南.md`，包含：
- 開發環境準備
- 生產環境部署（全新部署 vs 系統更新）
- 故障排除和維護指南

### 快速參考
```bash
# 開發環境準備
./合併遷移檔案.sh
./創建部署包.sh

# 生產環境部署
sudo ./全新部署.sh          # 全新環境
sudo ./系統更新.sh           # 更新已有系統
```

## 🏗️ 系統架構

- **後端**: Django 5.1.8 + Python 3.10
- **資料庫**: PostgreSQL
- **快取**: Redis
- **背景任務**: Celery
- **Web 伺服器**: Nginx + Gunicorn
- **前端**: Bootstrap 5 + Chart.js

## 📁 專案結構

```
/var/www/mes/
├── mes_config/         # Django 設定
├── workorder/          # 工單管理
├── system/             # 系統管理
├── reporting/          # 報表功能
├── erp_integration/    # ERP 整合
├── static/             # 靜態檔案
├── templates/          # 模板檔案
├── *.sh               # 部署腳本
└── *.md               # 說明文件
```

## 🎯 主要功能

- **工單管理**: 工單建立、派發、執行、完成
- **設備監控**: 設備狀態、維護記錄
- **品質控制**: 檢驗記錄、不良品管理
- **報表分析**: 生產報表、效率分析
- **ERP 整合**: 與正航 ERP 系統資料同步

## 📞 技術支援

如有問題，請參考：
- `MES系統部署指南.md` - 詳細部署說明
- `腳本清單.md` - 腳本使用說明
- 系統日誌 - 位於 `/var/log/mes/`

## 📝 版本資訊

- **版本**: v1.0
- **最後更新**: 2025-08-28
- **開發團隊**: MES 開發團隊

---

**注意**: 本專案所有文件均使用繁體中文，確保本地化支援。
