from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    EmailConfig, 
    BackupSchedule, 
    OperationLogConfig,
    CompletionCheckConfig
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


class CompletionCheckConfigForm(forms.ModelForm):
    """
    完工檢查配置表單
    """
    
    class Meta:
        model = CompletionCheckConfig
        fields = [
            'enabled',
            'interval_minutes', 
            'start_time',
            'end_time',
            'max_workorders_per_check',
            'enable_notifications'
        ]
        widgets = {
            'enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'enabled'
            }),
            'interval_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '60',
                'step': '1',
                'placeholder': '5'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'placeholder': '08:00'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control', 
                'type': 'time',
                'placeholder': '18:00'
            }),
            'max_workorders_per_check': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '1000',
                'step': '10',
                'placeholder': '100'
            }),
            'enable_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'enable_notifications'
            })
        }
        labels = {
            'enabled': '啟用完工檢查',
            'interval_minutes': '檢查間隔（分鐘）',
            'start_time': '開始時間',
            'end_time': '結束時間', 
            'max_workorders_per_check': '每次檢查最大工單數',
            'enable_notifications': '啟用完工通知'
        }
        help_texts = {
            'enabled': '啟用或停用完工檢查定時任務',
            'interval_minutes': '每多少分鐘檢查一次完工狀態（建議5-15分鐘）',
            'start_time': '每日開始檢查的時間',
            'end_time': '每日結束檢查的時間',
            'max_workorders_per_check': '每次檢查最多處理多少個工單，避免系統負載過重',
            'enable_notifications': '工單完工時是否發送通知'
        }
    
    def clean_interval_minutes(self):
        """驗證檢查間隔"""
        interval = self.cleaned_data.get('interval_minutes')
        if interval < 1 or interval > 60:
            raise forms.ValidationError('檢查間隔必須在1-60分鐘之間')
        return interval
    
    def clean_max_workorders_per_check(self):
        """驗證最大工單數"""
        max_workorders = self.cleaned_data.get('max_workorders_per_check')
        if max_workorders < 10 or max_workorders > 1000:
            raise forms.ValidationError('每次檢查最大工單數必須在10-1000之間')
        return max_workorders
    
    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('開始時間必須早於結束時間')
        
        return cleaned_data
