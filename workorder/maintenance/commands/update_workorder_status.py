#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工單狀態自動更新管理命令
當有填報紀錄或現場報工紀錄時，自動將工單狀態從「待生產」轉為「生產中」
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder
from workorder.services.workorder_status_service import WorkOrderStatusService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '更新工單狀態：當有填報紀錄或現場報工紀錄時自動轉為生產中'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定工單ID進行更新',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只檢查不實際更新',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='詳細輸出模式',
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')

        if verbose:
            logger.setLevel(logging.DEBUG)

        if workorder_id:
            # 更新指定工單
            self.update_specific_workorder(workorder_id, dry_run)
        else:
            # 更新所有待生產工單
            self.update_all_pending_workorders(dry_run)

    def update_specific_workorder(self, workorder_id, dry_run):
        """更新指定工單狀態"""
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            self.stdout.write(f"檢查工單：{workorder.order_number} (當前狀態：{workorder.status})")

            if workorder.status == 'pending':
                has_activity = WorkOrderStatusService._check_production_activity(workorder)
                
                if has_activity:
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(f"乾跑模式：工單 {workorder.order_number} 有生產活動，將更新為生產中")
                        )
                    else:
                        updated = WorkOrderStatusService.update_workorder_status(workorder.id)
                        if updated:
                            workorder.refresh_from_db()
                            self.stdout.write(
                                self.style.SUCCESS(f"工單 {workorder.order_number} 狀態已更新為：{workorder.status}")
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"工單 {workorder.order_number} 狀態更新失敗")
                            )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"工單 {workorder.order_number} 沒有生產活動，保持待生產狀態")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f"工單 {workorder.order_number} 狀態不是待生產，跳過更新")
                )

        except WorkOrder.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"工單 ID {workorder_id} 不存在")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"更新工單 {workorder_id} 失敗：{str(e)}")
            )

    def update_all_pending_workorders(self, dry_run):
        """更新所有待生產工單狀態"""
        try:
            pending_workorders = WorkOrder.objects.filter(status='pending')
            total_count = pending_workorders.count()
            
            self.stdout.write(f"找到 {total_count} 個待生產工單")
            
            if total_count == 0:
                self.stdout.write(self.style.SUCCESS("沒有待生產的工單需要更新"))
                return

            updated_count = 0
            skipped_count = 0

            for workorder in pending_workorders:
                try:
                    has_activity = WorkOrderStatusService._check_production_activity(workorder)
                    
                    if has_activity:
                        if dry_run:
                            self.stdout.write(
                                f"乾跑模式：工單 {workorder.order_number} 有生產活動，將更新為生產中"
                            )
                        else:
                            updated = WorkOrderStatusService.update_workorder_status(workorder.id)
                            if updated:
                                updated_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"工單 {workorder.order_number} 狀態已更新為生產中")
                                )
                            else:
                                skipped_count += 1
                                self.stdout.write(
                                    self.style.WARNING(f"工單 {workorder.order_number} 狀態更新失敗")
                                )
                    else:
                        skipped_count += 1
                        if dry_run:
                            self.stdout.write(
                                f"乾跑模式：工單 {workorder.order_number} 沒有生產活動，保持待生產狀態"
                            )
                        
                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"處理工單 {workorder.order_number} 失敗：{str(e)}")
                    )

            # 輸出統計結果
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"乾跑模式完成：共檢查 {total_count} 個工單")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"更新完成：成功更新 {updated_count} 個工單，跳過 {skipped_count} 個工單")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"批量更新工單狀態失敗：{str(e)}")
            ) 