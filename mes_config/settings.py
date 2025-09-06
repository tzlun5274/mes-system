import os
from pathlib import Path
from django.db import connections
import mimetypes
import environ

# 基本路徑設置
BASE_DIR = Path(__file__).resolve().parent.parent

# 初始化 environ 並讀取 .env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# 安全金鑰，從環境變數讀取
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-fallback-key-for-development-only')

# 開發/生產環境設定
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', '0.0.0.0', '*'])

# API 基礎 URL
SITE_URL = f"http://{env('HOST_IP', default='localhost')}:{env('DJANGO_PORT', default='8000')}"

# 已安裝的應用
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",  # 添加 django-cors-headers
    "django_celery_beat",  # 添加 Celery Beat 支援
    "equip",
    "material",
    "process",
    "scheduling.apps.SchedulingConfig",
    "quality",
    "system",
    "workorder",
    "workorder.company_order.apps.CompanyOrderConfig",
    "workorder.workorder_dispatch.apps.WorkOrderDispatchConfig",
    "workorder.onsite_reporting.apps.OnsiteReportingConfig",
    "workorder.workorder_completed.apps.WorkOrderCompletedConfig",
    "workorder.fill_work.apps.FillWorkConfig",
            # 移除 production_monitoring，改用派工單監控資料

    "kanban.apps.KanbanConfig",
    "erp_integration.apps.ErpIntegrationConfig",
    "ai.apps.AiConfig",
    "production",
    "reporting",
    # "work_reporting_management",  # 已移除新的報工管理系統
    "django.contrib.humanize",
]

# 中間件設置
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "mes_config.middleware.RobustSessionMiddleware",  # 使用增強版的 Session 中間件
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # 重新啟用認證
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mes_config.middleware.DatabaseConnectionMiddleware",  # 資料庫連線檢查中間件
    "mes_config.middleware.CompanyCodeMiddleware",  # 公司代號中間件
    "mes_config.middleware.DataIsolationMiddleware",  # 資料隔離中間件
]

# CORS 配置（根據環境自動調整）
if DEBUG:
    # 開發環境：允許所有來源
    CORS_ALLOWED_ORIGINS = [
        f"http://localhost:{env('DJANGO_PORT', default='8000')}",
        f"http://127.0.0.1:{env('DJANGO_PORT', default='8000')}",
        f"http://{env('HOST_IP', default='localhost')}",
    ]
    CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
else:
    # 生產環境：只允許指定來源
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
        f"https://{env('HOST_IP', default='localhost')}",
    ])
    CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)

CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)  # 允許傳遞 cookie（如 sessionid）

# 安全設定（根據環境自動調整）
if DEBUG:
    # 開發環境安全設定
    SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=False)
    SECURE_BROWSER_XSS_FILTER = env.bool("SECURE_BROWSER_XSS_FILTER", default=False)
    SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default='no-referrer-when-downgrade')
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
else:
    # 生產環境安全設定
    SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)
    SECURE_BROWSER_XSS_FILTER = env.bool("SECURE_BROWSER_XSS_FILTER", default=True)
    SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default='strict-origin-when-cross-origin')
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    CSRF_COOKIE_HTTPONLY = env.bool("CSRF_COOKIE_HTTPONLY", default=True)
    SESSION_COOKIE_HTTPONLY = env.bool("SESSION_COOKIE_HTTPONLY", default=True)

# 表單設定
WIDGET_ATTRS = {
    'default': {
        'class': 'form-control',
    },
    'password': {
        'class': 'form-control',
        'type': 'password',
    },
    'email': {
        'class': 'form-control',
        'type': 'email',
    },
    'number': {
        'class': 'form-control',
        'type': 'number',
    },
    'date': {
        'class': 'form-control',
        'type': 'date',
    },
    'datetime': {
        'class': 'form-control',
        'type': 'datetime-local',
    },
    'textarea': {
        'class': 'form-control',
        'rows': 3,
    },
    'select': {
        'class': 'form-select',
    },
    'checkbox': {
        'class': 'form-check-input',
    },
    'radio': {
        'class': 'form-check-input',
    },
}

# 報表清理設定
REPORT_FILE_RETENTION_DAYS = env.int("REPORT_FILE_RETENTION_DAYS", default=7)  # 報表檔案保留天數
REPORT_LOG_RETENTION_DAYS = env.int("REPORT_LOG_RETENTION_DAYS", default=30)  # 報表執行日誌保留天數

# URL 配置
ROOT_URLCONF = env("ROOT_URLCONF", default="mes_config.urls")

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
WSGI_APPLICATION = env("WSGI_APPLICATION", default="mes_config.wsgi.application")

