#!/bin/bash

# 腳本版本號
SCRIPT_VERSION="1.6.4"

# 使用主腳本定義的日誌文件
LOG_FILE="/var/log/mes/deploy.log"

# 定義工作目錄和關鍵路徑
PROJECT_DIR="/var/www/mes"
DJANGO_PROJECT_NAME="mes_config"

# 記錄腳本開始執行
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [v$SCRIPT_VERSION] 開始執行 $(basename "$0")..."

# 檢查環境中是否已存在 ENV_CONTENT 變數，若存在則清空
if [ -n "$ENV_CONTENT" ]; then
    echo "警告: 環境中已存在 ENV_CONTENT 變數，將其清空以避免衝突" | tee -a "$LOG_FILE"
    unset ENV_CONTENT
fi

# 定義 .env 內容（硬編碼方式，移除密碼引號）
HOST_IP=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -n 1)
if [ -z "$HOST_IP" ]; then
    echo "錯誤: 找不到主機 IP，嘗試重試..." | tee -a "$LOG_FILE"
    sleep 2
    HOST_IP=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -n 1)
    if [ -z "$HOST_IP" ]; then
        echo "錯誤: 仍無法獲取主機 IP" | tee -a "$LOG_FILE"
        exit 1
    fi
fi
echo "提取的主機 IP: $HOST_IP" | tee -a "$LOG_FILE"

# 定義預設變數
DATABASE_NAME="mes_db"
DATABASE_USER="mes_user"
DATABASE_PASSWORD="mes_password"
DATABASE_HOST="localhost"
DATABASE_PORT="5432"
SUPERUSER_NAME="admin"
SUPERUSER_PASSWORD="1234"

# 生成 DATABASE_URL
DATABASE_URL="postgresql://$DATABASE_USER:$DATABASE_PASSWORD@$DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo "生成的 DATABASE_URL: $DATABASE_URL" | tee -a "$LOG_FILE"

DJANGO_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n' | sed 's/[\/&]/\\&/g')
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "錯誤: 無法生成 DJANGO_SECRET_KEY" | tee -a "$LOG_FILE"
    exit 1
fi
echo "生成的 DJANGO_SECRET_KEY: [隱藏]" | tee -a "$LOG_FILE"

# 使用 cat << EOF（無單引號）生成 ENV_CONTENT，確保變數替換
ENV_CONTENT=$(cat << EOF
DJANGO_SECRET_KEY='$DJANGO_SECRET_KEY'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP
HOST_IP=$HOST_IP
DATABASE_NAME=$DATABASE_NAME
DATABASE_USER=$DATABASE_USER
DATABASE_PASSWORD=$DATABASE_PASSWORD
DATABASE_HOST=$DATABASE_HOST
DATABASE_PORT=$DATABASE_PORT
DATABASE_URL='$DATABASE_URL'
CELERY_BROKER_URL=redis://:mesredis2025@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:mesredis2025@127.0.0.1:6379/0
LOG_FILE=/var/log/mes/django/mes.log
SERVER_NAME=mes
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=mesredis2025
REDIS_MAXMEMORY=2147483648
REDIS_MAXCLIENTS=1000
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=user@gmail.com
EMAIL_HOST_PASSWORD=user_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=MES@gmail.com
SUPERUSER_NAME=$SUPERUSER_NAME
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=$SUPERUSER_PASSWORD
PROJECT_DIR=/var/www/mes
LOG_BASE_DIR=/var/log/mes
BACKUP_DIR=/var/www/mes/backups_DB
APP_USER=mes
APP_GROUP=www-data
GUNICORN_PORT=8000
NGINX_PORT=80
GUNICORN_WORKERS=3
DJANGO_PROJECT_NAME=mes_config
LANGUAGE_CODE=zh-hant
TIME_ZONE=Asia/Taipei
SESSION_COOKIE_AGE=259200
STATIC_ROOT=/var/www/mes/static
LOCALE_DIR=/var/www/mes/locale
TEMP_DIR=/tmp
REQUIREMENTS_FILE=/var/www/mes/requirements.txt
EOF
)

# MAXMEMORY 公式 2 GB = 2 * 1,073,741,824 字節 = 2,147,483,648 字節

# 驗證 ENV_CONTENT 是否生成
if [ -z "$ENV_CONTENT" ]; then
    echo "錯誤: ENV_CONTENT 未正確生成，請檢查腳本執行環境是否為 bash" | tee -a "$LOG_FILE"
    exit 1
fi
echo "ENV_CONTENT 已生成，包含正確的 DATABASE_URL: $DATABASE_URL" | tee -a "$LOG_FILE"

# 替換 DJANGO_SECRET_KEY 和 HOST_IP
ENV_CONTENT=$(echo "$ENV_CONTENT" | sed "s|DJANGO_SECRET_KEY_VALUE|$DJANGO_SECRET_KEY|" | sed "s|HOST_IP_VALUE|$HOST_IP|g")
if [ $? -ne 0 ]; then
    echo "錯誤: 替換 DJANGO_SECRET_KEY 或 HOST_IP 失敗" | tee -a "$LOG_FILE"
    echo "DJANGO_SECRET_KEY: [隱藏]" | tee -a "$LOG_FILE"
    echo "HOST_IP: $HOST_IP" | tee -a "$LOG_FILE"
    exit 1
fi
echo "ENV_CONTENT 替換後內容如下:" | tee -a "$LOG_FILE"
echo "$ENV_CONTENT" | tee -a "$LOG_FILE"

# 步驟 0-1: 檢查並修正 mes 用戶家目錄權限
echo "步驟 0-1: 檢查並修正 mes 用戶家目錄權限..." | tee -a "$LOG_FILE"
if [ "$(id -u)" != "0" ]; then
    echo "錯誤: 腳本必須以 root 權限執行，請使用 'sudo $0' 運行" | tee -a "$LOG_FILE"
    exit 1
fi
echo "驗證成功: 腳本以 root 權限運行" | tee -a "$LOG_FILE"

if [ -z "$LOG_FILE" ]; then
    echo "錯誤: 日誌文件變數 LOG_FILE 未定義" | tee -a "$LOG_FILE"
    exit 1
fi
LOG_DIR=$(dirname "$LOG_FILE")
if [ ! -w "$LOG_DIR" ]; then
    echo "錯誤: 日誌文件目錄 $LOG_DIR 不可寫" | tee -a "$LOG_FILE"
    exit 1
fi
echo "驗證成功: 日誌文件 $LOG_FILE 可寫" | tee -a "$LOG_FILE"

if ! id "mes" >/dev/null 2>&1; then
    echo "錯誤: mes 使用者不存在，請先創建 mes 使用者" | tee -a "$LOG_FILE"
    exit 1
fi
echo "驗證成功: mes 使用者已存在" | tee -a "$LOG_FILE"

if [ -d "/home/mes" ]; then
    echo "家目錄 /home/mes 已存在，檢查權限..." | tee -a "$LOG_FILE"
    CURRENT_OWNER=$(stat -c '%U:%G' /home/mes)
    if [ "$CURRENT_OWNER" != "mes:mes" ]; then
        chown mes:mes /home/mes 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
            echo "錯誤: 無法修正 /home/mes 的所有者權限 (chown 失敗)" | tee -a "$LOG_FILE"
            exit 1
        fi
        echo "已修正 /home/mes 的所有者為 mes:mes" | tee -a "$LOG_FILE"
    fi
    CURRENT_PERM=$(stat -c '%a' /home/mes)
    if [ "$CURRENT_PERM" != "755" ]; then
        chmod 755 /home/mes 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
            echo "錯誤: 無法修正 /home/mes 的權限 (chmod 失敗)" | tee -a "$LOG_FILE"
            exit 1
        fi
        echo "已修正 /home/mes 的權限為 755" | tee -a "$LOG_FILE"
    fi
    echo "成功檢查並修正 /home/mes 權限" | tee -a "$LOG_FILE"
else
    echo "家目錄 /home/mes 不存在，正在創建..." | tee -a "$LOG_FILE"
    mkdir -p /home/mes 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法創建 /home/mes 目錄 (mkdir 失敗)" | tee -a "$LOG_FILE"
        exit 1
    fi
    chown mes:mes /home/mes 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法設置 /home/mes 的所有者權限 (chown 失敗)" | tee -a "$LOG_FILE"
        exit 1
    fi
    chmod 755 /home/mes 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法設置 /home/mes 的權限 (chmod 失敗)" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "成功創建並設置 /home/mes 權限" | tee -a "$LOG_FILE"
fi

echo "將 mes 使用者加入 www-data 群組..." | tee -a "$LOG_FILE"
if ! getent group www-data >/dev/null 2>&1; then
    echo "www-data 群組不存在，正在創建..." | tee -a "$LOG_FILE"
    groupadd www-data 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法創建 www-data 群組" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "成功創建 www-data 群組" | tee -a "$LOG_FILE"
fi
usermod -aG www-data mes 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法將 mes 使用者加入 www-data 群組" | tee -a "$LOG_FILE"
    getent group www-data 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi
if ! groups mes | grep -q www-data; then
    echo "錯誤: mes 使用者未成功加入 www-data 群組" | tee -a "$LOG_FILE"
    groups mes 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi
echo "成功: mes 使用者已加入 www-data 群組" | tee -a "$LOG_FILE"

# 步驟 0-2: 設置環境變數和日誌文件處理
echo "步驟 0-2: 設置環境變數和日誌文件處理..." | tee -a "$LOG_FILE"

# 設置環境變數，確保包含 /usr/local/bin 和 /home/mes/.local/bin
export PATH=$PATH:/usr/local/bin:/home/mes/.local/bin
export PYTHONPATH=/usr/lib/python3/dist-packages:/usr/local/lib/python3.10/dist-packages:/home/mes/.local/lib/python3.10/site-packages:$PYTHONPATH
echo "環境變數已設置: PATH=$PATH" | tee -a "$LOG_FILE"
echo "環境變數已設置: PYTHONPATH=$PYTHONPATH" | tee -a "$LOG_FILE"

# 檢查並處理日誌目錄 /var/log/mes
if [ -d "/var/log/mes" ]; then
  echo "發現 /var/log/mes 目錄，正在清除內容以確保日誌為新..." | tee -a "$LOG_FILE"
  # 清除 /var/log/mes 下的所有檔案和子目錄，但保留目錄本身
  find /var/log/mes -mindepth 1 -type f -exec rm -f {} + 2>&1 | tee -a "$LOG_FILE"
  find /var/log/mes -mindepth 1 -type d -exec rm -rf {} + 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法清除 /var/log/mes 目錄下的內容，請檢查權限或磁碟空間" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "已成功清除 /var/log/mes 目錄下的內容" | tee -a "$LOG_FILE"
else
  echo "/var/log/mes 目錄不存在，正在創建..." | tee -a "$LOG_FILE"
  mkdir -p /var/log/mes 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法創建日誌目錄 /var/log/mes，請檢查權限或磁碟空間" | tee -a "$LOG_FILE"
    exit 1
  fi
fi

# 設置 /var/log/mes 目錄權限，確保 mes 使用者可寫入
chown mes:mes /var/log/mes
chmod 755 /var/log/mes

# 檢查 /var/log/mes 目錄的權限，確保可以寫入
sudo -u mes touch /var/log/mes/test_file 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: mes 使用者無法在 /var/log/mes 目錄中寫入檔案，請檢查權限或磁碟空間" | tee -a "$LOG_FILE"
  exit 1
fi
rm -f /var/log/mes/test_file

# 確保日誌檔案是新的（每次執行腳本時創建新檔案）
echo "創建新的日誌檔案 $LOG_FILE..." | tee "$LOG_FILE"
touch "$LOG_FILE" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法創建日誌檔案 $LOG_FILE，請檢查權限或磁碟空間" | tee -a "$LOG_FILE"
  exit 1
fi
echo "腳本版本號: $SCRIPT_VERSION" | tee -a "$LOG_FILE"
echo "日誌檔案 $LOG_FILE 已準備好" | tee -a "$LOG_FILE"

# 設置日誌檔案權限
chown mes:mes "$LOG_FILE"
chmod 644 "$LOG_FILE"

# 步驟 0-3: 檢查並安裝必須工具 lsof
echo "步驟 0-3: 檢查並安裝必須工具 lsof..." | tee -a "$LOG_FILE"
if ! which lsof >/dev/null && ! [ -x /usr/bin/lsof ]; then
  echo "lsof 未安裝，正在安裝..." | tee -a "$LOG_FILE"
  apt update 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
  apt install -y lsof 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 lsof，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "lsof 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
if ! which lsof >/dev/null && ! [ -x /usr/bin/lsof ]; then
  echo "驗證失敗: lsof 未正確安裝，無法繼續執行腳本" | tee -a "$LOG_FILE"
  exit 1
fi
echo "驗證成功: lsof 已準備就緒" | tee -a "$LOG_FILE"

# 步驟 0-4: 檢查並安裝必須工具 unzip
echo "步驟 0-4: 檢查並安裝必須工具 unzip..." | tee -a "$LOG_FILE"
if ! command -v unzip >/dev/null 2>&1; then
  echo "unzip 未安裝，正在安裝..." | tee -a "$LOG_FILE"
  apt update 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
  apt install -y unzip 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 unzip，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "unzip 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
if ! command -v unzip >/dev/null 2>&1; then
  echo "驗證失敗: unzip 未正確安裝，無法繼續執行腳本" | tee -a "$LOG_FILE"
  exit 1
fi
echo "驗證成功: unzip 已準備就緒" | tee -a "$LOG_FILE"

