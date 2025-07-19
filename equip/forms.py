# 設備管理表單
# 此檔案定義設備管理模組的表單類別，用於資料輸入驗證

from django import forms
from django.core.exceptions import ValidationError
from .models import Equipment


class EquipmentForm(forms.ModelForm):
    """
    設備表單
    """

    class Meta:
        model = Equipment
        fields = ["name", "model", "status", "production_line"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例如：SMT-001、測試機台A",
                }
            ),
            "model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例如：SMT-2023、TEST-001",
                }
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "production_line": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_name(self):
        """驗證設備名稱"""
        name = self.cleaned_data.get("name")
        if not name:
            raise ValidationError("請輸入設備名稱！")

        # 檢查名稱是否已存在（排除當前編輯的設備）
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            if Equipment.objects.filter(name=name).exclude(pk=instance.pk).exists():
                raise ValidationError(f"設備名稱 '{name}' 已存在，請選擇其他名稱！")
        else:
            if Equipment.objects.filter(name=name).exists():
                raise ValidationError(f"設備名稱 '{name}' 已存在，請選擇其他名稱！")

        return name

    def clean_model(self):
        """驗證設備型號"""
        model = self.cleaned_data.get("model", "").strip()
        return model

    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        status = cleaned_data.get("status")

        if name and status:
            # 可以添加其他驗證邏輯
            pass

        return cleaned_data
