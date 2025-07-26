# -*- coding: utf-8 -*-
"""
這個指令會自動清除產品工藝路線（ProductProcessRoute）重複資料，只保留每個產品編號唯一的那一筆（不管工序順序）。
執行方式：python3 manage.py clean_duplicate_product_routes
"""
from django.core.management.base import BaseCommand
from process.models import ProductProcessRoute


class Command(BaseCommand):
    help = "清除產品工藝路線重複資料，只保留每個產品編號唯一的那一筆（不管工序順序）"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("開始檢查產品編號重複的產品工藝路線..."))
        all_routes = ProductProcessRoute.objects.all().order_by("product_id", "id")
        seen = set()
        to_delete = []
        for route in all_routes:
            key = route.product_id
            if key in seen:
                to_delete.append(route.id)
            else:
                seen.add(key)
        if to_delete:
            count = len(to_delete)
            ProductProcessRoute.objects.filter(id__in=to_delete).delete()
            self.stdout.write(
                self.style.SUCCESS(f"已刪除 {count} 筆產品編號重複資料！")
            )
        else:
            self.stdout.write(self.style.SUCCESS("沒有發現產品編號重複資料。"))
        self.stdout.write(self.style.SUCCESS("清理完成！"))
