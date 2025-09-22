# -*- coding: utf-8 -*-
"""
系統管理模組的表單
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from .models import EmailConfig, BackupSchedule, OperationLogConfig, UserWorkPermission, OrderSyncSettings


class UserCreationFormCustom(UserCreationForm):
    """自定義用戶創建表單"""
    email = forms.EmailField(required=True, label="電子郵件")
    first_name = forms.CharField(max_length=30, required=False, label="名字")
    last_name = forms.CharField(max_length=30, required=False, label="姓氏")
    is_active = forms.BooleanField(required=False, initial=True, label="啟用帳號")
    is_staff = forms.BooleanField(required=False, initial=False, label="員工權限")
    
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "is_active", "is_staff", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class UserChangeFormCustom(UserChangeForm):
    """自定義用戶編輯表單"""
    email = forms.EmailField(required=True, label="電子郵件")
    first_name = forms.CharField(max_length=30, required=False, label="名字")
    last_name = forms.CharField(max_length=30, required=False, label="姓氏")
    is_active = forms.BooleanField(required=False, label="啟用帳號")
    is_staff = forms.BooleanField(required=False, label="管理員權限")
    is_superuser = forms.BooleanField(required=False, label="超級用戶")
    
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "is_active", "is_staff", "is_superuser")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class EmailConfigForm(forms.ModelForm):
    """郵件主機配置表單"""
    class Meta:
        model = EmailConfig
        fields = ["email_host", "email_port", "email_use_tls", "email_host_user", "email_host_password", "default_from_email"]
        widgets = {
            "email_host": forms.TextInput(attrs={"class": "form-control"}),
            "email_port": forms.NumberInput(attrs={"class": "form-control"}),
            "email_use_tls": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_host_user": forms.TextInput(attrs={"class": "form-control"}),
            "email_host_password": forms.PasswordInput(attrs={"class": "form-control"}),
            "default_from_email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class BackupScheduleForm(forms.ModelForm):
    """備份排程表單"""
    class Meta:
        model = BackupSchedule
        fields = ["schedule_type", "backup_time", "is_active", "retention_days"]
        widgets = {
            "schedule_type": forms.Select(attrs={"class": "form-select"}),
            "backup_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_days": forms.NumberInput(attrs={"class": "form-control"}),
        }


class OperationLogConfigForm(forms.ModelForm):
    """操作日誌配置表單"""
    class Meta:
        model = OperationLogConfig
        fields = ["log_level", "retention_days", "max_file_size", "is_active"]
        widgets = {
            "log_level": forms.Select(attrs={"class": "form-select"}),
            "retention_days": forms.NumberInput(attrs={"class": "form-control"}),
            "max_file_size": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class UserWorkPermissionForm(forms.ModelForm):
    """用戶工作權限表單"""
    # 作業員選擇欄位
    operator_choices = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="允許的作業員"
    )
    
    # 工序選擇欄位
    process_choices = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="允許的工序"
    )
    
    # 設備選擇欄位
    equipment_choices = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="允許的設備"
    )
    
    class Meta:
        model = UserWorkPermission
        fields = [
            'can_operate_all_operators', 'allowed_operators',
            'can_operate_all_processes', 'allowed_processes',
            'can_operate_all_equipments', 'allowed_equipments',
            'can_fill_work', 'can_onsite_reporting', 'can_operator_reporting', 'can_smt_reporting',
            'data_scope', 'can_view', 'can_add', 'can_edit', 'can_delete',
            'can_approve', 'can_reject', 'can_override_limits', 'can_export_data'
        ]
        widgets = {
            'can_operate_all_operators': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_operate_all_processes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_operate_all_equipments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_fill_work': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_onsite_reporting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_operator_reporting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_smt_reporting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_add': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_reject': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_override_limits': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_export_data': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_scope': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 動態載入作業員選項
        try:
            from process.models import Operator
            operators = Operator.objects.all().order_by('name')
            self.fields['operator_choices'].choices = [(op.id, op.name) for op in operators]
        except:
            self.fields['operator_choices'].choices = []
        
        # 動態載入工序選項
        try:
            from process.models import ProcessName
            processes = ProcessName.objects.all().order_by('name')
            self.fields['process_choices'].choices = [(proc.id, proc.name) for proc in processes]
        except:
            self.fields['process_choices'].choices = []
        
        # 動態載入設備選項
        try:
            from equip.models import Equipment
            equipments = Equipment.objects.all().order_by('name')
            self.fields['equipment_choices'].choices = [(eq.id, eq.name) for eq in equipments]
        except:
            self.fields['equipment_choices'].choices = []
        
        # 如果有實例，設定初始值
        if self.instance and self.instance.pk:
            self.fields['operator_choices'].initial = self.instance.allowed_operators
            self.fields['process_choices'].initial = self.instance.allowed_processes
            self.fields['equipment_choices'].initial = self.instance.allowed_equipments

    def clean(self):
        cleaned_data = super().clean()
        
        # 驗證權限邏輯
        can_operate_all_operators = cleaned_data.get('can_operate_all_operators')
        can_operate_all_processes = cleaned_data.get('can_operate_all_processes')
        can_operate_all_equipments = cleaned_data.get('can_operate_all_equipments')
        
        # 如果選擇了"可操作所有"，則清空限制列表
        if can_operate_all_operators:
            cleaned_data['allowed_operators'] = []
        else:
            cleaned_data['allowed_operators'] = self.data.getlist('operator_choices')
            
        if can_operate_all_processes:
            cleaned_data['allowed_processes'] = []
        else:
            cleaned_data['allowed_processes'] = self.data.getlist('process_choices')
            
        if can_operate_all_equipments:
            cleaned_data['allowed_equipments'] = []
        else:
            cleaned_data['allowed_equipments'] = self.data.getlist('equipment_choices')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 設定允許的ID列表
        if not instance.can_operate_all_operators:
            instance.allowed_operators = self.cleaned_data.get('allowed_operators', [])
        if not instance.can_operate_all_processes:
            instance.allowed_processes = self.cleaned_data.get('allowed_processes', [])
        if not instance.can_operate_all_equipments:
            instance.allowed_equipments = self.cleaned_data.get('allowed_equipments', [])
        
        if commit:
            instance.save()
        return instance


class OrderSyncSettingsForm(forms.ModelForm):
    """客戶訂單同步設定表單"""
    
    class Meta:
        model = OrderSyncSettings
        fields = [
            'sync_enabled', 'sync_interval_minutes',
            'cleanup_enabled', 'cleanup_interval_hours', 'cleanup_retention_days',
            'status_update_enabled', 'status_update_interval_minutes'
        ]
        widgets = {
            'sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_interval_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 1440}),
            'cleanup_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cleanup_interval_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 168}),
            'cleanup_retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365}),
            'status_update_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status_update_interval_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 1440}),
        }
# 
#     
#     def clean_sync_interval_minutes(self):
#         """驗證同步間隔"""
#         interval = self.cleaned_data.get('sync_interval_minutes')
#         if interval and interval < 1:
#             raise forms.ValidationError("同步間隔不能少於1分鐘")
#         if interval and interval > 1440:
#             raise forms.ValidationError("同步間隔不能超過1440分鐘（24小時）")
#         return interval
#     
#     def clean_cleanup_interval_hours(self):
#         """驗證清理間隔"""
#         interval = self.cleaned_data.get('cleanup_interval_hours')
#         if interval and interval < 1:
#             raise forms.ValidationError("清理間隔不能少於1小時")
#         if interval and interval > 168:
#             raise forms.ValidationError("清理間隔不能超過168小時（7天）")
#         return interval
#     
#     def clean_cleanup_retention_days(self):
#         """驗證資料保留天數"""
#         days = self.cleaned_data.get('cleanup_retention_days')
#         if days and days < 1:
#             raise forms.ValidationError("資料保留天數不能少於1天")
#         if days and days > 365:
#             raise forms.ValidationError("資料保留天數不能超過365天")
#         return days
#     
#     def clean_status_update_interval_minutes(self):
#         """驗證狀態更新間隔"""
#         interval = self.cleaned_data.get('status_update_interval_minutes')
#         if interval and interval < 1:
#             raise forms.ValidationError("狀態更新間隔不能少於1分鐘")
#         if interval and interval > 1440:
#             raise forms.ValidationError("狀態更新間隔不能超過1440分鐘（24小時）")
#         return interval