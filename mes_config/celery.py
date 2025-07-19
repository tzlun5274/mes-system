import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes_config.settings")
app = Celery("mes_config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
