"""
Auto Completion Check Management Command
檢查生產中工單詳情資料表中出貨包裝工序的合格品累積數量，達到生產數量時轉寫到已完工資料表
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder, WorkOrderProductionDetail, CompletedWorkOrder
from workorder.models import CompletedProductionReport
import logging
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Auto Completion Check - 完工判斷轉寫已完工'

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
        
        # 記錄開始執行
        logger.info(f'開始執行完工判斷轉寫命令 - 乾跑模式: {dry_run}, 指定工單ID: {workorder_id}')
        self.stdout.write(f'開始執行完工判斷轉寫命令 - 乾跑模式: {dry_run}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('執行乾跑模式，不會進行實際操作')
            )
        
        try:
            if workorder_id:
                # 檢查特定工單
                logger.info(f'檢查特定工單 ID: {workorder_id}')
                self._check_specific_workorder(workorder_id, dry_run)
            else:
                # 檢查所有生產中工單
                logger.info('檢查所有生產中工單')
                self._check_all_production_workorders(dry_run)
                
        except Exception as e:
            error_msg = f'執行過程中發生錯誤: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(f'完工判斷轉寫命令執行錯誤: {str(e)}')
            raise
        finally:
            logger.info('完工判斷轉寫命令執行完成')
    
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
            
            self.stdout.write(f'  生產數量: {workorder.quantity}')
            self.stdout.write(f'  出貨包裝合格品累積數量: {packaging_quantity}')
            
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
        檢查所有生產中工單詳情資料表中的工單
        
        Args:
            dry_run: 是否為乾跑模式
        """
        # 獲取生產中工單詳情資料表裡面的所有唯一工單
        from django.db.models import Q
        production_workorders = WorkOrderProductionDetail.objects.values_list(
            'workorder_production__workorder', flat=True
        ).distinct()
        all_workorders = WorkOrder.objects.filter(id__in=production_workorders)
        
        logger.info(f'找到 {all_workorders.count()} 個需要檢查的工單')
        self.stdout.write(f'找到 {all_workorders.count()} 個工單')
        
        if all_workorders.count() == 0:
            logger.info('沒有找到需要檢查的工單，執行完成')
            self.stdout.write(self.style.WARNING('沒有找到需要檢查的工單'))
            return
        
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
                        f'  出貨包裝合格品累積數量: {packaging_quantity}/{workorder.quantity}'
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'檢查工單 {workorder.order_number} 時發生錯誤: {str(e)}')
                )
        
        # 輸出統計結果
        logger.info(f'完工判斷轉寫結果統計 - 總檢查工單數: {all_workorders.count()}, 成功轉寫數: {completed_count}, 錯誤數: {error_count}')
        
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
        獲取工單的出貨包裝累積數量（良品+不良品，從生產中工單詳情資料表）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝累積總數量（良品+不良品）
        """
        try:
            # 從生產中工單詳情資料表查詢出貨包裝的報工記錄
            packaging_reports = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder,
                process_name="出貨包裝"
            )
            
            # 計算良品累積數量
            good_quantity = packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品累積數量
            defect_quantity = packaging_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            # 記錄日誌
            logger.info(f"工單 {workorder.order_number} 出貨包裝累積數量: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取工單 {workorder.order_number} 出貨包裝累積數量時發生錯誤: {str(e)}")
            return 0
    
    def _transfer_to_completed(self, workorder):
        """
        將已完工的工單資料轉寫到已完工工單資料表
        
        正確的資料流程：
        1. 報工資料表 (OperatorSupplementReport, SMTSupplementReport) - 永遠保留原始記錄
        2. 生產中資料表 (WorkOrderProductionDetail) - 轉移到已完工資料表
        3. 工單記錄 (WorkOrder) - 狀態改為已完工，不刪除記錄
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            bool: 是否成功轉寫
        """
        logger.info(f"開始轉寫工單 {workorder.order_number} 到已完工資料表")
        try:
            with transaction.atomic():
                # 檢查是否已經轉寫過，如果已轉寫則刪除舊記錄重新轉寫
                existing_completed = CompletedWorkOrder.objects.filter(original_workorder_id=workorder.id).first()
                if existing_completed:
                    logger.warning(f"工單 {workorder.order_number} 已經轉寫過，刪除舊記錄重新轉寫")
                    existing_completed.delete()
                
                # 獲取公司名稱
                company_name = ''
                try:
                    from erp_integration.models import CompanyConfig
                    company_config = CompanyConfig.objects.filter(
                        company_code=workorder.company_code
                    ).first()
                    if company_config:
                        company_name = company_config.company_name
                except Exception:
                    pass
                
                # 建立已完工工單記錄
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder.id,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code,
                    company_name=company_name,
                    planned_quantity=workorder.quantity,
                    completed_quantity=workorder.quantity,  # 完工數量等於計劃數量
                    status='completed',
                    created_at=workorder.created_at,
                    started_at=workorder.start_time,
                    completed_at=timezone.now(),
                )
                
                # 轉寫生產中工單詳情資料表的報工記錄
                self._transfer_production_reports(workorder, completed_workorder)
                
                # 修復BUG：不刪除工單記錄，而是將狀態改為已完工
                # 這樣可以保留所有報工記錄的工單關聯，確保已審核報工列表能正確顯示
                workorder.status = 'completed'
                workorder.completed_at = timezone.now()
                workorder.save()
                
                # 刪除WorkOrderProduction記錄和相關的WorkOrderProductionDetail記錄
                from workorder.models import WorkOrderProduction, WorkOrderProductionDetail
                production_record = WorkOrderProduction.objects.filter(workorder=workorder).first()
                if production_record:
                    # 先刪除相關的WorkOrderProductionDetail記錄
                    detail_count = WorkOrderProductionDetail.objects.filter(
                        workorder_production=production_record
                    ).count()
                    WorkOrderProductionDetail.objects.filter(
                        workorder_production=production_record
                    ).delete()
                    logger.info(f"刪除工單 {workorder.order_number} 的 {detail_count} 筆生產報工明細記錄")
                    
                    # 再刪除WorkOrderProduction記錄
                    production_record.delete()
                    logger.info(f"刪除工單 {workorder.order_number} 的生產記錄")
                
                logger.info(f"工單 {workorder.order_number} 成功轉寫到已完工資料表並刪除生產記錄")
                return True
                
        except Exception as e:
            logger.error(f"轉寫工單 {workorder.order_number} 時發生錯誤: {str(e)}")
            return False
    
    def _transfer_production_reports(self, workorder, completed_workorder):
        """
        轉寫生產中工單詳情資料表的報工記錄到已完工資料表
        
        注意：只轉移 WorkOrderProductionDetail 記錄，不影響原始報工資料表
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        # 轉寫生產中工單詳情資料表的報工記錄
        for report in WorkOrderProductionDetail.objects.filter(
            workorder_production__workorder=workorder
        ):
            # 處理時間欄位轉換
            start_datetime = None
            end_datetime = None
            if report.start_time and report.report_date:
                start_datetime = timezone.make_aware(
                    datetime.combine(report.report_date, report.start_time)
                )
            if report.end_time and report.report_date:
                end_datetime = timezone.make_aware(
                    datetime.combine(report.report_date, report.end_time)
                )
            
            CompletedProductionReport.objects.create(
                completed_workorder=completed_workorder,
                report_date=report.report_date,
                process_name=report.process_name,
                operator=report.operator or '-',
                equipment=report.equipment or '-',
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                work_hours=float(report.work_hours or 0),
                overtime_hours=float(report.overtime_hours or 0),
                start_time=start_datetime,
                end_time=end_datetime,
                report_source=report.report_source,
                report_type=report.report_source,
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                approval_status=report.approval_status,
                approved_by=report.approved_by,
                approved_at=report.approved_at,
            ) 