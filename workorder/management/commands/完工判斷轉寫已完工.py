"""
完工判斷轉寫已完工管理命令
檢查生產中工單的出貨包裝完工數量，達到目標數量時轉寫到已完工資料表
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder, WorkOrderProductionDetail, CompletedWorkOrder
from workorder.workorder_reporting.models import OperatorSupplementReport
from workorder.models import CompletedProductionReport
import logging
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '完工判斷轉寫已完工'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅檢查不執行實際操作',
        )
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定檢查特定工單ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workorder_id = options.get('workorder_id')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('執行乾跑模式，不會進行實際操作')
            )
        
        try:
            if workorder_id:
                # 檢查特定工單
                self._check_specific_workorder(workorder_id, dry_run)
            else:
                # 檢查所有生產中工單
                self._check_all_production_workorders(dry_run)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'執行過程中發生錯誤: {str(e)}')
            )
            logger.error(f'完工判斷轉寫命令執行錯誤: {str(e)}')
    
    def _check_specific_workorder(self, workorder_id, dry_run):
        """
        檢查特定工單
        
        Args:
            workorder_id: 工單ID
            dry_run: 是否為乾跑模式
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            self.stdout.write(f'檢查工單: {workorder.order_number}')
            
            # 只檢查出貨包裝完工數量
            packaging_quantity = self._get_packaging_quantity(workorder)
            
            self.stdout.write(f'  目標數量: {workorder.quantity}')
            self.stdout.write(f'  出貨包裝完工數量: {packaging_quantity}')
            
            if packaging_quantity >= workorder.quantity:
                self.stdout.write(
                    self.style.SUCCESS(f'  工單 {workorder.order_number} 已達到完工條件')
                )
                
                if not dry_run:
                    # 轉寫到已完工資料表
                    success = self._transfer_to_completed(workorder)
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f'  工單 {workorder.order_number} 已成功轉寫到已完工資料表')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  工單 {workorder.order_number} 轉寫失敗')
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  工單 {workorder.order_number} 尚未達到完工條件')
                )
                
        except WorkOrder.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'工單 ID {workorder_id} 不存在')
            )
    
    def _check_all_production_workorders(self, dry_run):
        """
        檢查所有工單
        
        Args:
            dry_run: 是否為乾跑模式
        """
        # 獲取所有工單（不限制狀態）
        all_workorders = WorkOrder.objects.all().select_related('production_record')
        
        self.stdout.write(f'找到 {all_workorders.count()} 個工單')
        
        completed_count = 0
        error_count = 0
        
        for workorder in all_workorders:
            try:
                self.stdout.write(f'檢查工單: {workorder.order_number}')
                
                # 只檢查出貨包裝完工數量
                packaging_quantity = self._get_packaging_quantity(workorder)
                
                if packaging_quantity >= workorder.quantity:
                    self.stdout.write(
                        self.style.SUCCESS(f'  工單 {workorder.order_number} 已達到完工條件')
                    )
                    
                    if not dry_run:
                        # 轉寫到已完工資料表
                        success = self._transfer_to_completed(workorder)
                        if success:
                            completed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  工單 {workorder.order_number} 已成功轉寫到已完工資料表')
                            )
                        else:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(f'  工單 {workorder.order_number} 轉寫失敗')
                            )
                else:
                    self.stdout.write(
                        f'  出貨包裝完工數量: {packaging_quantity}/{workorder.quantity}'
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'檢查工單 {workorder.order_number} 時發生錯誤: {str(e)}')
                )
        
        # 輸出統計結果
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('完工判斷轉寫結果統計:')
        self.stdout.write(f'  總檢查工單數: {all_workorders.count()}')
        self.stdout.write(f'  成功轉寫數: {completed_count}')
        self.stdout.write(f'  錯誤數: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('注意: 此為乾跑模式，未進行實際操作')
            )
    
    def _get_packaging_quantity(self, workorder):
        """
        獲取工單的出貨包裝完工數量（只計算良品數量，不包含不良品）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝完工總數量
        """
        try:
            # 從生產中資料表查詢出貨包裝的完工數量
            packaging_reports = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder,
                process_name="出貨包裝",
                report_source='operator_supplement'  # 作業員補登報工
            )
            
            # 計算總完工數量（只計算良品數量，不包含不良品）
            total_quantity = packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 記錄日誌
            logger.debug(f"工單 {workorder.order_number} 出貨包裝完工數量: {total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取工單 {workorder.order_number} 出貨包裝完工數量時發生錯誤: {str(e)}")
            return 0
    
    def _transfer_to_completed(self, workorder):
        """
        將已完工的工單資料轉寫到已完工工單資料表
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            bool: 是否成功轉寫
        """
        try:
            with transaction.atomic():
                # 檢查是否已經轉寫過
                if CompletedWorkOrder.objects.filter(original_workorder_id=workorder.id).exists():
                    logger.warning(f"工單 {workorder.order_number} 已經轉寫過")
                    return True
                
                # 建立已完工工單記錄
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder.id,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code,
                    planned_quantity=workorder.quantity,
                    completed_quantity=workorder.quantity,  # 完工數量等於計劃數量
                    status='completed',
                    created_at=workorder.created_at,
                    started_at=workorder.start_time,
                    completed_at=timezone.now(),
                )
                
                # 轉寫報工記錄
                self._transfer_production_reports(workorder, completed_workorder)
                
                # 刪除生產中的工單記錄
                workorder.delete()
                
                logger.info(f"工單 {workorder.order_number} 成功轉寫到已完工資料表")
                return True
                
        except Exception as e:
            logger.error(f"轉寫工單 {workorder.order_number} 時發生錯誤: {str(e)}")
            return False
    
    def _transfer_production_reports(self, workorder, completed_workorder):
        """
        轉寫報工記錄到已完工資料表
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        # 轉寫作業員報工記錄
        for report in OperatorSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ):
            # 處理時間欄位轉換
            start_datetime = None
            end_datetime = None
            if report.start_time and report.work_date:
                start_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.start_time)
                )
            if report.end_time and report.work_date:
                end_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.end_time)
                )
            
            CompletedProductionReport.objects.create(
                completed_workorder=completed_workorder,
                report_date=report.work_date,
                process_name=report.process.name if report.process else '-',
                operator=report.operator.name if report.operator else '-',
                equipment=report.equipment.name if report.equipment else '-',
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                work_hours=float(report.work_hours_calculated or 0),
                overtime_hours=float(report.overtime_hours_calculated or 0),
                start_time=start_datetime,
                end_time=end_datetime,
                report_source='作業員補登報工',
                report_type='operator',
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                approval_status=report.approval_status,
                approved_by=report.approved_by,
                approved_at=report.approved_at,
            ) 