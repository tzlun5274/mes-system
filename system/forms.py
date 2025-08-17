from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    EmailConfig, 
    BackupSchedule, 
    OperationLogConfig,
    UserWorkPermission
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


class UserWorkPermissionForm(forms.ModelForm):
    """使用者工作權限設定表單"""
    
    # 多選欄位
    operator_codes_multiple = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '8',
            'id': 'operator_codes_multiple'
        }),
        label="作業員編號（多選）",
        help_text="按住 Ctrl 鍵可多選，留空表示可操作所有作業員"
    )
    
    process_names_multiple = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '8',
            'id': 'process_names_multiple'
        }),
        label="工序名稱（多選）",
        help_text="按住 Ctrl 鍵可多選，留空表示可操作所有工序"
    )
    
    class Meta:
        model = UserWorkPermission
        fields = [
            'user',
            'operator_codes',
            'process_names',
            'permission_type',
            'is_active',
            'notes'
        ]
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control',
                'id': 'user_select'
            }),
            'operator_codes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '例如：OP001, OP002, OP003\n留空表示可操作所有作業員',
                'id': 'operator_codes_text',
                'style': 'display: none;'
            }),
            'process_names': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '例如：SMT貼片, 插件, 測試\n留空表示可操作所有工序',
                'id': 'process_names_text',
                'style': 'display: none;'
            }),
            'permission_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '備註說明'
            })
        }
        labels = {
            'user': '使用者',
            'operator_codes': '作業員編號',
            'process_names': '工序名稱',
            'permission_type': '權限類型',
            'is_active': '啟用狀態',
            'notes': '備註'
        }
        help_texts = {
            'operator_codes': '可操作的作業員編號，多個用逗號分隔，留空表示可操作所有作業員',
            'process_names': '可操作的工序名稱，多個用逗號分隔，留空表示可操作所有工序',
            'permission_type': '選擇使用者可以進行的報工類型',
            'is_active': '啟用或停用此權限設定'
        }
        labels = {
            'user': '使用者',
            'operator_codes': '作業員編號',
            'process_names': '工序名稱',
            'permission_type': '權限類型',
            'is_active': '啟用狀態',
            'notes': '備註'
        }
        help_texts = {
            'operator_codes': '可操作的作業員編號，多個用逗號分隔，留空表示可操作所有作業員',
            'process_names': '可操作的工序名稱，多個用逗號分隔，留空表示可操作所有工序',
            'permission_type': '選擇使用者可以進行的報工類型',
            'is_active': '啟用或停用此權限設定'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 將原始欄位設為非必填
        self.fields['operator_codes'].required = False
        self.fields['process_names'].required = False
        
        # 動態獲取作業員和工序選項
        self.fields['operator_codes_multiple'].choices = self._get_operator_choices()
        self.fields['process_names_multiple'].choices = self._get_process_choices()
        
        # 如果有實例，設定多選欄位的初始值
        if self.instance and self.instance.pk:
            if self.instance.operator_codes:
                operator_codes = [code.strip() for code in self.instance.operator_codes.split(',') if code.strip()]
                self.fields['operator_codes_multiple'].initial = operator_codes
            
            if self.instance.process_names:
                process_names = [name.strip() for name in self.instance.process_names.split(',') if name.strip()]
                self.fields['process_names_multiple'].initial = process_names
    
    def _get_operator_choices(self):
        """獲取作業員選項"""
        try:
            # 優先從製程模組獲取作業員資料
            try:
                from process.models import Operator
                operators = Operator.objects.all().order_by('name')
                if operators.exists():
                    return [(op.name, f"{op.name} - 作業員") for op in operators]
            except (ImportError, AttributeError):
                pass
            
            # 嘗試從填報記錄中獲取作業員資料
            try:
                from workorder.fill_work.models import FillWork
                from django.db.models import Q
                operators = FillWork.objects.values_list('operator', flat=True).distinct().exclude(
                    Q(operator__isnull=True) | Q(operator='')
                ).order_by('operator')
                if operators.exists():
                    return [(op, f"{op} - 作業員") for op in operators]
            except (ImportError, AttributeError):
                pass
            
            # 嘗試從現場報工記錄中獲取作業員資料
            try:
                from workorder.onsite_reporting.models import OnsiteReportSession
                from django.db.models import Q
                operators = OnsiteReportSession.objects.values_list('operator', flat=True).distinct().exclude(
                    Q(operator__isnull=True) | Q(operator='')
                ).order_by('operator')
                if operators.exists():
                    return [(op, f"{op} - 作業員") for op in operators]
            except (ImportError, AttributeError):
                pass
            
            # 如果沒有找到任何作業員資料，返回空列表
            return []
        except Exception as e:
            # 如果發生任何錯誤，返回空列表
            return []
    
    def _get_process_choices(self):
        """獲取工序選項"""
        try:
            # 嘗試從工單模組獲取工序資料
            try:
                from workorder.models import Process
                processes = Process.objects.filter(is_active=True).order_by('name')
                if processes.exists():
                    return [(proc.name, proc.name) for proc in processes]
            except (ImportError, AttributeError):
                pass
            
            # 嘗試從製程模組獲取工序資料
            try:
                from process.models import Process
                processes = Process.objects.filter(is_active=True).order_by('name')
                if processes.exists():
                    return [(proc.name, proc.name) for proc in processes]
            except (ImportError, AttributeError):
                pass
            
            # 嘗試從填報記錄中獲取工序資料
            try:
                from workorder.fill_work.models import FillWork
                from django.db.models import Q
                processes = FillWork.objects.values_list('process__name', flat=True).distinct().exclude(
                    Q(process__name__isnull=True) | Q(process__name='')
                ).order_by('process__name')
                if processes.exists():
                    return [(proc, proc) for proc in processes]
            except (ImportError, AttributeError):
                pass
            
            # 如果沒有找到任何工序資料，返回空列表
            return []
        except Exception:
            return []
    
    def clean_operator_codes_multiple(self):
        """驗證多選作業員編號"""
        operator_codes = self.cleaned_data.get('operator_codes_multiple')
        if operator_codes:
            # 將多選結果轉換為逗號分隔的字串
            if isinstance(operator_codes, list):
                return ', '.join(operator_codes)
            else:
                return operator_codes
        return ''
    
    def clean_process_names_multiple(self):
        """驗證多選工序名稱"""
        process_names = self.cleaned_data.get('process_names_multiple')
        if process_names:
            # 將多選結果轉換為逗號分隔的字串
            if isinstance(process_names, list):
                return ', '.join(process_names)
            else:
                return process_names
        return ''
    
    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()
        
        # 將多選結果同步到原始欄位
        cleaned_data['operator_codes'] = self.clean_operator_codes_multiple()
        cleaned_data['process_names'] = self.clean_process_names_multiple()
        
        user = cleaned_data.get('user')
        permission_type = cleaned_data.get('permission_type')
        
        # 檢查是否已存在相同使用者和權限類型的記錄
        if user and permission_type:
            existing = UserWorkPermission.objects.filter(
                user=user,
                permission_type=permission_type
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                permission_type_display = dict(self.fields["permission_type"].choices)[permission_type]
                raise forms.ValidationError(f'使用者 {user.username} 的 {permission_type_display} 權限已存在')
        
        return cleaned_data
    
    def save(self, commit=True):
        """儲存時處理多選欄位"""
        instance = super().save(commit=False)
        
        # 確保多選欄位的資料被正確設定
        if 'operator_codes_multiple' in self.cleaned_data:
            instance.operator_codes = self.clean_operator_codes_multiple()
        
        if 'process_names_multiple' in self.cleaned_data:
            instance.process_names = self.clean_process_names_multiple()
        
        if commit:
            instance.save()
        
        return instance


# 完工判斷設定已整合到現有的工單管理設定中
# 使用 workorder.workorder_erp.models.SystemConfig 來管理設定



