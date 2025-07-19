import os
from pathlib import Path
import mimetypes
import environ

# 生產環境設定檔，適合正式上線，強調安全與穩定
# 請務必根據實際情況修改 ALLOWED_HOSTS、資料庫、郵件等設定

BASE_DIR = Path(__file__).resolve().parent.parent

# 初始化 environ 並讀取 .env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="請改成正式金鑰")
DEBUG = False  # 生產模式，隱藏詳細錯誤
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["yourdomain.com"])  # 只允許正式網域

SITE_URL = f"https://{env('HOST_IP', default='yourdomain.com')}"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django_celery_beat",
    "django_celery_results",
    "rosetta",
    "corsheaders",
    "equip",
    "material",
    "process",
    "scheduling",
    "quality",
    "work_order",
    "reporting",
    "kanban",
    "erp_integration.apps.ErpIntegrationConfig",
    "ai",
    "system",
]

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

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["https://yourdomain.com"]
)
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "mes_config.urls"

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

WSGI_APPLICATION = "mes_config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default="mesdb"),
        "USER": env("DATABASE_USER", default="mesuser"),
        "PASSWORD": env("DATABASE_PASSWORD", default="mespassword"),
        "HOST": env("DATABASE_HOST", default="localhost"),
        "PORT": env("DATABASE_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = env("LANGUAGE_CODE", default="zh-hant")
TIME_ZONE = env("TIME_ZONE", default="Asia/Taipei")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static_collected")  # 生產環境建議 collectstatic
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Taipei"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/home/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, "tmp")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "django": {
        "handlers": ["console"],
        "level": "WARNING",  # 生產環境建議只顯示 WARNING 以上
        "propagate": True,
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
INTERNAL_IPS = ["127.0.0.1"]
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/x-icon", ".ico")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default="25")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@yourdomain.com")
# 這份設定檔只適用於正式上線，請勿用於開發測試！
