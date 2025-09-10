from django.contrib import admin
from .models import ProductProcessStandardCapacity, CapacityHistory, CapacityTemplate


@admin.register(ProductProcessStandardCapacity)
class ProductProcessStandardCapacityAdmin(admin.ModelAdmin):
    list_display = (
        "product_code",
        "process_name",
        "equipment_type",
        "operator_level",
        "standard_capacity_per_hour",
        "version",
        "is_active",
        "effective_date",
    )
    list_filter = (
        "process_name",
        "equipment_type",
        "operator_level",
        "is_active",
        "effective_date",
    )
    search_fields = ("product_code", "process_name", "notes")
    ordering = (
        "product_code",
        "process_name",
        "equipment_type",
        "operator_level",
        "-version",
    )

    fieldsets = (
        (
            "基本資訊",
            {
                "fields": (
                    "product_code",
                    "process_name",
                    "equipment_type",
                    "operator_level",
                )
            },
        ),
        (
            "產能參數",
            {
                "fields": (
                    "standard_capacity_per_hour",
                    "min_capacity_per_hour",
                    "max_capacity_per_hour",
                )
            },
        ),
        (
            "時間因素",
            {
                "fields": (
                    "setup_time_minutes",
                    "teardown_time_minutes",
                    "cycle_time_seconds",
                )
            },
        ),
        (
            "批量設定",
            {"fields": ("optimal_batch_size", "min_batch_size", "max_batch_size")},
        ),
        ("效率因子", {"fields": ("efficiency_factor", "learning_curve_factor")}),
        ("品質因素", {"fields": ("expected_defect_rate", "rework_time_factor")}),
        (
            "版本控制",
            {"fields": ("version", "effective_date", "expiry_date", "is_active")},
        ),
        ("審核資訊", {"fields": ("created_by", "approved_by", "approval_date")}),
        ("備註", {"fields": ("notes",)}),
    )

    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:  # 新增時
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)


@admin.register(CapacityHistory)
class CapacityHistoryAdmin(admin.ModelAdmin):
    list_display = ("capacity_name", "capacity_id", "change_type", "changed_by", "changed_at")
    list_filter = ("change_type", "changed_at")
    search_fields = ("capacity_name", "capacity_id", "changed_by")
    readonly_fields = (
        "capacity_id",
        "capacity_name",
        "change_type",
        "old_values",
        "new_values",
        "change_reason",
        "changed_by",
        "changed_at",
    )
    ordering = ("-changed_at",)


@admin.register(CapacityTemplate)
class CapacityTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "template_name",
        "process_name",
        "equipment_type",
        "operator_level",
        "standard_capacity_per_hour",
        "is_active",
    )
    list_filter = ("process_name", "equipment_type", "operator_level", "is_active")
    search_fields = ("template_name", "process_name", "description")
    ordering = ("template_name", "process_name", "equipment_type", "operator_level")

    fieldsets = (
        (
            "基本資訊",
            {
                "fields": (
                    "template_name",
                    "process_name",
                    "equipment_type",
                    "operator_level",
                )
            },
        ),
        (
            "標準參數",
            {
                "fields": (
                    "standard_capacity_per_hour",
                    "setup_time_minutes",
                    "cycle_time_seconds",
                    "efficiency_factor",
                )
            },
        ),
        ("適用範圍", {"fields": ("applicable_products", "description")}),
        ("狀態", {"fields": ("is_active",)}),
    )

    readonly_fields = ("created_at",)
    # 繁體中文說明：這個管理介面讓你可以查詢、編輯每個產品工序的標準產能