# 步驟 0-5: 設置無人值守模式
echo "步驟 0-5: 設置無人值守模式..." | tee -a "$LOG_FILE"
export DEBIAN_FRONTEND=noninteractive
echo "已設置 DEBIAN_FRONTEND=noninteractive" | tee -a "$LOG_FILE"

# 步驟 0-6: 安裝 apt-utils 以減少 debconf 警告
echo "步驟 0-6: 安裝 apt-utils 以減少 debconf 警告..." | tee -a "$LOG_FILE"
if ! dpkg -l | grep -q apt-utils; then
  echo "apt-utils 未安裝，正在安裝..." | tee -a "$LOG_FILE"
  apt update 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
  apt install -y apt-utils 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 apt-utils，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "apt-utils 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
echo "apt-utils 已安裝" | tee -a "$LOG_FILE"

# 步驟 0-7: 安裝 dialog 套件以避免 debconf 警告
echo "步驟 0-7: 安裝 dialog 套件以避免 debconf 警告..." | tee -a "$LOG_FILE"
if ! dpkg -l | grep -q dialog; then
  echo "dialog 套件未安裝，正在安裝..." | tee -a "$LOG_FILE"
  apt update 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
  apt install -y dialog 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 dialog 套件，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "dialog 套件已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
echo "dialog 套件已安裝" | tee -a "$LOG_FILE"

# 步驟 0-8: 設置 vm.overcommit_memory 為 0（Redis 建議值）
echo "步驟 0-8: 設置 vm.overcommit_memory 為 0（Redis 建議值）..." | tee -a "$LOG_FILE"
if ! command -v sysctl >/dev/null 2>&1; then
  echo "警告: sysctl 命令不可用，可能在容器環境中，無法設置 vm.overcommit_memory" | tee -a "$LOG_FILE"
  echo "建議: 如果在容器中，請通過容器啟動參數設置 --sysctl vm.overcommit_memory=0" | tee -a "$LOG_FILE"
  echo "繼續執行後續步驟，但可能影響 Redis 行為" | tee -a "$LOG_FILE"
else
  # 檢查當前 vm.overcommit_memory 設置
  CURRENT_OVERCOMMIT=$(sysctl -n vm.overcommit_memory 2>/dev/null)
  if [ $? -ne 0 ]; then
    echo "警告: 無法檢查 vm.overcommit_memory，可能沒有權限或環境限制" | tee -a "$LOG_FILE"
    CURRENT_OVERCOMMIT="unknown"
  else
    echo "當前 vm.overcommit_memory 設置: $CURRENT_OVERCOMMIT" | tee -a "$LOG_FILE"
  fi

  if [ "$CURRENT_OVERCOMMIT" != "0" ]; then
    echo "vm.overcommit_memory 未設為 0，嘗試設置..." | tee -a "$LOG_FILE"
    sysctl vm.overcommit_memory=0 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
      echo "警告: 無法立即設置 vm.overcommit_memory，可能沒有權限或環境限制" | tee -a "$LOG_FILE"
    else
      echo "成功: 已立即設置 vm.overcommit_memory 為 0" | tee -a "$LOG_FILE"
    fi

    # 持久化設置（嘗試多個配置文件）
    SYSCTL_CONF_FILE=""
    if [ -f /etc/sysctl.conf ] && [ -w /etc/sysctl.conf ]; then
      SYSCTL_CONF_FILE="/etc/sysctl.conf"
    elif [ -d /etc/sysctl.d ] && [ -w /etc/sysctl.d ]; then
      SYSCTL_CONF_FILE="/etc/sysctl.d/99-custom.conf"
    else
      echo "警告: 找不到可寫的 sysctl 配置文件（/etc/sysctl.conf 或 /etc/sysctl.d），無法持久化設置" | tee -a "$LOG_FILE"
    fi

    if [ -n "$SYSCTL_CONF_FILE" ]; then
      if ! grep -q "vm.overcommit_memory" "$SYSCTL_CONF_FILE"; then
        echo "vm.overcommit_memory = 0" >> "$SYSCTL_CONF_FILE" 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
          echo "警告: 無法將 vm.overcommit_memory 寫入 $SYSCTL_CONF_FILE，請手動檢查" | tee -a "$LOG_FILE"
        else
          echo "成功: 已將 vm.overcommit_memory 持久化設置到 $SYSCTL_CONF_FILE" | tee -a "$LOG_FILE"
        fi
      else
        sed -i 's/.*vm.overcommit_memory.*/vm.overcommit_memory = 0/' "$SYSCTL_CONF_FILE" 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
          echo "警告: 無法更新 $SYSCTL_CONF_FILE 中的 vm.overcommit_memory，請手動檢查" | tee -a "$LOG_FILE"
        else
          echo "成功: 已更新 $SYSCTL_CONF_FILE 中的 vm.overcommit_memory 設置" | tee -a "$LOG_FILE"
        fi
      fi
    fi
  else
    echo "vm.overcommit_memory 已設為 0，無需更改" | tee -a "$LOG_FILE"
  fi

  # 驗證設置（允許繼續執行）
  CURRENT_OVERCOMMIT=$(sysctl -n vm.overcommit_memory 2>/dev/null)
  if [ $? -ne 0 ]; then
    echo "警告: 無法驗證 vm.overcommit_memory 設置，可能沒有權限或環境限制" | tee -a "$LOG_FILE"
    echo "繼續執行後續步驟，但可能影響 Redis 行為" | tee -a "$LOG_FILE"
  elif [ "$CURRENT_OVERCOMMIT" != "0" ]; then
    echo "警告: 無法將 vm.overcommit_memory 設為 0，請手動檢查" | tee -a "$LOG_FILE"
    echo "繼續執行後續步驟，但可能影響 Redis 行為" | tee -a "$LOG_FILE"
  else
    echo "驗證成功: vm.overcommit_memory 已設為 0" | tee -a "$LOG_FILE"
  fi
fi

echo "步驟 0-8 完成" | tee -a "$LOG_FILE"

# 步驟 0-9: 檢查並安裝 xlrd 庫


# 步驟 0-10: 設置系統時區為 Asia/Taipei...
echo "步驟 0-10: 設置系統時區為 Asia/Taipei..." | tee -a "$LOG_FILE"
CURRENT_TZ=$(timedatectl show --property=Timezone --value)
if [ "$CURRENT_TZ" != "Asia/Taipei" ]; then
  timedatectl set-timezone Asia/Taipei 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法設置系統時區為 Asia/Taipei" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "系統時區已設置為 Asia/Taipei" | tee -a "$LOG_FILE"
else
  echo "當前系統時區: $CURRENT_TZ" | tee -a "$LOG_FILE"
  echo "系統時區已是 Asia/Taipei，無需更改" | tee -a "$LOG_FILE"
fi

# 驗證時區設置
CURRENT_TZ=$(timedatectl show --property=Timezone --value)
if [ "$CURRENT_TZ" != "Asia/Taipei" ]; then
  echo "錯誤: 系統時區設置失敗，當前時區為 $CURRENT_TZ" | tee -a "$LOG_FILE"
  exit 1
fi
echo "驗證成功: 系統時區已設置為 Asia/Taipei" | tee -a "$LOG_FILE"

# 安裝時間同步工具（ntpdate）
echo "安裝時間同步工具（ntpdate）..." | tee -a "$LOG_FILE"
if ! command -v ntpdate >/dev/null 2>&1; then
  apt-get install -y ntpdate 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 ntpdate" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "ntpdate 已安裝" | tee -a "$LOG_FILE"
else
  echo "ntpdate 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi

# 同步系統時間
echo "同步系統時間..." | tee -a "$LOG_FILE"
ntpdate pool.ntp.org 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "警告: 無法通過 pool.ntp.org 同步時間，嘗試使用備用伺服器..." | tee -a "$LOG_FILE"
  ntpdate time.google.com 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法同步系統時間" | tee -a "$LOG_FILE"
    exit 1
  fi
fi
echo "系統時間已通過 ntpdate 同步" | tee -a "$LOG_FILE"

# 步驟 0-11: 簡化網路連通性檢查
echo "步驟 0-11: 檢查網路連通性..." | tee -a "$LOG_FILE"

# 檢查 DNS 設定
echo "檢查 DNS 設定..." | tee -a "$LOG_FILE"
cat /etc/resolv.conf 2>&1 | tee -a "$LOG_FILE"
if grep -q "nameserver" /etc/resolv.conf; then
  echo "DNS 設定正常" | tee -a "$LOG_FILE"
else
  echo "警告: 未檢測到 DNS 設定，嘗試修復..." | tee -a "$LOG_FILE"
  echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf 2>&1 | tee -a "$LOG_FILE"
  echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf 2>&1 | tee -a "$LOG_FILE"
  if grep -q "nameserver" /etc/resolv.conf; then
    echo "DNS 設定已修復" | tee -a "$LOG_FILE"
  else
    echo "錯誤: 無法修復 DNS 設定，請手動檢查 /etc/resolv.conf" | tee -a "$LOG_FILE"
    exit 1
  fi
fi

# 測試網路連通性（僅檢查基本連通性）
echo "測試網路連通性（ping 測試）..." | tee -a "$LOG_FILE"
ping -c 4 8.8.8.8 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法連接到外部網路，請檢查網路設定" | tee -a "$LOG_FILE"
  exit 1
fi
echo "網路連通性正常" | tee -a "$LOG_FILE"

echo "步驟 0-11 完成: 網路連通性檢查完成" | tee -a "$LOG_FILE"

# 步驟 0-12: 安裝 build-essential
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 步驟 0-12: 安裝 build-essential..." | tee -a "$LOG_FILE"
if ! dpkg -s build-essential >/dev/null 2>&1; then
    apt-get update 2>&1 | tee -a "$LOG_FILE"
    apt-get install -y build-essential 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤: 無法安裝 build-essential" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] build-essential 安裝完成" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] build-essential 已安裝，跳過" | tee -a "$LOG_FILE"
fi

# 步驟 0-13: 安裝 curl
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 步驟 0-13: 安裝 curl..." | tee -a "$LOG_FILE"
if ! command -v curl >/dev/null 2>&1; then
    apt-get install -y curl 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤: 無法安裝 curl" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] curl 安裝完成" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] curl 已安裝，跳過" | tee -a "$LOG_FILE"
fi

# 步驟 1: 清理環境，確保乾淨
echo "步驟 1: 清理環境，確保乾淨..." | tee -a "$LOG_FILE"

# 子步驟 1-1: 清理 /var/www/mes 目錄
echo "子步驟 1-1: 清理 /var/www/mes 目錄..." | tee -a "$LOG_FILE"
if [ -d "/var/www/mes" ]; then
  echo "/var/www/mes 目錄已存在，正在刪除..." | tee -a "$LOG_FILE"
  rm -rf /var/www/mes 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法刪除 /var/www/mes 目錄" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "已成功刪除 /var/www/mes 目錄" | tee -a "$LOG_FILE"
else
  echo "/var/www/mes 目錄不存在，無需清理" | tee -a "$LOG_FILE"
fi
# 創建 /var/www/mes 目錄並設置權限
mkdir -p /var/www/mes 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法創建 /var/www/mes 目錄" | tee -a "$LOG_FILE"
  exit 1
fi
# 設置 /var/www/mes 目錄權限（群組為 www-data）
chown mes:www-data /var/www/mes 2>&1 | tee -a "$LOG_FILE"
chmod 775 /var/www/mes 2>&1 | tee -a "$LOG_FILE"
# 檢查 /var/www/mes 目錄是否可寫
sudo -u mes touch /var/www/mes/test_write 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: mes 使用者無法在 /var/www/mes 目錄中寫入檔案，請檢查權限或文件系統" | tee -a "$LOG_FILE"
  ls -ld /var/www/mes 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
rm -f /var/www/mes/test_write 2>&1 | tee -a "$LOG_FILE"
echo "已重新創建 /var/www/mes 目錄並設置權限" | tee -a "$LOG_FILE"

# 子步驟 1-2: 清理舊的 Gunicorn 進程
echo "子步驟 1-2: 清理舊的 Gunicorn 進程..." | tee -a "$LOG_FILE"
if lsof -i :8000 -t > /dev/null; then
  GUNICORN_PID=$(lsof -i :8000 -t)
  echo "發現占用 8000 端口的進程 (PID: $GUNICORN_PID)，正在終止 (嘗試 1)..." | tee -a "$LOG_FILE"
  lsof -i :8000 2>&1 | tee -a "$LOG_FILE"
  kill -9 $GUNICORN_PID 2>&1 | tee -a "$LOG_FILE"
  sleep 1
  if lsof -i :8000 -t > /dev/null; then
    echo "錯誤: 無法清理 8000 端口，仍然被占用，請檢查系統進程" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "8000 端口已清理" | tee -a "$LOG_FILE"
else
  echo "8000 端口未被占用，無需清理" | tee -a "$LOG_FILE"
fi

# 子步驟 1-3: 清理 Gunicorn systemd 服務...
echo "子步驟 1-3: 清理 Gunicorn systemd 服務..." | tee -a "$LOG_FILE"
# 停止 Gunicorn 服務（如果存在）
if systemctl is-active --quiet gunicorn-mes_config; then
    echo "停止 Gunicorn 服務..." | tee -a "$LOG_FILE"
    systemctl stop gunicorn-mes_config 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "警告: 無法停止 Gunicorn 服務，繼續清理..." | tee -a "$LOG_FILE"
    fi
fi
# 禁用 Gunicorn 服務（如果存在）
if systemctl is-enabled --quiet gunicorn-mes_config; then
    echo "禁用 Gunicorn 服務..." | tee -a "$LOG_FILE"
    systemctl disable gunicorn-mes_config 2>&1 | tee -a "$LOG_FILE"
