from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import BackupSchedule, OperationLogConfig  # 導入 OperationLogConfig 模型


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label="電子郵件", required=False, help_text="可選填，提供您的電子郵件地址。"
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class EmailConfigForm(forms.Form):
    email_host = forms.CharField(label="郵件主機", max_length=100, required=True)
    email_port = forms.IntegerField(
        label="郵件端口", min_value=1, max_value=65535, required=True
    )
    email_use_tls = forms.BooleanField(label="使用 TLS", required=False, initial=True)
    email_host_user = forms.CharField(
        label="使用者名稱", max_length=100, required=False
    )
    email_host_password = forms.CharField(
        label="密碼", max_length=100, required=False, widget=forms.PasswordInput
    )
    default_from_email = forms.EmailField(
        label="預設發件人地址", max_length=254, required=True
    )


class BackupScheduleForm(forms.ModelForm):
    class Meta:
        model = BackupSchedule
        fields = ["backup_time", "retain_count", "is_active"]
        labels = {
            "backup_time": "備份時間",
            "retain_count": "保留份數",
            "is_active": "啟用排程",
        }
        widgets = {
            "backup_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }
        help_texts = {
            "backup_time": "每天的備份時間，例如 02:00",
            "retain_count": "最多保留的備份份數（1-30）",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["retain_count"].widget.attrs.update({"min": 1, "max": 30})
        self.fields["is_active"].initial = False


class OperationLogConfigForm(forms.ModelForm):
    class Meta:
        model = OperationLogConfig
        fields = ["retain_days"]
        labels = {
            "retain_days": "操作紀錄保留天數",
        }
        help_texts = {
            "retain_days": "操作紀錄保留的天數（1-365）",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["retain_days"].widget.attrs.update({"min": 1, "max": 365})
