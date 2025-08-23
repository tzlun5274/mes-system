from django.contrib import admin
from .models import (
    Material,
    Product,
    Route,
    Process,
    MaterialRequirement,
    MaterialShortageAlert,
    MaterialSupplyPlan,
    MaterialKanban,
    MaterialInventoryManagement,
    MaterialRequirementEstimation,
    MaterialTransaction,
)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """
    材料管理：管理材料基本資料
    """

    list_display = ["name", "code", "category", "unit", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["name", "code", "category"]
    ordering = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    產品管理：管理產品基本資料
    """

    list_display = ["name", "code", "category", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["name", "code", "category"]
    ordering = ["name"]


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    """
    工序管理：管理生產工序
    """

    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """
    工藝路線管理：管理產品生產工藝路線
    """

    list_display = ["name", "product", "step_order", "process", "created_at"]
    list_filter = ["product", "process", "created_at"]
    search_fields = ["name", "product__name", "process__name"]
    ordering = ["product", "step_order"]


@admin.register(MaterialRequirement)
class MaterialRequirementAdmin(admin.ModelAdmin):
    """
    物料需求管理：管理產品材料需求（BOM）
    """

    list_display = ["product", "material", "quantity_per_unit", "created_at"]
    list_filter = ["product", "material", "created_at"]
    search_fields = ["product__name", "material__name"]
    ordering = ["product", "material"]


@admin.register(MaterialShortageAlert)
class MaterialShortageAlertAdmin(admin.ModelAdmin):
    """
    缺料警告管理：管理缺料警告
    """

    list_display = [
        "material",
        "work_order",
        "required_quantity",
        "available_quantity",
        "shortage_quantity",
        "alert_level",
        "is_resolved",
        "created_at",
    ]
    list_filter = ["alert_level", "is_resolved", "created_at"]
    search_fields = ["material__name", "work_order"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "resolved_at"]


@admin.register(MaterialSupplyPlan)
class MaterialSupplyPlanAdmin(admin.ModelAdmin):
    """
    物料供應計劃管理：管理根據生產排程的物料供應
    """

    list_display = [
        "work_order",
        "material",
        "planned_quantity",
        "supply_time",
        "supply_location",
        "status",
        "created_at",
    ]
    list_filter = ["status", "supply_time", "created_at"]
    search_fields = ["work_order", "material__name", "supply_location"]
    ordering = ["supply_time"]
    readonly_fields = ["created_at"]


@admin.register(MaterialKanban)
class MaterialKanbanAdmin(admin.ModelAdmin):
    """
    物料看板管理：管理 JIT 供料的看板
    """

    list_display = [
        "kanban_number",
        "material",
        "kanban_type",
        "quantity_per_kanban",
        "current_quantity",
        "status",
        "location",
        "last_updated",
    ]
    list_filter = ["kanban_type", "status", "last_updated"]
    search_fields = ["kanban_number", "material__name", "location"]
    ordering = ["kanban_number"]
    readonly_fields = ["last_updated"]


@admin.register(MaterialInventoryManagement)
class MaterialInventoryManagementAdmin(admin.ModelAdmin):
    """
    庫存管理管理介面
    """

    list_display = [
        "material",
        "warehouse",
        "current_stock",
        "safety_stock",
        "stock_status",
        "last_updated",
    ]
    list_filter = ["stock_status", "warehouse", "material__category"]
    search_fields = ["material__name", "material__code", "warehouse"]
    readonly_fields = ["last_updated"]

    fieldsets = (
        ("基本資訊", {"fields": ("material", "warehouse")}),
        (
            "庫存設定",
            {
                "fields": (
                    "current_stock",
                    "safety_stock",
                    "max_stock",
                    "reorder_point",
                    "reorder_quantity",
                )
            },
        ),
        ("成本資訊", {"fields": ("unit_cost",)}),
        ("狀態資訊", {"fields": ("stock_status", "last_updated")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("material")


@admin.register(MaterialRequirementEstimation)
class MaterialRequirementEstimationAdmin(admin.ModelAdmin):
    """
    物料需求估算管理介面
    """

    list_display = [
        "material",
        "estimation_date",
        "period_start",
        "period_end",
        "estimated_demand",
        "status",
        "estimation_method",
    ]
    list_filter = ["status", "estimation_method", "estimation_date"]
    search_fields = ["material__name", "material__code"]
    readonly_fields = ["created_at", "updated_at", "forecast_accuracy"]

    fieldsets = (
        (
            "基本資訊",
            {"fields": ("material", "estimation_date", "period_start", "period_end")},
        ),
        (
            "需求估算",
            {"fields": ("estimated_demand", "actual_demand", "forecast_accuracy")},
        ),
        ("供應計劃", {"fields": ("planned_supply", "actual_supply")}),
        ("庫存預測", {"fields": ("beginning_stock", "ending_stock")}),
        ("估算設定", {"fields": ("estimation_method", "status", "notes")}),
        (
            "時間戳記",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("material")


@admin.register(MaterialTransaction)
class MaterialTransactionAdmin(admin.ModelAdmin):
    """
    物料交易記錄管理介面
    """

    list_display = [
        "material",
        "transaction_type",
        "quantity",
        "unit_cost",
        "total_cost",
        "reference_no",
        "created_at",
    ]
    list_filter = ["transaction_type", "reference_type", "created_at"]
    search_fields = ["material__name", "material__code", "reference_no", "batch_no"]
    readonly_fields = ["created_at", "total_cost"]

    fieldsets = (
        (
            "交易資訊",
            {
                "fields": (
                    "material",
                    "transaction_type",
                    "quantity",
                    "unit_cost",
                    "total_cost",
                )
            },
        ),
        ("位置資訊", {"fields": ("from_location", "to_location")}),
        ("參考資訊", {"fields": ("reference_no", "reference_type")}),
        ("批次資訊", {"fields": ("batch_no", "expiry_date")}),
        ("其他資訊", {"fields": ("notes", "created_at", "created_by")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("material")
