"""
清理重複的產品工藝路線記錄
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from process.models import ProductProcessRoute


class Command(BaseCommand):
    help = '清理重複的產品工藝路線記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會刪除的記錄，不實際刪除',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 找出重複的記錄
        duplicates = ProductProcessRoute.objects.values(
            'product_id', 'step_order'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gt=1
        )
        
        if not duplicates.exists():
            self.stdout.write(
                self.style.SUCCESS('沒有發現重複的產品工藝路線記錄')
            )
            return
        
        self.stdout.write(f'發現 {duplicates.count()} 組重複記錄：')
        
        total_deleted = 0
        
        for duplicate in duplicates:
            product_id = duplicate['product_id']
            step_order = duplicate['step_order']
            count = duplicate['count']
            
            self.stdout.write(
                f'產品: {product_id}, 步驟: {step_order}, 重複數量: {count}'
            )
            
            # 獲取該組重複記錄
            routes = ProductProcessRoute.objects.filter(
                product_id=product_id,
                step_order=step_order
            ).order_by('id')
            
            # 保留第一個記錄，刪除其餘的
            keep_route = routes.first()
            delete_routes = routes.exclude(id=keep_route.id)
            
            self.stdout.write(f'  保留記錄 ID: {keep_route.id}')
            self.stdout.write(f'  將刪除記錄: {list(delete_routes.values_list("id", flat=True))}')
            
            if not dry_run:
                deleted_count = delete_routes.count()
                delete_routes.delete()
                total_deleted += deleted_count
                self.stdout.write(f'  已刪除 {deleted_count} 個重複記錄')
            else:
                self.stdout.write(f'  (乾跑模式) 將刪除 {delete_routes.count()} 個重複記錄')
            
            self.stdout.write('')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'乾跑模式：總共將刪除 {total_deleted} 個重複記錄')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'清理完成：總共刪除了 {total_deleted} 個重複記錄')
            ) 