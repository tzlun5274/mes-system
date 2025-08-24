"""
RD樣品工單建立管理命令
用於測試和手動建立RD樣品工單
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workorder.fill_work.models import FillWork
from workorder.fill_work.services import RDSampleWorkOrderService
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch


class Command(BaseCommand):
    help = '建立RD樣品工單和派工單'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fill-work-id',
            type=int,
            help='指定填報記錄ID，只處理該記錄'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            default='10',
            help='公司代號（預設：10，耀儀科技）'
        )
        parser.add_argument(
            '--product-id',
            type=str,
            default='PFP-CCT',
            help='產品編號（預設：PFP-CCT）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際建立資料'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制建立，即使工單已存在'
        )

    def handle(self, *args, **options):
        fill_work_id = options.get('fill_work_id')
        company_code = options.get('company_code')
        product_id = options.get('product_id')
        dry_run = options.get('dry_run')
        force = options.get('force')

        self.stdout.write(
            self.style.SUCCESS(f'開始處理RD樣品工單建立...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際建立資料')
            )

        try:
            if fill_work_id:
                # 處理指定ID的填報記錄
                self.process_specific_fill_work(fill_work_id, dry_run, force)
            else:
                # 處理所有RD樣品記錄
                self.process_all_rd_samples(company_code, product_id, dry_run, force)

        except Exception as e:
            raise CommandError(f'處理失敗: {str(e)}')

    def process_specific_fill_work(self, fill_work_id, dry_run, force):
        """處理指定ID的填報記錄"""
        try:
            fill_work = FillWork.objects.get(id=fill_work_id)
            self.stdout.write(f'處理填報記錄 ID: {fill_work_id}')
            
            # 檢查是否為RD樣品記錄
            if not RDSampleWorkOrderService.is_rd_sample_record(fill_work):
                self.stdout.write(
                    self.style.WARNING(f'填報記錄 {fill_work_id} 不是RD樣品記錄')
                )
                return

            self.process_rd_sample_record(fill_work, dry_run, force)

        except FillWork.DoesNotExist:
            raise CommandError(f'找不到填報記錄 ID: {fill_work_id}')

    def process_all_rd_samples(self, company_code, product_id, dry_run, force):
        """處理所有RD樣品記錄"""
        # 查找所有RD樣品相關的填報記錄
        rd_records = FillWork.objects.filter(
            workorder__icontains='RD樣品',
            approval_status='approved'
        )

        if not rd_records.exists():
            self.stdout.write(
                self.style.WARNING('沒有找到已核准的RD樣品填報記錄')
            )
            return

        self.stdout.write(f'找到 {rd_records.count()} 筆RD樣品填報記錄')

        for record in rd_records:
            self.process_rd_sample_record(record, dry_run, force)

    def process_rd_sample_record(self, fill_work, dry_run, force):
        """處理單筆RD樣品記錄"""
        self.stdout.write(f'處理記錄: {fill_work.id} - {fill_work.workorder} - {fill_work.product_id}')

        try:
            # 查找或建立工單
            workorder, workorder_created = self.find_or_create_workorder(
                fill_work, dry_run, force
            )

            if workorder_created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 建立工單: {workorder.order_number}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ 工單已存在: {workorder.order_number}')
                )

            # 查找或建立派工單
            dispatch, dispatch_created = self.find_or_create_dispatch(
                workorder, fill_work, dry_run, force
            )

            if dispatch_created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 建立派工單: {dispatch.order_number}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ 派工單已存在: {dispatch.order_number}')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ 處理失敗: {str(e)}')
            )

    def find_or_create_workorder(self, fill_work, dry_run, force):
        """查找或建立工單"""
        company_code = fill_work.company_code or '10'
        # 直接使用 workorder 欄位的內容作為工單號碼
        rd_workorder_number = fill_work.workorder
        product_code = fill_work.product_id

        # 查找現有工單
        existing_workorder = WorkOrder.objects.filter(
            company_code=company_code,
            order_number=rd_workorder_number,
            product_code=product_code
        ).first()

        if existing_workorder and not force:
            return existing_workorder, False

        if dry_run:
            self.stdout.write(f'[試運行] 將建立工單: {rd_workorder_number}')
            return None, True

        # 建立新工單
        with transaction.atomic():
            new_workorder = WorkOrder.objects.create(
                company_code=company_code,
                order_number=rd_workorder_number,
                product_code=product_code,
                quantity=fill_work.planned_quantity or 0,
                status='in_progress',  # RD樣品直接設為生產中狀態
                order_source='mes',
                created_at=timezone.now()
            )
            return new_workorder, True

    def find_or_create_dispatch(self, workorder, fill_work, dry_run, force):
        """查找或建立派工單"""
        # 查找現有派工單
        existing_dispatch = WorkOrderDispatch.objects.filter(
            company_code=workorder.company_code,
            order_number=workorder.order_number,
            product_code=workorder.product_code
        ).first()

        if existing_dispatch and not force:
            return existing_dispatch, False

        if dry_run:
            self.stdout.write(f'[試運行] 將建立派工單: {workorder.order_number}')
            return None, True

        # 建立新派工單
        with transaction.atomic():
            new_dispatch = WorkOrderDispatch.objects.create(
                company_code=workorder.company_code,
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                product_name=f"RD樣品-{workorder.product_code}",
                planned_quantity=workorder.quantity,
                status='in_production',  # 直接設為生產中
                dispatch_date=fill_work.work_date,
                assigned_operator=fill_work.operator,
                assigned_equipment=fill_work.equipment,
                process_name='',  # RD樣品不設定預定工序
                notes=f"RD樣品自動建立 - 建立時間: {timezone.now()} - 注意：RD樣品無預定工序流程",
                created_by='system'
            )
            return new_dispatch, True 