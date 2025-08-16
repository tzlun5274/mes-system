"""
清理測試資料管理命令
移除所有測試用的假資料，保持系統資料的純淨
"""

from django.core.management.base import BaseCommand
from workorder.models import WorkOrder, CompletedWorkOrder
from workorder.fill_work.models import FillWork
from workorder.models import WorkOrderProductionDetail
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理測試資料 - 移除所有測試用的假資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只檢查不執行實際刪除'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制刪除，不詢問確認'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        force = options.get('force')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 乾跑模式 ==='))
        
        # 定義測試資料的識別規則
        test_patterns = [
            'RD樣品-',  # RD樣品開頭的工單
            'TEST-',    # TEST開頭的工單
            '測試-',     # 測試開頭的工單
        ]
        
        self.stdout.write("開始清理測試資料...")
        
        # 1. 清理已完工工單中的測試資料
        self._cleanup_completed_workorders(test_patterns, dry_run, force)
        
        # 2. 清理生產中工單中的測試資料
        self._cleanup_workorders(test_patterns, dry_run, force)
        
        # 3. 清理填報記錄中的測試資料
        self._cleanup_fill_works(test_patterns, dry_run, force)
        
        # 4. 清理工序記錄中的測試資料
        self._cleanup_production_details(test_patterns, dry_run, force)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("注意：此為乾跑模式，未進行實際刪除")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("測試資料清理完成！")
            )

    def _cleanup_completed_workorders(self, test_patterns, dry_run, force):
        """清理已完工工單中的測試資料"""
        self.stdout.write("\n檢查已完工工單中的測試資料...")
        
        test_completed_workorders = []
        for pattern in test_patterns:
            test_completed_workorders.extend(
                CompletedWorkOrder.objects.filter(order_number__startswith=pattern)
            )
        
        if test_completed_workorders:
            self.stdout.write(f"找到 {len(test_completed_workorders)} 個測試已完工工單：")
            for wo in test_completed_workorders:
                self.stdout.write(f"  - {wo.order_number} ({wo.company_name})")
            
            if not dry_run:
                if force or self._confirm_deletion("已完工工單"):
                    deleted_count = 0
                    for wo in test_completed_workorders:
                        try:
                            wo.delete()
                            deleted_count += 1
                            self.stdout.write(f"已刪除：{wo.order_number}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"刪除 {wo.order_number} 失敗：{str(e)}")
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"成功刪除 {deleted_count} 個測試已完工工單")
                    )
        else:
            self.stdout.write("未找到測試已完工工單")

    def _cleanup_workorders(self, test_patterns, dry_run, force):
        """清理生產中工單中的測試資料"""
        self.stdout.write("\n檢查生產中工單中的測試資料...")
        
        test_workorders = []
        for pattern in test_patterns:
            test_workorders.extend(
                WorkOrder.objects.filter(order_number__startswith=pattern)
            )
        
        if test_workorders:
            self.stdout.write(f"找到 {len(test_workorders)} 個測試工單：")
            for wo in test_workorders:
                self.stdout.write(f"  - {wo.order_number} ({wo.company_code}) - 狀態：{wo.status}")
            
            if not dry_run:
                if force or self._confirm_deletion("生產中工單"):
                    deleted_count = 0
                    for wo in test_workorders:
                        try:
                            wo.delete()
                            deleted_count += 1
                            self.stdout.write(f"已刪除：{wo.order_number}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"刪除 {wo.order_number} 失敗：{str(e)}")
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"成功刪除 {deleted_count} 個測試工單")
                    )
        else:
            self.stdout.write("未找到測試工單")

    def _cleanup_fill_works(self, test_patterns, dry_run, force):
        """清理填報記錄中的測試資料"""
        self.stdout.write("\n檢查填報記錄中的測試資料...")
        
        test_fill_works = []
        for pattern in test_patterns:
            test_fill_works.extend(
                FillWork.objects.filter(workorder__startswith=pattern)
            )
        
        if test_fill_works:
            self.stdout.write(f"找到 {len(test_fill_works)} 個測試填報記錄：")
            for fw in test_fill_works[:10]:  # 只顯示前10個
                self.stdout.write(f"  - 工單：{fw.workorder}, 工序：{fw.process}, 數量：{fw.work_quantity}")
            
            if len(test_fill_works) > 10:
                self.stdout.write(f"  ... 還有 {len(test_fill_works) - 10} 個記錄")
            
            if not dry_run:
                if force or self._confirm_deletion("填報記錄"):
                    deleted_count = 0
                    for fw in test_fill_works:
                        try:
                            fw.delete()
                            deleted_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"刪除填報記錄失敗：{str(e)}")
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"成功刪除 {deleted_count} 個測試填報記錄")
                    )
        else:
            self.stdout.write("未找到測試填報記錄")

    def _cleanup_production_details(self, test_patterns, dry_run, force):
        """清理工序記錄中的測試資料"""
        self.stdout.write("\n檢查工序記錄中的測試資料...")
        
        # 先找到測試工單的ID
        test_workorder_ids = []
        for pattern in test_patterns:
            test_workorder_ids.extend(
                WorkOrder.objects.filter(order_number__startswith=pattern).values_list('id', flat=True)
            )
        
        if test_workorder_ids:
            test_production_details = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder_id__in=test_workorder_ids
            )
            
            if test_production_details:
                self.stdout.write(f"找到 {test_production_details.count()} 個測試工序記錄")
                
                if not dry_run:
                    if force or self._confirm_deletion("工序記錄"):
                        deleted_count = 0
                        for pd in test_production_details:
                            try:
                                pd.delete()
                                deleted_count += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f"刪除工序記錄失敗：{str(e)}")
                                )
                        
                        self.stdout.write(
                            self.style.SUCCESS(f"成功刪除 {deleted_count} 個測試工序記錄")
                        )
            else:
                self.stdout.write("未找到測試工序記錄")
        else:
            self.stdout.write("未找到測試工序記錄")

    def _confirm_deletion(self, data_type):
        """確認刪除操作"""
        response = input(f"\n確定要刪除所有測試{data_type}嗎？(y/N): ")
        return response.lower() in ['y', 'yes', '是'] 