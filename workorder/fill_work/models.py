"""
填報作業管理子模組 - 資料模型
負責填報作業的資料庫模型定義
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class FillWork(models.Model):
    """
    填報作業統一資料模型
    用於管理所有類型的填報作業記錄
    """
    
    # 核准狀態選擇
    APPROVAL_STATUS_CHOICES = [
        ('pending', '待核准'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
    ]
    
    # 基本資訊欄位
    operator = models.CharField(max_length=100, verbose_name="作業員", help_text="作業員姓名")
    company_code = models.CharField(max_length=10, verbose_name="公司代號", null=True, blank=True, help_text="公司代號")
    company_name = models.CharField(max_length=100, verbose_name="公司名稱", help_text="公司名稱")
    
    # 工單相關欄位
    workorder = models.CharField(max_length=100, verbose_name="工單號碼", help_text="工單號碼")
    product_id = models.CharField(max_length=100, verbose_name="產品編號", help_text="產品編號")
    planned_quantity = models.IntegerField(default=0, verbose_name="工單預設生產數量", help_text="工單預設生產數量")
    
    # 製程相關欄位
    process_id = models.CharField(max_length=50, verbose_name="工序ID", help_text="工序ID")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱", help_text="工序名稱")
    operation = models.CharField(max_length=100, blank=True, verbose_name="工序名稱", help_text="工序名稱")
    equipment = models.CharField(max_length=100, blank=True, default='', verbose_name="使用的設備", help_text="使用的設備")
    
    # 時間相關欄位
    work_date = models.DateField(verbose_name="工作日期", help_text="工作日期")
    start_time = models.TimeField(verbose_name="開始時間", help_text="開始時間")
    end_time = models.TimeField(verbose_name="結束時間", help_text="結束時間")
    
    # 休息時間相關欄位
    has_break = models.BooleanField(default=False, verbose_name="是否有休息時間", help_text="是否有休息時間")
    break_start_time = models.TimeField(null=True, blank=True, verbose_name="休息開始時間", help_text="休息開始時間")
    break_end_time = models.TimeField(null=True, blank=True, verbose_name="休息結束時間", help_text="休息結束時間")
    break_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'), verbose_name="休息時數", help_text="休息時數")
    
    # 工時計算欄位
    work_hours_calculated = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'), verbose_name="工作時數", help_text="工作時數")
    overtime_hours_calculated = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'), verbose_name="加班時數", help_text="加班時數")
    
    # 數量相關欄位
    work_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="工作數量", help_text="工作數量")
    defect_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="不良品數量", help_text="不良品數量")
    
    # 狀態欄位
    is_completed = models.BooleanField(default=False, verbose_name="是否已完工", help_text="是否已完工")
    
    # 核准相關欄位
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending', verbose_name="核准狀態", help_text="核准狀態")
    approved_by = models.CharField(max_length=100, blank=True, verbose_name="核准人員", help_text="核准人員")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="核准時間", help_text="核准時間")
    approval_remarks = models.TextField(blank=True, verbose_name="核准備註", help_text="核准備註")
    
    # 駁回相關欄位
    rejection_reason = models.TextField(blank=True, verbose_name="駁回原因", help_text="駁回原因")
    rejected_by = models.CharField(max_length=100, blank=True, verbose_name="駁回人員", help_text="駁回人員")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="駁回時間", help_text="駁回時間")
    
    # 備註欄位
    remarks = models.TextField(blank=True, verbose_name="備註", help_text="備註")
    abnormal_notes = models.TextField(blank=True, verbose_name="異常記錄", help_text="異常記錄")
    
    # 系統欄位
    created_by = models.CharField(max_length=100, verbose_name="建立人員", help_text="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間", help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間", help_text="更新時間")
    
    class Meta:
        verbose_name = "填報作業"
        verbose_name_plural = "填報作業"
        db_table = 'workorder_fill_work'
        ordering = ['-created_at']
        # 唯一性約束：company_name + workorder + product_id + operation + operator + work_date + start_time
        unique_together = (("company_name", "workorder", "product_id", "operation", "operator", "work_date", "start_time"),)
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['company_name']),
            models.Index(fields=['work_date']),
            models.Index(fields=['operator']),
            models.Index(fields=['workorder']),
            models.Index(fields=['product_id']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.operator} - {self.workorder} - {self.work_date}"
    
    def save(self, *args, **kwargs):
        """儲存時自動計算工時
        若實體有臨時屬性 `_skip_auto_hours_calculation=True`，則跳過自動計算（例如：匯入時已提供工時）。
        """
        # 檢查是否為新增記錄且存在重複
        if not self.pk:  # 新增記錄
            # 檢查是否已存在相同的記錄（更合理的唯一性檢查）
            # 考慮：公司名稱 + 工單號碼 + 產品編號 + 工序 + 作業員 + 工作日期 + 開始時間
            existing_record = FillWork.objects.filter(
                company_name=self.company_name,
                workorder=self.workorder,
                product_id=self.product_id,
                operation=self.operation,
                operator=self.operator,
                work_date=self.work_date,
                start_time=self.start_time
            ).first()
            
            if existing_record:
                # 如果存在重複記錄，覆蓋舊記錄而不是拋出異常
                # 更新現有記錄的所有欄位
                existing_record.operator = self.operator
                existing_record.company_name = self.company_name
                existing_record.workorder = self.workorder
                existing_record.product_id = self.product_id
                existing_record.planned_quantity = self.planned_quantity
                existing_record.process_id = self.process_id
                existing_record.operation = self.operation
                existing_record.equipment = self.equipment
                existing_record.work_date = self.work_date
                existing_record.start_time = self.start_time
                existing_record.end_time = self.end_time
                existing_record.has_break = self.has_break
                existing_record.break_start_time = self.break_start_time
                existing_record.break_end_time = self.break_end_time
                existing_record.work_quantity = self.work_quantity
                existing_record.defect_quantity = self.defect_quantity
                existing_record.approval_status = self.approval_status
                existing_record.remarks = self.remarks
                existing_record.abnormal_notes = self.abnormal_notes
                existing_record.created_by = self.created_by
                
                # 計算工作時數和加班時數（允許在匯入時以臨時旗標跳過）
                if not getattr(self, '_skip_auto_hours_calculation', False):
                    existing_record.calculate_work_hours()
                else:
                    # 如果跳過自動計算，直接使用提供的值
                    existing_record.work_hours_calculated = self.work_hours_calculated
                    existing_record.overtime_hours_calculated = self.overtime_hours_calculated
                
                # 儲存更新後的記錄
                existing_record.save()
                
                # 將現有記錄的ID設定給當前物件，這樣調用者可以知道記錄已更新
                self.pk = existing_record.pk
                return
            
            # 移除派工單驗證，直接使用匯入的工單號碼
            # 驗證派工單（RD樣品除外）
            # if not self._is_rd_sample():
            #     self._validate_workorder_dispatch()
        
        # 計算工作時數和加班時數（允許在匯入時以臨時旗標跳過）
        if not getattr(self, '_skip_auto_hours_calculation', False):
            self.calculate_work_hours()
        super().save(*args, **kwargs)
    
    def calculate_work_hours(self):
        """計算工作時數和加班時數"""
        from datetime import datetime, time
        
        if not self.start_time or not self.end_time:
            return
        
        try:
            # 計算總工作時間（分鐘）
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60  # 跨日處理
            
            # 判斷是否為作業員填報（有午休機制）
            is_operator_fill = bool(self.has_break)
            
            # 固定午休區間（12:00~13:00），僅作業員適用
            lunch_deduction_minutes = 0
            if is_operator_fill:
                lunch_start = 12 * 60
                lunch_end = 13 * 60
                overlaps_lunch = (start_minutes < lunch_end and end_minutes > lunch_start)
                if overlaps_lunch:
                    lunch_deduction_minutes = 60
                    self.break_hours = Decimal('1.00')
                else:
                    self.break_hours = Decimal('0.00')
            else:
                self.break_hours = Decimal('0.00')
            
            # 決定加班起算時間
            if is_operator_fill:
                # 作業員填報：17:30後加班
                overtime_start_minutes = 17 * 60 + 30
            else:
                # SMT填報：16:30後加班
                overtime_start_minutes = 16 * 60 + 30
            
            # 計算正常工時和加班時數
            normal_minutes = 0
            overtime_minutes = 0
            
            current_minutes = start_minutes
            while current_minutes < end_minutes:
                if current_minutes < overtime_start_minutes:
                    normal_minutes += 1
                else:
                    overtime_minutes += 1
                current_minutes += 1
            
            # 作業員：若與午休有交集，固定扣除1小時（僅扣正常工時，且不低於0）
            if is_operator_fill and lunch_deduction_minutes > 0:
                normal_minutes = max(0, normal_minutes - lunch_deduction_minutes)
            
            self.work_hours_calculated = Decimal(str(normal_minutes / 60))
            self.overtime_hours_calculated = Decimal(str(overtime_minutes / 60))
            
        except (ValueError, AttributeError):
            # 如果時間格式錯誤，設為0
            self.work_hours_calculated = Decimal('0.00')
            self.overtime_hours_calculated = Decimal('0.00')
    
    def _is_rd_sample(self):
        """判斷是否為RD樣品"""
        return (self.workorder == 'RD樣品' and 
                self.product_id and 
                self.product_id.startswith('PFP-CCT'))
    
    def _validate_workorder_dispatch(self):
        """驗證派工單是否存在且資料一致"""
        try:
            from workorder.workorder_dispatch.models import WorkOrderDispatch
            
            # 查找對應的派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=self.workorder,
                product_code=self.product_id
            ).first()
            
            if not dispatch:
                raise ValueError(
                    f"找不到對應的派工單：工單號碼={self.workorder}, 產品編號={self.product_id}"
                )
            
            # 驗證公司代號是否一致（需要從公司代號轉換為公司名稱進行比較）
            from erp_integration.models import CompanyConfig
            company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
            dispatch_company_name = company_config.company_name if company_config else None
            
            if dispatch_company_name != self.company_name:
                raise ValueError(
                    f"公司名稱不一致：填報記錄={self.company_name}, 派工單={dispatch_company_name}"
                )
            
            # 驗證產品編號是否一致
            if dispatch.product_code != self.product_id:
                raise ValueError(
                    f"產品編號不一致：填報記錄={self.product_id}, 派工單={dispatch.product_code}"
                )
                
        except ImportError:
            # 如果派工單模組不存在，跳過驗證
            pass 