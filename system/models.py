from django.db import models
from django.utils import timezone

class EmailConfig(models.Model):
    email_host = models.CharField(max_length=100, blank=True, default='')
    email_port = models.IntegerField(default=25)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=100, blank=True, default='')
    email_host_password = models.CharField(max_length=100, blank=True, default='')
    default_from_email = models.EmailField(max_length=254, blank=True, default='')

    class Meta:
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return "Email Configuration"

class BackupSchedule(models.Model):
    backup_time = models.TimeField(default="00:00")
    retain_count = models.IntegerField(default=5)
    is_active = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"Backup Schedule at {self.backup_time}"

class OperationLogConfig(models.Model):
    retain_days = models.IntegerField(default=30)

    class Meta:
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"Operation Log Config - Retain {self.retain_days} days"
