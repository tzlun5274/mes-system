"""
Django 管理命令：重新分析失敗的工單
"""
from django.core.management.base import BaseCommand
from workorder.models import CompletedWorkOrder
from reporting.workorder_analysis_service import WorkOrderAnalysisService
from django.db.models import Q


class Command(BaseCommand):
    help = '重新分析失敗的工單，找出並修復問題'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-code',
            type=str,
            help='指定公司代號'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際執行分析'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='處理工單數量限制 (預設: 10)'
        )
    
    def handle(self, *args, **options):
        company_code = options.get('company_code')
        dry_run = options.get('dry_run')
        limit = options.get('limit')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際執行分析')
            )
        
        # 找出可能有問題的工單
        queryset = CompletedWorkOrder.objects.exclude(order_number__icontains='RD樣品')
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        # 找出沒有完成數量或計劃數量的工單
        problem_orders = queryset.filter(
            Q(completed_quantity__isnull=True) | Q(completed_quantity=0),
            Q(planned_quantity__isnull=True) | Q(planned_quantity=0)
        )[:limit]
        
        self.stdout.write(f'找到 {problem_orders.count()} 個可能有問題的工單')
        
        if problem_orders.count() == 0:
            # 如果沒有明顯問題的工單，檢查其他可能的原因
            self.stdout.write('檢查其他可能的問題...')
            
            # 檢查沒有完工時間的工單
            no_completion = queryset.filter(completed_at__isnull=True)[:limit]
            if no_completion.exists():
                self.stdout.write(f'找到 {no_completion.count()} 個沒有完工時間的工單')
                for order in no_completion:
                    self.stdout.write(f'  - {order.order_number} ({order.company_code})')
            
            # 檢查沒有開始時間的工單
            no_start = queryset.filter(started_at__isnull=True)[:limit]
            if no_start.exists():
                self.stdout.write(f'找到 {no_start.count()} 個沒有開始時間的工單')
                for order in no_start:
                    self.stdout.write(f'  - {order.order_number} ({order.company_code})')
        
        # 嘗試重新分析這些工單
        success_count = 0
        error_count = 0
        
        for order in problem_orders:
            self.stdout.write(f'處理工單: {order.order_number} ({order.company_code})')
            
            if not dry_run:
                result = WorkOrderAnalysisService.analyze_completed_workorder(
                    order.order_number,
                    order.company_code,
                    order.product_code,
                    force=True
                )
                
                if result['success']:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ 分析成功')
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ 分析失敗: {result["error"]}')
                    )
            else:
                self.stdout.write(f'  試運行: 將分析工單 {order.order_number}')
        
        self.stdout.write(
            self.style.SUCCESS(f'重新分析完成 - 成功: {success_count}, 失敗: {error_count}')
        )