fi
# 移除 Gunicorn 服務單元文件
if [ -f /etc/systemd/system/gunicorn-mes_config.service ]; then
    echo "移除 Gunicorn 服務單元文件..." | tee -a "$LOG_FILE"
    rm -f /etc/systemd/system/gunicorn-mes_config.service 2>&1 | tee -a "$LOG_FILE"
fi
systemctl daemon-reload 2>&1 | tee -a "$LOG_FILE"
systemctl reset-failed 2>&1 | tee -a "$LOG_FILE"
echo "Gunicorn systemd 服務已清理" | tee -a "$LOG_FILE"

# 子步驟 1-4: 清理 Gunicorn 進程和端口...
echo "子步驟 1-4: 清理 Gunicorn 進程和端口..." | tee -a "$LOG_FILE"
# 檢查並清理佔用端口 8000 的進程
if netstat -tulnp 2>/dev/null | grep ":8000 " >/dev/null; then
    echo "發現端口 8000 被佔用，正在清理..." | tee -a "$LOG_FILE"
    pids=$(netstat -tulnp 2>/dev/null | grep ":8000 " | awk '{print $7}' | cut -d'/' -f1 | sort -u)
    for pid in $pids; do
        echo "終止進程 PID: $pid..." | tee -a "$LOG_FILE"
        kill -9 $pid 2>&1 | tee -a "$LOG_FILE"
    done
    sleep 1
fi
# 檢查是否有殘留的 Gunicorn 進程
if pgrep -u mes -f "gunicorn.*mes_config" >/dev/null; then
    echo "發現殘留的 Gunicorn 進程，正在清理..." | tee -a "$LOG_FILE"
    pkill -u mes -f "gunicorn.*mes_config" 2>&1 | tee -a "$LOG_FILE"
    sleep 1
fi
# 確認端口和進程已清理
if netstat -tulnp 2>/dev/null | grep ":8000 " >/dev/null; then
    echo "錯誤: 無法清理端口 8000，請手動檢查" | tee -a "$LOG_FILE" >&2
    exit 1
fi
if pgrep -u mes -f "gunicorn.*mes_config" >/dev/null; then
    echo "錯誤: 無法清理 Gunicorn 進程，請手動檢查" | tee -a "$LOG_FILE" >&2
    exit 1
fi
echo "Gunicorn 進程和端口已清理" | tee -a "$LOG_FILE"

# 子步驟 1-5: 清理 Celery systemd 服務
echo "子步驟 1-5: 清理 Celery systemd 服務..." | tee -a "$LOG_FILE"
CELERY_SERVICES=$(systemctl list-units --all | grep -E 'celery|celery-beat' | awk '{print $1}')
for service in $CELERY_SERVICES; do
    if systemctl list-units --all | grep -q "$service"; then
        systemctl stop "$service" 2>&1 | tee -a "$LOG_FILE"
        systemctl disable "$service" 2>&1 | tee -a "$LOG_FILE"
        rm -f "/etc/systemd/system/$service" 2>&1 | tee -a "$LOG_FILE"
        systemctl daemon-reload 2>&1 | tee -a "$LOG_FILE"
        systemctl reset-failed 2>&1 | tee -a "$LOG_FILE"
        echo "$service systemd 服務已清理" | tee -a "$LOG_FILE"
    else
        echo "$service systemd 服務不存在，無需清理" | tee -a "$LOG_FILE"
    fi
done

# 子步驟 1-6: 清理 Celery 日誌檔案
echo "子步驟 1-6: 清理 Celery 日誌檔案..." | tee -a "$LOG_FILE"
rm -rf /var/log/mes/celery.log 2>&1 | tee -a "$LOG_FILE"
rm -rf /var/log/mes/celery 2>&1 | tee -a "$LOG_FILE"  # 修改：清理 Celery Beat 日誌目錄
echo "Celery 日誌檔案已清理" | tee -a "$LOG_FILE"

# 子步驟 1-7: 清理 Nginx...
echo "子步驟 1-7: 清理 Nginx..." | tee -a "$LOG_FILE"
echo "停止 Nginx 服務 (嘗試 1)..." | tee -a "$LOG_FILE"
if systemctl is-active --quiet nginx; then
  systemctl stop nginx 2>&1 | tee -a "$LOG_FILE"
  systemctl disable nginx 2>&1 | tee -a "$LOG_FILE"
  echo "Nginx 服務已停止並禁用" | tee -a "$LOG_FILE"
else
  echo "Nginx 服務未運行，無需停止" | tee -a "$LOG_FILE"
fi

echo "檢查是否有 Nginx 進程..." | tee -a "$LOG_FILE"
if lsof -i :80 | grep -q nginx; then
  echo "發現 Nginx 進程，嘗試終止..." | tee -a "$LOG_FILE"
  killall nginx 2>&1 | tee -a "$LOG_FILE"
  sleep 2
  if lsof -i :80 | grep -q nginx; then
    echo "錯誤: 無法終止 Nginx 進程" | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "Nginx 進程已終止" | tee -a "$LOG_FILE"
else
  echo "未發現 Nginx 進程，無需終止" | tee -a "$LOG_FILE"
fi

echo "移除 Nginx 套件..." | tee -a "$LOG_FILE"
echo "預清理 Nginx 相關配置文件以避免卡住..." | tee -a "$LOG_FILE"
apt-get remove -y --purge nginx nginx-common nginx-core libnginx-mod-* 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法移除 Nginx 套件" | tee -a "$LOG_FILE"
  exit 1
fi

# 保護網路相關套件
echo "保護網路相關套件..." | tee -a "$LOG_FILE"
apt-get install -y isc-dhcp-client isc-dhcp-common iproute2 netplan.io network-manager iputils-ping 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝網路相關套件" | tee -a "$LOG_FILE"
  exit 1
fi

# 保護 vim 和 net-tools
echo "保護 vim 和 net-tools 套件..." | tee -a "$LOG_FILE"
apt-get install -y vim vim-runtime net-tools 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝 vim 和 net-tools 套件" | tee -a "$LOG_FILE"
  exit 1
fi

echo "跳過 apt autoremove 操作以避免服務重啟..." | tee -a "$LOG_FILE"
echo "移除 Nginx 配置文件和數據目錄..." | tee -a "$LOG_FILE"
rm -rf /etc/nginx /usr/share/nginx /var/cache/nginx /var/run/nginx.pid 2>&1 | tee -a "$LOG_FILE"
echo "強制清理 /var/www/html 目錄..." | tee -a "$LOG_FILE"
rm -rf /var/www/html 2>&1 | tee -a "$LOG_FILE"
echo "80 端口未被占用，無需清理" | tee -a "$LOG_FILE"
echo "Nginx 已清理" | tee -a "$LOG_FILE"

# 子步驟 1-8: 清理 Apache
echo "子步驟 1-8: 清理 Apache..." | tee -a "$LOG_FILE"
# 停止 Apache 服務
if systemctl list-units --full -all | grep -q "apache2.service"; then
  systemctl stop apache2 2>&1 | tee -a "$LOG_FILE"
  systemctl disable apache2 2>&1 | tee -a "$LOG_FILE"
fi
# 移除 Apache 套件
if dpkg -l | grep -q apache2; then
  echo "移除 Apache 套件..." | tee -a "$LOG_FILE"
  timeout 300 apt remove --purge --force-yes -y apache2 apache2-bin apache2-data apache2-utils 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法移除 Apache 套件，嘗試強制清理..." | tee -a "$LOG_FILE"
    timeout 300 apt remove --purge --force-yes -y apache2 apache2-bin apache2-data apache2-utils 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
      echo "錯誤: 無法移除 Apache 套件，請手動檢查並移除" | tee -a "$LOG_FILE"
      exit 1
    fi
  fi
  timeout 300 apt autoremove --purge -y 2>&1 | tee -a "$LOG_FILE"
fi
# 移除 Apache 配置文件和日誌目錄
rm -rf /etc/apache2 2>&1 | tee -a "$LOG_FILE"
rm -rf /var/log/apache2 2>&1 | tee -a "$LOG_FILE"
echo "Apache 已清理" | tee -a "$LOG_FILE"

# 子步驟 1-9: 清理非系統默認的 Python 套件...
echo "子步驟 1-9: 清理非系統默認的 Python 套件..." | tee -a "$LOG_FILE"
echo "使用 apt 移除系統級 Python 套件（排除系統核心套件和依賴）..." | tee -a "$LOG_FILE"

# 移除非核心 Python 套件（保留 netplan.io 所需的依賴）
echo "發現非核心系統級 Python 套件，正在移除..." | tee -a "$LOG_FILE"
apt-get remove -y --purge \
  libpython3-dev \
  libpython3.10-dev \
  python3-dev \
  python3-distutils \
  python3-lib2to3 \
  python3-pip \
  python3-pkg-resources \
  python3-setuptools \
  python3-wheel \
  python3.10-dev 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法移除非核心 Python 套件" | tee -a "$LOG_FILE"
  exit 1
fi

# 保護網路相關套件（包括 netplan.io 所需的 python3 套件）
echo "保護網路相關套件..." | tee -a "$LOG_FILE"
apt-get install -y isc-dhcp-client isc-dhcp-common iproute2 netplan.io network-manager iputils-ping python3 python3-netifaces python3-yaml 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝網路相關套件" | tee -a "$LOG_FILE"
  exit 1
fi

# 保護 vim 和 net-tools
echo "保護 vim 和 net-tools 套件..." | tee -a "$LOG_FILE"
apt-get install -y vim vim-runtime net-tools 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝 vim 和 net-tools 套件" | tee -a "$LOG_FILE"
  exit 1
fi

echo "跳過 apt autoremove 操作以避免服務重啟..." | tee -a "$LOG_FILE"
echo "使用 pip3 移除用戶級 Python 套件（如果 pip3 仍然存在）..." | tee -a "$LOG_FILE"
if command -v pip3 >/dev/null 2>&1; then
  pip3 freeze | xargs pip3 uninstall -y 2>&1 | tee -a "$LOG_FILE"
else
  echo "pip3 已不存在，跳過用戶級 Python 套件移除" | tee -a "$LOG_FILE"
fi
echo "清理殘留的 Python 套件目錄..." | tee -a "$LOG_FILE"
rm -rf /usr/local/lib/python3.10/dist-packages 2>&1 | tee -a "$LOG_FILE"
rm -rf /usr/local/bin/__pycache__ /usr/local/bin/pip* /usr/local/bin/easy_install* 2>&1 | tee -a "$LOG_FILE"
# 清理 /usr/lib/python3/dist-packages 和 /usr/local/bin 中的殘留文件
find /usr/lib/python3/dist-packages -mindepth 1 -maxdepth 1 -type d -not -name "distutils" -not -name "apt_pkg*" -not -name "dbus*" -not -name "gi*" -not -name "yaml*" -not -name "netifaces*" -exec rm -rf {} + 2>&1 | tee -a "$LOG_FILE"
find /usr/local/bin -type f -not -name "celery" -not -name "django-admin" -not -name "gunicorn" -not -name "redis*" -exec rm -f {} + 2>&1 | tee -a "$LOG_FILE"
echo "非系統默認的 Python 套件已清理" | tee -a "$LOG_FILE"

# 子步驟 1-10: 從 ENV_CONTENT 中提取 DATABASE_NAME 和 DATABASE_USER
echo "子步驟 1-10: 從 ENV_CONTENT 中提取 DATABASE_NAME 和 DATABASE_USER..." | tee -a "$LOG_FILE"
DATABASE_NAME=$(echo "$ENV_CONTENT" | grep '^DATABASE_NAME=' | cut -d'=' -f2)
DATABASE_USER=$(echo "$ENV_CONTENT" | grep '^DATABASE_USER=' | cut -d'=' -f2)

# 檢查提取的值是否有效
if [ -z "$DATABASE_NAME" ] || [ -z "$DATABASE_USER" ]; then
  echo "錯誤: 無法從 ENV_CONTENT 中提取 DATABASE_NAME 或 DATABASE_USER" | tee -a "$LOG_FILE"
  exit 1
fi

echo "提取的資料庫名稱: $DATABASE_NAME" | tee -a "$LOG_FILE"
echo "提取的使用者名稱: $DATABASE_USER" | tee -a "$LOG_FILE"

