from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    EmailConfig, 
    BackupSchedule, 
    OperationLogConfig
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
