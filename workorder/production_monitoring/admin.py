"""
生產中監控子模組 - 管理介面
"""

from django.contrib import admin
from .models import ProductionMonitoringData


@admin.register(ProductionMonitoringData)
class ProductionMonitoringDataAdmin(admin.ModelAdmin):
    """
    生產中工單監控資料管理介面
    """
    list_display = [
        'workorder', 'total_quantity', 'packaging_total_quantity', 
        'completion_rate', 'can_complete', 'last_updated'
    ]
    list_filter = [
        'can_complete', 'completion_threshold_met', 'last_updated'
    ]
    search_fields = [
        'workorder__order_number', 'workorder__product_code'
    ]
    readonly_fields = [
        'created_at', 'last_updated', 'last_fillwork_update', 
        'last_onsite_update', 'last_process_update'
    ]
    
    fieldsets = (
        ('工單資訊', {
            'fields': ('workorder',)
        }),
        ('數量統計', {
            'fields': (
                'total_good_quantity', 'total_defect_quantity', 'total_quantity',
                'packaging_good_quantity', 'packaging_defect_quantity', 'packaging_total_quantity'
            )
        }),
        ('時數統計', {
            'fields': ('total_work_hours', 'total_overtime_hours', 'total_all_hours')
        }),
        ('記錄統計', {
            'fields': (
                'fillwork_report_count', 'fillwork_approved_count', 'fillwork_pending_count',
                'onsite_report_count', 'onsite_completed_count'
            )
        }),
        ('工序統計', {
            'fields': (
                'total_processes', 'completed_processes', 'in_progress_processes', 'pending_processes'
            )
        }),
        ('人員設備', {
            'fields': (
                'unique_operators', 'unique_equipment', 'operator_count', 'equipment_count'
            )
        }),
        ('完成率', {
            'fields': ('completion_rate', 'packaging_completion_rate')
        }),
        ('完工判斷', {
            'fields': ('can_complete', 'completion_threshold_met')
        }),
        ('時間戳記', {
            'fields': (
                'created_at', 'last_updated', 'last_fillwork_update', 
                'last_onsite_update', 'last_process_update'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """禁止手動新增，只能透過系統自動建立"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """禁止刪除，避免資料遺失"""
        return False
    
    actions = ['update_statistics']
    
    def update_statistics(self, request, queryset):
        """更新選中工單的統計資料"""
        updated_count = 0
        for monitoring_data in queryset:
            try:
                monitoring_data.update_all_statistics()
                updated_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f'更新工單 {monitoring_data.workorder.order_number} 失敗: {str(e)}', 
                    level='ERROR'
                )
        
        self.message_user(
            request, 
            f'成功更新 {updated_count} 個工單的統計資料'
        )
    
    update_statistics.short_description = "更新統計資料" 