# 子步驟 1-11: 清理 PostgreSQL
echo "子步驟 1-11: 清理 PostgreSQL..." | tee -a "$LOG_FILE"
if command -v psql > /dev/null; then
  INSTANCES=$(systemctl list-units --full -all | grep -o 'postgresql@[^ ]*' | grep -v '\.scope' | sort -u || true)
  if [ -n "$INSTANCES" ]; then
    for INSTANCE in $INSTANCES; do
      echo "檢測到的 PostgreSQL 服務實例: $INSTANCE" | tee -a "$LOG_FILE"
      VERSION=$(echo "$INSTANCE" | grep -o '[0-9]\+')
      echo "檢測到的 PostgreSQL 版本: $VERSION" | tee -a "$LOG_FILE"
      # 確保 PostgreSQL 服務正在運行
      if ! systemctl is-active --quiet "$INSTANCE"; then
        echo "PostgreSQL 服務 $INSTANCE 未運行，啟動服務以進行資料庫操作..." | tee -a "$LOG_FILE"
        systemctl start "$INSTANCE" 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
          echo "錯誤: 無法啟動 PostgreSQL 服務 $INSTANCE" | tee -a "$LOG_FILE"
          exit 1
        fi
      fi
      # 檢查資料庫和使用者是否存在
      DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DATABASE_NAME'" 2>/dev/null)
      USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DATABASE_USER'" 2>/dev/null)
      if [ -z "$DB_EXISTS" ] && [ -z "$USER_EXISTS" ]; then
        echo "資料庫 $DATABASE_NAME 和使用者 $DATABASE_USER 不存在，跳過清理" | tee -a "$LOG_FILE"
      else
        # 刪除主要資料庫（如果存在）
        if [ -n "$DB_EXISTS" ]; then
          echo "檢測到資料庫 $DATABASE_NAME，準備刪除..." | tee -a "$LOG_FILE"
          sudo -u postgres psql -c "DROP DATABASE \"$DATABASE_NAME\";" 2>&1 | tee -a "$LOG_FILE"
          if [ $? -ne 0 ]; then
            echo "錯誤: 無法刪除資料庫 $DATABASE_NAME" | tee -a "$LOG_FILE"
            exit 1
          fi
          echo "資料庫 $DATABASE_NAME 已刪除" | tee -a "$LOG_FILE"
        else
          echo "資料庫 $DATABASE_NAME 不存在，無需刪除" | tee -a "$LOG_FILE"
        fi
        # 檢查並刪除所有依賴於 mes_user 的資料庫
        if [ -n "$USER_EXISTS" ]; then
          echo "檢測到使用者 $DATABASE_USER，檢查其依賴並準備刪除..." | tee -a "$LOG_FILE"
          # 列出所有由 mes_user 擁有的資料庫
          DEPENDENT_DBS=$(sudo -u postgres psql -tAc "SELECT datname FROM pg_database WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname = '$DATABASE_USER');" 2>/dev/null)
          if [ -n "$DEPENDENT_DBS" ]; then
            echo "發現以下資料庫依賴於 $DATABASE_USER：" | tee -a "$LOG_FILE"
            echo "$DEPENDENT_DBS" | tee -a "$LOG_FILE"
            for DB in $DEPENDENT_DBS; do
              # 確保不刪除系統資料庫（如 postgres, template0, template1）
              if [ "$DB" != "postgres" ] && [ "$DB" != "template0" ] && [ "$DB" != "template1" ]; then
                echo "刪除資料庫 $DB..." | tee -a "$LOG_FILE"
                sudo -u postgres psql -c "DROP DATABASE \"$DB\";" 2>&1 | tee -a "$LOG_FILE"
                if [ $? -ne 0 ]; then
                  echo "錯誤: 無法刪除資料庫 $DB" | tee -a "$LOG_FILE"
                  exit 1
                fi
                echo "資料庫 $DB 已刪除" | tee -a "$LOG_FILE"
              else
                echo "跳過系統資料庫 $DB，不予刪除" | tee -a "$LOG_FILE"
              fi
            done
          else
            echo "未發現依賴於 $DATABASE_USER 的資料庫" | tee -a "$LOG_FILE"
          fi
          # 重新分配 mes_user 擁有的所有物件給 postgres（以防仍有其他依賴）
          echo "重新分配 $DATABASE_USER 擁有的物件給 postgres..." | tee -a "$LOG_FILE"
          sudo -u postgres psql -c "REASSIGN OWNED BY $DATABASE_USER TO postgres;" 2>&1 | tee -a "$LOG_FILE"
          if [ $? -ne 0 ]; then
            echo "錯誤: 無法重新分配 $DATABASE_USER 擁有的物件" | tee -a "$LOG_FILE"
            exit 1
          fi
          # 刪除使用者
          echo "刪除使用者 $DATABASE_USER..." | tee -a "$LOG_FILE"
          sudo -u postgres psql -c "DROP ROLE $DATABASE_USER;" 2>&1 | tee -a "$LOG_FILE"
          if [ $? -ne 0 ]; then
            echo "錯誤: 無法刪除使用者 $DATABASE_USER" | tee -a "$LOG_FILE"
            exit 1
          fi
          echo "使用者 $DATABASE_USER 已刪除" | tee -a "$LOG_FILE"
        else
          echo "使用者 $DATABASE_USER 不存在，無需刪除" | tee -a "$LOG_FILE"
        fi
      fi
    done
  else
    echo "未檢測到正在運行的 PostgreSQL 實例，跳過資料庫和使用者檢查" | tee -a "$LOG_FILE"
  fi
else
  echo "PostgreSQL 未安裝，跳過清理步驟" | tee -a "$LOG_FILE"
fi

# 子步驟 1-12: 清理 Redis
echo "子步驟 1-12: 清理 Redis..." | tee -a "$LOG_FILE"
echo "移除所有 Redis 相關套件..." | tee -a "$LOG_FILE"
apt-get remove -y --purge redis redis-server redis-tools 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法移除 Redis 套件" | tee -a "$LOG_FILE"
    exit 1
fi
# 檢查並終止占用 6379 端口的進程
if lsof -i :6379 -t > /dev/null; then
    REDIS_PIDS=$(lsof -i :6379 -t | sort -u)
    echo "發現占用 6379 端口的進程 (PIDs: $REDIS_PIDS)，正在終止..." | tee -a "$LOG_FILE"
    for pid in $REDIS_PIDS; do
        kill -9 $pid 2>&1 | tee -a "$LOG_FILE"
    done
    sleep 1
    if lsof -i :6379 -t > /dev/null; then
        echo "錯誤: 無法清理 6379 端口，仍然被占用，請手動檢查" | tee -a "$LOG_FILE"
        lsof -i :6379 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "6379 端口已清理" | tee -a "$LOG_FILE"
else
    echo "6379 端口未被占用，無需清理" | tee -a "$LOG_FILE"
fi

# 保護網路相關套件
echo "保護網路相關套件..." | tee -a "$LOG_FILE"
apt-get install -y isc-dhcp-client isc-dhcp-common iproute2 netplan.io network-manager iputils-ping 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝網路相關套件" | tee -a "$LOG_FILE"
  exit 1
fi

# 保護 vim 和 net-tools
echo "保護 vim 和 net-tools 套件..." | tee -a "$LOG_FILE"
apt-get install -y vim vim-runtime net-tools 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法重新安裝 vim 和 net-tools 套件" | tee -a "$LOG_FILE"
  exit 1
fi

echo "跳過 apt autoremove 操作以避免服務重啟..." | tee -a "$LOG_FILE"
echo "清理系統預設的 Redis 相關目錄..." | tee -a "$LOG_FILE"
rm -rf /var/lib/redis /var/log/redis /etc/redis 2>&1 | tee -a "$LOG_FILE"
echo "成功: 已清理系統預設的 Redis 相關目錄和文件" | tee -a "$LOG_FILE"

for service in celery celery-beat; do
  if systemctl list-units --all | grep -q "$service"; then
    echo "錯誤: $service 服務仍存在於系統中" | tee -a "$LOG_FILE"
    systemctl list-units --all | grep "$service" 2>&1 | tee -a "$LOG_FILE"
    ERROR_FOUND=true
  fi
  if systemctl is-active --quiet "$service"; then
    echo "錯誤: $service 服務仍在運行" | tee -a "$LOG_FILE"
    systemctl status "$service" 2>&1 | tee -a "$LOG_FILE"
    ERROR_FOUND=true
  fi
done

# 步驟 2：創建或更新 .env 文件，並生成 requirements.txt
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 步驟 2：創建或更新 .env 文件，並生成 requirements.txt..." | tee -a "$LOG_FILE"

# 定義 .env 和 requirements.txt 文件路徑
echo "定義 .env 和 requirements.txt 文件路徑..." | tee -a "$LOG_FILE"
ENV_FILE="/var/www/mes/.env"
REQUIREMENTS_FILE="/var/www/mes/requirements.txt"

# 創建或覆蓋 .env 文件（保持不變）
echo "創建或覆蓋 .env 文件..." | tee -a "$LOG_FILE"
echo "$ENV_CONTENT" > "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤: 無法創建或更新 .env 文件" | tee -a "$LOG_FILE"
    exit 1
fi
chown mes:www-data "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
chmod 640 "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
echo "已生成 .env 文件，包含正確的 DATABASE_URL" | tee -a "$LOG_FILE"

# 生成 requirements.txt 文件（移除 django-scheduler 和 python-gantt）
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 生成 requirements.txt 文件..." | tee -a "$LOG_FILE"
cat <<EOL > "$REQUIREMENTS_FILE"
django==5.1.8
django-environ==0.12.0
django-import-export==4.3.7
djangorestframework==3.16.0
gunicorn==22.0.0
psycopg2-binary==2.9.10
python-decouple==3.8
celery==5.5.0
redis==5.2.1
pandas==2.2.3
numpy==1.26.4
openpyxl==3.1.5
xlrd==2.0.1
tablib==3.7.0
django-rosetta==0.10.0
django-celery-beat==2.7.0
django-celery-results==2.5.1
pymssql==2.3.4
pytz==2024.2
django-filter==24.3
django-tables2==2.7.0
python-dateutil==2.9.0
plotly==5.24.1
matplotlib==3.9.2
scikit-learn==1.5.2
tensorflow==2.17.0
requests==2.32.3
django-cors-headers==4.4.0
django-storages==1.14.4
pillow==10.4.0
sqlparse>=0.3.1
asgiref<4,>=3.8.1
diff-match-patch==20241021
EOL
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤: 無法創建 requirements.txt 文件" | tee -a "$LOG_FILE"
    exit 1
fi
chown mes:www-data "$REQUIREMENTS_FILE" 2>&1 | tee -a "$LOG_FILE"
chmod 640 "$REQUIREMENTS_FILE" 2>&1 | tee -a "$LOG_FILE"
echo "已生成 requirements.txt 文件" | tee -a "$LOG_FILE"

# 步驟 3: 安裝並初始化 PostgreSQL
echo "步驟 3: 安裝並初始化 PostgreSQL..." | tee -a "$LOG_FILE"

# 安裝 PostgreSQL（如果未安裝）
echo "檢查並安裝 PostgreSQL..." | tee -a "$LOG_FILE"
if ! command -v psql >/dev/null 2>&1; then
  echo "正在安裝 PostgreSQL..." | tee -a "$LOG_FILE"
  apt-get install -y postgresql postgresql-contrib 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 PostgreSQL" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "PostgreSQL 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi

# 安裝 libpq-dev 以支持 psycopg2
echo "安裝 libpq-dev 以支持 psycopg2..." | tee -a "$LOG_FILE"
apt-get install -y libpq-dev 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝 libpq-dev" | tee -a "$LOG_FILE"
  exit 1
fi
echo "libpq-dev 已安裝" | tee -a "$LOG_FILE"

# 檢查 PostgreSQL 服務是否正在運行
echo "檢查 PostgreSQL 服務是否正在運行..." | tee -a "$LOG_FILE"
PG_SERVICE=$(systemctl list-units --type=service --state=running | grep -E 'postgresql.*\.service' | awk '{print $1}' | head -n 1)
if [ -z "$PG_SERVICE" ]; then
  echo "錯誤: PostgreSQL 服務未運行，嘗試啟動..." | tee -a "$LOG_FILE"
  systemctl start postgresql 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法啟動 PostgreSQL 服務" | tee -a "$LOG_FILE"
    systemctl status postgresql 2>&1 | tee -a "$LOG_FILE"
    exit 1
  fi
  PG_SERVICE=$(systemctl list-units --type=service --state=running | grep -E 'postgresql.*\.service' | awk '{print $1}' | head -n 1)
fi
echo "檢測到的 PostgreSQL 服務實例: $PG_SERVICE" | tee -a "$LOG_FILE"

# 獲取 PostgreSQL 版本
PG_VERSION=$(psql --version | awk '{print $3}' | cut -d '.' -f 1)
echo "檢測到的 PostgreSQL 版本: $PG_VERSION" | tee -a "$LOG_FILE"

# 從 ENV_CONTENT 中提取資料庫配置（與步驟 2 保持一致）
DB_USER=$(echo "$ENV_CONTENT" | grep '^DATABASE_USER=' | cut -d'=' -f2)
DB_PASSWORD=$(echo "$ENV_CONTENT" | grep '^DATABASE_PASSWORD=' | cut -d'=' -f2)
DB_HOST=$(echo "$ENV_CONTENT" | grep '^DATABASE_HOST=' | cut -d'=' -f2)
DB_PORT=$(echo "$ENV_CONTENT" | grep '^DATABASE_PORT=' | cut -d'=' -f2)
DB_NAME=$(echo "$ENV_CONTENT" | grep '^DATABASE_NAME=' | cut -d'=' -f2)

# 檢查是否成功提取資料庫配置
if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ]; then
  echo "錯誤: 無法從 ENV_CONTENT 中提取資料庫配置" | tee -a "$LOG_FILE"
  echo "$ENV_CONTENT" | tee -a "$LOG_FILE"
  exit 1
fi

echo "提取的資料庫配置:" | tee -a "$LOG_FILE"
echo "DATABASE_USER: $DB_USER" | tee -a "$LOG_FILE"
echo "DATABASE_PASSWORD: $DB_PASSWORD" | tee -a "$LOG_FILE"
echo "DATABASE_HOST: $DB_HOST" | tee -a "$LOG_FILE"
echo "DATABASE_PORT: $DB_PORT" | tee -a "$LOG_FILE"
echo "DATABASE_NAME: $DB_NAME" | tee -a "$LOG_FILE"

# 創建 PostgreSQL 使用者
echo "創建 PostgreSQL 使用者 $DB_USER..." | tee -a "$LOG_FILE"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法創建 PostgreSQL 使用者 $DB_USER" | tee -a "$LOG_FILE"
  exit 1
fi

# 顯式設置密碼並驗證
echo "顯式設置 $DB_USER 的密碼並驗證..." | tee -a "$LOG_FILE"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法設置 $DB_USER 的密碼" | tee -a "$LOG_FILE"
  exit 1
fi

