from django.contrib import admin
from django.utils.html import format_html
from .models import Equipment, EquipOperationLog


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """
    設備管理介面
    """

    list_display = ["name", "model", "status", "production_line", "created_at"]
    list_filter = ["status", "production_line", "created_at"]
    search_fields = ["name", "model"]
    ordering = ["name"]

    fieldsets = (
        ("基本資訊", {"fields": ("name", "model")}),
        ("狀態設定", {"fields": ("status", "production_line")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("production_line")


@admin.register(EquipOperationLog)
class EquipOperationLogAdmin(admin.ModelAdmin):
    """
    設備操作日誌管理介面
    """

    list_display = ["timestamp", "user", "action"]
    list_filter = ["timestamp", "user"]
    search_fields = ["user", "action"]
    ordering = ["-timestamp"]
    readonly_fields = ["timestamp"]

    def has_add_permission(self, request):
        return False  # 不允許手動添加日誌
