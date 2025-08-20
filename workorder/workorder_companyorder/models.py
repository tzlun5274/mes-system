"""
公司製令單管理子模組 - 模型定義
負責公司製令單的管理功能，包括公司製令單、ERP系統配置、ERP製令主檔、ERP製令明細
"""

from django.db import models
from django.utils import timezone


class CompanyOrder(models.Model):
    """
    公司製令單：MES專用公司製令單表，對應公司製令單頁面所有欄位
    支援多公司架構，唯一識別：公司代號 + 製令單號 + 產品編號
    """
    
    # 基本識別資訊（多公司架構）
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號，例如：01、02、03"
    )
    
    # 製令單資訊
    mkordno = models.CharField(
        max_length=50, 
        verbose_name="製令單號",
        help_text="製令單號碼"
    )
    product_id = models.CharField(
        max_length=100, 
        verbose_name="產品編號",
        help_text="產品編號"
    )
    prodt_qty = models.PositiveIntegerField(
        verbose_name="生產數量",
        help_text="計劃生產數量"
    )
    
    # 時間資訊
    est_take_mat_date = models.CharField(
        max_length=20, 
        verbose_name="預定開工日",
        help_text="預定開工日期"
    )
    est_stock_out_date = models.CharField(
        max_length=20, 
        verbose_name="預定出貨日",
        help_text="預定出貨日期"
    )
    
    # 狀態資訊
    complete_status = models.IntegerField(
        verbose_name="完工狀態",
        null=True, 
        blank=True,
        help_text="完工狀態代碼"
    )
    bill_status = models.IntegerField(
        verbose_name="單況",
        null=True, 
        blank=True,
        help_text="單據狀況代碼"
    )
    
    # 同步資訊
    sync_time = models.DateTimeField(
        auto_now=True, 
        verbose_name="同步時間",
        help_text="最後同步時間"
    )
    is_converted = models.BooleanField(
        default=False, 
        verbose_name="已轉成MES工單",
        help_text="是否已轉換為MES工單"
    )
    
    # 系統欄位 - 移除 created_at 和 updated_at，因為實際資料表中沒有這些欄位
    # 使用 sync_time 作為時間戳記

    class Meta:
        verbose_name = "公司製令單"
        verbose_name_plural = "公司製令單管理"
        # 使用 Django 自動命名：workorder_companyorder_companyorder
        # 唯一性約束：公司代號 + 製令單號 + 產品編號
        unique_together = (("company_code", "mkordno", "product_id"),)
        ordering = ['-sync_time']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['mkordno']),
            models.Index(fields=['product_id']),
            models.Index(fields=['sync_time']),
            models.Index(fields=['is_converted']),
        ]

    def __str__(self):
        # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
        formatted_company_code = self.company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)
        return f"[{formatted_company_code}] 製令單 {self.mkordno} - {self.product_id}"


class ERPSystemConfig(models.Model):
    """
    ERP系統配置：公司製令單ERP系統配置
    存放各公司的ERP系統連線設定
    """
    
    # 基本識別資訊（多公司架構）
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號，例如：01、02、03"
    )
    
    # ERP連線設定
    server_name = models.CharField(
        max_length=100, 
        verbose_name="伺服器名稱",
        help_text="ERP資料庫伺服器名稱"
    )
    database_name = models.CharField(
        max_length=100, 
        verbose_name="資料庫名稱",
        help_text="ERP資料庫名稱"
    )
    username = models.CharField(
        max_length=50, 
        verbose_name="使用者名稱",
        help_text="ERP資料庫使用者名稱"
    )
    password = models.CharField(
        max_length=100, 
        verbose_name="密碼",
        help_text="ERP資料庫密碼"
    )
    
    # 同步設定
    sync_interval = models.IntegerField(
        default=30, 
        verbose_name="同步間隔(分鐘)",
        help_text="自動同步間隔時間（分鐘）"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="啟用狀態",
        help_text="是否啟用此ERP連線"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="更新時間"
    )

    class Meta:
        verbose_name = "ERP系統配置"
        verbose_name_plural = "ERP系統配置管理"
        db_table = 'workorder_companyorder_erp_systemconfig'
        # 唯一性約束：每個公司只能有一個ERP配置
        unique_together = (("company_code",),)
        ordering = ['company_code']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        formatted_company_code = self.company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)
        return f"[{formatted_company_code}] ERP配置 - {self.server_name}"


