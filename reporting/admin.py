from django.contrib import admin
from .models import (
    ProductionDailyReport,
    OperatorPerformance,
    ReportEmailSchedule,
    ReportEmailLog,
    ReportingOperationLog,
    WorkTimeReport,
    WorkOrderProductReport,
    PersonnelPerformanceReport,
    EquipmentEfficiencyReport,
    QualityAnalysisReport,
    ComprehensiveAnalysisReport,
    ManufacturingWorkHour,
    ReportSyncSettings,
)

# 報表管理模組管理介面
@admin.register(ProductionDailyReport)
class ProductionDailyReportAdmin(admin.ModelAdmin):
    """生產日報表管理"""
    list_display = ['date', 'operator_or_line', 'equipment_name', 'line', 'completed_quantity', 'created_at']
    list_filter = ['date', 'operator_or_line', 'equipment_name', 'line']
    search_fields = ['operator_or_line', 'equipment_name', 'process_name']
    date_hierarchy = 'date'
    verbose_name = "生產日報表"
    verbose_name_plural = "生產日報表"


@admin.register(OperatorPerformance)
class OperatorPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        "operator_name",
        "equipment_name",
        "production_quantity",
        "equipment_usage_rate",
        "date",
    ]
    list_filter = ["date", "operator_name", "equipment_name"]
    search_fields = ["operator_name", "equipment_name"]
    date_hierarchy = "date"


@admin.register(ReportSyncSettings)
class ReportSyncSettingsAdmin(admin.ModelAdmin):
    list_display = ["report_type", "sync_interval_hours", "is_active", "updated_at"]
    list_filter = ["report_type", "is_active"]
    readonly_fields = ["created_at", "updated_at"]

    def has_add_permission(self, request):
        # 只允許為每種報表類型創建一個設定
        return ReportSyncSettings.objects.count() < 2


@admin.register(ReportEmailSchedule)
class ReportEmailScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "report_type",
        "schedule_type",
        "send_time",
        "is_active",
        "updated_at",
    ]
    list_filter = ["report_type", "schedule_type", "is_active"]
    search_fields = ["recipients", "cc_recipients"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "基本設定",
            {"fields": ("report_type", "schedule_type", "send_time", "is_active")},
        ),
        ("收件人設定", {"fields": ("recipients", "cc_recipients", "subject_template")}),
        (
            "時間記錄",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ReportEmailLog)
class ReportEmailLogAdmin(admin.ModelAdmin):
    list_display = ["report_type", "status", "sent_at", "schedule"]
    list_filter = ["status", "report_type", "sent_at"]
    search_fields = ["recipients", "subject", "error_message"]
    readonly_fields = ["sent_at"]

    fieldsets = (
        ("基本資訊", {"fields": ("schedule", "report_type", "recipients", "subject")}),
        ("發送狀態", {"fields": ("status", "error_message", "sent_at")}),
    )

    def has_add_permission(self, request):
        # 不允許手動創建記錄
        return False

    def has_change_permission(self, request, obj=None):
        # 不允許修改記錄
        return False