# 創建資料庫
echo "創建資料庫 $DB_NAME..." | tee -a "$LOG_FILE"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法創建資料庫 $DB_NAME" | tee -a "$LOG_FILE"
  exit 1
fi

# 授予權限
echo "授予 $DB_USER 對 $DB_NAME 的所有權限..." | tee -a "$LOG_FILE"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法授予 $DB_USER 對 $DB_NAME 的權限" | tee -a "$LOG_FILE"
  exit 1
fi

# 檢查 pg_hba.conf 配置（僅支持 TCP 連接，因為使用 -h 127.0.0.1）
echo "檢查並更新 pg_hba.conf 配置..." | tee -a "$LOG_FILE"
PG_HBA_FILE="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
if [ ! -f "$PG_HBA_FILE" ]; then
  echo "錯誤: 找不到 pg_hba.conf 文件，路徑: $PG_HBA_FILE" | tee -a "$LOG_FILE"
  exit 1
fi
if ! grep -q "host.*$DB_USER.*127.0.0.1/32.*md5" "$PG_HBA_FILE"; then
  echo "添加 $DB_USER 的 md5 認證配置到 pg_hba.conf（TCP 連線）..." | tee -a "$LOG_FILE"
  echo "host    all             $DB_USER        127.0.0.1/32            md5" | sudo tee -a "$PG_HBA_FILE" 2>&1 | tee -a "$LOG_FILE"
  # 重啟 PostgreSQL 服務以應用配置
  systemctl restart postgresql 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法重啟 PostgreSQL 服務" | tee -a "$LOG_FILE"
    systemctl status postgresql 2>&1 | tee -a "$LOG_FILE"
    exit 1
  fi
fi

# 測試資料庫連接（使用 -h 127.0.0.1 的 TCP 連線）
echo "測試資料庫連接（TCP 連線，使用 -h 127.0.0.1）..." | tee -a "$LOG_FILE"
sudo -u mes HOME=/tmp PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -h 127.0.0.1 -c "SELECT 1;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法連接到資料庫 $DB_NAME，詳細錯誤如下:" | tee -a "$LOG_FILE"
  sudo -u mes HOME=/tmp PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -h 127.0.0.1 -c "SELECT 1;" 2>&1 | tee -a "$LOG_FILE"
  echo "檢查 PostgreSQL 日誌:" | tee -a "$LOG_FILE"
  cat /var/log/postgresql/postgresql-$PG_VERSION-main.log 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "TCP 連線測試成功" | tee -a "$LOG_FILE"

# 驗證密碼是否正確設置（通過獨立測試）
echo "驗證 $DB_USER 的密碼是否正確設置..." | tee -a "$LOG_FILE"
sudo -u mes HOME=/tmp PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -h 127.0.0.1 -c "SELECT current_user;" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 密碼驗證失敗，無法使用提取的密碼進行連線" | tee -a "$LOG_FILE"
  exit 1
fi
echo "密碼驗證成功" | tee -a "$LOG_FILE"

echo "驗證成功: PostgreSQL 已準備就緒" | tee -a "$LOG_FILE"

# 步驟 4: 根據 .env 文件安裝並配置 Redis
echo "步驟 4: 根據 .env 文件安裝並配置 Redis..." | tee -a "$LOG_FILE"

# 從 .env 文件中讀取 Redis 配置
if [ ! -f "$ENV_FILE" ]; then
    echo "錯誤: .env 文件不存在，無法讀取 Redis 配置，路徑: $ENV_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# 提取 Redis 配置
REDIS_HOST=$(grep '^REDIS_HOST=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PORT=$(grep '^REDIS_PORT=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_MAXMEMORY=$(grep '^REDIS_MAXMEMORY=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_MAXCLIENTS=$(grep '^REDIS_MAXCLIENTS=' "$ENV_FILE" | cut -d'=' -f2)

# 驗證 Redis 配置
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ] || [ -z "$REDIS_PASSWORD" ] || [ -z "$REDIS_MAXMEMORY" ] || [ -z "$REDIS_MAXCLIENTS" ]; then
    echo "錯誤: 無法從 .env 文件中提取完整的 Redis 配置" | tee -a "$LOG_FILE"
    cat "$ENV_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

echo "從 .env 文件中提取的 Redis 配置:" | tee -a "$LOG_FILE"
echo "REDIS_HOST: $REDIS_HOST" | tee -a "$LOG_FILE"
echo "REDIS_PORT: $REDIS_PORT" | tee -a "$LOG_FILE"
echo "REDIS_PASSWORD: [隱藏]" | tee -a "$LOG_FILE"
echo "REDIS_MAXMEMORY: $REDIS_MAXMEMORY 字節" | tee -a "$LOG_FILE"
echo "REDIS_MAXCLIENTS: $REDIS_MAXCLIENTS" | tee -a "$LOG_FILE"

# 定義 Redis 配置文件和工作目錄
REDIS_CONF_FILE="/etc/redis/redis.conf"
REDIS_DATA_DIR="/var/lib/redis"

# 檢查並清理端口 6379（如果被佔用）
echo "檢查並清理 Redis 端口 $REDIS_PORT..." | tee -a "$LOG_FILE"
if lsof -i :$REDIS_PORT -t > /dev/null; then
    REDIS_PIDS=$(lsof -i :$REDIS_PORT -t | sort -u)
    echo "發現占用 $REDIS_PORT 端口的進程 (PIDs: $REDIS_PIDS)，正在終止..." | tee -a "$LOG_FILE"
    for pid in $REDIS_PIDS; do
        kill -9 $pid 2>&1 | tee -a "$LOG_FILE"
    done
    sleep 1
    if lsof -i :$REDIS_PORT -t > /dev/null; then
        echo "錯誤: 無法清理 $REDIS_PORT 端口，仍然被占用，請手動檢查" | tee -a "$LOG_FILE"
        lsof -i :$REDIS_PORT 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "$REDIS_PORT 端口已清理" | tee -a "$LOG_FILE"
else
    echo "$REDIS_PORT 端口未被占用，無需清理" | tee -a "$LOG_FILE"
fi

# 安裝 Redis（自動創建 redis 使用者和群組）
echo "正在安裝 Redis..." | tee -a "$LOG_FILE"
apt-get update 2>&1 | tee -a "$LOG_FILE"
apt-get install -y redis-server 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 Redis 服務" | tee -a "$LOG_FILE"
    exit 1
fi

# 確保 Redis 工作目錄存在並設置正確權限
echo "確保 Redis 工作目錄 $REDIS_DATA_DIR 存在並設置正確權限..." | tee -a "$LOG_FILE"
mkdir -p "$REDIS_DATA_DIR" 2>&1 | tee -a "$LOG_FILE"
chown redis:redis "$REDIS_DATA_DIR" 2>&1 | tee -a "$LOG_FILE"
chmod 755 "$REDIS_DATA_DIR" 2>&1 | tee -a "$LOG_FILE"
if ! sudo -u redis touch "$REDIS_DATA_DIR/test_write" 2>/dev/null; then
    echo "錯誤: redis 使用者無法在 $REDIS_DATA_DIR 目錄中寫入檔案" | tee -a "$LOG_FILE"
    ls -ld "$REDIS_DATA_DIR" 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi
rm -f "$REDIS_DATA_DIR/test_write" 2>/dev/null

# 生成 Redis 配置文件
echo "生成 Redis 配置文件 $REDIS_CONF_FILE..." | tee -a "$LOG_FILE"
mkdir -p /etc/redis 2>&1 | tee -a "$LOG_FILE"
rm -rf /etc/redis/redis.conf.d 2>&1 | tee -a "$LOG_FILE"
cat > "$REDIS_CONF_FILE" << EOF
# Redis configuration file (generated by MES script)
bind $REDIS_HOST
port $REDIS_PORT
requirepass $REDIS_PASSWORD
maxmemory $REDIS_MAXMEMORY
maxclients $REDIS_MAXCLIENTS
dir $REDIS_DATA_DIR
appendonly no
save 900 1
save 300 10
save 60 10000
loglevel notice
EOF
if [ $? -ne 0 ]; then
    echo "錯誤: 無法生成 Redis 配置文件" | tee -a "$LOG_FILE"
    exit 1
fi

# 驗證配置文件內容
if ! grep -q "requirepass $REDIS_PASSWORD" "$REDIS_CONF_FILE"; then
    echo "錯誤: Redis 配置文件未包含正確的 requirepass 配置，期望值: $REDIS_PASSWORD" | tee -a "$LOG_FILE"
    cat "$REDIS_CONF_FILE" | tee -a "$LOG_FILE"
    exit 1
fi
echo "Redis 配置文件已正確包含 requirepass 配置" | tee -a "$LOG_FILE"

# 設置 Redis 配置文件權限
chown redis:redis "$REDIS_CONF_FILE" 2>&1 | tee -a "$LOG_FILE"
chmod 644 "$REDIS_CONF_FILE" 2>&1 | tee -a "$LOG_FILE"

# 啟用 Redis 服務開機自動啟動
echo "啟用 Redis 服務開機自動啟動..." | tee -a "$LOG_FILE"
systemctl enable redis-server 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法啟用 Redis 服務開機自動啟動" | tee -a "$LOG_FILE"
    exit 1
fi

# 停止 Redis 服務以應用新配置
echo "停止 Redis 服務以應用新配置..." | tee -a "$LOG_FILE"
systemctl stop redis-server 2>/dev/null
sleep 1
if pgrep redis-server >/dev/null; then
    echo "警告: Redis 進程仍在運行，嘗試強制終止..." | tee -a "$LOG_FILE"
    pkill -9 redis-server 2>&1 | tee -a "$LOG_FILE"
    sleep 1
    if pgrep redis-server >/dev/null; then
        echo "錯誤: 無法終止 Redis 進程，請手動檢查" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "成功: Redis 進程已強制終止" | tee -a "$LOG_FILE"
fi
echo "Redis 服務已停止" | tee -a "$LOG_FILE"

# 啟動 Redis 服務
echo "啟動 Redis 服務..." | tee -a "$LOG_FILE"
timeout 30 systemctl start redis-server 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法啟動 Redis 服務，詳細錯誤如下:" | tee -a "$LOG_FILE"
    systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
    journalctl -xeu redis-server.service 2>&1 | tee -a "$LOG_FILE"
    if [ -f "/var/log/redis/redis-server.log" ]; then
        echo "Redis 日誌內容:" | tee -a "$LOG_FILE"
        tail -n 50 "/var/log/redis/redis-server.log" 2>&1 | tee -a "$LOG_FILE"
    fi
    exit 1
fi

# 驗證 Redis 服務是否活躍
if ! systemctl is-active --quiet redis-server; then
    echo "錯誤: Redis 服務啟動失敗，詳細錯誤如下:" | tee -a "$LOG_FILE"
    systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
    journalctl -xeu redis-server.service 2>&1 | tee -a "$LOG_FILE"
    if [ -f "/var/log/redis/redis-server.log" ]; then
        echo "Redis 日誌內容:" | tee -a "$LOG_FILE"
        tail -n 50 "/var/log/redis/redis-server.log" 2>&1 | tee -a "$LOG_FILE"
    fi
    exit 1
fi
echo "Redis 服務正在運行" | tee -a "$LOG_FILE"

# 等待 Redis 服務完全啟動
echo "等待 Redis 服務完全啟動..." | tee -a "$LOG_FILE"
sleep 2

# 測試 Redis 客戶端連接（使用密碼）
echo "測試 Redis 客戶端連接..." | tee -a "$LOG_FILE"
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: Redis 客戶端連接失敗，嘗試無密碼連接..." | tee -a "$LOG_FILE"
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1 | tee -a "$LOG_FILE"
    if [ $? -eq 0 ]; then
        echo "錯誤: Redis 允許無密碼連接，密碼配置未生效" | tee -a "$LOG_FILE"
        # 嘗試動態設置密碼作為備用方案
        echo "嘗試動態設置 Redis 密碼..." | tee -a "$LOG_FILE"
        redis-cli -h 127.0.0.1 -p $REDIS_PORT CONFIG SET requirepass "$REDIS_PASSWORD" 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
            echo "錯誤: 無法動態設置 Redis 密碼" | tee -a "$LOG_FILE"
            exit 1
        fi
        # 重新測試帶密碼的連接
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>&1 | tee -a "$LOG_FILE"
        if [ $? -ne 0 ]; then
            echo "錯誤: 動態設置 Redis 密碼後仍無法連接" | tee -a "$LOG_FILE"
            exit 1
        fi
        echo "成功: Redis 密碼已動態設置並驗證成功" | tee -a "$LOG_FILE"
    else
        echo "錯誤: Redis 客戶端連接失敗，且無密碼連接也被拒絕" | tee -a "$LOG_FILE"
        systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
        if [ -f "/var/log/redis/redis-server.log" ]; then
            echo "Redis 日誌內容:" | tee -a "$LOG_FILE"
            tail -n 50 "/var/log/redis/redis-server.log" 2>&1 | tee -a "$LOG_FILE"
        fi
        exit 1
    fi
else
    echo "Redis 客戶端連接成功" | tee -a "$LOG_FILE"
fi

# 驗證 Redis 端口綁定
echo "檢查 Redis 端口是否被正確綁定..." | tee -a "$LOG_FILE"
REDIS_PIDS=$(lsof -i :$REDIS_PORT -t | sort -u 2>/dev/null)
if [ -z "$REDIS_PIDS" ]; then
    echo "錯誤: Redis 端口 $REDIS_PORT 未被綁定，請檢查 Redis 服務" | tee -a "$LOG_FILE"
    systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi
for pid in $REDIS_PIDS; do
    if ! ps -p "$pid" -o comm= | grep -q "redis-server"; then
        echo "錯誤: Redis 端口 $REDIS_PORT 被其他進程占用（PID: $pid），請檢查" | tee -a "$LOG_FILE"
        ps -p "$pid" -o pid,comm 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
done
echo "Redis 端口 $REDIS_PORT 已正確綁定，且進程為 redis-server" | tee -a "$LOG_FILE"

# 驗證 Redis 配置
echo "驗證 Redis 配置..." | tee -a "$LOG_FILE"
for config in "bind $REDIS_HOST" "port $REDIS_PORT" "requirepass $REDIS_PASSWORD" "maxmemory $REDIS_MAXMEMORY" "maxclients $REDIS_MAXCLIENTS" "dir $REDIS_DATA_DIR"; do
    key=$(echo "$config" | cut -d' ' -f1)
    expected=$(echo "$config" | cut -d' ' -f2-)
    REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT -a "$REDIS_PASSWORD" CONFIG GET $key 2>/dev/null | grep -w "$expected")
    if [ -z "$REDIS_CLI_CHECK" ]; then
        echo "錯誤: Redis 配置 $key 未正確設置，期望值: $expected" | tee -a "$LOG_FILE"
        CURRENT_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT -a "$REDIS_PASSWORD" CONFIG GET $key 2>/dev/null | grep -v "$key")
        echo "當前 $key 值: $CURRENT_VALUE" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "Redis 配置 $key 已正確設置為 $expected" | tee -a "$LOG_FILE"
