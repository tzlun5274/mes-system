# Django 應用程式初始化檔案
# 確保 Celery 應用程式在 Django 啟動時正確初始化

from .celery import app as celery_app

__all__ = ("celery_app",)
