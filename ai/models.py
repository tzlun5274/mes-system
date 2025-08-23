from django.db import models
from django.utils import timezone


class AIPrediction(models.Model):
    prediction_type = models.CharField(
        max_length=50,
        verbose_name="預測類型",
        choices=[
            ("production", "生產預測"),
            ("demand", "需求預測"),
            ("quality", "品質預測"),
        ],
    )
    # 生產預測的輸入字段
    production_line = models.CharField(
        max_length=100, verbose_name="生產線名稱", blank=True
    )
    current_output = models.FloatField(verbose_name="當前產量", null=True, blank=True)
    # 需求預測的輸入字段
    product_name = models.CharField(max_length=100, verbose_name="產品名稱", blank=True)
    historical_demand = models.FloatField(
        verbose_name="歷史需求量", null=True, blank=True
    )
    # 品質預測的輸入字段
    production_temperature = models.FloatField(
        verbose_name="生產溫度", null=True, blank=True
    )
    production_pressure = models.FloatField(
        verbose_name="生產壓力", null=True, blank=True
    )
    # 輸出字段（共用）
    predicted_output = models.FloatField(verbose_name="預測結果", null=True, blank=True)
    confidence = models.FloatField(verbose_name="信心度", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "AI 預測"
        verbose_name_plural = "AI 預測"
        default_permissions = ()
        permissions = [
            ("can_view_ai_prediction", "可以查看 AI 預測"),
            ("can_run_ai_prediction", "可以執行 AI 預測"),
        ]

    def __str__(self):
        return f"{self.get_prediction_type_display()} - {self.created_at}"


class AIOptimization(models.Model):
    optimization_type = models.CharField(
        max_length=50,
        verbose_name="優化類型",
        choices=[
            ("production", "生產優化"),
            ("scheduling", "自動化調度"),
        ],
    )
    # 生產優化的輸入字段
    production_line = models.CharField(
        max_length=100, verbose_name="生產線名稱", blank=True
    )
    current_capacity = models.FloatField(verbose_name="當前產能", null=True, blank=True)
    # 自動化調度的輸入字段
    task_name = models.CharField(max_length=100, verbose_name="任務名稱", blank=True)
    resource_available = models.CharField(
        max_length=100, verbose_name="可用資源", blank=True
    )
    # 輸出字段（共用）
    optimized_result = models.CharField(
        max_length=200, verbose_name="優化結果", blank=True
    )
    efficiency_gain = models.FloatField(verbose_name="效率提升", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "AI 優化"
        verbose_name_plural = "AI 優化"
        default_permissions = ()
        permissions = [
            ("can_view_ai_optimization", "可以查看 AI 優化"),
            ("can_run_ai_optimization", "可以執行 AI 優化"),
        ]

    def __str__(self):
        return f"{self.get_optimization_type_display()} - {self.created_at}"


class AIAnomaly(models.Model):
    anomaly_type = models.CharField(
        max_length=50,
        verbose_name="異常類型",
        choices=[
            ("production", "生產異常"),
            ("defect", "缺陷檢測"),
        ],
    )
    # 生產異常檢測的輸入字段
    production_line = models.CharField(
        max_length=100, verbose_name="生產線名稱", blank=True
    )
    production_rate = models.FloatField(verbose_name="生產速率", null=True, blank=True)
    # 缺陷檢測的輸入字段
    product_name = models.CharField(max_length=100, verbose_name="產品名稱", blank=True)
    defect_type = models.CharField(max_length=100, verbose_name="缺陷類型", blank=True)
    # 輸出字段（共用）
    anomaly_detected = models.BooleanField(verbose_name="是否檢測到異常", default=False)
    anomaly_details = models.CharField(
        max_length=200, verbose_name="異常詳情", blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "AI 異常檢測"
        verbose_name_plural = "AI 異常檢測"
        default_permissions = ()
        permissions = [
            ("can_view_ai_anomaly", "可以查看 AI 異常檢測"),
            ("can_run_ai_anomaly", "可以執行 AI 異常檢測"),
        ]

    def __str__(self):
        return f"{self.get_anomaly_type_display()} - {self.created_at}"


class AIOperationLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.CharField(max_length=150)
    action = models.CharField(max_length=255)

    class Meta:
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"
