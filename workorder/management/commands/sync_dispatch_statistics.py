#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步派工單統計資料管理命令
用於同步所有派工單的統計資料和工單狀態
"""

from django.core.management.base import BaseCommand
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.models import WorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步所有派工單的統計資料和工單狀態'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dispatch-id',
            type=int,
            help='指定派工單ID進行同步',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，不實際更新資料',
        )

    def handle(self, *args, **options):
        dispatch_id = options.get('dispatch_id')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 乾跑模式 - 不會實際更新資料'))

        try:
            if dispatch_id:
                # 同步指定派工單
                self.stdout.write(f'🔄 同步派工單 ID: {dispatch_id}')
                self._sync_single_dispatch(dispatch_id, dry_run)
            else:
                # 同步所有派工單
                self.stdout.write('🔄 開始同步所有派工單統計資料...')
                self._sync_all_dispatches(dry_run)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 同步失敗: {str(e)}')
            )
            logger.error(f"同步派工單統計資料失敗: {str(e)}")

    def _sync_single_dispatch(self, dispatch_id, dry_run=False):
        """同步單一派工單"""
        try:
            dispatch = WorkOrderDispatch.objects.get(id=dispatch_id)
            
            # 顯示同步前狀態
            self._show_dispatch_status(dispatch, "同步前")
            
            if not dry_run:
                # 執行統計更新
                dispatch.update_all_statistics()
                
                # 顯示同步後狀態
                self._show_dispatch_status(dispatch, "同步後")
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 派工單 {dispatch.order_number} 同步完成')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'🔍 乾跑模式 - 派工單 {dispatch.order_number} 不會實際更新')
                )
                
        except WorkOrderDispatch.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 派工單 ID {dispatch_id} 不存在')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 同步派工單 {dispatch_id} 失敗: {str(e)}')
            )

    def _sync_all_dispatches(self, dry_run=False):
        """同步所有派工單"""
        dispatches = WorkOrderDispatch.objects.all()
        total_count = dispatches.count()
        
        self.stdout.write(f'📊 總共找到 {total_count} 個派工單')
        
        success_count = 0
        error_count = 0
        
        for i, dispatch in enumerate(dispatches, 1):
            try:
                self.stdout.write(f'🔄 [{i}/{total_count}] 同步派工單 {dispatch.order_number}...')
                
                if not dry_run:
                    # 執行統計更新
                    dispatch.update_all_statistics()
                    success_count += 1
                else:
                    # 乾跑模式，只顯示狀態
                    self._show_dispatch_status(dispatch, "當前狀態")
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ 同步派工單 {dispatch.order_number} 失敗: {str(e)}')
                )
                logger.error(f"同步派工單 {dispatch.order_number} 失敗: {str(e)}")

        # 顯示統計結果
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'🔍 乾跑完成 - 檢查了 {total_count} 個派工單')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ 同步完成 - 成功: {success_count}, 失敗: {error_count}')
            )

    def _show_dispatch_status(self, dispatch, prefix=""):
        """顯示派工單狀態"""
        # 查找對應的工單
        workorder = WorkOrder.objects.filter(
            order_number=dispatch.order_number,
            product_code=dispatch.product_code,
            company_code=dispatch.company_code
        ).first()
        
        self.stdout.write(f'  {prefix}狀態:')
        self.stdout.write(f'    派工單狀態: {dispatch.get_status_display()}')
        self.stdout.write(f'    出貨包裝數量: {dispatch.packaging_total_quantity}/{dispatch.planned_quantity}')
        self.stdout.write(f'    可完工: {dispatch.can_complete}')
        
        if workorder:
            self.stdout.write(f'    工單狀態: {workorder.get_status_display()}')
        else:
            self.stdout.write(f'    工單狀態: 找不到對應工單')
