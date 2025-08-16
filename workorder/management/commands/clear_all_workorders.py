"""
管理命令：清除所有工單
安全地刪除所有工單資料，包括相關的工序和報工記錄
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder
from workorder.workorder_erp.models import PrdMKOrdMain, PrdMkOrdMats, CompanyOrder
from workorder.fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清除所有工單資料，包括相關的工序和報工記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='確認執行刪除操作',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='在刪除前創建備份',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會刪除的資料數量',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('⚠️  警告：此操作將刪除所有工單資料！')
        )
        
        if not options['confirm'] and not options['dry_run']:
            self.stdout.write(
                self.style.ERROR('❌ 請使用 --confirm 參數確認執行刪除操作')
            )
            self.stdout.write('💡 建議先使用 --dry-run 查看會刪除的資料數量')
            return
        
        try:
            # 統計要刪除的資料
            workorder_count = WorkOrder.objects.count()
            fillwork_count = FillWork.objects.count()
            company_order_count = CompanyOrder.objects.count()
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.WARNING('📊 要刪除的資料統計'))
            self.stdout.write('='*60)
            self.stdout.write(f"工單數量: {workorder_count}")
            self.stdout.write(f"填報紀錄數量: {fillwork_count}")
            self.stdout.write(f"公司製令單數量: {company_order_count}")
            self.stdout.write(f"總計: {workorder_count + fillwork_count + company_order_count} 筆記錄")
            
            if options['dry_run']:
                self.stdout.write('\n✅ 乾跑模式完成，沒有實際刪除任何資料')
                return
            
            # 確認執行
            if not options['confirm']:
                self.stdout.write('\n❌ 請使用 --confirm 參數確認執行刪除操作')
                return
            
            # 創建備份
            if options['backup']:
                self._create_backup()
            
            # 執行刪除
            with transaction.atomic():
                self._delete_all_data()
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ 所有工單資料已成功刪除！'))
            self.stdout.write('='*60)
            self.stdout.write('💡 現在您可以重新匯入工單資料')
            
        except Exception as e:
            raise CommandError(f'刪除過程中發生錯誤: {e}')
    
    def _create_backup(self):
        """創建資料備份"""
        self.stdout.write('\n📦 正在創建資料備份...')
        
        try:
            from django.core import serializers
            import os
            from datetime import datetime
            
            # 創建備份目錄
            backup_dir = f'/var/www/mes/backups/workorder_clear_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.makedirs(backup_dir, exist_ok=True)
            
            # 備份工單資料
            workorders = WorkOrder.objects.all()
            with open(f'{backup_dir}/workorders.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', workorders, stream=f)
            
            # 備份填報紀錄
            fillworks = FillWork.objects.all()
            with open(f'{backup_dir}/fillworks.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', fillworks, stream=f)
            
            # 備份公司製令單
            company_orders = CompanyOrder.objects.all()
            with open(f'{backup_dir}/company_orders.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', company_orders, stream=f)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ 備份已創建到: {backup_dir}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 備份創建失敗: {e}')
            )
    
    def _delete_all_data(self):
        """刪除所有相關資料"""
        self.stdout.write('\n🗑️  正在刪除所有工單資料...')
        
        # 刪除填報紀錄
        fillwork_count = FillWork.objects.count()
        FillWork.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {fillwork_count} 筆填報紀錄")
        
        # 刪除公司製令單
        company_order_count = CompanyOrder.objects.count()
        CompanyOrder.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {company_order_count} 筆公司製令單")
        
        # 刪除工單
        workorder_count = WorkOrder.objects.count()
        WorkOrder.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {workorder_count} 筆工單")
        
        # 新增：刪除已完工工單相關資料
        from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport
        
        # 刪除已完工生產報工記錄
        completed_report_count = CompletedProductionReport.objects.count()
        CompletedProductionReport.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {completed_report_count} 筆已完工生產報工記錄")
        
        # 刪除已完工工單工序
        completed_process_count = CompletedWorkOrderProcess.objects.count()
        CompletedWorkOrderProcess.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {completed_process_count} 筆已完工工單工序")
        
        # 刪除已完工工單
        completed_workorder_count = CompletedWorkOrder.objects.count()
        CompletedWorkOrder.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {completed_workorder_count} 筆已完工工單")
        
        # 新增：刪除派工單相關資料
        from workorder.workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess
        
        # 刪除派工單工序
        dispatch_process_count = WorkOrderDispatchProcess.objects.count()
        WorkOrderDispatchProcess.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {dispatch_process_count} 筆派工單工序")
        
        # 刪除派工單
        dispatch_count = WorkOrderDispatch.objects.count()
        WorkOrderDispatch.objects.all().delete()
        self.stdout.write(f"✅ 已刪除 {dispatch_count} 筆派工單")
        
        # 清理相關的ERP資料（可選）
        self._clean_erp_data()
    
    def _clean_erp_data(self):
        """清理ERP相關資料"""
        try:
            # 刪除製令主檔
            mkord_main_count = PrdMKOrdMain.objects.count()
            PrdMKOrdMain.objects.all().delete()
            self.stdout.write(f"✅ 已刪除 {mkord_main_count} 筆製令主檔")
            
            # 刪除製令用料
            mkord_mats_count = PrdMkOrdMats.objects.count()
            PrdMkOrdMats.objects.all().delete()
            self.stdout.write(f"✅ 已刪除 {mkord_mats_count} 筆製令用料")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  ERP資料清理時發生錯誤: {e}')
            ) 