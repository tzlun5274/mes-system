# MES 製造執行系統 (Manufacturing Execution System)

## 專案概述

MES 製造執行系統是一套專為電子製造業設計的完整解決方案，支援多公司架構，整合 ERP 系統，提供智能化的生產管理功能。

## 技術架構

- **後端框架**：Django 5.1.8
- **資料庫**：PostgreSQL
- **快取系統**：Redis
- **任務佇列**：Celery
- **前端技術**：Bootstrap 5, Chart.js
- **AI/ML**：TensorFlow, Scikit-learn

## 系統模組

### 核心模組
- **工單管理** (`workorder/`) - 工單建立、派工、執行、追蹤
- **設備管理** (`equip/`) - 設備資訊、狀態監控、維護管理
- **物料管理** (`material/`) - 物料需求估算、庫存管理
- **製程管理** (`process/`) - 工藝路線、工序、標準作業
- **排程管理** (`scheduling/`) - 生產排程、甘特圖、產能規劃
- **品質管理** (`quality/`) - 檢驗管理、不良品追蹤、品質分析
- **生產管理** (`production/`) - 產線管理、生產執行、進度監控
- **看板管理** (`kanban/`) - 生產看板、設備看板、品質看板
- **報表管理** (`reporting/`) - 生產報表、品質報表、效率報表
- **系統管理** (`system/`) - 使用者管理、權限控制、系統設定

### 進階功能
- **AI 功能** (`ai/`) - 預測分析、異常檢測、優化建議
- **ERP 整合** (`erp_integration/`) - 與正航 ERP 系統整合

## 安裝與設定

### 1. 環境需求
- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Node.js 16+ (用於前端資源編譯)

### 2. 安裝步驟

```bash
# 1. 克隆專案
git clone https://github.com/tzlun5274/mes-system.git
cd mes-system

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安裝依賴套件
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 檔案，設定資料庫連線等資訊

# 5. 執行資料庫遷移
python manage.py migrate

# 6. 建立超級使用者
python manage.py createsuperuser

# 7. 收集靜態檔案
python manage.py collectstatic

# 8. 啟動開發伺服器
python manage.py runserver
```

### 3. 環境變數設定

在 `.env` 檔案中設定以下變數：

```env
# Django 設定
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 資料庫設定
DATABASE_URL=postgresql://username:password@localhost:5432/mes_db

# Redis 設定
REDIS_URL=redis://localhost:6379/0

# Celery 設定
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 功能特色

### 多公司架構
- 支援多家公司獨立營運
- 資料隔離與權限控制
- 統一的公司配置管理

### ERP 整合
- 與正航 ERP 系統無縫整合
- 自動資料同步機制
- 支援增量與全量同步

### 智能分析
- AI 驅動的生產預測
- 異常檢測與警報
- 優化建議與決策支援

### 即時監控
- 生產進度即時追蹤
- 設備狀態監控
- 品質指標即時顯示

### 報表分析
- 豐富的報表功能
- 圖表視覺化
- 資料匯出功能

## 使用指南

### 工單管理
1. 建立工單：選擇產品、設定數量、分配資源
2. 派工作業：分配作業員與設備
3. 執行追蹤：即時監控生產進度
4. 完工確認：記錄實際產出與品質

### 設備管理
1. 設備資訊：維護設備基本資料
2. 狀態監控：即時顯示設備運行狀態
3. 維護管理：排程維護、記錄維護歷史

### 品質管理
1. 檢驗計畫：建立檢驗標準與流程
2. 檢驗執行：記錄檢驗結果
3. 不良品管理：追蹤不良品處理流程

## 開發指南

### 程式碼規範
- 遵循 PEP 8 程式碼風格
- 使用繁體中文註解與文件
- 完整的單元測試覆蓋

### 模組開發
- 每個功能模組獨立開發
- 遵循 Django 最佳實踐
- 完整的 API 文件

### 資料庫設計
- 統一的命名規範
- 完整的關聯設計
- 效能優化考量

## 部署說明

### 生產環境部署
1. 設定生產環境變數
2. 配置 Web 伺服器 (Nginx)
3. 設定 Celery 背景任務
4. 配置資料庫備份

### Docker 部署
```bash
# 使用 Docker Compose
docker-compose up -d
```

## 維護與支援

### 日常維護
- 定期資料庫備份
- 系統效能監控
- 日誌檔案管理

### 故障排除
- 檢查系統日誌
- 驗證資料庫連線
- 確認服務狀態

## 授權條款

本專案採用 MIT 授權條款，詳見 [LICENSE](LICENSE) 檔案。

## 聯絡資訊

- 專案維護者：MES 開發團隊
- 電子郵件：mes@example.com
- 專案網址：https://github.com/tzlun5274/mes-system

## 更新日誌

### v1.0.0 (2024-07-19)
- 初始版本發布
- 完整的 MES 功能模組
- ERP 整合功能
- AI 分析功能 