# WinSCP 複製清單 - 開發主機到測試主機

## 📋 複製步驟

### 1. 連接到測試主機
- **主機**: 192.168.1.28
- **用戶名**: mes
- **密碼**: (您的密碼)

### 2. 建立測試目錄
在測試主機上建立：`/var/www/mes_test/`

### 3. 需要複製的檔案和資料夾

#### 📁 核心模組 (必須複製)
```
workorder/          → /var/www/mes_test/workorder/
system/             → /var/www/mes_test/system/
reporting/          → /var/www/mes_test/reporting/
erp_integration/    → /var/www/mes_test/erp_integration/
equip/              → /var/www/mes_test/equip/
quality/            → /var/www/mes_test/quality/
material/           → /var/www/mes_test/material/
kanban/             → /var/www/mes_test/kanban/
scheduling/         → /var/www/mes_test/scheduling/
ai/                 → /var/www/mes_test/ai/
process/            → /var/www/mes_test/process/
production/         → /var/www/mes_test/production/
```

#### ⚙️ 設定檔案 (必須複製)
```
mes_config/         → /var/www/mes_test/mes_config/
requirements.txt    → /var/www/mes_test/requirements.txt
manage.py           → /var/www/mes_test/manage.py
```

#### 🎨 模板和靜態檔案 (必須複製)
```
templates/          → /var/www/mes_test/templates/
static/             → /var/www/mes_test/static/
```

#### 📄 管理文件 (可選)
```
README.md           → /var/www/mes_test/README.md
一頁指南.md         → /var/www/mes_test/一頁指南.md
快速命令.md         → /var/www/mes_test/快速命令.md
CHANGELOG.md        → /var/www/mes_test/CHANGELOG.md
DEVELOPMENT_STATUS.md → /var/www/mes_test/DEVELOPMENT_STATUS.md
deploy_test_environment.sh → /var/www/mes_test/deploy_test_environment.sh
```

## ❌ 不需要複製的檔案

### 🗑️ 開發和測試檔案
```
*.pyc               (Python 編譯檔案)
__pycache__/        (Python 快取目錄)
.git/               (Git 版本控制)
logs/               (日誌檔案)
*.log               (日誌檔案)
celery_*.log        (Celery 日誌)
nohup.out           (背景執行日誌)
```

### 🧪 測試和除錯檔案
```
test_*.py           (測試檔案)
debug_*.py          (除錯檔案)
fix_*.py            (修復檔案)
*.md                (除了管理文件外的說明檔案)
*.csv               (測試資料檔案)
```

### 📊 報表和備份
```
reports/            (報表檔案)
backups_DB/         (資料庫備份)
media/              (媒體檔案)
staticfiles/        (靜態檔案備份)
```

## 🚀 複製完成後的步驟

### 1. 在測試主機上建立資料庫
```bash
# 登入測試主機
ssh mes@192.168.1.28

# 建立測試資料庫
sudo -u postgres psql
CREATE DATABASE mes_test_db;
CREATE USER mes_test_user WITH PASSWORD 'mes_test_password';
GRANT ALL PRIVILEGES ON DATABASE mes_test_db TO mes_test_user;
\q
```

### 2. 設定測試環境
```bash
cd /var/www/mes_test
export DJANGO_SETTINGS_MODULE=mes_config.settings_test

# 安裝依賴
pip3 install -r requirements.txt

# 執行遷移
python3 manage.py migrate

# 建立超級用戶
python3 manage.py createsuperuser
```

### 3. 啟動測試服務器
```bash
# 啟動測試服務器 (端口 8001)
python3 manage.py runserver 0.0.0.0:8001

# 啟動 Celery 背景任務
celery -A mes_config worker -l info
```

## 🌐 訪問地址

- **開發環境**: http://192.168.1.21:8000
- **測試環境**: http://192.168.1.28:8001

## 💡 提示

1. **使用 WinSCP 拖拽複製**：直接拖拽資料夾到測試主機
2. **檢查複製結果**：確保所有必要檔案都已複製
3. **權限設定**：確保檔案權限正確
4. **測試連接**：複製完成後測試網站是否正常

## 🔄 後續更新

當開發主機有新功能時，只需要複製更新的模組即可：
- 複製更新的模組資料夾
- 複製更新的設定檔案
- 在測試主機上執行遷移