done

# 檢查 Redis 日誌是否有錯誤
echo "檢查 Redis 日誌是否有錯誤..." | tee -a "$LOG_FILE"
if [ -f "/var/log/redis/redis-server.log" ]; then
    if grep -i "error" "/var/log/redis/redis-server.log" | grep -v "no error" >/dev/null; then
        echo "錯誤: Redis 日誌中包含錯誤信息，請檢查" | tee -a "$LOG_FILE"
        tail -n 50 "/var/log/redis/redis-server.log" 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "Redis 日誌檢查通過，無錯誤信息" | tee -a "$LOG_FILE"
else
    echo "警告: Redis 日誌文件 /var/log/redis/redis-server.log 不存在，無法檢查日誌" | tee -a "$LOG_FILE"
fi

echo "驗證成功: Redis 服務已安裝並配置完成" | tee -a "$LOG_FILE"

# 步驟 5: 安裝專案相關工具和 Python 套件
echo "步驟 5: 安裝專案相關工具和 Python 套件..." | tee -a "$LOG_FILE"

# 檢查並安裝 gettext（提供 msgfmt 命令）
echo "檢查並安裝 gettext..." | tee -a "$LOG_FILE"
if ! command -v msgfmt >/dev/null 2>&1; then
  echo "msgfmt 未安裝，正在安裝 gettext..." | tee -a "$LOG_FILE"
  apt update 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
  apt install -y gettext 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 gettext 套件，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "msgfmt 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
if ! command -v msgfmt >/dev/null 2>&1; then
  echo "驗證失敗: msgfmt 未正確安裝，無法繼續執行腳本" | tee -a "$LOG_FILE"
  exit 1
fi
echo "驗證成功: msgfmt 已準備就緒" | tee -a "$LOG_FILE"

# 安裝 Python 3 和 pip
echo "正在安裝 Python 3 和 pip..." | tee -a "$LOG_FILE"
apt update 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
  exit 1
fi
apt install -y python3 python3-pip python3-dev python3-setuptools python3-wheel 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝 Python 3 和 pip，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
  exit 1
fi

# 驗證 Python 3 和 pip 是否安裝成功
if ! command -v python3 >/dev/null 2>&1; then
  echo "錯誤: Python 3 未正確安裝" | tee -a "$LOG_FILE"
  exit 1
fi
if ! command -v pip3 >/dev/null 2>&1; then
  echo "錯誤: pip3 未正確安裝" | tee -a "$LOG_FILE"
  exit 1
fi
echo "Python 3 和 pip 已安裝，版本如下:" | tee -a "$LOG_FILE"
python3 --version 2>&1 | tee -a "$LOG_FILE"
pip3 --version 2>&1 | tee -a "$LOG_FILE"

# 使用 requirements.txt 安裝套件（系統級安裝）
echo "正在安裝 MES 專案所需的 Python 套件（從 requirements.txt）..." | tee -a "$LOG_FILE"
pip3 install -r "$REQUIREMENTS_FILE" --no-cache-dir 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝 requirements.txt 中的套件，請檢查網絡或 pip 配置" | tee -a "$LOG_FILE"
  pip3 list 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi

# 驗證套件是否安裝成功
echo "驗證 Python 套件是否安裝成功..." | tee -a "$LOG_FILE"
while IFS= read -r package || [ -n "$package" ]; do
  if [ -n "$package" ]; then
    package_name=$(echo "$package" | grep -oP '^[a-zA-Z0-9_-]+' | head -n 1)
    if ! pip3 show "$package_name" >/dev/null 2>&1; then
      echo "錯誤: 套件 $package_name 未正確安裝" | tee -a "$LOG_FILE"
      pip3 list 2>&1 | tee -a "$LOG_FILE"
      exit 1
    fi
    echo "套件 $package_name 已安裝，版本信息如下:" | tee -a "$LOG_FILE"
    pip3 show "$package_name" 2>&1 | tee -a "$LOG_FILE"
  fi
done < "$REQUIREMENTS_FILE"
echo "所有專案相關工具和 Python 套件已成功安裝" | tee -a "$LOG_FILE"

# 步驟 5.1: 開始驗證套件導入
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [步驟 5.1] 開始驗證套件導入..." | tee -a "$LOG_FILE"
pip check 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [步驟 5.1] 錯誤: 套件相容性檢查失敗" | tee -a "$LOG_FILE"
    exit 1
fi
# 創建臨時 check_apps.py 來檢查關鍵模組
CHECK_APPS_PY="/var/www/mes/check_apps.py"
cat > "$CHECK_APPS_PY" << EOL
import django
import psycopg2
import gunicorn
import celery
import redis
import rosetta
import pymssql
import pandas
import numpy
import openpyxl
import rest_framework
import environ
import decouple
import django_celery_beat
import django_celery_results
import import_export
print("所有關鍵模組導入成功")
EOL
chown mes:www-data "$CHECK_APPS_PY" 2>&1 | tee -a "$LOG_FILE"
chmod 644 "$CHECK_APPS_PY" 2>&1 | tee -a "$LOG_FILE"
sudo -u mes python3 "$CHECK_APPS_PY" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [步驟 5.1] 錯誤: 模組導入檢查失敗" | tee -a "$LOG_FILE"
    exit 1
fi
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [步驟 5.1] 套件和模組驗證成功" | tee -a "$LOG_FILE"

# 步驟 6: 安裝 ERP 模組所需的驅動和套件
echo "步驟 6: 安裝 ERP 模組所需的驅動和套件..." | tee -a "$LOG_FILE"

# 安裝 pymssql 所需的系統級依賴
echo "安裝 pymssql 所需的系統級依賴（freetds-dev 和 libssl-dev）..." | tee -a "$LOG_FILE"
apt-get update 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
fi
apt-get install -y freetds-dev libssl-dev 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: 無法安裝 freetds-dev 或 libssl-dev，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
    exit 1
fi
echo "freetds-dev 和 libssl-dev 已安裝" | tee -a "$LOG_FILE"

# 檢查 pymssql 是否已安裝
echo "檢查 pymssql 是否已安裝..." | tee -a "$LOG_FILE"
if ! python3 -c "import pymssql" 2>/dev/null; then
    echo "錯誤: pymssql 套件不可用，嘗試重新安裝..." | tee -a "$LOG_FILE"
    pip3 install pymssql --no-cache-dir 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法安裝 pymssql 套件，請檢查網絡或 pip 配置" | tee -a "$LOG_FILE"
        pip3 show pymssql 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi
fi
echo "pymssql 已準備就緒" | tee -a "$LOG_FILE"

echo "步驟 6 完成: ERP 模組所需的驅動和套件已安裝" | tee -a "$LOG_FILE"


# 步驟 7: 檢查 Django 執行環境是否正常
echo "步驟 7: 檢查 Django 執行環境是否正常..." | tee -a "$LOG_FILE"

# 檢查 django-admin 命令是否可用
if ! command -v django-admin >/dev/null 2>&1; then
  echo "錯誤: django-admin 命令不可用，請檢查 Django 安裝" | tee -a "$LOG_FILE"
  pip3 show django 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "django-admin 命令已準備就緒" | tee -a "$LOG_FILE"

# 檢查 Django 版本
DJANGO_VERSION=$(django-admin --version 2>&1)
if [ $? -ne 0 ]; then
  echo "錯誤: 無法檢查 Django 版本，請檢查 Django 安裝" | tee -a "$LOG_FILE"
  pip3 show django 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "Django 版本: $DJANGO_VERSION" | tee -a "$LOG_FILE"

# 檢查 psycopg2 是否可用（PostgreSQL 適配器）
echo "檢查 psycopg2 是否可用..." | tee -a "$LOG_FILE"
if ! python3 -c "import psycopg2" 2>/dev/null; then
  echo "錯誤: psycopg2 套件不可用，請檢查 libpq-dev 和 psycopg2 安裝" | tee -a "$LOG_FILE"
  pip3 show psycopg2-binary 2>&1 | tee -a "$LOG_FILE"
  dpkg -l | grep libpq-dev 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "psycopg2 已準備就緒" | tee -a "$LOG_FILE"

# 檢查 gunicorn 是否可用
echo "檢查 gunicorn 是否可用..." | tee -a "$LOG_FILE"
if ! command -v gunicorn >/dev/null 2>&1; then
  echo "錯誤: gunicorn 命令不可用，請檢查 gunicorn 安裝" | tee -a "$LOG_FILE"
  pip3 show gunicorn 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
GUNICORN_VERSION=$(gunicorn --version 2>&1 | head -n 1)
if [ $? -ne 0 ]; then
  echo "錯誤: 無法檢查 gunicorn 版本，請檢查 gunicorn 安裝" | tee -a "$LOG_FILE"
  pip3 show gunicorn 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "gunicorn 版本: $GUNICORN_VERSION" | tee -a "$LOG_FILE"

# 檢查 celery 是否可用
echo "檢查 celery 是否可用..." | tee -a "$LOG_FILE"
if ! command -v celery >/dev/null 2>&1; then
  echo "錯誤: celery 命令不可用，請檢查 celery 安裝" | tee -a "$LOG_FILE"
  pip3 show celery 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
CELERY_VERSION=$(celery --version 2>&1 | head -n 1)
if [ $? -ne 0 ]; then
  echo "錯誤: 無法檢查 celery 版本，請檢查 celery 安裝" | tee -a "$LOG_FILE"
  pip3 show celery 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "celery 版本: $CELERY_VERSION" | tee -a "$LOG_FILE"

# 檢查 redis 套件是否可用
echo "檢查 redis 套件是否可用..." | tee -a "$LOG_FILE"
if ! python3 -c "import redis" 2>/dev/null; then
  echo "錯誤: redis 套件不可用，請檢查 redis 安裝" | tee -a "$LOG_FILE"
  pip3 show redis 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "redis 套件已準備就緒" | tee -a "$LOG_FILE"

# 檢查 django-rosetta 套件是否可用
echo "檢查 django-rosetta 套件是否可用..." | tee -a "$LOG_FILE"
if ! python3 -c "import rosetta" 2>/dev/null; then
  echo "錯誤: django-rosetta 套件不可用，請檢查 django-rosetta 安裝" | tee -a "$LOG_FILE"
  pip3 show django-rosetta 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "django-rosetta 套件已準備就緒" | tee -a "$LOG_FILE"

echo "Django 執行環境檢查完成，所有依賴已準備就緒" | tee -a "$LOG_FILE"

# 步驟 8: 安裝 Python 執行環境和相關套件
echo "步驟 8: 安裝 Python 執行環境和相關套件..." | tee -a "$LOG_FILE"

# 安裝 Python 3 和 pip
echo "正在安裝 Python 3 和 pip..." | tee -a "$LOG_FILE"
apt-get update 2>&1 | tee -a "$LOG_FILE"
apt-get install -y python3 python3-pip python3-dev 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝 Python 3 或 pip" | tee -a "$LOG_FILE"
  exit 1
fi

# 安裝 requirements.txt 中列出的 Python 套件
echo "正在安裝 MES 專案所需的 Python 套件（從 requirements.txt）..." | tee -a "$LOG_FILE"
pip3 install -r /var/www/mes/requirements.txt 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝 requirements.txt 中的套件" | tee -a "$LOG_FILE"
  exit 1
fi

echo "步驟 8 完成: Python 執行環境和相關套件已安裝" | tee -a "$LOG_FILE"

# 步驟 9: 檢查 Celery 執行環境是否正常
echo "步驟 9: 檢查 Celery 執行環境是否正常..." | tee -a "$LOG_FILE"

# 檢查 Celery 命令是否可用
echo "檢查 Celery 命令是否可用..." | tee -a "$LOG_FILE"
if ! command -v celery >/dev/null 2>&1; then
  echo "錯誤: celery 命令不可用，請檢查 celery 安裝" | tee -a "$LOG_FILE"
  pip3 show celery 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
CELERY_VERSION=$(celery --version 2>&1 | head -n 1)
if [ $? -ne 0 ]; then
  echo "錯誤: 無法檢查 celery 版本，請檢查 celery 安裝" | tee -a "$LOG_FILE"
  pip3 show celery 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "Celery 版本: $CELERY_VERSION" | tee -a "$LOG_FILE"

