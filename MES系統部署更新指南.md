# MES 系統部署指南

## 📋 目錄
- [部署概述](#部署概述)
- [遷移依賴問題解決方案](#遷移依賴問題解決方案)
- [部署流程](#部署流程)
- [遷移檔案說明](#遷移檔案說明)
- [注意事項](#注意事項)
- [故障排除](#故障排除)
- [後續開發](#後續開發)

---

## 🎯 部署概述

本指南說明如何將 MES 系統從開發環境部署到生產環境，特別是如何處理遷移依賴問題。

### 📊 系統架構
- **Web 伺服器**: Nginx + Gunicorn
- **資料庫**: PostgreSQL
- **快取/訊息佇列**: Redis
- **背景任務**: Celery Worker + Celery Beat
- **應用框架**: Django 5.1.8

### 🎯 部署目標
- 將 MES 系統部署到全新的 Ubuntu 主機
- 自動化所有安裝和配置步驟
- 確保系統穩定運行
- 提供完整的監控和維護功能

---

## 🔧 遷移依賴問題解決方案

### 問題描述
在開發過程中，會產生大量的遷移檔案（migrations），這些檔案會造成：
1. 遷移依賴複雜化
2. 生產環境部署困難
3. 資料庫結構不一致的風險

### 解決方案
使用 Django 的 `squashmigrations` 功能，將多個遷移檔案合併成一個初始遷移檔案。

### 遷移管理腳本

#### 1. 重置遷移腳本 (`重置遷移.sh`)
**用途**：重置當前開發環境的遷移狀態，重新生成初始遷移

**適用場景**：
- 遷移檔案出現問題需要重置
- 開發環境遷移狀態混亂
- 需要重新整理遷移歷史
- 當前環境的資料庫結構需要更新

**執行流程**：
1. **備份現有遷移**：創建時間戳備份目錄
2. **刪除遷移檔案**：清理所有 `.py` 遷移檔案（保留 `__init__.py`）
3. **重新生成遷移**：為每個應用執行 `makemigrations`
4. **執行遷移**：真正執行遷移（不是 `--fake`）
5. **檢查結果**：驗證遷移狀態和系統檢查

**安全特性**：
- ✅ 自動備份現有遷移檔案
- ✅ 要求用戶確認操作
- ✅ 詳細的日誌記錄
- ✅ 只針對特定應用（system, workorder, erp_integration, reporting）

**使用注意**：
- ⚠️ 會真正執行遷移，可能改變資料庫結構
- ⚠️ 使用前務必備份資料庫
- ⚠️ 僅適用於開發環境問題修復

#### 2. 清理專案遷移腳本 (`清理專案遷移.sh`)
**用途**：完全清理專案的所有遷移相關檔案，準備部署到生產主機

**適用場景**：
- 準備部署到全新的生產主機
- 遷移檔案出現嚴重問題需要重置
- 專案重新整理，需要乾淨的遷移狀態

**執行流程**：
1. **刪除遷移檔案**：清理所有 `.py` 遷移檔案
2. **刪除備份目錄**：清理遷移備份目錄
3. **清理資料庫記錄**：刪除 `django_migrations` 表中的遷移記錄
4. **重新生成遷移**：執行 `makemigrations` 生成新的初始遷移

**重要特點**：
- 🚨 **完全不可逆**：刪除的遷移檔案無法恢復
- 🚨 **清理資料庫記錄**：會清空 `django_migrations` 表
- 🚨 **僅限生產部署**：不應該在開發環境使用

**部署建議**：
1. 打包專案：`tar -czf mes_clean.tar.gz .`
2. 上傳到生產主機
3. 執行遷移：`python3 manage.py migrate --fake`
4. 創建超級用戶：`python3 manage.py createsuperuser`

### 腳本選擇指南

| 使用場景 | 推薦腳本 | 執行主機 | 原因 |
|---------|----------|----------|------|
| **開發環境遷移問題** | `重置遷移.sh` | 開發環境主機 | 會備份、會執行遷移、相對安全 |
| **生產環境部署準備** | `清理專案遷移.sh` | 開發環境主機 | 完全清理、準備乾淨部署 |
| **遷移檔案損壞** | `重置遷移.sh` | 開發環境主機 | 保留備份、可恢復 |
| **全新生產環境部署** | `清理專案遷移.sh` | 開發環境主機 | 最乾淨的狀態 |
| **測試環境重置** | `重置遷移.sh` | 開發環境主機 | 較安全的重置方式 |

**重要說明**：所有腳本都只能在開發環境主機上執行，生產環境主機只需要執行 Django 的 migrate 命令！

### 腳本執行權限
```bash
# 設定腳本執行權限
chmod +x 重置遷移.sh
chmod +x 清理專案遷移.sh

# 以 mes 用戶身份執行
su - mes
./重置遷移.sh
# 或
./清理專案遷移.sh
```

### 🖥️ 腳本執行主機說明

#### **重置遷移腳本 (`重置遷移.sh`)**
- **執行主機**：**開發環境主機**（當前開發的機器）
- **執行時機**：開發過程中遇到遷移問題時
- **執行用戶**：`mes` 用戶
- **執行位置**：`/var/www/mes/` 專案目錄
- **影響範圍**：當前開發環境的遷移狀態

#### **清理專案遷移腳本 (`清理專案遷移.sh`)**
- **執行主機**：**開發環境主機**（準備部署包的機器）
- **執行時機**：準備部署到生產環境前
- **執行用戶**：`mes` 用戶
- **執行位置**：`/var/www/mes/` 專案目錄
- **影響範圍**：開發環境的遷移檔案（為生產部署做準備）

### 📍 腳本執行位置示意圖

```
開發環境主機 (192.168.1.21)
├── /var/www/mes/
│   ├── 重置遷移.sh          ← 在這裡執行
│   ├── 清理專案遷移.sh      ← 在這裡執行
│   ├── system/migrations/
│   ├── workorder/migrations/
│   └── ...
└── 執行腳本後生成部署包

生產環境主機 (生產主機IP)
├── 接收部署包
├── 解壓部署包
└── 執行 python3 manage.py migrate --fake
```

### ⚠️ 重要提醒

1. **兩個腳本都只能在開發環境主機上執行**
2. **絕對不能在生產環境主機上執行這些腳本**
3. **腳本執行後，會影響開發環境的遷移狀態**
4. **生產環境只需要執行 Django 的 migrate 命令**

---

## 🚀 部署流程

### 1. 準備階段（開發環境）

**執行主機**：開發環境主機（如：192.168.1.21）

#### 1.1 合併遷移檔案
```bash
# 執行遷移合併腳本
./merge_migrations.sh
```

這個腳本會：
- 備份所有現有遷移檔案
- 合併以下模組的遷移檔案：
  - workorder: 29個 → 1個
  - system: 13個 → 1個
  - reporting: 14個 → 1個
  - workorder_dispatch: 7個 → 1個
  - fill_work: 8個 → 1個
  - onsite_reporting: 10個 → 1個
  - manufacturing_order: 5個 → 1個

#### 1.2 創建部署包
```bash
# 執行部署包創建腳本
./create_production_package.sh
```

這個腳本會：
- 備份當前資料庫
- 檢查並合併遷移檔案（如果還沒合併）
- 創建完整的部署包
- 生成詳細的部署說明文件

### 2. 部署階段（生產環境）

**執行主機**：生產環境主機（目標部署機器）

#### 2.1 環境準備
```bash
# 安裝必要套件
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev
sudo apt install postgresql postgresql-contrib
sudo apt install redis-server
sudo apt install nginx
```

#### 2.2 資料庫設定
```bash
# 創建資料庫和用戶
sudo -u postgres psql
CREATE DATABASE mes_db;
CREATE USER mes_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mes_db TO mes_user;
\q
```

#### 2.3 部署應用程式
```bash
# 解壓部署包
tar -xzf mes_production_YYYYMMDD_HHMMSS.tar.gz
cd mes_production_YYYYMMDD_HHMMSS

# 創建虛擬環境
python3.10 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 檔案，設定正確的資料庫連線資訊

# 執行遷移（使用合併後的遷移檔案）
python3 manage.py migrate

# 收集靜態檔案
python3 manage.py collectstatic --noinput

# 創建超級用戶
python3 manage.py createsuperuser
```

#### 2.4 設定服務
```bash
# 設定 Celery 服務
sudo cp deployment/celery.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable celery-mes_config
sudo systemctl start celery-mes_config

# 設定 Nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/mes
sudo ln -s /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 設定 Gunicorn
sudo cp deployment/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-mes_config
sudo systemctl start gunicorn-mes_config
```

---

## 📁 遷移檔案說明

### 合併後的遷移檔案
部署包包含以下合併後的遷移檔案：

1. **workorder**: `0001_squashed_0029_alter_completedworkorder_completed_at.py`
   - 包含 29 個原始遷移檔案的內容
   - 涵蓋工單管理的所有功能

2. **system**: `0001_squashed_0013_ordersynclog_ordersyncsettings.py`
   - 包含 13 個原始遷移檔案的內容
   - 涵蓋系統管理的所有功能

3. **reporting**: `0001_squashed_0014_alter_completedworkorderanalysis_unique_together.py`
   - 包含 14 個原始遷移檔案的內容
   - 涵蓋報表功能的所有功能

4. **workorder_dispatch**: `0001_squashed_0007_update_dispatch_default_status.py`
   - 包含 7 個原始遷移檔案的內容
   - 涵蓋工單派發的所有功能

5. **fill_work**: `0001_squashed_0008_alter_fillwork_unique_together.py`
   - 包含 8 個原始遷移檔案的內容
   - 涵蓋填報工作的所有功能

6. **onsite_reporting**: `0001_squashed_0010_alter_onsitereport_abnormal_notes_and_more.py`
   - 包含 10 個原始遷移檔案的內容
   - 涵蓋現場報工的所有功能

7. **manufacturing_order**: `0001_squashed_0005_delete_companyordersystemconfig.py`
   - 包含 5 個原始遷移檔案的內容
   - 涵蓋公司訂單的所有功能

### 遷移檔案優化
合併過程中，Django 會自動優化遷移操作：
- 移除重複的操作
- 合併相關的欄位變更
- 減少總操作數量

例如：
- workorder: 86個操作 → 77個操作
- system: 25個操作 → 12個操作
- reporting: 28個操作 → 5個操作

---

## ⚠️ 注意事項

### 1. 備份重要性
- 部署前務必備份現有資料庫
- 遷移檔案合併前會自動備份原始檔案

### 2. 環境一致性
- 確保開發環境和生產環境的 Python 版本一致
- 確保資料庫版本一致
- 確保所有依賴套件版本一致

### 3. 測試驗證
- 部署後要測試所有主要功能
- 檢查 Celery 任務是否正常運行
- 檢查定時任務是否正常執行

### 4. 監控維護
- 定期檢查系統日誌
- 監控資料庫效能
- 定期備份資料庫

---

## 🔧 故障排除

### 常見問題

1. **遷移失敗**
   ```bash
   # 檢查遷移狀態
   python3 manage.py showmigrations
   
   # 強制執行遷移
   python3 manage.py migrate --fake-initial
   
   # 如果遷移檔案嚴重損壞，使用重置腳本
   ./重置遷移.sh
   ```

2. **遷移檔案混亂**
   ```bash
   # 檢查遷移檔案數量
   find . -path "*/migrations/*.py" -not -name "__init__.py" | wc -l
   
   # 使用重置腳本整理遷移狀態
   ./重置遷移.sh
   
   # 或使用清理腳本（僅限生產部署）
   ./清理專案遷移.sh
   ```

2. **服務啟動失敗**
   ```bash
   # 檢查服務狀態
   sudo systemctl status celery-mes_config
   sudo systemctl status gunicorn-mes_config
   sudo systemctl status nginx
   
   # 查看日誌
   sudo journalctl -u celery-mes_config -f
   sudo journalctl -u gunicorn-mes_config -f
   ```

3. **資料庫連線問題**
   ```bash
   # 測試資料庫連線
   python3 manage.py dbshell
   
   # 檢查環境變數
   cat .env | grep DATABASE
   ```

4. **權限問題**
   ```bash
   # 修復權限
   sudo chown -R mes:www-data /var/www/mes/
   sudo chown -R mes:www-data /var/log/mes/
   sudo chmod -R 755 /var/www/mes/
   ```

---

## 🔄 後續開發與維護

### 📝 開發流程（給程式開發人員）

#### 1. 日常開發
當您需要修改資料庫結構時（例如新增欄位、修改表格）：

```bash
# 1. 修改 models.py 檔案
# 2. 產生新的遷移檔案
python3 manage.py makemigrations

# 3. 在開發環境測試
python3 manage.py migrate
python3 manage.py runserver
```

#### 2. 準備部署
當開發完成，要部署到生產環境時：

```bash
# 1. 合併所有遷移檔案（解決依賴問題）
./合併遷移檔案.sh

# 2. 創建新的部署包
./創建部署包.sh

# 3. 將部署包上傳到生產環境
```

#### 2.1 遷移檔案管理（重要！）
**執行主機**：開發環境主機

在部署前，可能需要整理遷移檔案：

```bash
# 情況 A: 開發環境遷移問題
./重置遷移.sh

# 情況 B: 準備生產部署（完全清理）
./清理專案遷移.sh

# 情況 C: 檢查遷移狀態
python3 manage.py showmigrations
find . -path "*/migrations/*.py" -not -name "__init__.py" | wc -l
```

#### 3. 生產環境部署
```bash
# 1. 解壓新的部署包
tar -xzf mes_production_YYYYMMDD_HHMMSS.tar.gz

# 2. 執行部署
sudo ./全新部署.sh
```

### 🔄 系統更新流程（重要！）

#### 情況 1: 全新部署（第一次安裝）
```bash
# 適用於：全新的生產環境
sudo ./全新部署.sh
```

#### 情況 2: 系統更新（已有系統，要更新功能）
```bash
# 1. 備份現有系統
sudo -u postgres pg_dump mes_db > /backup/mes_db_before_update_$(date +%Y%m%d_%H%M%S).sql
sudo tar -czf /backup/mes_files_before_update_$(date +%Y%m%d_%H%M%S).tar.gz /var/www/mes/

# 2. 停止服務
sudo systemctl stop gunicorn-mes_config celery-mes_config

# 3. 備份當前程式碼
sudo cp -r /var/www/mes /var/www/mes_backup_$(date +%Y%m%d_%H%M%S)

# 4. 解壓新版本
cd /var/www
sudo tar -xzf mes_production_YYYYMMDD_HHMMSS.tar.gz
sudo mv mes mes_old
sudo mv mes_production_YYYYMMDD_HHMMSS mes

# 5. 設定權限
sudo chown -R mes:www-data /var/www/mes/
sudo chmod -R 755 /var/www/mes/

# 6. 更新環境設定（保留原有的 .env）
sudo cp /var/www/mes_old/.env /var/www/mes/

# 7. 執行資料庫遷移
cd /var/www/mes
source venv/bin/activate
python3 manage.py migrate

# 8. 收集靜態檔案
python3 manage.py collectstatic --noinput

# 9. 重啟服務
sudo systemctl start gunicorn-mes_config celery-mes_config

# 10. 檢查服務狀態
sudo systemctl status gunicorn-mes_config celery-mes_config

# 11. 測試網站功能
curl -I http://localhost

# 12. 如果一切正常，清理舊檔案
sudo rm -rf /var/www/mes_old
```

#### 情況 3: 緊急修復（只更新特定檔案）
```bash
# 適用於：修復 BUG，只更新少數檔案

# 1. 備份要修改的檔案
sudo cp /var/www/mes/workorder/views.py /backup/workorder_views_$(date +%Y%m%d_%H%M%S).py

# 2. 停止服務
sudo systemctl stop gunicorn-mes_config

# 3. 更新檔案
sudo cp new_workorder_views.py /var/www/mes/workorder/views.py

# 4. 重啟服務
sudo systemctl start gunicorn-mes_config

# 5. 檢查服務狀態
sudo systemctl status gunicorn-mes_config
```

### 🔧 系統維護（給系統管理員）

#### 遷移檔案維護
```bash
# 定期檢查遷移檔案狀態
find . -path "*/migrations/*.py" -not -name "__init__.py" | wc -l

# 檢查遷移記錄
python3 manage.py showmigrations

# 如果遷移檔案過多或混亂，考慮整理
./重置遷移.sh  # 開發環境
# 或
./清理專案遷移.sh  # 生產環境（謹慎使用）
```

#### 日常檢查
```bash
# 檢查所有服務是否正常運行
sudo systemctl status nginx postgresql redis-server
sudo systemctl status gunicorn-mes_config
sudo systemctl status celery-mes_config

# 檢查系統資源使用情況
htop                    # CPU 和記憶體使用
df -h                   # 硬碟空間
free -h                 # 記憶體使用
```

#### 查看日誌
```bash
# 查看 MES 系統日誌
tail -f /var/log/mes/django/mes.log

# 查看網站訪問日誌
tail -f /var/log/nginx/access.log

# 查看錯誤日誌
tail -f /var/log/nginx/error.log

# 查看 Celery 任務日誌
sudo journalctl -u celery-mes_config -f
```

#### 定期備份
```bash
# 備份資料庫（每天執行一次）
sudo -u postgres pg_dump mes_db > /backup/mes_db_$(date +%Y%m%d).sql

# 備份重要檔案
sudo tar -czf /backup/mes_files_$(date +%Y%m%d).tar.gz /var/www/mes/

# 保留最近 7 天的備份
find /backup/ -name "*.sql" -mtime +7 -delete
find /backup/ -name "*.tar.gz" -mtime +7 -delete
```

#### 系統更新
```bash
# 更新系統套件（每週執行一次）
sudo apt update
sudo apt upgrade -y

# 重啟服務
sudo systemctl restart nginx postgresql redis-server
sudo systemctl restart gunicorn-mes_config
sudo systemctl restart celery-mes_config

# 檢查服務狀態
sudo systemctl status nginx postgresql redis-server
sudo systemctl status gunicorn-mes_config
sudo systemctl status celery-mes_config
```

### 🚨 緊急處理

#### 服務無法啟動
```bash
# 1. 檢查錯誤日誌
sudo journalctl -u gunicorn-mes_config -n 50

# 2. 檢查資料庫連線
python3 manage.py dbshell

# 3. 重新啟動服務
sudo systemctl restart gunicorn-mes_config
```

#### 網站無法訪問
```bash
# 1. 檢查 Nginx 狀態
sudo systemctl status nginx

# 2. 檢查 Nginx 配置
sudo nginx -t

# 3. 重新載入 Nginx
sudo systemctl reload nginx
```

#### 資料庫問題
```bash
# 1. 檢查資料庫狀態
sudo systemctl status postgresql

# 2. 檢查資料庫連線
sudo -u postgres psql -d mes_db

# 3. 從備份還原（如果需要）
sudo -u postgres psql -d mes_db < /backup/mes_db_YYYYMMDD.sql
```

### 📋 維護檢查清單

#### 每日檢查
- [ ] 網站是否可以正常訪問
- [ ] 所有服務是否正常運行
- [ ] 系統資源使用是否正常
- [ ] 錯誤日誌是否有異常

#### 每週檢查
- [ ] 執行系統更新
- [ ] 檢查備份是否成功
- [ ] 清理舊的日誌檔案
- [ ] 檢查磁碟空間

#### 每月檢查
- [ ] 檢查系統效能
- [ ] 更新安全套件
- [ ] 檢查備份還原測試
- [ ] 檢查使用者權限

---

## 📞 技術支援

### 緊急聯絡
- **系統管理員**: [聯絡資訊]
- **技術支援**: [聯絡資訊]
- **緊急電話**: [電話號碼]

### 相關文件
- [MES 系統使用手冊]
- [API 文件]
- [開發者文件]

---

## 📝 版本資訊

- **文件版本**: 1.0
- **最後更新**: 2025-08-28
- **適用版本**: MES 系統 v1.0
- **作者**: MES 開發團隊

---

## 🎉 總結

通過使用遷移合併技術，我們可以：
1. 簡化生產環境的部署流程
2. 減少遷移依賴問題
3. 確保開發環境和生產環境的一致性
4. 提高部署的可靠性和效率

這個解決方案特別適合需要頻繁部署的專案，可以大大減少部署過程中的問題和風險。

---

**注意**: 本文件適用於 MES 系統的生產環境部署。如有疑問，請聯絡技術支援團隊。
