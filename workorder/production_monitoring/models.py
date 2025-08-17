"""
生產中監控子模組 - 資料模型
專門用於生產中工單監控的資料表
"""

from django.db import models
from django.db.models import Sum
from django.utils import timezone
from ..models import WorkOrder


class ProductionMonitoringData(models.Model):
    """
    生產中工單監控資料表
    專門用於記錄和統計各工單的生產監控資訊
    整合填報記錄、現場報工、工序進度等所有相關資料
    """
    # 工單關聯資訊
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="production_monitoring_data"
    )
    
    # 基本統計資料
    total_work_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總工作時數")
    total_overtime_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總加班時數")
    total_all_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總時數")
    
    # 數量統計資料
    total_good_quantity = models.IntegerField(default=0, verbose_name="總良品數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量")
    total_quantity = models.IntegerField(default=0, verbose_name="總數量")
    
    # 出貨包裝專項統計
    packaging_good_quantity = models.IntegerField(default=0, verbose_name="出貨包裝良品數量")
    packaging_defect_quantity = models.IntegerField(default=0, verbose_name="出貨包裝不良品數量")
    packaging_total_quantity = models.IntegerField(default=0, verbose_name="出貨包裝總數量")
    
    # 填報記錄統計
    fillwork_report_count = models.IntegerField(default=0, verbose_name="填報記錄數量")
    fillwork_approved_count = models.IntegerField(default=0, verbose_name="已核准填報數量")
    fillwork_pending_count = models.IntegerField(default=0, verbose_name="待審核填報數量")
    
    # 現場報工統計
    onsite_report_count = models.IntegerField(default=0, verbose_name="現場報工記錄數量")
    onsite_completed_count = models.IntegerField(default=0, verbose_name="已完成現場報工數量")
    
    # 工序進度統計
    total_processes = models.IntegerField(default=0, verbose_name="總工序數")
    completed_processes = models.IntegerField(default=0, verbose_name="已完成工序數")
    in_progress_processes = models.IntegerField(default=0, verbose_name="進行中工序數")
    pending_processes = models.IntegerField(default=0, verbose_name="待開始工序數")
    
    # 人員和設備統計
    unique_operators = models.JSONField(default=list, verbose_name="參與作業員清單")
    unique_equipment = models.JSONField(default=list, verbose_name="使用設備清單")
    operator_count = models.IntegerField(default=0, verbose_name="參與作業員數量")
    equipment_count = models.IntegerField(default=0, verbose_name="使用設備數量")
    
    # 完成率計算
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="完成率(%)")
    packaging_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="出貨包裝完成率(%)")
    
    # 完工判斷
    can_complete = models.BooleanField(default=False, verbose_name="可完工")
    completion_threshold_met = models.BooleanField(default=False, verbose_name="達到完工閾值")
    
    # 最後更新資訊
    last_fillwork_update = models.DateTimeField(null=True, blank=True, verbose_name="最後填報更新時間")
    last_onsite_update = models.DateTimeField(null=True, blank=True, verbose_name="最後現場報工更新時間")
    last_process_update = models.DateTimeField(null=True, blank=True, verbose_name="最後工序更新時間")
    
    # 時間戳記
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "生產中工單監控資料"
        verbose_name_plural = "生產中工單監控資料"
        db_table = 'workorder_production_monitoring_data'
        unique_together = ['workorder']
        indexes = [
            models.Index(fields=['workorder', 'can_complete']),
            models.Index(fields=['completion_threshold_met']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"工單 {self.workorder.order_number} 監控資料"
    
    def update_all_statistics(self):
        """更新所有統計資料"""
        try:
            # 1. 更新填報記錄統計
            self._update_fillwork_statistics()
            
            # 2. 更新現場報工統計
            self._update_onsite_statistics()
            
            # 3. 更新工序進度統計
            self._update_process_statistics()
            
            # 4. 更新人員和設備統計
            self._update_operator_equipment_statistics()
            
            # 5. 更新完成率計算
            self._update_completion_rates()
            
            # 6. 更新完工判斷
            self._update_completion_status()
            
            self.save()
            
        except Exception as e:
            import logging
            logger = logging.getLogger('workorder')
            logger.error(f"更新工單 {self.workorder.order_number} 監控資料失敗: {str(e)}")
    
    def _update_fillwork_statistics(self):
        """更新填報記錄統計"""
        from workorder.fill_work.models import FillWork
        from erp_integration.models import CompanyConfig
        
        # 基本查詢條件
        fillwork_reports = FillWork.objects.filter(
            workorder=self.workorder.order_number,
            product_id=self.workorder.product_code
        )
        
        # 按公司分離
        if self.workorder.company_code:
            company_config = CompanyConfig.objects.filter(
                company_code=self.workorder.company_code
            ).first()
            if company_config:
                fillwork_reports = fillwork_reports.filter(
                    company_name=company_config.company_name
                )
        
        # 統計數量
        self.fillwork_report_count = fillwork_reports.count()
        self.fillwork_approved_count = fillwork_reports.filter(approval_status='approved').count()
        self.fillwork_pending_count = fillwork_reports.filter(approval_status='pending').count()
        
        # 統計時數
        approved_reports = fillwork_reports.filter(approval_status='approved')
        self.total_work_hours = approved_reports.aggregate(
            total=Sum('work_hours_calculated')
        )['total'] or 0
        
        self.total_overtime_hours = approved_reports.aggregate(
            total=Sum('overtime_hours_calculated')
        )['total'] or 0
        
        self.total_all_hours = self.total_work_hours + self.total_overtime_hours
        
        # 統計數量
        self.total_good_quantity = approved_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        self.total_defect_quantity = approved_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        self.total_quantity = self.total_good_quantity + self.total_defect_quantity
        
        # 出貨包裝專項統計
        packaging_reports = approved_reports.filter(process__name__exact='出貨包裝')
        self.packaging_good_quantity = packaging_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        self.packaging_defect_quantity = packaging_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        self.packaging_total_quantity = self.packaging_good_quantity + self.packaging_defect_quantity
        
        # 更新最後填報時間
        if approved_reports.exists():
            self.last_fillwork_update = approved_reports.latest('updated_at').updated_at
    
    def _update_onsite_statistics(self):
        """更新現場報工統計"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_reports = OnsiteReport.objects.filter(
                order_number=self.workorder.order_number,
                product_code=self.workorder.product_code
            )
            
            # 按公司分離
            if self.workorder.company_code:
                onsite_reports = onsite_reports.filter(
                    company_code=self.workorder.company_code
                )
            
            self.onsite_report_count = onsite_reports.count()
            self.onsite_completed_count = onsite_reports.filter(status='completed').count()
            
            # 現場報工數量統計
            completed_reports = onsite_reports.filter(status='completed')
            onsite_good_quantity = completed_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            onsite_defect_quantity = completed_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 出貨包裝現場報工統計
            packaging_onsite_reports = completed_reports.filter(process="出貨包裝")
            onsite_packaging_good = packaging_onsite_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            onsite_packaging_defect = packaging_onsite_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 合併到總統計
            self.total_good_quantity += onsite_good_quantity
            self.total_defect_quantity += onsite_defect_quantity
            self.total_quantity = self.total_good_quantity + self.total_defect_quantity
            
            self.packaging_good_quantity += onsite_packaging_good
            self.packaging_defect_quantity += onsite_packaging_defect
            self.packaging_total_quantity = self.packaging_good_quantity + self.packaging_defect_quantity
            
            # 更新最後現場報工時間
            if completed_reports.exists():
                self.last_onsite_update = completed_reports.latest('updated_at').updated_at
                
        except Exception as e:
            # 如果現場報工模組不存在，設為0
            self.onsite_report_count = 0
            self.onsite_completed_count = 0
    
    def _update_process_statistics(self):
        """更新工序進度統計"""
        processes = self.workorder.processes.all()
        self.total_processes = processes.count()
        self.completed_processes = processes.filter(status='completed').count()
        self.in_progress_processes = processes.filter(status='in_progress').count()
        self.pending_processes = processes.filter(status='pending').count()
        
        # 更新最後工序時間
        if processes.exists():
            self.last_process_update = processes.latest('updated_at').updated_at
    
    def _update_operator_equipment_statistics(self):
        """更新人員和設備統計"""
        from workorder.fill_work.models import FillWork
        from erp_integration.models import CompanyConfig
        
        # 獲取填報記錄的人員和設備
        fillwork_reports = FillWork.objects.filter(
            workorder=self.workorder.order_number,
            product_id=self.workorder.product_code,
            approval_status='approved'
        )
        
        # 按公司分離
        if self.workorder.company_code:
            company_config = CompanyConfig.objects.filter(
                company_code=self.workorder.company_code
            ).first()
            if company_config:
                fillwork_reports = fillwork_reports.filter(
                    company_name=company_config.company_name
                )
        
        # 統計人員和設備
        operators = list(set(report.operator for report in fillwork_reports if report.operator))
        equipment = list(set(report.equipment for report in fillwork_reports if report.equipment))
        
        # 加入現場報工的人員和設備
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            onsite_reports = OnsiteReport.objects.filter(
                order_number=self.workorder.order_number,
                product_code=self.workorder.product_code,
                status='completed'
            )
            
            if self.workorder.company_code:
                onsite_reports = onsite_reports.filter(
                    company_code=self.workorder.company_code
                )
            
            onsite_operators = list(set(report.operator for report in onsite_reports if report.operator))
            onsite_equipment = list(set(report.equipment for report in onsite_reports if report.equipment))
            
            operators.extend(onsite_operators)
            equipment.extend(onsite_equipment)
            
        except Exception:
            pass
        
        # 去重並排序
        self.unique_operators = sorted(list(set(operators)))
        self.unique_equipment = sorted(list(set(equipment)))
        self.operator_count = len(self.unique_operators)
        self.equipment_count = len(self.unique_equipment)
    
    def _update_completion_rates(self):
        """更新完成率計算"""
        # 總完成率
        if self.workorder.quantity > 0:
            self.completion_rate = (self.total_quantity / self.workorder.quantity) * 100
        else:
            self.completion_rate = 0
        
        # 出貨包裝完成率
        if self.workorder.quantity > 0:
            self.packaging_completion_rate = (self.packaging_total_quantity / self.workorder.quantity) * 100
        else:
            self.packaging_completion_rate = 0
    
    def _update_completion_status(self):
        """更新完工判斷"""
        # 出貨包裝數量達到工單目標數量即可完工
        self.can_complete = self.packaging_total_quantity >= self.workorder.quantity
        self.completion_threshold_met = self.can_complete
    
    @classmethod
    def get_or_create_for_workorder(cls, workorder):
        """為工單取得或建立監控資料"""
        monitoring_data, created = cls.objects.get_or_create(
            workorder=workorder,
            defaults={}
        )
        
        if created:
            monitoring_data.update_all_statistics()
        
        return monitoring_data
    
    @classmethod
    def update_all_workorders(cls):
        """更新所有工單的監控資料"""
        from workorder.models import WorkOrder
        
        workorders = WorkOrder.objects.filter(status__in=['pending', 'in_progress'])
        
        for workorder in workorders:
            try:
                monitoring_data = cls.get_or_create_for_workorder(workorder)
                monitoring_data.update_all_statistics()
            except Exception as e:
                import logging
                logger = logging.getLogger('workorder')
                logger.error(f"更新工單 {workorder.order_number} 監控資料失敗: {str(e)}") 