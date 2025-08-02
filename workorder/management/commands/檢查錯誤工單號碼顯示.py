"""
檢查錯誤工單號碼顯示管理命令
檢查所有可能顯示錯誤工單號碼的地方，包括報工紀錄、生產明細等
"""

from django.core.management.base import BaseCommand
from workorder.models import WorkOrder, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '檢查所有可能顯示錯誤工單號碼的地方'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('開始檢查錯誤工單號碼顯示...')
        )
        
        try:
            self._check_workorder_numbers()
            self._check_production_details()
            self._check_operator_reports()
            self._check_smt_reports()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'檢查過程中發生錯誤: {str(e)}')
            )
            logger.error(f'檢查錯誤工單號碼顯示失敗: {str(e)}')
    
    def _check_workorder_numbers(self):
        """檢查工單號碼"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('📊 檢查工單號碼'))
        self.stdout.write('='*60)
        
        # 檢查包含空格的工單號碼
        workorders_with_spaces = WorkOrder.objects.filter(
            order_number__contains=' '
        )
        
        self.stdout.write(f'包含空格的工單號碼: {workorders_with_spaces.count()} 個')
        for workorder in workorders_with_spaces:
            self.stdout.write(f'  ID: {workorder.id}, 工單號: "{workorder.order_number}"')
        
        # 檢查包含特殊字符的工單號碼
        workorders_with_special = WorkOrder.objects.filter(
            order_number__regex=r'[^\w\-]'
        )
        
        self.stdout.write(f'\n包含特殊字符的工單號碼: {workorders_with_special.count()} 個')
        for workorder in workorders_with_special:
            self.stdout.write(f'  ID: {workorder.id}, 工單號: "{workorder.order_number}"')
    
    def _check_production_details(self):
        """檢查生產中工單明細"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('📊 檢查生產中工單明細'))
        self.stdout.write('='*60)
        
        # 檢查生產明細中關聯到錯誤工單號碼的記錄
        production_details = WorkOrderProductionDetail.objects.filter(
            workorder_production__workorder__order_number__contains=' '
        )
        
        self.stdout.write(f'關聯到錯誤工單號碼的生產明細: {production_details.count()} 筆')
        for detail in production_details:
            workorder = detail.workorder_production.workorder
            self.stdout.write(f'  明細ID: {detail.id}, 工單號: "{workorder.order_number}", 工序: {detail.process_name}')
    
    def _check_operator_reports(self):
        """檢查作業員報工紀錄"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('📊 檢查作業員報工紀錄'))
        self.stdout.write('='*60)
        
        # 檢查作業員報工中關聯到錯誤工單號碼的記錄
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder__order_number__contains=' '
        )
        
        self.stdout.write(f'關聯到錯誤工單號碼的作業員報工: {operator_reports.count()} 筆')
        for report in operator_reports:
            self.stdout.write(f'  報工ID: {report.id}, 工單號: "{report.workorder.order_number}", 作業員: {report.operator.name if report.operator else "無"}, 工序: {report.process.name if report.process else "無"}')
        
        # 檢查特定報工紀錄
        try:
            specific_report = OperatorSupplementReport.objects.get(id=20943)
            self.stdout.write(f'\n特定報工紀錄 (ID: 20943):')
            self.stdout.write(f'  工單號: "{specific_report.workorder.order_number if specific_report.workorder else "無工單"}"')
            self.stdout.write(f'  工單ID: {specific_report.workorder.id if specific_report.workorder else "無工單"}')
            self.stdout.write(f'  作業員: {specific_report.operator.name if specific_report.operator else "無作業員"}')
            self.stdout.write(f'  工序: {specific_report.process.name if specific_report.process else "無工序"}')
        except OperatorSupplementReport.DoesNotExist:
            self.stdout.write(f'\n特定報工紀錄 (ID: 20943) 不存在')
    
    def _check_smt_reports(self):
        """檢查SMT報工紀錄"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('📊 檢查SMT報工紀錄'))
        self.stdout.write('='*60)
        
        # 檢查SMT報工中關聯到錯誤工單號碼的記錄
        smt_reports = SMTProductionReport.objects.filter(
            workorder__order_number__contains=' '
        )
        
        self.stdout.write(f'關聯到錯誤工單號碼的SMT報工: {smt_reports.count()} 筆')
        for report in smt_reports:
            self.stdout.write(f'  報工ID: {report.id}, 工單號: "{report.workorder.order_number}", 設備: {report.equipment.name if report.equipment else "無"}')
        
        # 檢查所有包含空格的工單號碼
        all_workorders_with_spaces = WorkOrder.objects.filter(
            order_number__contains=' '
        )
        
        if all_workorders_with_spaces.count() > 0:
            self.stdout.write(f'\n⚠️  發現 {all_workorders_with_spaces.count()} 個包含空格的工單號碼:')
            for workorder in all_workorders_with_spaces:
                self.stdout.write(f'  ID: {workorder.id}, 工單號: "{workorder.order_number}"')
        else:
            self.stdout.write(f'\n✅ 沒有發現包含空格的工單號碼')
        
        self.stdout.write(f'\n檢查完成！') 