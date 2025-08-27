# MES 系統快速導覽

## 🚀 快速開始

### 1. 啟動開發環境
```bash
# 啟動開發服務器
python3 manage.py runserver 0.0.0.0:8000

# 啟動背景任務
celery -A mes_config worker -l info
```

### 2. 建立測試環境
```bash
# 一鍵建立測試環境
./deploy_test_environment.sh

# 啟動測試環境
cd /var/www/mes_test
./start_test_server.sh
```

## 📊 專案狀態 (75% 完成)

### ✅ 已完成功能
- **ERP 整合** - 多公司資料同步
- **工單管理** - 自動派工、完工判斷
- **報表系統** - 分析報表、Excel匯出
- **自動審核定時任務** - 多個執行間隔
- **權限管理** - 使用者、角色管理
- **設備管理** - 設備監控、維護記錄
- **品質管理** - 檢驗記錄、不良品管理
- **物料管理** - 需求估算、庫存管理
- **看板系統** - 生產、設備、品質看板

### 🔄 部分完成
- **排程管理** - 需要完善甘特圖
- **製程管理** - 需要完善工藝路線
- **AI 功能** - 需要開發預測分析

### ⏳ 未開始
- **生產管理** - 生產線、生產計劃

## 🛠️ 常用命令

### 系統檢查
```bash
# 檢查專案狀態
./check_project_status.sh

# 檢查系統
python3 manage.py check

# 查看資料庫
python3 manage.py showmigrations
```

### 資料庫管理
```bash
# 建立遷移
python3 manage.py makemigrations

# 執行遷移
python3 manage.py migrate

# 建立超級用戶
python3 manage.py createsuperuser
```

### 定時任務
```bash
# 建立預設定時任務
python3 manage.py setup_auto_approval_tasks

# 查看 Celery 狀態
celery -A mes_config inspect active
```

## 📁 重要檔案位置

### 核心模組
- `workorder/` - 工單管理
- `system/` - 系統管理
- `reporting/` - 報表系統
- `erp_integration/` - ERP整合
- `equip/` - 設備管理
- `quality/` - 品質管理
- `material/` - 物料管理
- `kanban/` - 看板系統

### 設定檔案
- `mes_config/settings.py` - 主要設定
- `mes_config/settings_test.py` - 測試環境設定
- `requirements.txt` - Python套件

### 管理文件
- `DEVELOPMENT_STATUS.md` - 詳細開發狀態
- `CHANGELOG.md` - 功能更新記錄
- `專案管理指南.md` - 完整管理指南

## 🌐 訪問地址

### 開發環境
- **主網站**: http://localhost:8000
- **管理後台**: http://localhost:8000/admin

### 測試環境
- **主網站**: http://localhost:8001
- **管理後台**: http://localhost:8001/admin

## 🔧 快速故障排除

### 系統無法啟動
```bash
# 檢查錯誤
python3 manage.py check

# 重新啟動
pkill -f "python3 manage.py runserver"
python3 manage.py runserver 0.0.0.0:8000
```

### 資料庫問題
```bash
# 檢查遷移
python3 manage.py showmigrations

# 重新遷移
python3 manage.py migrate --fake-initial
```

### 套件問題
```bash
# 更新套件
pip3 install -r requirements.txt --upgrade
```

## 📞 需要更多資訊？

- **詳細開發狀態**: `cat DEVELOPMENT_STATUS.md`
- **功能更新記錄**: `cat CHANGELOG.md`
- **完整管理指南**: `cat 專案管理指南.md`
- **專案狀態檢查**: `./check_project_status.sh`

## 🎯 下一步開發重點

1. **完善排程管理** - 實現甘特圖功能
2. **開發 AI 功能** - 預測分析和異常檢測
3. **完善製程管理** - 工藝路線和標準作業
4. **開發生產管理** - 生產線和生產計劃

---

**💡 提示**: 這個 README.md 包含了最重要的資訊，其他詳細文件可以按需查看！ 