"""
公司製令單管理子模組 - 模型定義
負責ERP整合功能，包括公司製令單、ERP製令主檔等
"""

from django.db import models
from django.utils import timezone


class PrdMKOrdMain(models.Model):
    """
    ERP 製令主檔：從正航 ERP 同步的製令主檔資料
    """
    row_id = models.BigAutoField(primary_key=True, verbose_name="主鍵ID")
    Flag = models.IntegerField(verbose_name="狀態Flag")
    MKOrdNO = models.CharField(max_length=30, verbose_name="製令單號")
    MKOrdDate = models.CharField(
        max_length=20, verbose_name="製令日期", blank=True, null=True
    )
    MakeType = models.CharField(
        max_length=20, verbose_name="製令類型", blank=True, null=True
    )
    FromRowNO = models.CharField(
        max_length=20, verbose_name="來源行號", blank=True, null=True
    )
    ProductID = models.CharField(max_length=50, verbose_name="產品編號")
    ProductType = models.CharField(
        max_length=20, verbose_name="產品類型", blank=True, null=True
    )
    ProdtQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="生產數量"
    )
    Producer = models.CharField(
        max_length=20, verbose_name="生產人員", blank=True, null=True
    )
    CostType = models.CharField(
        max_length=20, verbose_name="成本類型", blank=True, null=True
    )
    SourceType = models.CharField(
        max_length=20, verbose_name="來源類型", blank=True, null=True
    )
    SourceNo = models.CharField(
        max_length=50, verbose_name="來源單號", blank=True, null=True
    )
    Functionary = models.CharField(
        max_length=20, verbose_name="負責人", blank=True, null=True
    )
    WareInType = models.CharField(
        max_length=20, verbose_name="入庫類型", blank=True, null=True
    )
    EstTakeMatDate = models.CharField(
        max_length=20, verbose_name="預計領料日", blank=True, null=True
    )
    EstWareInDate = models.CharField(
        max_length=20, verbose_name="預計入庫日", blank=True, null=True
    )
    CompleteStatus = models.IntegerField(verbose_name="完工狀態")
    ChangeDate = models.CharField(
        max_length=20, verbose_name="異動日期", blank=True, null=True
    )
    GoodsQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="良品數量"
    )
    BadsQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="不良品數量"
    )
    Remark = models.TextField(verbose_name="備註", blank=True, null=True)
    Maker = models.CharField(
        max_length=20, verbose_name="製單人", blank=True, null=True
    )
    Permitter = models.CharField(
        max_length=20, verbose_name="核准人", blank=True, null=True
    )
    updated_at = models.DateTimeField(verbose_name="更新時間")
    BillStatus = models.IntegerField(verbose_name="單況", blank=True, null=True)

    class Meta:
        verbose_name = "製令主檔"
        verbose_name_plural = "製令主檔"

    def __str__(self):
        return f"{self.MKOrdNO} - {self.ProductID}"


class PrdMkOrdMats(models.Model):
    """
    ERP 製令明細：從正航 ERP 同步的製令明細資料
    """
    row_id = models.BigAutoField(primary_key=True, verbose_name="主鍵ID")
    Flag = models.IntegerField(verbose_name="狀態Flag")
    MkOrdNO = models.CharField(max_length=30, verbose_name="製令單號")
    RowNO = models.IntegerField(verbose_name="表身行號")
    SerNO = models.IntegerField(verbose_name="序號")
    SubProdID = models.CharField(max_length=50, verbose_name="用料編號")
    OriginalQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="需求數量"
    )
    WestingRate = models.DecimalField(
        max_digits=8, decimal_places=3, verbose_name="損耗率", blank=True, null=True
    )
    MatsRemark = models.TextField(verbose_name="用料備註", blank=True, null=True)
    Detail = models.TextField(verbose_name="說明", blank=True, null=True)
    UnitOughtQty = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        verbose_name="單位應發數量",
        blank=True,
        null=True,
    )
    OughtQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="應發數量", blank=True, null=True
    )
    updated_at = models.DateTimeField(verbose_name="更新時間")

    class Meta:
        verbose_name = "製令明細"
        verbose_name_plural = "製令明細"

    def __str__(self):
        return f"{self.MkOrdNO} - {self.SubProdID}"


class CompanyOrder(models.Model):
    """
    MES 專用公司製令單表，對應公司製令單頁面所有欄位
    """

    company_code = models.CharField(
        max_length=10, verbose_name="公司代號"
    )  # 例如 01、02、03
    mkordno = models.CharField(max_length=50, verbose_name="製令單號")
    product_id = models.CharField(max_length=100, verbose_name="產品編號")
    prodt_qty = models.PositiveIntegerField(verbose_name="生產數量")
    est_take_mat_date = models.CharField(max_length=20, verbose_name="預定開工日")
    est_stock_out_date = models.CharField(max_length=20, verbose_name="預定出貨日")
    complete_status = models.IntegerField(
        verbose_name="完工狀態", null=True, blank=True
    )
    bill_status = models.IntegerField(verbose_name="單況", null=True, blank=True)
    sync_time = models.DateTimeField(auto_now=True, verbose_name="同步時間")
    is_converted = models.BooleanField(default=False, verbose_name="已轉成 MES 工單")

    class Meta:
        verbose_name = "公司製令單"
        verbose_name_plural = "公司製令單"
        unique_together = (("company_code", "mkordno", "product_id"),)

    def __str__(self):
        # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
        formatted_company_code = self.company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)
        return f"[{formatted_company_code}] 製令單 {self.mkordno}"


class SystemConfig(models.Model):
    """
    系統設定表：存放全域設定，例如自動轉換工單間隔（分鐘）
    """

    key = models.CharField(
        max_length=50, unique=True, verbose_name="設定名稱"
    )  # 例如 auto_convert_interval
    value = models.CharField(max_length=100, verbose_name="設定值（分鐘）")

    class Meta:
        verbose_name = "系統設定"
        verbose_name_plural = "系統設定"

    def __str__(self):
        return f"{self.key}: {self.value}" 