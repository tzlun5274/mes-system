# Generated by Django 5.1.8 on 2025-06-27 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "workorder",
            "0002_workorder_company_code_alter_workorder_order_number_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="PrdMKOrdMain",
            fields=[
                (
                    "row_id",
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name="主鍵ID"
                    ),
                ),
                ("Flag", models.IntegerField(verbose_name="狀態Flag")),
                ("MKOrdNO", models.CharField(max_length=30, verbose_name="製令單號")),
                (
                    "MKOrdDate",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="製令日期"
                    ),
                ),
                (
                    "MakeType",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="製令類型"
                    ),
                ),
                (
                    "FromRowNO",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="來源行號"
                    ),
                ),
                ("ProductID", models.CharField(max_length=50, verbose_name="產品編號")),
                (
                    "ProductType",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="產品類型"
                    ),
                ),
                (
                    "ProdtQty",
                    models.DecimalField(
                        decimal_places=4, max_digits=16, verbose_name="生產數量"
                    ),
                ),
                (
                    "Producer",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="生產人員"
                    ),
                ),
                (
                    "CostType",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="成本類型"
                    ),
                ),
                (
                    "SourceType",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="來源類型"
                    ),
                ),
                (
                    "SourceNo",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="來源單號"
                    ),
                ),
                (
                    "Functionary",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="負責人"
                    ),
                ),
                (
                    "WareInType",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="入庫類型"
                    ),
                ),
                (
                    "EstTakeMatDate",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="預計領料日"
                    ),
                ),
                (
                    "EstWareInDate",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="預計入庫日"
                    ),
                ),
                ("CompleteStatus", models.IntegerField(verbose_name="完工狀態")),
                (
                    "ChangeDate",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="異動日期"
                    ),
                ),
                (
                    "GoodsQty",
                    models.DecimalField(
                        decimal_places=4, max_digits=16, verbose_name="良品數量"
                    ),
                ),
                (
                    "BadsQty",
                    models.DecimalField(
                        decimal_places=4, max_digits=16, verbose_name="不良品數量"
                    ),
                ),
                (
                    "Remark",
                    models.TextField(blank=True, null=True, verbose_name="備註"),
                ),
                (
                    "Maker",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="製單人"
                    ),
                ),
                (
                    "Permitter",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="審核人"
                    ),
                ),
                ("updated_at", models.DateTimeField(verbose_name="更新時間")),
            ],
            options={
                "verbose_name": "製令主檔",
                "verbose_name_plural": "製令主檔",
            },
        ),
        migrations.CreateModel(
            name="PrdMkOrdMats",
            fields=[
                (
                    "row_id",
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name="主鍵ID"
                    ),
                ),
                ("Flag", models.IntegerField(verbose_name="狀態Flag")),
                ("MkOrdNO", models.CharField(max_length=30, verbose_name="製令單號")),
                ("RowNO", models.IntegerField(verbose_name="表身行號")),
                ("SerNO", models.IntegerField(verbose_name="序號")),
                ("SubProdID", models.CharField(max_length=50, verbose_name="用料編號")),
                (
                    "OriginalQty",
                    models.DecimalField(
                        decimal_places=4, max_digits=16, verbose_name="需求數量"
                    ),
                ),
                (
                    "WestingRate",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=8,
                        null=True,
                        verbose_name="損耗率",
                    ),
                ),
                (
                    "MatsRemark",
                    models.TextField(blank=True, null=True, verbose_name="用料備註"),
                ),
                (
                    "Detail",
                    models.TextField(blank=True, null=True, verbose_name="說明"),
                ),
                (
                    "UnitOughtQty",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        max_digits=16,
                        null=True,
                        verbose_name="單位應發數量",
                    ),
                ),
                (
                    "OughtQty",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        max_digits=16,
                        null=True,
                        verbose_name="應發數量",
                    ),
                ),
                ("updated_at", models.DateTimeField(verbose_name="更新時間")),
            ],
            options={
                "verbose_name": "製令明細",
                "verbose_name_plural": "製令明細",
            },
        ),
    ]