class ERPPrdMKOrdMain(models.Model):
    """
    ERP製令主檔：公司製令單ERP製令主檔
    從正航ERP同步的製令主檔資料
    """
    
    row_id = models.BigAutoField(
        primary_key=True, 
        verbose_name="主鍵ID"
    )
    
    # 基本資訊
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號"
    )
    Flag = models.IntegerField(
        verbose_name="狀態Flag"
    )
    MKOrdNO = models.CharField(
        max_length=30, 
        verbose_name="製令單號"
    )
    MKOrdDate = models.CharField(
        max_length=20, 
        verbose_name="製令日期", 
        blank=True, 
        null=True
    )
    MakeType = models.CharField(
        max_length=20, 
        verbose_name="製令類型", 
        blank=True, 
        null=True
    )
    FromRowNO = models.CharField(
        max_length=20, 
        verbose_name="來源行號", 
        blank=True, 
        null=True
    )
    ProductID = models.CharField(
        max_length=50, 
        verbose_name="產品編號"
    )
    ProductType = models.CharField(
        max_length=20, 
        verbose_name="產品類型", 
        blank=True, 
        null=True
    )
    ProdtQty = models.DecimalField(
        max_digits=16, 
        decimal_places=4, 
        verbose_name="生產數量"
    )
    Producer = models.CharField(
        max_length=20, 
        verbose_name="生產人員", 
        blank=True, 
        null=True
    )
    CostType = models.CharField(
        max_length=20, 
        verbose_name="成本類型", 
        blank=True, 
        null=True
    )
    SourceType = models.CharField(
        max_length=20, 
        verbose_name="來源類型", 
        blank=True, 
        null=True
    )
    SourceNo = models.CharField(
        max_length=50, 
        verbose_name="來源單號", 
        blank=True, 
        null=True
    )
    Functionary = models.CharField(
        max_length=20, 
        verbose_name="負責人", 
        blank=True, 
        null=True
    )
    WareInType = models.CharField(
        max_length=20, 
        verbose_name="入庫類型", 
        blank=True, 
        null=True
    )
    EstTakeMatDate = models.CharField(
        max_length=20, 
        verbose_name="預計領料日", 
        blank=True, 
        null=True
    )
    EstWareInDate = models.CharField(
        max_length=20, 
        verbose_name="預計入庫日", 
        blank=True, 
        null=True
    )
    CompleteStatus = models.IntegerField(
        verbose_name="完工狀態"
    )
    ChangeDate = models.CharField(
        max_length=20, 
        verbose_name="異動日期", 
        blank=True, 
        null=True
    )
    GoodsQty = models.DecimalField(
        max_digits=16, 
        decimal_places=4, 
        verbose_name="良品數量"
    )
    BadsQty = models.DecimalField(
        max_digits=16, 
        decimal_places=4, 
        verbose_name="不良品數量"
    )
    Remark = models.TextField(
        verbose_name="備註", 
        blank=True, 
        null=True
    )
    Maker = models.CharField(
        max_length=20, 
        verbose_name="製單人", 
        blank=True, 
        null=True
    )
    Permitter = models.CharField(
        max_length=20, 
        verbose_name="核准人", 
        blank=True, 
        null=True
    )
    BillStatus = models.IntegerField(
        verbose_name="單況", 
        blank=True, 
        null=True
    )
    
    # 同步資訊
    updated_at = models.DateTimeField(
        verbose_name="更新時間"
    )

    class Meta:
        verbose_name = "ERP製令主檔"
        verbose_name_plural = "ERP製令主檔管理"
        db_table = 'workorder_companyorder_erp_prdmkordmain'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['MKOrdNO']),
            models.Index(fields=['ProductID']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"[{self.company_code}] {self.MKOrdNO} - {self.ProductID}"


class ERPPrdMkOrdMats(models.Model):
    """
    ERP製令明細：公司製令單ERP製令明細
    從正航ERP同步的製令明細資料
    """
    
    row_id = models.BigAutoField(
        primary_key=True, 
        verbose_name="主鍵ID"
    )
    
    # 基本資訊
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號"
    )
    Flag = models.IntegerField(
        verbose_name="狀態Flag"
    )
    MkOrdNO = models.CharField(
        max_length=30, 
        verbose_name="製令單號"
    )
    RowNO = models.IntegerField(
        verbose_name="表身行號"
    )
    SerNO = models.IntegerField(
        verbose_name="序號"
    )
    SubProdID = models.CharField(
        max_length=50, 
        verbose_name="用料編號"
    )
    OriginalQty = models.DecimalField(
        max_digits=16, 
        decimal_places=4, 
        verbose_name="需求數量"
    )
    WestingRate = models.DecimalField(
        max_digits=8, 
        decimal_places=3, 
        verbose_name="損耗率", 
        blank=True, 
        null=True
    )
    MatsRemark = models.TextField(
        verbose_name="用料備註", 
        blank=True, 
        null=True
    )
    Detail = models.TextField(
        verbose_name="說明", 
        blank=True, 
        null=True
    )
    UnitOughtQty = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        verbose_name="單位應發數量",
        blank=True,
        null=True,
    )
    OughtQty = models.DecimalField(
        max_digits=16, 
        decimal_places=4, 
        verbose_name="應發數量", 
        blank=True, 
        null=True
    )
    
    # 同步資訊
    updated_at = models.DateTimeField(
        verbose_name="更新時間"
    )

    class Meta:
        verbose_name = "ERP製令明細"
        verbose_name_plural = "ERP製令明細管理"
        db_table = 'workorder_companyorder_erp_prdmkordmats'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['MkOrdNO']),
            models.Index(fields=['SubProdID']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"[{self.company_code}] {self.MkOrdNO} - {self.SubProdID}" 