from django import forms
from .models import WorkOrder, CompanyOrder, WorkOrderProcess
from process.models import Operator
from equip.models import Equipment
from .models import WorkOrderAssignment


# 工單管理表單，支援新增與編輯
class WorkOrderForm(forms.ModelForm):
    # 公司代號欄位（手動輸入或下拉）
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 工單編號（手動輸入）
    order_number = forms.CharField(
        max_length=50,
        label="工單編號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 產品編號（手動輸入）
    product_code = forms.CharField(
        max_length=100,
        label="產品編號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 數量（手動輸入）
    quantity = forms.IntegerField(
        label="數量",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=True,
        min_value=1,
    )
    # 狀態（下拉選單）
    status = forms.ChoiceField(
        label="狀態",
        choices=[
            ("pending", "待生產"),
            ("in_progress", "生產中"),
            ("completed", "已完工"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )

    class Meta:
        model = WorkOrder
        fields = ["company_code", "order_number", "product_code", "quantity", "status"]
        labels = {
            "company_code": "公司代號",
            "order_number": "工單編號",
            "product_code": "產品編號",
            "quantity": "數量",
            "status": "狀態",
        }
        widgets = {
            "company_code": forms.TextInput(attrs={"class": "form-control"}),
            "order_number": forms.TextInput(attrs={"class": "form-control"}),
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動態載入產品編號選項
        self.fields["product_code"].choices = self.get_product_choices()

    def get_product_choices(self):
        """取得產品編號選項，從公司製令單中取得"""
        choices = [("", "請選擇產品編號")]
        try:
            # 取得所有未轉換的公司製令單
            from .models import CompanyOrder
            company_orders = (
                CompanyOrder.objects.filter(is_converted=False)
                .values_list("product_id", "product_id")
                .distinct()
                .order_by("product_id")
            )

            for product_id, _ in company_orders:
                choices.append((product_id, product_id))
        except Exception as e:
            # 如果發生錯誤，至少提供空選項
            pass

        return choices