# 檢查 Celery 與 Redis 的連接是否正常
echo "檢查 Celery 與 Redis 的連接是否正常..." | tee -a "$LOG_FILE"
# 從 .env 文件中讀取 Redis 配置
REDIS_HOST=$(grep '^REDIS_HOST=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PORT=$(grep '^REDIS_PORT=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ] || [ -z "$REDIS_PASSWORD" ]; then
  echo "錯誤: 無法從 .env 文件中提取 Redis 配置" | tee -a "$LOG_FILE"
  exit 1
fi
# 測試 Redis 連接
echo "測試 Redis 連接..." | tee -a "$LOG_FILE"
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --pass "$REDIS_PASSWORD" ping 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法連接到 Redis 服務，請檢查 Redis 配置或服務狀態" | tee -a "$LOG_FILE"
  systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "Redis 連接正常" | tee -a "$LOG_FILE"

# 使用簡單的 Python 腳本測試 Celery 與 Redis 的連接（以 mes 使用者身份）
echo "使用簡單的 Python 腳本測試 Celery 與 Redis 的連接（以 mes 使用者身份）..." | tee -a "$LOG_FILE"
# 創建一個臨時 Python 腳本來測試 Celery 連接
TEMP_CELERY_TEST=$(mktemp)
cat > "$TEMP_CELERY_TEST" << EOF
from celery import Celery
app = Celery('test', broker='redis://:$REDIS_PASSWORD@$REDIS_HOST:$REDIS_PORT/0')
app.control.inspect().ping()
print("Celery 與 Redis 連接成功")
EOF
# 設置臨時文件的權限，確保 mes 使用者可以讀取
chmod 644 "$TEMP_CELERY_TEST" 2>&1 | tee -a "$LOG_FILE"
chown mes:mes "$TEMP_CELERY_TEST" 2>&1 | tee -a "$LOG_FILE"
# 執行測試腳本
sudo -u mes -H bash -c "env PATH=\"$PATH:/usr/local/bin:/home/mes/.local/bin\" python3 \"$TEMP_CELERY_TEST\"" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: Celery 與 Redis 連接測試失敗，請檢查 Celery 和 Redis 配置" | tee -a "$LOG_FILE"
  cat "$TEMP_CELERY_TEST" 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
# 清理臨時文件
rm -f "$TEMP_CELERY_TEST"
echo "Celery 與 Redis 連接測試成功" | tee -a "$LOG_FILE"

echo "Celery 執行環境檢查完成，環境正常" | tee -a "$LOG_FILE"

# 步驟 10: 檢查 Redis 執行環境是否正常
echo "步驟 10: 檢查 Redis 執行環境是否正常..." | tee -a "$LOG_FILE"

# 檢查 Redis 服務是否正在運行
echo "檢查 Redis 服務是否正在運行..." | tee -a "$LOG_FILE"
if ! systemctl is-active --quiet redis-server; then
  echo "錯誤: Redis 服務未運行，請檢查 Redis 安裝和配置" | tee -a "$LOG_FILE"
  systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
  journalctl -xeu redis-server.service 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "Redis 服務正在運行" | tee -a "$LOG_FILE"

# 從 .env 文件中讀取 Redis 配置
echo "從 .env 文件中讀取 Redis 配置..." | tee -a "$LOG_FILE"
REDIS_HOST=$(grep '^REDIS_HOST=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PORT=$(grep '^REDIS_PORT=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_MAXMEMORY=$(grep '^REDIS_MAXMEMORY=' "$ENV_FILE" | cut -d'=' -f2)
REDIS_MAXCLIENTS=$(grep '^REDIS_MAXCLIENTS=' "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ] || [ -z "$REDIS_PASSWORD" ] || [ -z "$REDIS_MAXMEMORY" ] || [ -z "$REDIS_MAXCLIENTS" ]; then
  echo "錯誤: 無法從 .env 文件中提取 Redis 配置" | tee -a "$LOG_FILE"
  cat "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi

# 檢查 Redis 配置是否與 .env 文件一致
echo "檢查 Redis 配置是否與 .env 文件一致..." | tee -a "$LOG_FILE"
REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET bind 2>/dev/null | grep -w "$REDIS_HOST")
if [ -z "$REDIS_CLI_CHECK" ]; then
  echo "錯誤: Redis 綁定地址未正確配置，當前值不為 $REDIS_HOST" | tee -a "$LOG_FILE"
  CURRENT_BIND_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET bind 2>/dev/null | grep -v "bind")
  echo "當前 bind 值: $CURRENT_BIND_VALUE" | tee -a "$LOG_FILE"
  exit 1
fi
REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET port 2>/dev/null | grep -w "$REDIS_PORT")
if [ -z "$REDIS_CLI_CHECK" ]; then
  echo "錯誤: Redis 端口未正確配置，當前值不為 $REDIS_PORT" | tee -a "$LOG_FILE"
  CURRENT_PORT_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET port 2>/dev/null | grep -v "port")
  echo "當前 port 值: $CURRENT_PORT_VALUE" | tee -a "$LOG_FILE"
  exit 1
fi
REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET requirepass 2>/dev/null | grep -w "$REDIS_PASSWORD")
if [ -z "$REDIS_CLI_CHECK" ]; then
  echo "錯誤: Redis 密碼未正確配置，當前值不為 $REDIS_PASSWORD" | tee -a "$LOG_FILE"
  CURRENT_PASSWORD_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET requirepass 2>/dev/null | grep -v "requirepass")
  echo "當前 requirepass 值: $CURRENT_PASSWORD_VALUE" | tee -a "$LOG_FILE"
  exit 1
fi
REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET maxmemory 2>/dev/null | grep -w "$REDIS_MAXMEMORY")
if [ -z "$REDIS_CLI_CHECK" ]; then
  echo "錯誤: Redis 最大內存未正確配置，當前值不為 $REDIS_MAXMEMORY 字節" | tee -a "$LOG_FILE"
  CURRENT_MAXMEMORY_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET maxmemory 2>/dev/null | grep -v "maxmemory")
  echo "當前 maxmemory 值: $CURRENT_MAXMEMORY_VALUE" | tee -a "$LOG_FILE"
  exit 1
fi
REDIS_CLI_CHECK=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET maxclients 2>/dev/null | grep -w "$REDIS_MAXCLIENTS")
if [ -z "$REDIS_CLI_CHECK" ]; then
  echo "錯誤: Redis 最大客戶端數量未正確配置，當前值不為 $REDIS_MAXCLIENTS" | tee -a "$LOG_FILE"
  CURRENT_MAXCLIENTS_VALUE=$(redis-cli -h 127.0.0.1 -p $REDIS_PORT --pass "$REDIS_PASSWORD" CONFIG GET maxclients 2>/dev/null | grep -v "maxclients")
  echo "當前 maxclients 值: $CURRENT_MAXCLIENTS_VALUE" | tee -a "$LOG_FILE"
  exit 1
fi
echo "Redis 配置檢查通過，與 .env 文件一致" | tee -a "$LOG_FILE"

# 檢查 Redis 端口是否被正確綁定
echo "檢查 Redis 端口是否被正確綁定..." | tee -a "$LOG_FILE"
REDIS_PID=$(lsof -i :$REDIS_PORT -t 2>/dev/null)
if [ -z "$REDIS_PID" ]; then
  echo "錯誤: Redis 端口 $REDIS_PORT 未被綁定，請檢查 Redis 服務" | tee -a "$LOG_FILE"
  systemctl status redis-server.service 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
# 確認進程是否為 redis-server
if ! ps -p "$REDIS_PID" -o comm= | grep -q "redis-server"; then
  echo "錯誤: Redis 端口 $REDIS_PORT 被其他進程占用（PID: $REDIS_PID），請檢查" | tee -a "$LOG_FILE"
  ps -p "$REDIS_PID" -o comm= 2>&1 | tee -a "$LOG_FILE"
  exit 1
fi
echo "Redis 端口 $REDIS_PORT 已正確綁定，且進程為 redis-server" | tee -a "$LOG_FILE"

# 檢查 Redis 日誌是否有錯誤
echo "檢查 Redis 日誌是否有錯誤..." | tee -a "$LOG_FILE"
if [ -f /var/log/redis/redis-server.log ]; then
  if grep -i "error" /var/log/redis/redis-server.log | grep -v "no error" >/dev/null; then
    echo "錯誤: Redis 日誌中包含錯誤信息，請檢查" | tee -a "$LOG_FILE"
    tail -n 50 /var/log/redis/redis-server.log 2>&1 | tee -a "$LOG_FILE"
    exit 1
  fi
  echo "Redis 日誌檢查通過，無錯誤信息" | tee -a "$LOG_FILE"
else
  echo "警告: Redis 日誌文件 /var/log/redis/redis-server.log 不存在，無法檢查日誌" | tee -a "$LOG_FILE"
fi

echo "Redis 執行環境檢查完成，環境正常" | tee -a "$LOG_FILE"

# 步驟 11: 配置 Gunicorn
echo "步驟 11: 配置 Gunicorn（不啟動）..." | tee -a "$LOG_FILE"
GUNICORN_PATH=$(command -v gunicorn)
if [ -z "$GUNICORN_PATH" ]; then
    echo "錯誤: Gunicorn 未安裝或未找到" | tee -a "$LOG_FILE"
    exit 1
fi
echo "Gunicorn 路徑: $GUNICORN_PATH" | tee -a "$LOG_FILE"

# 生成 Gunicorn 配置文件
echo "生成 Gunicorn 配置文件..." | tee -a "$LOG_FILE"
GUNICORN_CONF_DIR="/etc/gunicorn.d"
mkdir -p "$GUNICORN_CONF_DIR"
GUNICORN_CONF_FILE="$GUNICORN_CONF_DIR/mes_config.py"
CPU_CORES=$(nproc)
WORKERS=$((2 * CPU_CORES + 1))
cat > "$GUNICORN_CONF_FILE" << EOL
bind = "0.0.0.0:8000"
workers = 3
user = "mes"
group = "www-data"
loglevel = "info"
accesslog = "/var/log/mes/gunicorn.accesslog.log"
errorlog = "/var/log/mes/gunicorn.errorlog.log"
timeout = 300
EOL
chown root:root "$GUNICORN_CONF_FILE"
chmod 644 "$GUNICORN_CONF_FILE"

# 創建 Gunicorn 日誌文件
echo "創建 Gunicorn 日誌文件..." | tee -a "$LOG_FILE"
touch /var/log/mes/gunicorn.accesslog.log 2>&1 | tee -a "$LOG_FILE"
touch /var/log/mes/gunicorn.errorlog.log 2>&1 | tee -a "$LOG_FILE"
chown mes:mes /var/log/mes/gunicorn.accesslog.log /var/log/mes/gunicorn.errorlog.log 2>&1 | tee -a "$LOG_FILE"
chmod 644 /var/log/mes/gunicorn.accesslog.log /var/log/mes/gunicorn.errorlog.log 2>&1 | tee -a "$LOG_FILE"
echo "Gunicorn 日誌文件已創建並設置權限" | tee -a "$LOG_FILE"

# 從 .env 文件中提取 Celery 配置
CELERY_BROKER_URL=$(grep '^CELERY_BROKER_URL=' "$ENV_FILE" | cut -d'=' -f2-)
CELERY_RESULT_BACKEND=$(grep '^CELERY_RESULT_BACKEND=' "$ENV_FILE" | cut -d'=' -f2-)
if [ -z "$CELERY_BROKER_URL" ] || [ -z "$CELERY_RESULT_BACKEND" ]; then
    echo "錯誤: 無法從 .env 文件中提取 Celery 配置" | tee -a "$LOG_FILE"
    cat "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# 生成 Gunicorn systemd 服務文件，內嵌正確的 DATABASE_URL 和 Celery 配置
echo "生成 Gunicorn systemd 服務文件..." | tee -a "$LOG_FILE"
cat > /etc/systemd/system/gunicorn-mes_config.service << EOL
[Unit]
Description=Gunicorn instance to serve MES
After=network.target

[Service]
User=mes
Group=www-data
WorkingDirectory=/var/www/mes
Environment="DJANGO_SETTINGS_MODULE=mes_config.settings"
Environment="ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP"
Environment="DATABASE_URL=$DATABASE_URL"
Environment="DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY"
Environment="DEBUG=True"
Environment="CELERY_BROKER_URL=$CELERY_BROKER_URL"
Environment="CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND"
ExecStart=$GUNICORN_PATH --config $GUNICORN_CONF_FILE mes_config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL
chown root:root /etc/systemd/system/gunicorn-mes_config.service
chmod 644 /etc/systemd/system/gunicorn-mes_config.service
systemctl daemon-reload
echo "Gunicorn 配置完成（未啟動）" | tee -a "$LOG_FILE"

# 步驟 12: 配置 Celery 和 Celery Beat
echo "步驟 12: 配置 Celery 和 Celery Beat（不啟動）..." | tee -a "$LOG_FILE"
mkdir -p /var/run/celery
chown mes:www-data /var/run/celery
chmod 775 /var/run/celery

# 創建 systemd-tmpfiles 配置文件以確保 /var/run/celery 持久存在
echo "創建 systemd-tmpfiles 配置文件以確保 /var/run/celery 持久存在..." | tee -a "$LOG_FILE"
cat > /etc/tmpfiles.d/celery.conf << EOL
d /var/run/celery 0775 mes www-data -
EOL

# 自動應用 systemd-tmpfiles 配置
echo "應用 systemd-tmpfiles 配置以確保 /var/run/celery 立即生效..." | tee -a "$LOG_FILE"
systemd-tmpfiles --create 2>&1 | tee -a "$LOG_FILE"

touch /var/log/mes/celery.log /var/log/mes/celery-beat.log
chown mes:mes /var/log/mes/celery.log /var/log/mes/celery-beat.log
chmod 644 /var/log/mes/celery.log /var/log/mes/celery-beat.log

