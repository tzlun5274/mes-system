# -*- coding: utf-8 -*-
"""
這個指令可以徹底刪除所有包含指定產品編號的產品工藝路線。
用法：python manage.py delete_product_route_force <產品編號關鍵字>
"""
from django.core.management.base import BaseCommand
from process.models import ProductProcessRoute
import logging

logger = logging.getLogger("process")


class Command(BaseCommand):
    help = "徹底刪除所有包含指定產品編號的產品工藝路線（支援模糊比對、空白、特殊字元）"

    def add_arguments(self, parser):
        parser.add_argument(
            "keyword", type=str, help="要徹底刪除的產品編號關鍵字（支援模糊比對）"
        )

    def handle(self, *args, **options):
        keyword = options["keyword"]
        self.stdout.write(
            self.style.WARNING(f"準備徹底刪除所有包含「{keyword}」的產品工藝路線...")
        )
        qs = ProductProcessRoute.objects.filter(product_id__icontains=keyword)
        count = qs.count()
        if count == 0:
            self.stdout.write(
                self.style.ERROR(f"找不到任何包含「{keyword}」的產品工藝路線。")
            )
            return
        for obj in qs:
            logger.info(
                f"徹底刪除產品工藝路線：產品編號={obj.product_id}，工序={obj.process_name}，順序={obj.step_order}"
            )
        qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"已徹底刪除 {count} 筆產品工藝路線，關鍵字：「{keyword}」"
            )
        )
