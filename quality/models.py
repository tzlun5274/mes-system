from django.db import models
from django.utils import timezone


class InspectionItem(models.Model):
    name = models.CharField(max_length=100, verbose_name="檢驗項目名稱")
    standard = models.TextField(verbose_name="檢驗標準")
    requirement = models.TextField(verbose_name="檢驗要求", blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "檢驗項目"
        verbose_name_plural = "檢驗項目"

    def __str__(self):
        return self.name


class InspectionRecord(models.Model):
    inspection_item = models.ForeignKey(
        InspectionItem, on_delete=models.CASCADE, verbose_name="檢驗項目"
    )
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    inspection_date = models.DateField(verbose_name="檢驗日期")
    result = models.CharField(
        max_length=20,
        verbose_name="檢驗結果",
        choices=[
            ("pass", "通過"),
            ("fail", "不通過"),
        ],
    )
    remarks = models.TextField(verbose_name="備註", blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "檢驗記錄"
        verbose_name_plural = "檢驗記錄"

    def __str__(self):
        return f"{self.product_name} - {self.inspection_date}"


class DefectiveProduct(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    defect_reason = models.TextField(verbose_name="不合格原因")
    quantity = models.IntegerField(verbose_name="不合格數量")
    defect_date = models.DateField(verbose_name="不合格日期")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "不良品記錄"
        verbose_name_plural = "不良品記錄"

    def __str__(self):
        return f"{self.product_name} - {self.defect_date}"


class FinalInspectionReport(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    inspection_date = models.DateField(verbose_name="檢驗日期")
    meets_standards = models.BooleanField(verbose_name="是否符合入庫標準")
    remarks = models.TextField(verbose_name="備註", blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "製成檢驗/入庫檢驗表"
        verbose_name_plural = "製成檢驗/入庫檢驗表"

    def __str__(self):
        return f"{self.product_name} - {self.inspection_date}"


class AOITestReport(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    test_date = models.DateField(verbose_name="測試日期")
    defect_detected = models.BooleanField(verbose_name="是否檢測到缺陷")
    defect_details = models.TextField(verbose_name="缺陷詳情", blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "AOI 測試報告"
        verbose_name_plural = "AOI 測試報告"

    def __str__(self):
        return f"{self.product_name} - {self.test_date}"


class QualityOperationLog(models.Model):
    user = models.CharField(max_length=100, verbose_name="用戶")
    action = models.TextField(verbose_name="操作")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")

    class Meta:
        verbose_name = "品質操作日誌"
        verbose_name_plural = "品質操作日誌"
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"