# 從 .env 文件中提取 Celery 配置（已存在，但保留以保持一致性）
CELERY_BROKER_URL=$(grep '^CELERY_BROKER_URL=' "$ENV_FILE" | cut -d'=' -f2-)
CELERY_RESULT_BACKEND=$(grep '^CELERY_RESULT_BACKEND=' "$ENV_FILE" | cut -d'=' -f2-)
if [ -z "$CELERY_BROKER_URL" ] || [ -z "$CELERY_RESULT_BACKEND" ]; then
    echo "錯誤: 無法從 .env 文件中提取 Celery 配置" | tee -a "$LOG_FILE"
    cat "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

# 生成 Celery systemd 服務文件
echo "生成 Celery systemd 服務文件..." | tee -a "$LOG_FILE"
cat > /etc/systemd/system/celery-mes_config.service << EOL
[Unit]
Description=Celery Service for MES
After=network.target

[Service]
User=mes
Group=www-data
WorkingDirectory=/var/www/mes
Environment="CELERY_BROKER_URL=$CELERY_BROKER_URL"
Environment="CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND"
Environment="DJANGO_SETTINGS_MODULE=mes_config.settings"
Environment="ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP"
Environment="DATABASE_URL=$DATABASE_URL"
Environment="DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY"
Environment="DEBUG=True"
ExecStart=/usr/local/bin/celery -A mes_config worker --loglevel=info --logfile=/var/log/mes/celery.log --pidfile=/var/run/celery/%n.pid
Restart=always

[Install]
WantedBy=multi-user.target
EOL
chown root:root /etc/systemd/system/celery-mes_config.service
chmod 644 /etc/systemd/system/celery-mes_config.service

# 生成 Celery Beat systemd 服務文件
echo "生成 Celery Beat systemd 服務文件..." | tee -a "$LOG_FILE"
cat > /etc/systemd/system/celery-beat.service << EOL
[Unit]
Description=Celery Beat Service for MES
After=network.target

[Service]
User=mes
Group=www-data
WorkingDirectory=/var/www/mes
Environment="CELERY_BROKER_URL=$CELERY_BROKER_URL"
Environment="CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND"
Environment="DJANGO_SETTINGS_MODULE=mes_config.settings"
Environment="ALLOWED_HOSTS=localhost,127.0.0.1,$HOST_IP"
Environment="DATABASE_URL=$DATABASE_URL"
Environment="DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY"
Environment="DEBUG=True"
ExecStart=/usr/local/bin/celery -A mes_config beat --loglevel=info --logfile=/var/log/mes/celery-beat.log --scheduler django_celery_beat.schedulers:DatabaseScheduler --max-interval=5
Restart=always

[Install]
WantedBy=multi-user.target
EOL
chown root:root /etc/systemd/system/celery-beat.service
chmod 644 /etc/systemd/system/celery-beat.service
echo "Celery 和 Celery Beat 配置完成（未啟動）" | tee -a "$LOG_FILE"

# 步驟 13: 安裝並配置 Nginx（不啟動）
echo "步驟 13: 安裝並配置 Nginx（不啟動）..." | tee -a "$LOG_FILE"
# 檢查並安裝 Nginx
if ! command -v nginx >/dev/null 2>&1; then
    echo "Nginx 未安裝，正在安裝..." | tee -a "$LOG_FILE"
    apt-get update 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
        exit 1
    fi
    apt-get install -y nginx 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法安裝 Nginx" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "Nginx 安裝成功" | tee -a "$LOG_FILE"
else
    echo "Nginx 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi
# 確保 Nginx 服務未運行，留給 restart_services.sh 啟動
if systemctl is-active --quiet nginx; then
    systemctl stop nginx 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "警告: 無法停止 Nginx 服務，嘗試強制終止進程..." | tee -a "$LOG_FILE"
    fi
    # 檢查是否仍有進程占用 80 端口
    if lsof -i :80 -t > /dev/null; then
        NGINX_PIDS=$(lsof -i :80 -t | sort -u)
        echo "發現占用 80 端口的進程 (PIDs: $NGINX_PIDS)，正在終止..." | tee -a "$LOG_FILE"
        for pid in $NGINX_PIDS; do
            kill -9 $pid 2>&1 | tee -a "$LOG_FILE"
        done
        sleep 1
        if lsof -i :80 -t > /dev/null; then
            echo "錯誤: 無法清理 80 端口，仍然被占用，請手動檢查" | tee -a "$LOG_FILE"
            lsof -i :80 2>&1 | tee -a "$LOG_FILE"
            exit 1
        fi
        echo "80 端口已清理" | tee -a "$LOG_FILE"
    fi
    echo "Nginx 服務已停止，等待後續腳本啟動" | tee -a "$LOG_FILE"
else
    echo "Nginx 服務未運行，無需停止" | tee -a "$LOG_FILE"
fi

# 確保 Nginx 配置目錄存在
mkdir -p /etc/nginx/sites-available 2>&1 | tee -a "$LOG_FILE"
mkdir -p /etc/nginx/sites-enabled 2>&1 | tee -a "$LOG_FILE"

# 從 .env 文件中提取 HOST_IP
HOST_IP=$(grep '^HOST_IP=' "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$HOST_IP" ]; then
    echo "錯誤: 無法從 .env 文件中提取 HOST_IP" | tee -a "$LOG_FILE"
    cat "$ENV_FILE" 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi
echo "從 .env 文件提取的 HOST_IP: $HOST_IP" | tee -a "$LOG_FILE"

# 確保靜態文件路徑存在並設置正確權限
STATIC_DIR="/var/www/mes/static"
if [ ! -d "$STATIC_DIR" ]; then
    echo "靜態文件路徑 $STATIC_DIR 不存在，正在創建..." | tee -a "$LOG_FILE"
    mkdir -p "$STATIC_DIR" 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法創建靜態文件路徑 $STATIC_DIR" | tee -a "$LOG_FILE"
        exit 1
    fi
fi
chown mes:www-data "$STATIC_DIR" 2>&1 | tee -a "$LOG_FILE"
chmod 775 "$STATIC_DIR" 2>&1 | tee -a "$LOG_FILE"
echo "靜態文件路徑 $STATIC_DIR 已準備好" | tee -a "$LOG_FILE"

# 創建 Nginx 配置文件
NGINX_CONF="/etc/nginx/sites-available/mes"
cat > "$NGINX_CONF" << EOF
upstream mes_app {
    server 127.0.0.1:8000;
}
server {
    listen 80;
    server_name $HOST_IP;
    location / {
        proxy_pass http://mes_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        # 設置超時時間（可根據需求調整）
        proxy_read_timeout 120s;  # 設置為 120 秒（2 分鐘）
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
    }
    location /static/ {
        alias /var/www/mes/static/;
    }
}
EOF
chown root:root "$NGINX_CONF" 2>&1 | tee -a "$LOG_FILE"
chmod 644 "$NGINX_CONF" 2>&1 | tee -a "$LOG_FILE"
# 創建符號鏈接
ln -sf /etc/nginx/sites-available/mes /etc/nginx/sites-enabled/mes 2>&1 | tee -a "$LOG_FILE"
# 驗證 Nginx 配置
nginx -t 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: Nginx 配置檔案無效，請檢查 /etc/nginx/sites-available/mes" | tee -a "$LOG_FILE"
    cat "$NGINX_CONF" | tee -a "$LOG_FILE"
    exit 1
fi
echo "Nginx 配置檔案驗證通過" | tee -a "$LOG_FILE"
echo "Nginx 配置完成（未啟動，等待後續腳本啟動）" | tee -a "$LOG_FILE"

# 步驟 14: 安裝其他工具（僅 gettext 和 htop）
echo "步驟 14: 安裝其他工具..." | tee -a "$LOG_FILE"

# 安裝輔助工具（僅 gettext 和 htop）
echo "正在安裝輔助工具（gettext, htop）..." | tee -a "$LOG_FILE"
apt-get update 2>&1 | tee -a "$LOG_FILE"
apt-get install -y gettext htop 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
  echo "錯誤: 無法安裝輔助工具（gettext, htop）" | tee -a "$LOG_FILE"
  exit 1
fi

echo "步驟 14 完成: 其他工具（gettext, htop）安裝完成" | tee -a "$LOG_FILE"

# 步驟 15: 檢查 SELinux 和 AppArmor
echo "步驟 15: 檢查 SELinux 和 AppArmor..." | tee -a "$LOG_FILE"

# 檢查 SELinux
if command -v sestatus >/dev/null 2>&1; then
    sestatus 2>&1 | tee -a "$LOG_FILE"
else
    echo "SELinux 未啟用或未安裝" | tee -a "$LOG_FILE"
fi

# 檢查 AppArmor
aa-status 2>&1 | tee -a "$LOG_FILE" || echo "AppArmor 未啟用" | tee -a "$LOG_FILE"

echo "SELinux 和 AppArmor 檢查完成" | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [v$SCRIPT_VERSION] 腳本 $(basename "$0") 執行成功" | tee -a "$LOG_FILE"

# 步驟 16: 配置日誌輪轉以管理日誌文件
echo "步驟 16: 配置日誌輪轉以管理日誌文件..." | tee -a "$LOG_FILE"

# 檢查並安裝 logrotate
if ! command -v logrotate >/dev/null 2>&1; then
    echo "logrotate 未安裝，正在安裝..." | tee -a "$LOG_FILE"
    apt-get update 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法更新套件列表，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
        exit 1
    fi
    apt-get install -y logrotate 2>&1 | tee -a "$LOG_FILE"
    if [ $? -ne 0 ]; then
        echo "錯誤: 無法安裝 logrotate，請檢查網絡或 apt 配置" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "logrotate 安裝成功" | tee -a "$LOG_FILE"
else
    echo "logrotate 已安裝，跳過安裝步驟" | tee -a "$LOG_FILE"
fi

# 創建 logrotate 配置文件
LOGROTATE_CONF="/etc/logrotate.d/mes"
echo "創建 logrotate 配置文件 $LOGROTATE_CONF..." | tee -a "$LOG_FILE"
cat > "$LOGROTATE_CONF" << EOF
# logrotate 配置 for MES 日誌文件
/var/log/mes/gunicorn.accesslog.log /var/log/mes/gunicorn.errorlog.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 mes mes
    postrotate
        systemctl reload gunicorn-mes_config >/dev/null 2>&1 || true
    endscript
}

/var/log/mes/celery.log /var/log/mes/celery-beat.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 mes mes
    postrotate
        systemctl reload celery-mes_config >/dev/null 2>&1 || true
        systemctl reload celery-beat >/dev/null 2>&1 || true
    endscript
}

/var/log/redis/redis-server.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 redis redis
    postrotate
        systemctl reload redis-server >/dev/null 2>&1 || true
    endscript
}

/var/log/mes/deploy.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 mes mes
}
EOF
if [ $? -ne 0 ]; then
    echo "錯誤: 無法創建 logrotate 配置文件 $LOGROTATE_CONF" | tee -a "$LOG_FILE"
    exit 1
fi
chown root:root "$LOGROTATE_CONF" 2>&1 | tee -a "$LOG_FILE"
chmod 644 "$LOGROTATE_CONF" 2>&1 | tee -a "$LOG_FILE"

# 驗證 logrotate 配置
logrotate -d "$LOGROTATE_CONF" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "錯誤: logrotate 配置無效，請檢查 $LOGROTATE_CONF" | tee -a "$LOG_FILE"
    cat "$LOGROTATE_CONF" | tee -a "$LOG_FILE"
    exit 1
fi
echo "logrotate 配置驗證通過" | tee -a "$LOG_FILE"

# 立即應用 logrotate 配置（可選）
echo "立即應用 logrotate 配置..." | tee -a "$LOG_FILE"
logrotate -f "$LOGROTATE_CONF" 2>&1 | tee -a "$LOG_FILE"
if [ $? -ne 0 ]; then
    echo "警告: 無法立即應用 logrotate 配置，但配置已生成，將在下次輪轉時生效" | tee -a "$LOG_FILE"
fi
echo "日誌輪轉配置完成" | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [v$SCRIPT_VERSION] 腳本 $(basename "$0") 執行成功" | tee -a "$LOG_FILE"

echo ""
echo "=== 環境配置完成 ==="
echo ""
echo "✅ 基礎環境已建立完成！"
echo ""
echo "📁 已建立的目錄和檔案："
echo "   - 專案目錄: /var/www/mes"
echo "   - 日誌目錄: /var/log/mes"
echo "   - 備份目錄: /var/backups/mes"
echo "   - 環境檔案: /var/www/mes/.env"
echo "   - 依賴檔案: /var/www/mes/requirements.txt"
echo ""
echo "🔧 已安裝的服務："
echo "   - PostgreSQL 資料庫"
echo "   - Redis 快取服務"
echo "   - Nginx 網頁伺服器"
echo "   - Python 環境和套件"
echo ""
echo "⚠️  重要提醒："
echo "請檢查並配置 /var/www/mes/.env 檔案中的設定："
echo "   - 資料庫連線設定"
echo "   - Redis 連線設定"
echo "   - 其他環境變數"
echo ""
echo "📝 下一步："
echo "配置 .env 檔案後，執行專案部署："
echo "   sudo ./deploy_production.sh"
echo ""
echo "📞 如需協助："
echo "   - 查看部署日誌: /var/log/mes/deploy.log"
echo "   - 檢查服務狀態: sudo systemctl status postgresql redis-server nginx"
echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [v$SCRIPT_VERSION] 腳本 $(basename "$0") 執行成功" | tee -a "$LOG_FILE"