# 保留原本的 PostgreSQL 資料庫設定
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default="mesdb"),
        "USER": env("DATABASE_USER", default="mesuser"),
        "PASSWORD": env("DATABASE_PASSWORD", default="mespassword"),
        "HOST": env("DATABASE_HOST", default="localhost"),
        "PORT": env("DATABASE_PORT", default="5432"),
        "OPTIONS": {
            "options": "-c search_path=public"
        },
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
LANGUAGE_CODE = env("LANGUAGE_CODE", default="zh-hant")
TIME_ZONE = env("TIME_ZONE", default="Asia/Taipei")
USE_I18N = env.bool("USE_I18N", default=True)
USE_TZ = env.bool("USE_TZ", default=True)

# 支援的語言設定
LANGUAGES = [
    ('zh-hant', '繁體中文'),
    ('en', 'English'),
]

# 翻譯文件目錄設定
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# 編碼設定
DEFAULT_CHARSET = env("DEFAULT_CHARSET", default="utf-8")
FILE_CHARSET = env("FILE_CHARSET", default="utf-8")

# 根據環境設定靜態檔案
if DEBUG:
    # 開發環境：使用 STATICFILES_DIRS
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static"),
    ]
    # 開發環境也需要 STATIC_ROOT 用於 collectstatic 命令
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
else:
    # 生產環境：使用 STATIC_ROOT
    STATICFILES_DIRS = []
    STATIC_ROOT = env("STATIC_ROOT", default=os.path.join(BASE_DIR, "staticfiles"))

# 靜態檔案 URL 設定
STATIC_URL = env("STATIC_URL", default="/static/")

# 媒體檔案設定
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# 自動主鍵字段設置
DEFAULT_AUTO_FIELD = env("DEFAULT_AUTO_FIELD", default="django.db.models.BigAutoField")

# Celery 配置：使用環境變數
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"redis://localhost:{env('REDIS_PORT', default='6379')}/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=f"redis://localhost:{env('REDIS_PORT', default='6379')}/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = env("CELERY_TASK_SERIALIZER", default="json")
CELERY_RESULT_SERIALIZER = env("CELERY_RESULT_SERIALIZER", default="json")
CELERY_TIMEZONE = env("TIME_ZONE", default="Asia/Taipei")

# 認證和重定向設置
LOGIN_URL = env("LOGIN_URL", default="/accounts/login/")
LOGIN_REDIRECT_URL = env("LOGIN_REDIRECT_URL", default="/home/")
LOGOUT_REDIRECT_URL = env("LOGOUT_REDIRECT_URL", default="/accounts/login/")

# Session 設定 - 使用資料庫儲存 session (避免額外依賴)
SESSION_ENGINE = env("SESSION_ENGINE", default="django.contrib.sessions.backends.db")

# 會話超時設定 (預設 30 分鐘)
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=30 * 60)  # 30 分鐘 * 60 秒
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=False)  # 瀏覽器關閉時不立即過期
SESSION_SAVE_EVERY_REQUEST = env.bool("SESSION_SAVE_EVERY_REQUEST", default=True)  # 每次請求都更新會話

# Session 安全設定
SESSION_COOKIE_SECURE = False  # 開發環境設為 False，生產環境應設為 True
SESSION_COOKIE_HTTPONLY = env.bool("SESSION_COOKIE_HTTPONLY", default=True)  # 防止 XSS 攻擊
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default='Lax')  # CSRF 保護

# Session 資料庫連線設定
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
SESSION_COOKIE_PATH = env("SESSION_COOKIE_PATH", default='/')

# 改善 session 處理的設定
SESSION_SERIALIZER = env("SESSION_SERIALIZER", default='django.contrib.sessions.serializers.JSONSerializer')

# 文件上傳設置
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=None)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=2621440)
FILE_UPLOAD_TEMP_DIR = env("FILE_UPLOAD_TEMP_DIR", default=os.path.join(BASE_DIR, "tmp"))

# 日誌設置（根據 DEBUG 設定自動調整）

