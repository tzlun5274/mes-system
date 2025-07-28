from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    EmailConfig, 
    BackupSchedule, 
    OperationLogConfig,
    ReportSyncSettings,
    ReportEmailSettings
)


class EmailConfigForm(forms.ModelForm):
    """郵件主機設定表單"""
    
    class Meta:
        model = EmailConfig
        fields = [
            'email_host', 
            'email_port', 
            'email_use_tls', 
            'email_host_user', 
            'email_host_password', 
            'default_from_email'
        ]
        widgets = {
            'email_host': forms.TextInput(attrs={'class': 'form-control'}),
            'email_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'email_use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_host_user': forms.TextInput(attrs={'class': 'form-control'}),
            'email_host_password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'default_from_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class BackupScheduleForm(forms.ModelForm):
    """備份排程設定表單"""
    
    class Meta:
        model = BackupSchedule
        fields = [
            'schedule_type', 
            'backup_time', 
            'retention_days', 
            'is_active'
        ]
        widgets = {
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
            'backup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OperationLogConfigForm(forms.ModelForm):
    """操作日誌設定表單"""
    
    class Meta:
        model = OperationLogConfig
        fields = [
            'log_level', 
            'retention_days', 
            'max_file_size', 
            'is_active'
        ]
        widgets = {
            'log_level': forms.Select(attrs={'class': 'form-control'}),
            'retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365}),
            'max_file_size': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ReportSyncSettingsForm(forms.ModelForm):
    """報表同步設定表單"""
    
    class Meta:
        model = ReportSyncSettings
        fields = [
            'sync_type',
            'sync_frequency',
            'sync_time',
            'data_source_modules',
            'include_pending_reports',
            'include_approved_reports',
            'auto_sync',
            'sync_retention_days',
            'retry_on_failure',
            'max_retry_attempts',
            'is_active'
        ]
        widgets = {
            'sync_type': forms.Select(attrs={'class': 'form-control'}),
            'sync_frequency': forms.Select(attrs={'class': 'form-control'}),
            'sync_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'data_source_modules': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '請輸入模組名稱，每行一個，例如：\nworkorder\nsmt_equipment\noperator'
            }),
            'include_pending_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_approved_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_sync': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 30, 'max': 1095}),
            'retry_on_failure': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_retry_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_data_source_modules(self):
        """清理資料來源模組欄位"""
        modules_text = self.cleaned_data.get('data_source_modules')
        if isinstance(modules_text, str):
            # 如果是字串，轉換為列表
            modules = [module.strip() for module in modules_text.split('\n') if module.strip()]
            return modules
        return modules_text


class ReportEmailSettingsForm(forms.ModelForm):
    """報表郵件設定表單"""
    
    class Meta:
        model = ReportEmailSettings
        fields = [
            'report_type',
            'send_frequency',
            'send_time',
            'recipients',
            'cc_recipients',
            'bcc_recipients',
            'subject_template',
            'email_template',
            'include_excel',
            'include_csv',
            'include_pdf',
            'is_active',
            'auto_send'
        ]
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-control'}),
            'send_frequency': forms.Select(attrs={'class': 'form-control'}),
            'send_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'recipients': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '請輸入收件人郵箱，多個郵箱請用逗號分隔'
            }),
            'cc_recipients': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': '請輸入副本收件人郵箱，多個郵箱請用逗號分隔'
            }),
            'bcc_recipients': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': '請輸入密件副本收件人郵箱，多個郵箱請用逗號分隔'
            }),
            'subject_template': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MES 系統 - {report_type} - {date}'
            }),
            'email_template': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 8,
                'placeholder': '請輸入郵件內容模板，支援 HTML 格式'
            }),
            'include_excel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_csv': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_pdf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_send': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_recipients(self):
        """驗證收件人郵箱格式"""
        recipients = self.cleaned_data.get('recipients')
        if recipients:
            emails = [email.strip() for email in recipients.split(',') if email.strip()]
            for email in emails:
                if not forms.EmailField().clean(email):
                    raise forms.ValidationError(f"無效的郵箱格式: {email}")
        return recipients

    def clean_cc_recipients(self):
        """驗證副本收件人郵箱格式"""
        cc_recipients = self.cleaned_data.get('cc_recipients')
        if cc_recipients:
            emails = [email.strip() for email in cc_recipients.split(',') if email.strip()]
            for email in emails:
                if not forms.EmailField().clean(email):
                    raise forms.ValidationError(f"無效的副本郵箱格式: {email}")
        return cc_recipients

    def clean_bcc_recipients(self):
        """驗證密件副本收件人郵箱格式"""
        bcc_recipients = self.cleaned_data.get('bcc_recipients')
        if bcc_recipients:
            emails = [email.strip() for email in bcc_recipients.split(',') if email.strip()]
            for email in emails:
                if not forms.EmailField().clean(email):
                    raise forms.ValidationError(f"無效的密件副本郵箱格式: {email}")
        return bcc_recipients


class CustomUserCreationForm(forms.ModelForm):
    """自訂用戶建立表單"""
    password1 = forms.CharField(label='密碼', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='確認密碼', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("密碼不匹配")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
