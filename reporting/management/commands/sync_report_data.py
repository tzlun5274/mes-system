"""
同步報表資料管理命令
將填報資料同步到報表專用資料表
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from reporting.models import WorkOrderReportData
from workorder.fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步填報資料到報表專用資料表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='指定公司代號，不指定則同步所有公司',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步所有資料',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['approved', 'pending', 'all'],
            default='approved',
            help='同步狀態：approved(已核准)、pending(待核准)、all(全部)',
        )

    def handle(self, *args, **options):
        company_code = options.get('company')
        force = options.get('force')
        status = options.get('status')
        
        self.stdout.write(
            self.style.SUCCESS('開始同步報表資料...')
        )
        
        try:
            # 同步填報資料
            self.stdout.write(self.style.SUCCESS('開始同步填報資料...'))
            
            # 根據狀態選擇同步範圍
            if status == 'approved':
                fill_works = FillWork.objects.filter(approval_status='approved')
                status_text = '已核准'
            elif status == 'pending':
                fill_works = FillWork.objects.filter(approval_status='pending')
                status_text = '待核准'
            else:  # all
                fill_works = FillWork.objects.all()
                status_text = '全部'
            
            if company_code:
                fill_works = fill_works.filter(company_name=company_code)
            
            if not force:
                # 只同步尚未同步的資料
                synced_workorders = WorkOrderReportData.objects.values_list('workorder_id', flat=True).distinct()
                fill_works = fill_works.exclude(workorder__in=synced_workorders)
            
            fill_works_count = fill_works.count()
            self.stdout.write(f'找到 {fill_works_count} 筆{status_text}的填報資料')
            
            # 同步填報資料
            fill_works_synced = 0
            fill_works_errors = 0
            
            for fill_work in fill_works:
                try:
                    WorkOrderReportData.create_from_fill_work(fill_work)
                    fill_works_synced += 1
                    
                    if fill_works_synced % 100 == 0:
                        self.stdout.write(f'已同步 {fill_works_synced} 筆填報資料...')
                        
                except Exception as e:
                    fill_works_errors += 1
                    logger.error(f"同步填報資料失敗: {fill_work.id} - {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f'同步填報失敗: 工單 {fill_work.workorder} - {str(e)}')
                    )
            
            # 同步現場報工資料
            self.stdout.write(self.style.SUCCESS('開始同步現場報工資料...'))
            
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_reports = OnsiteReport.objects.filter(status='completed')
            if company_code:
                onsite_reports = onsite_reports.filter(company_code=company_code)
            
            if not force:
                # 只同步尚未同步的資料
                synced_onsite_workorders = WorkOrderReportData.objects.values_list('workorder_id', flat=True).distinct()
                onsite_reports = onsite_reports.exclude(workorder__in=synced_onsite_workorders)
            
            onsite_reports_count = onsite_reports.count()
            self.stdout.write(f'找到 {onsite_reports_count} 筆已完成的現場報工資料')
            
            # 同步現場報工資料
            onsite_synced = 0
            onsite_errors = 0
            
            for onsite_report in onsite_reports:
                try:
                    WorkOrderReportData.create_from_onsite_report(onsite_report)
                    onsite_synced += 1
                    
                    if onsite_synced % 100 == 0:
                        self.stdout.write(f'已同步 {onsite_synced} 筆現場報工資料...')
                        
                except Exception as e:
                    onsite_errors += 1
                    logger.error(f"同步現場報工資料失敗: {onsite_report.id} - {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f'同步現場報工失敗: 工單 {onsite_report.workorder} - {str(e)}')
                    )
            
            # 輸出總結果
            total_synced = fill_works_synced + onsite_synced
            total_errors = fill_works_errors + onsite_errors
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'同步完成！\n'
                    f'填報資料：成功 {fill_works_synced} 筆，失敗 {fill_works_errors} 筆\n'
                    f'現場報工：成功 {onsite_synced} 筆，失敗 {onsite_errors} 筆\n'
                    f'總計：成功 {total_synced} 筆，失敗 {total_errors} 筆'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'同步過程發生錯誤: {str(e)}')
            )
            logger.error(f"同步報表資料失敗: {str(e)}") 