# Django Admin 管理介面
# 此檔案設定產線管理模組的後台管理介面

from django.contrib import admin
from django.utils.html import format_html
from .models import ProductionLineType, ProductionLine, ProductionLineSchedule


@admin.register(ProductionLineType)
class ProductionLineTypeAdmin(admin.ModelAdmin):
    """
    產線類型管理介面
    """

    list_display = ["type_code", "type_name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["type_code", "type_name"]
    ordering = ["type_code"]

    fieldsets = (
        ("基本資訊", {"fields": ("type_code", "type_name", "description")}),
        ("狀態設定", {"fields": ("is_active",)}),
    )

    def get_queryset(self, request):
        """根據使用者權限過濾資料"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # 一般使用者只能看到啟用的類型
        return qs.filter(is_active=True)


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    """
    產線管理介面
    """

    list_display = [
        "line_code",
        "line_name",
        "line_type",
        "work_time_display",
        "work_days_display",
        "is_active",
    ]
    list_filter = ["line_type", "is_active", "created_at"]
    search_fields = ["line_code", "line_name"]
    ordering = ["line_code"]

    fieldsets = (
        (
            "基本資訊",
            {"fields": ("line_code", "line_name", "line_type", "description")},
        ),
        (
            "工作時間設定",
            {
                "fields": (
                    "work_start_time",
                    "work_end_time",
                    "lunch_start_time",
                    "lunch_end_time",
                    "overtime_start_time",
                    "overtime_end_time",
                )
            },
        ),
        ("工作日設定", {"fields": ("work_days",)}),
        ("狀態設定", {"fields": ("is_active",)}),
    )

    def work_time_display(self, obj):
        """顯示工作時間"""
        return format_html(
            "{} - {}<br>午休: {} - {}<br>加班: {} - {}",
            obj.work_start_time.strftime("%H:%M"),
            obj.work_end_time.strftime("%H:%M"),
            obj.lunch_start_time.strftime("%H:%M"),
            obj.lunch_end_time.strftime("%H:%M"),
            obj.overtime_start_time.strftime("%H:%M"),
            obj.overtime_end_time.strftime("%H:%M"),
        )

    work_time_display.short_description = "工作時間"

    def work_days_display(self, obj):
        """顯示工作日"""
        return obj.get_work_days_display()

    work_days_display.short_description = "工作日"

    def get_queryset(self, request):
        """根據使用者權限過濾資料"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # 一般使用者只能看到啟用的產線
        return qs.filter(is_active=True)


@admin.register(ProductionLineSchedule)
class ProductionLineScheduleAdmin(admin.ModelAdmin):
    """
    產線排程記錄管理介面
    """

    list_display = [
        "production_line",
        "schedule_date",
        "work_time_display",
        "is_holiday",
        "created_by",
        "created_at",
    ]
    list_filter = [
        "production_line__line_type",
        "is_holiday",
        "schedule_date",
        "created_at",
    ]
    search_fields = [
        "production_line__line_code",
        "production_line__line_name",
        "created_by",
    ]
    ordering = ["-schedule_date", "production_line"]

    fieldsets = (
        ("基本資訊", {"fields": ("production_line", "schedule_date")}),
        (
            "工作時間設定",
            {
                "fields": (
                    "work_start_time",
                    "work_end_time",
                    "lunch_start_time",
                    "lunch_end_time",
                    "overtime_start_time",
                    "overtime_end_time",
                    "work_days",
                )
            },
        ),
        ("假日設定", {"fields": ("is_holiday", "holiday_reason")}),
        (
            "系統資訊",
            {"fields": ("created_by", "created_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at"]

    def work_time_display(self, obj):
        """顯示工作時間"""
        if obj.is_holiday:
            return format_html('<span style="color: red;">假日</span>')
        return format_html(
            "{} - {}<br>午休: {} - {}<br>加班: {} - {}",
            obj.work_start_time.strftime("%H:%M"),
            obj.work_end_time.strftime("%H:%M"),
            obj.lunch_start_time.strftime("%H:%M"),
            obj.lunch_end_time.strftime("%H:%M"),
            obj.overtime_start_time.strftime("%H:%M"),
            obj.overtime_end_time.strftime("%H:%M"),
        )

    work_time_display.short_description = "工作時間"

    def save_model(self, request, obj, form, change):
        """儲存時自動設定建立人員"""
        if not change:  # 新增時
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)
