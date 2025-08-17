"""
現場報工子模組 - 資料模型
負責現場報工的資料庫模型定義
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone


class OnsiteReport(models.Model):
    """
    現場報工記錄模型
    每筆記錄代表一次完整的工作時段（開始到結束）
    """
    
    # 報工類型選擇
    REPORT_TYPE_CHOICES = [
        ('operator', '作業員現場報工'),
        ('operator_rd', '作業員RD樣品現場報工'),
        ('smt', 'SMT現場報工'),
        ('smt_rd', 'SMT_RD樣品現場報工'),
    ]
    
    # 報工狀態選擇
    STATUS_CHOICES = [
        ('started', '開工'),
        ('paused', '暫停'),
        ('resumed', '重啟開工'),
        ('completed', '完工'),
        ('stopped', '停工'),
    ]
    
    # 基本資訊欄位
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="報工類型")
    operator = models.CharField(max_length=100, verbose_name="作業員")
    company_code = models.CharField(max_length=10, verbose_name="公司代號", null=True, blank=True)
    
    # 工單相關欄位 - 修正欄位名稱以與工單模型一致
    order_number = models.CharField(max_length=100, verbose_name="工單號碼")  # 修正：workorder -> order_number
    product_code = models.CharField(max_length=100, verbose_name="產品編號")  # 修正：product_id -> product_code
    planned_quantity = models.IntegerField(default=0, verbose_name="工單預設生產數量")
    
    # 製程相關欄位
    process = models.CharField(max_length=100, verbose_name="工序")
    operation = models.CharField(max_length=100, blank=True, verbose_name="工序名稱")
    equipment = models.CharField(max_length=100, blank=True, default='', verbose_name="使用的設備")
    
    # 時間相關欄位
    work_date = models.DateField(default=timezone.now, verbose_name="報工日期")
    start_datetime = models.DateTimeField(verbose_name="開始日期時間")
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name="結束日期時間")
    work_minutes = models.IntegerField(default=0, verbose_name="工作分鐘數")
    
    # 數量相關欄位
    work_quantity = models.IntegerField(default=0, verbose_name="工作數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 狀態欄位
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started', verbose_name="報工狀態")
    
    # 備註欄位
    remarks = models.TextField(blank=True, verbose_name="備註")
    abnormal_notes = models.TextField(blank=True, verbose_name="異常記錄")
    
    # 系統欄位
    created_by = models.CharField(max_length=100, verbose_name="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "現場報工記錄"
        verbose_name_plural = "現場報工記錄"
        db_table = 'workorder_onsite_report'
        ordering = ['-created_at']
        unique_together = (("company_code", "order_number", "product_code"),)  # 公司代號+工單號碼+產品編號唯一
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['operator']),
            models.Index(fields=['order_number']),
            models.Index(fields=['product_code']),
            models.Index(fields=['status']),
            models.Index(fields=['report_type']),
            models.Index(fields=['work_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.operator} - {self.order_number} - {self.get_status_display()}"
    
    def get_duration_minutes(self):
        """取得此筆記錄的工作時間（分鐘）"""
        if not self.start_datetime:
            return 0
        
        end_datetime = self.end_datetime or timezone.now()
        duration = end_datetime - self.start_datetime
        return int(duration.total_seconds() / 60)
    
    def complete_work(self, work_quantity=0, defect_quantity=0):
        """完成此筆工作記錄"""
        if self.status in ['started', 'resumed']:
            self.end_datetime = timezone.now()
            self.work_quantity = work_quantity
            self.defect_quantity = defect_quantity
            self.work_minutes = self.get_duration_minutes()
            self.status = 'completed'
            self.save()
            
            # 記錄歷史
            OnsiteReportHistory.objects.create(
                onsite_report=self,
                change_type='complete',
                old_status=self.status,
                new_status='completed',
                old_quantity=0,
                new_quantity=work_quantity,
                change_notes=f"完成工作 - 工作數量: {work_quantity}, 不良品: {defect_quantity}",
                changed_by=self.created_by
            )
    
    def pause_work(self):
        """暫停此筆工作記錄"""
        if self.status in ['started', 'resumed']:
            self.end_datetime = timezone.now()
            self.work_minutes = self.get_duration_minutes()
            self.status = 'paused'
            self.save()
            
            # 記錄歷史
            OnsiteReportHistory.objects.create(
                onsite_report=self,
                change_type='pause',
                old_status=self.status,
                new_status='paused',
                old_quantity=0,
                new_quantity=self.work_quantity,
                change_notes="暫停工作",
                changed_by=self.created_by
            )
    
    def resume_work(self):
        """恢復此筆工作記錄"""
        if self.status == 'paused':
            self.status = 'resumed'
            self.start_datetime = timezone.now()
            self.save()
            
            # 記錄歷史
            OnsiteReportHistory.objects.create(
                onsite_report=self,
                change_type='resume',
                old_status='paused',
                new_status='resumed',
                old_quantity=self.work_quantity,
                new_quantity=self.work_quantity,
                change_notes="恢復工作",
                changed_by=self.created_by
            )
    
    def stop_work(self):
        """停工此筆工作記錄"""
        if self.status in ['started', 'resumed']:
            self.end_datetime = timezone.now()
            self.work_minutes = self.get_duration_minutes()
            self.status = 'stopped'
            self.save()
            
            # 記錄歷史
            OnsiteReportHistory.objects.create(
                onsite_report=self,
                change_type='stop',
                old_status=self.status,
                new_status='stopped',
                old_quantity=0,
                new_quantity=self.work_quantity,
                change_notes="停工",
                changed_by=self.created_by
            )
    
    def get_progress_percentage(self):
        """取得進度百分比"""
        if self.planned_quantity <= 0:
            return 0
        return min(100, (self.work_quantity / self.planned_quantity) * 100)
    
    def is_completed(self):
        """檢查是否已完成"""
        return self.status == 'completed'


class OnsiteReportSession(models.Model):
    """
    現場報工工作時段管理模型
    用於管理整個工單的報工流程，包含多個工作時段
    """
    
    # 基本資訊欄位
    operator = models.CharField(max_length=100, verbose_name="作業員", help_text="作業員姓名")
    order_number = models.CharField(max_length=100, verbose_name="工單號碼", help_text="工單號碼")  # 修正：workorder -> order_number
    product_code = models.CharField(max_length=100, verbose_name="產品編號", help_text="產品編號")  # 修正：product_id -> product_code
    company_code = models.CharField(max_length=10, verbose_name="公司代號", null=True, blank=True, help_text="公司代號")
    
    # 製程相關欄位
    process = models.CharField(max_length=100, verbose_name="工序", help_text="工序")
    operation = models.CharField(max_length=100, blank=True, verbose_name="工序名稱", help_text="工序名稱")
    equipment = models.CharField(max_length=100, blank=True, default='', verbose_name="使用的設備", help_text="使用的設備")
    
    # 工單資訊
    planned_quantity = models.IntegerField(default=0, verbose_name="工單預設生產數量", help_text="工單預設生產數量")
    
    # 累積統計
    total_work_minutes = models.IntegerField(default=0, verbose_name="總工作分鐘數", help_text="總工作分鐘數")
    total_quantity_produced = models.IntegerField(default=0, verbose_name="總生產數量", help_text="總生產數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量", help_text="總不良品數量")
    session_count = models.IntegerField(default=0, verbose_name="工作時段數", help_text="工作時段數")
    
    # 狀態欄位
    is_active = models.BooleanField(default=True, verbose_name="是否活躍", help_text="是否活躍")
    
    # 系統欄位
    created_by = models.CharField(max_length=100, verbose_name="建立人員", help_text="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間", help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間", help_text="更新時間")
    
    class Meta:
        verbose_name = "現場報工工作時段"
        verbose_name_plural = "現場報工工作時段"
        db_table = 'workorder_onsite_report_session'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operator']),
            models.Index(fields=['order_number']),
            models.Index(fields=['product_code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.operator} - {self.order_number} - {self.session_count}時段"
    
    def get_progress_percentage(self):
        """取得進度百分比"""
        if self.planned_quantity <= 0:
            return 0
        return min(100, (self.total_quantity_produced / self.planned_quantity) * 100)
    
    def update_statistics(self):
        """更新統計資料"""
        reports = OnsiteReport.objects.filter(
            operator=self.operator,
            order_number=self.order_number,
            product_code=self.product_code,
            status='completed'
        )
        
        self.total_work_minutes = sum(report.work_minutes for report in reports)
        self.total_quantity_produced = sum(report.work_quantity for report in reports)
        self.total_defect_quantity = sum(report.defect_quantity for report in reports)
        self.session_count = reports.count()
        self.save()
    
    def is_completed(self):
        """檢查工單是否已完成"""
        return self.total_quantity_produced >= self.planned_quantity


class OnsiteReportHistory(models.Model):
    """
    現場報工歷史記錄模型
    用於記錄現場報工的歷史變更記錄
    """
    
    # 變更類型選擇
    CHANGE_TYPE_CHOICES = [
        ('start', '開始報工'),
        ('update', '更新數量'),
        ('pause', '暫停'),
        ('resume', '恢復'),
        ('complete', '完成'),
        ('abnormal', '異常'),
        ('normal', '恢復正常'),
    ]
    
    # 關聯欄位
    onsite_report = models.ForeignKey(OnsiteReport, on_delete=models.CASCADE, verbose_name="現場報工記錄", help_text="現場報工記錄")
    
    # 變更資訊欄位
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name="變更類型", help_text="變更類型")
    old_status = models.CharField(max_length=20, blank=True, verbose_name="原狀態", help_text="原狀態")
    new_status = models.CharField(max_length=20, blank=True, verbose_name="新狀態", help_text="新狀態")
    old_quantity = models.IntegerField(default=0, verbose_name="原數量", help_text="原數量")
    new_quantity = models.IntegerField(default=0, verbose_name="新數量", help_text="新數量")
    
    # 變更說明
    change_notes = models.TextField(blank=True, verbose_name="變更說明", help_text="變更說明")
    
    # 系統欄位
    changed_by = models.CharField(max_length=100, verbose_name="變更人員", help_text="變更人員")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="變更時間", help_text="變更時間")
    
    class Meta:
        verbose_name = "現場報工歷史記錄"
        verbose_name_plural = "現場報工歷史記錄"
        db_table = 'workorder_onsite_report_history'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['onsite_report']),
            models.Index(fields=['change_type']),
            models.Index(fields=['changed_at']),
        ]
    
    def __str__(self):
        return f"{self.onsite_report.operator} - {self.get_change_type_display()} - {self.changed_at}"


class OnsiteReportConfig(models.Model):
    """
    現場報工配置模型
    用於管理現場報工的系統配置
    """
    
    # 配置類型選擇
    CONFIG_TYPE_CHOICES = [
        ('operator', '作業員報工'),
        ('smt', 'SMT設備報工'),
        ('system', '系統配置'),
    ]
    
    # 基本資訊欄位
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPE_CHOICES, verbose_name="配置類型", help_text="配置類型")
    config_key = models.CharField(max_length=100, verbose_name="配置鍵", help_text="配置鍵")
    config_value = models.TextField(verbose_name="配置值", help_text="配置值")
    config_description = models.TextField(blank=True, verbose_name="配置說明", help_text="配置說明")
    
    # 系統欄位
    is_active = models.BooleanField(default=True, verbose_name="是否啟用", help_text="是否啟用")
    created_by = models.CharField(max_length=100, verbose_name="建立人員", help_text="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間", help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間", help_text="更新時間")
    
    class Meta:
        verbose_name = "現場報工配置"
        verbose_name_plural = "現場報工配置"
        db_table = 'workorder_onsite_report_config'
        unique_together = ['config_type', 'config_key']
        ordering = ['config_type', 'config_key']
        indexes = [
            models.Index(fields=['config_type']),
            models.Index(fields=['config_key']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_config_type_display()} - {self.config_key}" 