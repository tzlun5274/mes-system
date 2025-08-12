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
    company_name = models.CharField(max_length=100, verbose_name="公司名稱", help_text="公司名稱")
    
    # 工單相關欄位
    workorder = models.CharField(max_length=100, verbose_name="工單號碼", help_text="工單號碼")
    product_id = models.CharField(max_length=100, verbose_name="產品編號", help_text="產品編號")
    planned_quantity = models.IntegerField(default=0, verbose_name="工單預設生產數量", help_text="工單預設生產數量")
    
    # 製程相關欄位
    process = models.ForeignKey('process.ProcessName', on_delete=models.CASCADE, verbose_name="工序", help_text="工序")
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
        indexes = [
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
        """儲存時自動計算工時"""
        # 計算工作時數和加班時數
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
            
            total_minutes = end_minutes - start_minutes
            
            # 扣除休息時間（若有且休息區間大於0）
            break_minutes = 0
            has_valid_break = False
            if self.has_break and self.break_start_time and self.break_end_time:
                break_start_minutes = self.break_start_time.hour * 60 + self.break_start_time.minute
                break_end_minutes = self.break_end_time.hour * 60 + self.break_end_time.minute
                
                # 休息開始與結束相同 → 視為沒有休息（符合 SMT 12:00~12:00 的設計）
                if break_end_minutes != break_start_minutes:
                    if break_end_minutes <= break_start_minutes:
                        break_end_minutes += 24 * 60
                    break_minutes = break_end_minutes - break_start_minutes
                    has_valid_break = break_minutes > 0
                
                self.break_hours = Decimal(str(break_minutes / 60))
            
            # 判斷是否為作業員填報（有真正休息時段）
            is_operator_fill = has_valid_break
            
            if is_operator_fill:
                # 作業員填報：12:00-13:00休息，17:30後加班
                overtime_start_minutes = 17 * 60 + 30
            else:
                # SMT填報：無休息時間，16:30後加班
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
            
            # 從正常工時中扣除休息時間（僅在有有效休息時段時扣除）
            if has_valid_break:
                break_start_minutes = self.break_start_time.hour * 60 + self.break_start_time.minute
                break_end_minutes = self.break_end_time.hour * 60 + self.break_end_time.minute
                if break_end_minutes <= break_start_minutes:
                    break_end_minutes += 24 * 60
                # 從正常工時中扣除休息時間（如落在加班前時段）
                if break_start_minutes < overtime_start_minutes:
                    break_in_normal = min(break_end_minutes, overtime_start_minutes) - break_start_minutes
                    normal_minutes -= max(break_in_normal, 0)
            
            self.work_hours_calculated = Decimal(str(normal_minutes / 60))
            self.overtime_hours_calculated = Decimal(str(overtime_minutes / 60))
            
        except (ValueError, AttributeError):
            # 如果時間格式錯誤，設為0
            self.work_hours_calculated = Decimal('0.00')
            self.overtime_hours_calculated = Decimal('0.00') 