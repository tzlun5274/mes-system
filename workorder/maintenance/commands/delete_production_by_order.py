"""
刪除指定工單號碼在「生產執行監控」中的資料（不影響原始填報與已完工資料）。
使用方式：
    python manage.py delete_production_by_order --order 331-25213001
    python manage.py delete_production_by_order --order 331-25213001 --company 01
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from workorder.models import WorkOrder, WorkOrderProduction, WorkOrderProductionDetail


class Command(BaseCommand):
    help = "刪除指定工單號在生產監控中的資料（WorkOrderProduction 與 WorkOrderProductionDetail）"

    def add_arguments(self, parser):
        parser.add_argument("--order", required=True, help="工單號碼，例如 331-25213001")
        parser.add_argument(
            "--company",
            required=False,
            help="公司代號（可選，用於縮小範圍，例如 01）",
        )

    def handle(self, *args, **options):
        order_number: str = options["order"].strip()
        company_code: str | None = (options.get("company") or "").strip() or None

        if not order_number:
            raise CommandError("請提供 --order 參數（工單號碼）")

        qs = WorkOrder.objects.filter(order_number=order_number)
        if company_code:
            qs = qs.filter(company_code=company_code)

        count_workorders = qs.count()
        if count_workorders == 0:
            self.stdout.write(self.style.WARNING("找不到對應工單，無資料可刪除"))
            return

        deleted_details_total = 0
        deleted_productions_total = 0

        with transaction.atomic():
            for wo in qs:
                prods = WorkOrderProduction.objects.filter(workorder=wo)
                details = WorkOrderProductionDetail.objects.filter(workorder_production__in=prods)
                d_count = details.count()
                p_count = prods.count()
                details.delete()
                prods.delete()
                deleted_details_total += d_count
                deleted_productions_total += p_count

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：工單 {order_number}（匹配 {count_workorders} 筆）已刪除 生產明細 {deleted_details_total} 筆、監控主檔 {deleted_productions_total} 筆。"
            )
        ) 