# 日誌目錄設定
LOG_DIR = env("LOG_DIR", default=os.path.join(BASE_DIR, "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

# 統一日誌路徑配置
LOG_BASE_DIR = env("LOG_BASE_DIR", default="/var/log/mes")
DJANGO_LOG_DIR = os.path.join(LOG_BASE_DIR, "django")
SYSTEM_LOG_DIR = os.path.join(LOG_BASE_DIR, "system")
WORKORDER_LOG_DIR = os.path.join(LOG_BASE_DIR, "workorder")
ERP_LOG_DIR = os.path.join(LOG_BASE_DIR, "erp_integration")
EQUIP_LOG_DIR = os.path.join(LOG_BASE_DIR, "equip")
MATERIAL_LOG_DIR = os.path.join(LOG_BASE_DIR, "material")
QUALITY_LOG_DIR = os.path.join(LOG_BASE_DIR, "quality")
KANBAN_LOG_DIR = os.path.join(LOG_BASE_DIR, "kanban")
PRODUCTION_LOG_DIR = os.path.join(LOG_BASE_DIR, "production")
AI_LOG_DIR = os.path.join(LOG_BASE_DIR, "ai")
SCHEDULING_LOG_DIR = os.path.join(LOG_BASE_DIR, "scheduling")
PROCESS_LOG_DIR = os.path.join(LOG_BASE_DIR, "process")

# 確保日誌目錄存在
for log_dir in [LOG_BASE_DIR, DJANGO_LOG_DIR, SYSTEM_LOG_DIR, WORKORDER_LOG_DIR, 
                ERP_LOG_DIR, EQUIP_LOG_DIR, MATERIAL_LOG_DIR, QUALITY_LOG_DIR,
                KANBAN_LOG_DIR, PRODUCTION_LOG_DIR, AI_LOG_DIR, SCHEDULING_LOG_DIR, PROCESS_LOG_DIR]:
    os.makedirs(log_dir, exist_ok=True)

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
            "filename": os.path.join(env("LOG_BASE_DIR", default="/var/log/mes"), "mes.log"),
            "formatter": "detailed",
        },
        "workorder_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(env("LOG_BASE_DIR", default="/var/log/mes"), "workorder.log"),
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

# 根據 DEBUG 設定調整日誌級別
if DEBUG:
    # 開發環境：最詳細的日誌
    LOGGING["loggers"]["django"]["level"] = "DEBUG"
    LOGGING["loggers"]["mes"]["level"] = "DEBUG"
    LOGGING["loggers"]["erp_integration"]["level"] = "DEBUG"
else:
    # 生產環境：INFO 等級
    LOGGING["loggers"]["django"]["level"] = "INFO"
    LOGGING["loggers"]["mes"]["level"] = "INFO"
    LOGGING["loggers"]["erp_integration"]["level"] = "INFO"

# 只需要設置 EMAIL_BACKEND，具體郵件設定從資料庫讀取
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")

# Debug Toolbar 設置
INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1", "localhost"])

# 安全設置
if DEBUG:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None  # 開發環境禁用 COOP 檢查
else:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = env("SECURE_CROSS_ORIGIN_OPENER_POLICY", default="same-origin")  # 生產環境啟用 COOP 檢查

# 添加正確的 MIME 類型
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/x-icon", ".ico")

# 日期格式設定 - 支援多種輸入格式，統一輸出為標準格式
DATE_FORMAT = env("DATE_FORMAT", default='Y-m-d')
DATE_INPUT_FORMATS = [
    '%Y-%m-%d',     # 2025-08-12 (ISO標準)
    '%Y/%m/%d',     # 2025/08/12
    '%Y.%m.%d',     # 2025.08.12
    '%Y%m%d',       # 20250812
    '%d/%m/%Y',     # 12/08/2025
    '%d-%m-%Y',     # 12-08-2025
    '%d.%m.%Y',     # 12.08.2025
    '%m/%d/%Y',     # 08/12/2025 (美式)
    '%m-%d-%Y',     # 08-12-2025 (美式)
    '%m.%d.%Y',     # 08.12.2025 (美式)
]
DATETIME_FORMAT = env("DATETIME_FORMAT", default='Y-m-d H:i:s')
DATETIME_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M:%S',    # 2025-08-12 14:30:00
    '%Y-%m-%d %H:%M',       # 2025-08-12 14:30
    '%Y/%m/%d %H:%M:%S',    # 2025/08/12 14:30:00
    '%Y/%m/%d %H:%M',       # 2025/08/12 14:30
    '%Y.%m.%d %H:%M:%S',    # 2025.08.12 14:30:00
    '%Y.%m.%d %H:%M',       # 2025.08.12 14:30
    '%Y%m%d %H:%M:%S',      # 20250812 14:30:00
    '%Y%m%d %H:%M',         # 20250812 14:30
    '%d/%m/%Y %H:%M:%S',    # 12/08/2025 14:30:00
    '%d/%m/%Y %H:%M',       # 12/08/2025 14:30
    '%d-%m-%Y %H:%M:%S',    # 12-08-2025 14:30:00
    '%d-%m-%Y %H:%M',       # 12-08-2025 14:30
    '%m/%d/%Y %H:%M:%S',    # 08/12/2025 14:30:00 (美式)
    '%m/%d/%Y %H:%M',       # 08/12/2025 14:30 (美式)
]
TIME_FORMAT = env("TIME_FORMAT", default='H:i')
TIME_INPUT_FORMATS = [
    '%H:%M:%S',     # 14:30:00
    '%H:%M',        # 14:30
    '%H.%M',        # 14.30
    '%H%M',         # 1430
]

# 新增的 EMAIL 設置
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")
