# 產線管理模型
# 此檔案定義產線類型管理和產線管理的資料模型
# 包含工作時間設定、工作日設定等功能

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json
from datetime import datetime, timedelta


class ProductionLineType(models.Model):
    """
    產線類型管理模型
    定義不同類型的產線，例如：SMT產線、組裝產線、測試產線等
    """

    type_code = models.CharField(
        max_length=20,
        verbose_name="類型代號",
        help_text="產線類型代號，例如：SMT、ASSY、TEST",
        unique=True,
    )

    type_name = models.CharField(
        max_length=100, verbose_name="類型名稱", help_text="產線類型的中文名稱"
    )

    description = models.TextField(
        blank=True, null=True, verbose_name="類型描述", help_text="產線類型的詳細描述"
    )

    is_active = models.BooleanField(
        default=True, verbose_name="啟用狀態", help_text="是否啟用此產線類型"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "產線類型"
        verbose_name_plural = "產線類型管理"
        ordering = ["type_code"]

    def __str__(self):
        return f"{self.type_name} ({self.type_code})"


class ProductionLine(models.Model):
    """
    產線管理模型
    管理具體的產線資訊，包含工作時間設定、工作日設定等
    """

    line_code = models.CharField(
        max_length=20,
        verbose_name="產線代號",
        help_text="產線的唯一識別代號",
        unique=True,
    )

    line_name = models.CharField(
        max_length=100, verbose_name="產線名稱", help_text="產線的中文名稱"
    )

    line_type = models.ForeignKey(
        ProductionLineType,
        on_delete=models.CASCADE,
        verbose_name="產線類型",
        help_text="此產線所屬的類型",
    )

    description = models.TextField(
        blank=True, null=True, verbose_name="產線描述", help_text="產線的詳細描述"
    )

    # 工作時間設定
    work_start_time = models.TimeField(
        verbose_name="工作開始時間", help_text="每日工作開始時間，格式：HH:MM"
    )

    work_end_time = models.TimeField(
        verbose_name="工作結束時間", help_text="每日工作結束時間，格式：HH:MM"
    )

    lunch_start_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="午休開始時間",
        help_text="午休開始時間，格式：HH:MM（可為空，表示無午休時間）",
    )

    lunch_end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="午休結束時間",
        help_text="午休結束時間，格式：HH:MM（可為空，表示無午休時間）",
    )

    overtime_start_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="加班開始時間",
        help_text="加班開始時間，格式：HH:MM（可為空，表示無加班時間）",
    )

    overtime_end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="加班結束時間",
        help_text="加班結束時間，格式：HH:MM（可為空，表示無加班時間）",
    )

    # 工作日設定（JSON格式儲存，例如：["1","2","3","4","5"] 表示週一到週五）
    work_days = models.TextField(
        default='["1","2","3","4","5"]',
        verbose_name="工作日設定",
        help_text="工作日設定，JSON格式，1=週一，2=週二，以此類推",
    )

    is_active = models.BooleanField(
        default=True, verbose_name="啟用狀態", help_text="是否啟用此產線"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "產線管理"
        verbose_name_plural = "產線管理"
        ordering = ["line_code"]

    def __str__(self):
        return f"{self.line_name} ({self.line_code})"

    def get_work_days_list(self):
        """
        取得工作日列表
        回傳：['1', '2', '3', '4', '5'] 格式的列表
        """
        try:
            return json.loads(str(self.work_days))
        except (json.JSONDecodeError, TypeError):
            # 如果解析失敗，回傳預設值（週一到週五）
            return ["1", "2", "3", "4", "5"]

    def set_work_days_list(self, days_list):
        """
        設定工作日列表
        參數：['1', '2', '3', '4', '5'] 格式的列表
        """
        if isinstance(days_list, list):
            self.work_days = json.dumps(days_list)
        else:
            raise ValueError("工作日列表必須是列表格式")

    def get_work_days_display(self):
        """
        取得工作日的顯示文字
        回傳：例如 "週一、週二、週三、週四、週五"
        """
        day_names = {
            "1": "週一",
            "2": "週二",
            "3": "週三",
            "4": "週四",
            "5": "週五",
            "6": "週六",
            "7": "週日",
        }
        work_days = self.get_work_days_list()
        return "、".join([day_names.get(day, day) for day in work_days])

    def get_daily_work_hours(self):
        """
        計算每日工作時數（不含午休）
        回傳：工作時數（小時）
        """
        if self.work_start_time and self.work_end_time:
            start_dt = datetime.combine(datetime.today(), self.work_start_time)
            end_dt = datetime.combine(datetime.today(), self.work_end_time)

            # 如果結束時間小於開始時間，表示跨日
            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            # 計算總工作時間
            total_hours = (end_dt - start_dt).total_seconds() / 3600

            # 扣除午休時間
            if self.lunch_start_time and self.lunch_end_time:
                lunch_start = datetime.combine(datetime.today(), self.lunch_start_time)
                lunch_end = datetime.combine(datetime.today(), self.lunch_end_time)

                if lunch_end < lunch_start:
                    lunch_end += timedelta(days=1)

                lunch_hours = (lunch_end - lunch_start).total_seconds() / 3600
                total_hours -= lunch_hours

            return round(total_hours, 2)
        return 0

    def get_overtime_hours(self):
        """
        計算加班時數
        回傳：加班時數（小時）
        """
        if self.overtime_start_time and self.overtime_end_time:
            start_dt = datetime.combine(datetime.today(), self.overtime_start_time)
            end_dt = datetime.combine(datetime.today(), self.overtime_end_time)

            # 如果結束時間小於開始時間，表示跨日
            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            overtime_hours = (end_dt - start_dt).total_seconds() / 3600
            return round(overtime_hours, 2)
        return 0


class ProductionLineSchedule(models.Model):
    """
    產線排程記錄模型
    記錄產線的排程歷史和變更記錄
    """

    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.CASCADE,
        verbose_name="產線",
        related_name="schedules",
    )

    schedule_date = models.DateField(verbose_name="排程日期")

    work_start_time = models.TimeField(verbose_name="工作開始時間")

    work_end_time = models.TimeField(verbose_name="工作結束時間")

    lunch_start_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="午休開始時間",
        help_text="午休開始時間，格式：HH:MM（可為空，表示無午休時間）",
    )

    lunch_end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="午休結束時間",
        help_text="午休結束時間，格式：HH:MM（可為空，表示無午休時間）",
    )

    overtime_start_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="加班開始時間",
        help_text="加班開始時間，格式：HH:MM（可為空，表示無加班時間）",
    )

    overtime_end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="加班結束時間",
        help_text="加班結束時間，格式：HH:MM（可為空，表示無加班時間）",
    )

    work_days = models.TextField(verbose_name="工作日設定")

    is_holiday = models.BooleanField(default=False, verbose_name="是否為假日")

    holiday_reason = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="假日原因"
    )

    created_by = models.CharField(max_length=100, verbose_name="建立人員")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "產線排程記錄"
        verbose_name_plural = "產線排程記錄"
        unique_together = (("production_line", "schedule_date"),)
        ordering = ["-schedule_date", "production_line"]

    def __str__(self):
        return f"{self.production_line.line_name} - {self.schedule_date}"
