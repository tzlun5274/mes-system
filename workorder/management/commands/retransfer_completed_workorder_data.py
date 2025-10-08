"""
重新轉移已完工工單資料的管理指令
用於修復已完工工單工序表資料不完整的問題
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess
from workorder.fill_work.models import FillWork


class Command(BaseCommand):
    help = '重新轉移已完工工單資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=str,
            help='指定要重新轉移的工單編號'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            help='指定要重新轉移的公司代號'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='重新轉移所有已完工工單資料'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行，不詢問確認'
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        company_code = options.get('company_code')
        transfer_all = options.get('all', False)
        force = options.get('force', False)

        try:
            with transaction.atomic():
                if transfer_all:
                    # 重新轉移所有已完工工單資料
                    if not force:
                        confirm = input('⚠️  警告：您即將重新轉移所有已完工工單資料！\n'
                                      '此操作會覆蓋現有的工序資料，確定要繼續嗎？(yes/no): ')
                        if confirm.lower() != 'yes':
                            self.stdout.write(self.style.WARNING('操作已取消'))
                            return

                    completed_workorders = CompletedWorkOrder.objects.all()
                    self.stdout.write(f'找到 {completed_workorders.count()} 筆已完工工單')
                    
                    success_count = 0
                    error_count = 0
                    
                    for completed_workorder in completed_workorders:
                        try:
                            self._retransfer_workorder_data(completed_workorder)
                            success_count += 1
                            self.stdout.write(f'✅ 工單 {completed_workorder.order_number} 重新轉移成功')
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f'❌ 工單 {completed_workorder.order_number} 重新轉移失敗: {str(e)}'))
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 重新轉移完成，成功: {success_count}，失敗: {error_count}')
                    )

                elif workorder_id and company_code:
                    # 重新轉移指定工單的資料
                    completed_workorder = CompletedWorkOrder.objects.filter(
                        order_number=workorder_id,
                        company_code=company_code
                    ).first()
                    
                    if not completed_workorder:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到工單 {workorder_id} (公司: {company_code})')
                        )
                        return

                    self._retransfer_workorder_data(completed_workorder)
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 工單 {workorder_id} (公司: {company_code}) 重新轉移成功')
                    )

                elif workorder_id:
                    # 重新轉移指定工單的所有資料
                    completed_workorders = CompletedWorkOrder.objects.filter(
                        order_number=workorder_id
                    )
                    
                    if not completed_workorders.exists():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到工單 {workorder_id}')
                        )
                        return

                    for completed_workorder in completed_workorders:
                        self._retransfer_workorder_data(completed_workorder)
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ 工單 {workorder_id} (公司: {completed_workorder.company_code}) 重新轉移成功')
                        )

                elif company_code:
                    # 重新轉移指定公司的所有資料
                    completed_workorders = CompletedWorkOrder.objects.filter(
                        company_code=company_code
                    )
                    
                    if not completed_workorders.exists():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到公司 {company_code} 的已完工工單')
                        )
                        return

                    for completed_workorder in completed_workorders:
                        self._retransfer_workorder_data(completed_workorder)
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ 工單 {completed_workorder.order_number} 重新轉移成功')
                        )

                else:
                    # 顯示使用說明
                    self.stdout.write(self.style.ERROR('❌ 請指定重新轉移條件'))
                    self.stdout.write('')
                    self.stdout.write('使用方式：')
                    self.stdout.write('  python manage.py retransfer_completed_workorder_data --workorder-id 331-25815001 --company-code 10')
                    self.stdout.write('  python manage.py retransfer_completed_workorder_data --workorder-id 331-25815001')
                    self.stdout.write('  python manage.py retransfer_completed_workorder_data --company-code 10')
                    self.stdout.write('  python manage.py retransfer_completed_workorder_data --all --force')
                    self.stdout.write('')
                    self.stdout.write('參數說明：')
                    self.stdout.write('  --workorder-id: 指定工單編號')
                    self.stdout.write('  --company-code: 指定公司代號')
                    self.stdout.write('  --all: 重新轉移所有已完工工單資料')
                    self.stdout.write('  --force: 強制執行，不詢問確認')

        except Exception as e:
            raise CommandError(f'重新轉移已完工工單資料時發生錯誤: {str(e)}')

    def _retransfer_workorder_data(self, completed_workorder):
        """
        重新轉移單一工單的資料
        
        Args:
            completed_workorder: 已完工工單物件
        """
        # 刪除現有的工序記錄
        CompletedWorkOrderProcess.objects.filter(
            completed_workorder_id=completed_workorder.id
        ).delete()
        
        # 從填報記錄重新統計並建立工序記錄
        fill_work_records = FillWork.objects.filter(
            workorder=completed_workorder.order_number,
            product_id=completed_workorder.product_code,
            approval_status='approved'
        )
        
        if not fill_work_records.exists():
            self.stdout.write(f'⚠️  工單 {completed_workorder.order_number} 沒有找到填報記錄')
            return
        
        # 按工序分組統計
        process_data = {}
        for record in fill_work_records:
            process_name = record.operation or '未知工序'
            if process_name not in process_data:
                process_data[process_name] = {
                    'total_work_hours': 0,
                    'total_overtime_hours': 0,
                    'total_good_quantity': 0,
                    'total_defect_quantity': 0,
                    'report_count': 0,
                    'operators': set(),
                    'equipment': set(),
                    'process_order': len(process_data) + 1
                }
            
            process_data[process_name]['total_work_hours'] += float(record.work_hours_calculated or 0)
            process_data[process_name]['total_overtime_hours'] += float(record.overtime_hours_calculated or 0)
            process_data[process_name]['total_good_quantity'] += int(record.work_quantity or 0)
            process_data[process_name]['total_defect_quantity'] += int(record.defect_quantity or 0)
            process_data[process_name]['report_count'] += 1
            
            if record.operator:
                process_data[process_name]['operators'].add(record.operator)
            if record.equipment:
                process_data[process_name]['equipment'].add(record.equipment)
        
        # 建立新的工序記錄
        for process_name, data in process_data.items():
            CompletedWorkOrderProcess.objects.create(
                completed_workorder_id=completed_workorder.id,
                process_name=process_name,
                process_order=data['process_order'],
                planned_quantity=completed_workorder.planned_quantity,
                completed_quantity=data['total_good_quantity'],
                status='completed',
                assigned_operator='',
                assigned_equipment='',
                total_work_hours=data['total_work_hours'],
                total_good_quantity=data['total_good_quantity'],
                total_defect_quantity=data['total_defect_quantity'],
                report_count=data['report_count'],
                operators=list(data['operators']),
                equipment=list(data['equipment'])
            )
