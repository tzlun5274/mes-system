"""
派工單管理子模組 - 模型定義
負責派工單的管理功能，包括派工單主表、工序明細等
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum


class WorkOrderDispatch(models.Model):
    """
    派工單主表：專門用於派工管理
    記錄工單的派工資訊，不包含報工記錄
    """
    STATUS_CHOICES = [
        ("pending", "待派工"),
        ("dispatched", "已派工"),
        ("in_production", "生產中"),
        ("completed", "已完工"),
        ("cancelled", "已取消"),
    ]

    # 基本資訊
    company_code = models.CharField(max_length=20, verbose_name="公司代號", null=True, blank=True)
    company_name = models.CharField(max_length=100, verbose_name="公司名稱", null=True, blank=True)
    order_number = models.CharField(max_length=100, verbose_name="工單號碼", db_index=True)
    product_code = models.CharField(max_length=100, verbose_name="產品編號", db_index=True)
    product_name = models.CharField(max_length=200, verbose_name="產品名稱", null=True, blank=True)
    planned_quantity = models.PositiveIntegerField(verbose_name="計劃數量", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_production", verbose_name="派工狀態")
    
    # 派工相關資訊
    dispatch_date = models.DateField(verbose_name="派工日期", null=True, blank=True)
    planned_start_date = models.DateField(verbose_name="計劃開始日期", null=True, blank=True)
    planned_end_date = models.DateField(verbose_name="計劃完成日期", null=True, blank=True)
    
    # 作業員和設備資訊
    assigned_operator = models.CharField(max_length=100, verbose_name="分配作業員", null=True, blank=True)
    assigned_equipment = models.CharField(max_length=100, verbose_name="分配設備", null=True, blank=True)
    process_name = models.CharField(max_length=100, verbose_name="工序名稱", null=True, blank=True)
    
    # 生產監控資料（合併自ProductionMonitoringData）
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
    
    # 備註
    notes = models.TextField(verbose_name="備註", blank=True)
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立人員", default="system")

    class Meta:
        verbose_name = "派工單"
        verbose_name_plural = "派工單管理"
        db_table = "workorder_dispatch"
        ordering = ["-created_at"]
        unique_together = (("company_code", "order_number", "product_code"),)  # 公司代號+工單號碼+產品編號唯一
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['product_code']),
            models.Index(fields=['status']),
            models.Index(fields=['dispatch_date']),
        ]

    def __str__(self):
        return f"派工單 {self.order_number} - {self.product_code}"

    def clean(self):
        """資料驗證"""
        if self.planned_start_date and self.planned_end_date:
            if self.planned_start_date > self.planned_end_date:
                raise ValidationError(_('計劃開始日期不能晚於計劃完成日期'))

    def save(self, *args, **kwargs):
        """儲存前處理"""
        self.clean()
        super().save(*args, **kwargs)
    
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
            
            # 7. 同步工單狀態
            self._sync_workorder_status()
            
            self.save()
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger('workorder')
            error_details = traceback.format_exc()
            logger.error(f"更新派工單 {self.order_number} 統計資料失敗: {str(e)}\n詳細錯誤:\n{error_details}")
            # 即使有錯誤，也要嘗試儲存已更新的資料
            try:
                self.save()
            except:
                pass
    
    def _update_fillwork_statistics(self):
        """更新填報記錄統計"""
        from workorder.fill_work.models import FillWork
        
        # 基本查詢條件
        fillwork_reports = FillWork.objects.filter(
            workorder=self.order_number,
            product_id=self.product_code
        )
        
        # 按公司分離
        if self.company_code:
            fillwork_reports = fillwork_reports.filter(
                company_name=self._get_company_name()
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
        
        # 出貨包裝專項統計（填報記錄）
        packaging_reports = approved_reports.filter(process__name='出貨包裝')
        packaging_good_quantity = packaging_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        packaging_defect_quantity = packaging_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        # 加上現場報工出貨包裝數量
        onsite_packaging_quantity = self._get_onsite_packaging_quantity()
        
        # 總出貨包裝數量 = 填報記錄 + 現場報工
        self.packaging_good_quantity = packaging_good_quantity + onsite_packaging_quantity['good']
        self.packaging_defect_quantity = packaging_defect_quantity + onsite_packaging_quantity['defect']
        self.packaging_total_quantity = self.packaging_good_quantity + self.packaging_defect_quantity
        
        # 更新最後填報時間
        if approved_reports.exists():
            self.last_fillwork_update = approved_reports.latest('updated_at').updated_at
    
    def _update_onsite_statistics(self):
        """更新現場報工統計"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_reports = OnsiteReport.objects.filter(
                order_number=self.order_number,
                product_code=self.product_code
            )
            
            # 按公司分離
            if self.company_code:
                onsite_reports = onsite_reports.filter(
                    company_code=self.company_code
                )
            
            self.onsite_report_count = onsite_reports.count()
            self.onsite_completed_count = onsite_reports.filter(status='completed').count()
            
            # 更新最後現場報工時間
            if onsite_reports.exists():
                self.last_onsite_update = onsite_reports.latest('updated_at').updated_at
                
        except ImportError:
            # 如果現場報工模組不存在，跳過更新
            pass
    
    def _update_process_statistics(self):
        """更新工序進度統計"""
        try:
            # 從產品工序路線獲取總工序數
            from process.models import ProductProcessRoute
            total_processes = ProductProcessRoute.objects.filter(
                product_id=self.product_code
            ).count()
            
            # 從填報記錄獲取已完成的工序
            from workorder.fill_work.models import FillWork
            from erp_integration.models import CompanyConfig
            
            # 獲取公司名稱
            company_name = None
            if self.company_code:
                company_config = CompanyConfig.objects.filter(company_code=self.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            
            # 統計已完成的工序（有報工記錄的工序）
            if company_name:
                completed_processes = FillWork.objects.filter(
                    workorder=self.order_number,
                    product_id=self.product_code,
                    company_name=company_name,
                    approval_status='approved'
                ).values('operation').distinct().count()
            else:
                completed_processes = 0
            
            # 統計進行中的工序（有報工記錄但未完成的工序）
            # 這裡簡化處理，假設有報工記錄的工序就是進行中
            in_progress_processes = completed_processes
            
            # 待處理工序 = 總工序數 - 已完成工序
            pending_processes = max(0, total_processes - completed_processes)
            
            # 更新派工單的工序統計
            self.total_processes = total_processes
            self.completed_processes = completed_processes
            self.in_progress_processes = in_progress_processes
            self.pending_processes = pending_processes
            
        except Exception as e:
            # 如果發生錯誤，設定預設值
            self.total_processes = 0
            self.completed_processes = 0
            self.in_progress_processes = 0
            self.pending_processes = 0
    
    def _update_operator_equipment_statistics(self):
        """更新人員和設備統計"""
        # 這裡可以根據實際需求實現人員和設備統計邏輯
        pass
    
    def _update_completion_rates(self):
        """更新完成率計算"""
        if self.planned_quantity and self.planned_quantity > 0:
            self.completion_rate = (self.total_quantity / self.planned_quantity) * 100
        else:
            self.completion_rate = 0
        
        if self.planned_quantity and self.planned_quantity > 0:
            self.packaging_completion_rate = (self.packaging_total_quantity / self.planned_quantity) * 100
        else:
            self.packaging_completion_rate = 0
    
    def _update_completion_status(self):
        """更新完工判斷"""
        # 簡化完工判斷邏輯：只要出貨包裝數量 >= 計劃數量就完工
        # 不依賴複雜的統計資料，直接比較數量
        if (self.packaging_total_quantity >= self.planned_quantity and 
            self.planned_quantity > 0):
            self.completion_threshold_met = True
            self.can_complete = True
            # 記錄完工判斷日誌
            import logging
            logger = logging.getLogger('workorder')
            logger.info(f"派工單 {self.order_number} 達到完工條件：出貨包裝數量={self.packaging_total_quantity}, 計劃數量={self.planned_quantity}")
        else:
            self.completion_threshold_met = False
            self.can_complete = False
            # 記錄未完工原因
            import logging
            logger = logging.getLogger('workorder')
            logger.debug(f"派工單 {self.order_number} 未達到完工條件：出貨包裝數量={self.packaging_total_quantity}, 計劃數量={self.planned_quantity}")
    
    def _get_company_name(self):
        """取得公司名稱"""
        from erp_integration.models import CompanyConfig
        company_config = CompanyConfig.objects.filter(company_code=self.company_code).first()
        return company_config.company_name if company_config else None

    def _get_onsite_packaging_quantity(self):
        """獲取現場報工出貨包裝數量"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_packaging_reports = OnsiteReport.objects.filter(
                workorder=self.order_number,
                product_id=self.product_code,
                operation='出貨包裝',
                status='completed'
            )
            
            # 按公司分離
            if self.company_code:
                onsite_packaging_reports = onsite_packaging_reports.filter(
                    company_code=self.company_code
                )
            
            # 統計良品和不良品數量
            good_quantity = onsite_packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            defect_quantity = onsite_packaging_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            return {
                'good': good_quantity,
                'defect': defect_quantity,
                'total': good_quantity + defect_quantity
            }
            
        except ImportError:
            # 如果現場報工模組不存在，返回0
            return {'good': 0, 'defect': 0, 'total': 0}
    
    def _sync_workorder_status(self):
        """同步工單狀態"""
        try:
            from workorder.models import WorkOrder
            import logging
            logger = logging.getLogger('workorder')
            
            # 查找對應的工單
            workorder = WorkOrder.objects.filter(
                order_number=self.order_number,
                product_code=self.product_code,
                company_code=self.company_code
            ).first()
            
            if workorder:
                # 根據派工單狀態和完工判斷來更新工單狀態
                if self.can_complete:
                    # 如果達到完工條件，標記為已完成
                    if workorder.status != 'completed':
                        workorder.status = 'completed'
                        # 只有在完工時間未設定時才設定為當前時間
                        if workorder.completed_at is None:
                            workorder.completed_at = timezone.now()
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為已完成")
                elif self.total_quantity > 0:
                    # 如果有生產數量，標記為生產中
                    if workorder.status == 'pending':
                        workorder.status = 'in_progress'
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為生產中")
                else:
                    # 如果沒有生產數量，保持待生產狀態
                    if workorder.status != 'pending':
                        workorder.status = 'pending'
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為待生產")
                        
        except Exception as e:
            import logging
            logger = logging.getLogger('workorder')
            logger.error(f"同步工單狀態失敗: {str(e)}")


class WorkOrderDispatchProcess(models.Model):
    """
    派工單工序明細：記錄每個派工單的工序分配
    """
    workorder_dispatch = models.ForeignKey(
        WorkOrderDispatch,
        on_delete=models.CASCADE,
        verbose_name="派工單",
        related_name="dispatch_processes"
    )
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    step_order = models.IntegerField(verbose_name="工序順序")
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    
    # 派工分配資訊
    assigned_operator = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配作業員")
    assigned_equipment = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配設備")
    dispatch_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "待派工"),
            ("dispatched", "已派工"),
            ("in_progress", "進行中"),
            ("completed", "已完成"),
        ],
        default="pending",
        verbose_name="派工狀態"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "派工單工序"
        verbose_name_plural = "派工單工序明細"
        db_table = "workorder_dispatch_process"
        unique_together = (("workorder_dispatch", "step_order"),)
        ordering = ["workorder_dispatch", "step_order"]

    def __str__(self):
        return f"{self.workorder_dispatch.order_number} - {self.process_name}"


class DispatchHistory(models.Model):
    """
    派工歷史記錄：記錄每次派工操作的歷史
    """
    workorder_dispatch = models.ForeignKey(
        WorkOrderDispatch,
        on_delete=models.CASCADE,
        verbose_name="派工單",
        related_name="dispatch_history"
    )
    action = models.CharField(max_length=50, verbose_name="操作類型")
    old_status = models.CharField(max_length=20, verbose_name="原狀態", null=True, blank=True)
    new_status = models.CharField(max_length=20, verbose_name="新狀態", null=True, blank=True)
    operator = models.CharField(max_length=100, verbose_name="操作人員")
    notes = models.TextField(verbose_name="備註", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作時間")

    class Meta:
        verbose_name = "派工歷史"
        verbose_name_plural = "派工歷史記錄"
        db_table = "workorder_dispatch_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workorder_dispatch.order_number} - {self.action} - {self.created_at}" 