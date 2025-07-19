import os
from pathlib import Path
from django.db import connections
import mimetypes
import environ

# 安全金鑰，Django 啟動必須，請勿外洩
SECRET_KEY = "m3s$2024!@#MES系統安全金鑰987654321"

# 基本路徑設置
BASE_DIR = Path(__file__).resolve().parent.parent

# 初始化 environ 並讀取 .env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# 僅保留開發環境設定
DEBUG = True  # 開發模式
ALLOWED_HOSTS = ["*"]  # 允許所有主機存取

# API 基礎 URL
SITE_URL = f"http://{os.environ.get('HOST_IP', 'localhost')}:8000"

# 已安裝的應用
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",  # 添加 admin 介面
    "django_celery_beat",
    "django_celery_results",
    "rosetta",
    "corsheaders",  # 添加 django-cors-headers
    "equip",
    "material",
    "process",
    "scheduling.apps.SchedulingConfig",
    "quality",
    "reporting",
    "system",
    "workorder",
    "kanban.apps.KanbanConfig",
    "erp_integration.apps.ErpIntegrationConfig",
    "ai.apps.AiConfig",
    "production",
    "django.contrib.humanize",
]

# 中間件設置
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS 配置（可選，如果前端或模組跨域訪問 API）
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.1.29",
]
CORS_ALLOW_CREDENTIALS = True  # 允許傳遞 cookie（如 sessionid）

# URL 配置
ROOT_URLCONF = "mes_config.urls"

# 模板設置
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "mes_config.context_processors.timezone",
            ],
        },
    },
]

# WSGI 應用
WSGI_APPLICATION = "mes_config.wsgi.application"

# 保留原本的 PostgreSQL 資料庫設定
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_NAME", "mesdb"),
        "USER": os.environ.get("DATABASE_USER", "mesuser"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "mespassword"),
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
    }
}

# 密碼驗證器
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# 國際化和時區設置
LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "zh-hant")
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Taipei")
USE_I18N = True
USE_TZ = True

# 編碼設定
DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'

# 靜態檔案設定（開發模式下自動處理）
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # 新增 STATIC_ROOT 設定

# 自動主鍵字段設置
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery 配置：硬編碼值
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Taipei"

# 認證和重定向設置
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/home/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# 文件上傳設置
DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, "tmp")

# 日誌設置（支援多環境）
ENVIRONMENT = os.environ.get(
    "DJANGO_ENV", "development"
)  # development, testing, production

# 日誌目錄設定
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 基礎日誌配置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "[{asctime}] {levelname} {name} {module} {funcName} {lineno:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "mes_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/log/mes/mes.log",
            "formatter": "detailed",
        },
        "workorder_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/log/mes/workorder.log",
            "formatter": "detailed",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["mes_file"],
            "level": "INFO",
            "propagate": True,
        },
        "mes": {
            "handlers": ["mes_file"],
            "level": "INFO",
            "propagate": True,
        },
        "erp_integration": {
            "handlers": ["mes_file"],
            "level": "INFO",
            "propagate": True,
        },
        "workorder": {
            "handlers": ["workorder_file"],
            "level": "INFO",
            "propagate": False,
        },
        # 其他模組也都寫進 mes.log
    },
}

# 根據環境調整日誌級別
if ENVIRONMENT == "production":
    # 生產環境：只記錄重要日誌
    LOGGING["loggers"]["django"]["level"] = "WARNING"
    LOGGING["loggers"]["mes"]["level"] = "WARNING"
    LOGGING["loggers"]["erp_integration"]["level"] = "INFO"

    # 添加郵件通知
    LOGGING["loggers"]["django.security"] = {
        "handlers": ["production_mail"],
        "level": "ERROR",
        "propagate": False,
    }

elif ENVIRONMENT == "testing":
    # 測試環境：中等詳細度
    LOGGING["loggers"]["django"]["level"] = "INFO"
    LOGGING["loggers"]["mes"]["level"] = "INFO"
    LOGGING["loggers"]["erp_integration"]["level"] = "DEBUG"

else:
    # 開發環境：最詳細的日誌
    LOGGING["loggers"]["django"]["level"] = "DEBUG"
    LOGGING["loggers"]["mes"]["level"] = "DEBUG"
    LOGGING["loggers"]["erp_integration"]["level"] = "DEBUG"

# 只需要設置 EMAIL_BACKEND，具體郵件設定從資料庫讀取
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Debug Toolbar 設置
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
    "192.168.1.21",  # 添加您的 IP
]

# 安全設置
SECURE_CROSS_ORIGIN_OPENER_POLICY = None  # 禁用 COOP 檢查
CORS_ALLOW_ALL_ORIGINS = True  # 允許所有來源的跨域請求
CORS_ALLOW_CREDENTIALS = True

# 添加正確的 MIME 類型
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/x-icon", ".ico")

# 新增的 EMAIL 設置
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = os.environ.get("EMAIL_PORT", "25")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost")
