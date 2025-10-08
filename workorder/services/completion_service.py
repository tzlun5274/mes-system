"""
工單完工服務
提供工單完工相關的功能，包括完工檢查、轉移等
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from ..models import WorkOrder, CompletedWorkOrder, WorkOrderProductionDetail
from ..fill_work.models import FillWork
from ..workorder_dispatch.models import WorkOrderDispatch

logger = logging.getLogger(__name__)


class FillWorkCompletionService:
    """
    填報完工服務
    提供工單完工相關的功能
    """
    
    # 出貨包裝工序名稱
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    @classmethod
    def archive_workorders(cls):
        """
        工單歸檔服務：合併完工判斷、資料轉移與清除的完整流程
        觸發條件：出貨包裝累積數量 >= 預計生產數量
        執行動作：
        1. 完工判斷：將符合條件的工單狀態變更為 completed
        2. 資料轉移：立即將該工單的所有相關資料轉移至已完工表格
        3. 資料清除：確認轉移成功後，立即從原始表格中刪除已轉移的資料
        
        Returns:
            dict: 歸檔結果統計
        """
        try:
            logger.info("開始執行工單歸檔流程")
            
            # 獲取所有進行中的派工單（真正在生產中的工單）
            from workorder.workorder_dispatch.models import WorkOrderDispatch
            active_dispatches = WorkOrderDispatch.objects.filter(status='in_production')
            
            total_checked = active_dispatches.count()
            archived_count = 0
            error_count = 0
            errors = []
            
            for dispatch in active_dispatches:
                # 直接檢查完工條件，不使用模型中的複雜函數
                can_complete = (dispatch.packaging_total_quantity >= dispatch.planned_quantity and 
                               dispatch.planned_quantity > 0)
                
                # 更新派工單的完工狀態
                dispatch.completion_threshold_met = can_complete
                dispatch.can_complete = can_complete
                dispatch.save()
                
                # 通過公司名稱+工單號碼+產品編號獲取對應的工單（唯一性條件）
                try:
                    workorder = WorkOrder.objects.get(
                        company_code=dispatch.company_code,
                        order_number=dispatch.order_number,
                        product_code=dispatch.product_code
                    )
                except WorkOrder.DoesNotExist:
                    logger.warning(f"派工單 {dispatch.company_code}-{dispatch.order_number}-{dispatch.product_code} 對應的工單不存在，跳過")
                    continue
                except WorkOrder.MultipleObjectsReturned:
                    logger.error(f"派工單 {dispatch.company_code}-{dispatch.order_number}-{dispatch.product_code} 對應多個工單，資料不一致，跳過")
                    continue
                
                # 排除條件：跳過工單號碼是「RD樣品」的工單
                if workorder.order_number == 'RD樣品':
                    logger.info(f"工單 {workorder.order_number} 是RD樣品工單，跳過完工判斷")
                    continue
                try:
                    # 1. 完工判斷：使用派工單的完工狀態
                    if dispatch.can_complete and dispatch.completion_threshold_met:
                        logger.info(f"工單 {workorder.order_number} 達到歸檔條件：出貨包裝數量={dispatch.packaging_total_quantity} >= 計劃數量={dispatch.planned_quantity}")
                        
                        # 2. 資料轉移：使用統一轉移服務
                        from .unified_transfer_service import UnifiedTransferService
                        transfer_result = UnifiedTransferService.transfer_workorder_to_completed(
                            workorder.id, "工單歸檔"
                        )
                        
                        if transfer_result.get('success'):
                            # 3. 更新派工單狀態為已完工
                            dispatch.status = 'completed'
                            dispatch.production_end_date = timezone.now()
                            dispatch.save()
                            
                            archived_count += 1
                            logger.info(f"工單 {workorder.order_number} 歸檔完成")
                        else:
                            error_count += 1
                            errors.append(f"工單 {workorder.order_number}: 資料轉移失敗 - {transfer_result.get('error', '未知錯誤')}")
                    else:
                        logger.debug(f"工單 {workorder.order_number} 尚未達到歸檔條件：可以完工={dispatch.can_complete}, 閾值達成={dispatch.completion_threshold_met}")
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"工單 {workorder.order_number} 歸檔失敗: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'total_checked': total_checked,
                'archived_count': archived_count,
                'error_count': error_count,
                'errors': errors[:10],  # 只返回前10個錯誤
                'message': f'工單歸檔完成：檢查 {total_checked} 個工單，成功歸檔 {archived_count} 個，錯誤 {error_count} 個'
            }
            
            logger.info(f"工單歸檔流程完成：{result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"執行工單歸檔流程失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'total_checked': 0,
                'archived_count': 0,
                'error_count': 1
            }
    
    
    @classmethod
    def _get_last_packaging_end_time(cls, workorder):
        """
        獲取最後一筆出貨包裝報工的結束時間（嚴格按公司分離）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            datetime: 最後一筆出貨包裝報工的結束時間，如果沒有則返回當前時間
        """
        try:
            from datetime import datetime
            from django.utils import timezone
            from ..fill_work.models import FillWork
            
            # 基本查詢條件（不限制產品編號，只找最後一筆出貨包裝報工）
            fillwork_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                process_name__exact=cls.PACKAGING_PROCESS_NAME,
                approval_status='approved'
            )
            
            # 嚴格的公司分離
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    fillwork_reports = fillwork_reports.filter(
                        company_name=company_config.company_name
                    )
                    logger.debug(f"工單 {workorder.order_number} 完工時間查詢按公司名稱 '{company_config.company_name}' 過濾")
                else:
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置")
                    fillwork_reports = FillWork.objects.none()
            else:
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號")
                fillwork_reports = FillWork.objects.none()
            
            # 獲取最後一筆出貨包裝報工記錄
            last_packaging_report = fillwork_reports.order_by('-work_date', '-end_time').first()
            
            if last_packaging_report and last_packaging_report.end_time:
                # 組合日期和時間
                end_datetime = datetime.combine(
                    last_packaging_report.work_date, 
                    last_packaging_report.end_time
                )
                # 轉換為 timezone-aware datetime
                end_datetime = timezone.make_aware(end_datetime)
                
                logger.debug(f"工單 {workorder.order_number} (公司: {workorder.company_code}) 最後一筆出貨包裝報工結束時間: {end_datetime}")
                return end_datetime
            else:
                logger.warning(f"工單 {workorder.order_number} (公司: {workorder.company_code}) 找不到出貨包裝報工記錄，使用當前時間")
                return timezone.now()
                
        except Exception as e:
            logger.error(f"獲取最後一筆出貨包裝報工結束時間失敗: {str(e)}")
            from django.utils import timezone
            return timezone.now()
    
    @classmethod
    def _get_packaging_quantity(cls, workorder):
        """
        獲取出貨包裝數量（嚴格按公司分離）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝數量
        """
        try:
            # 基本查詢條件
            fillwork_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                operation__exact=cls.PACKAGING_PROCESS_NAME,
                approval_status='approved'
            )
            
            # 嚴格的公司分離
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    fillwork_reports = fillwork_reports.filter(
                        company_name=company_config.company_name
                    )
                    logger.debug(f"工單 {workorder.order_number} 填報記錄按公司名稱 '{company_config.company_name}' 過濾")
                else:
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置")
                    fillwork_reports = FillWork.objects.none()
            else:
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號")
                fillwork_reports = FillWork.objects.none()
            
            # 計算良品數量
            good_quantity = fillwork_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            logger.debug(f"工單 {workorder.order_number} 出貨包裝數量: {good_quantity}")
            return good_quantity
            
        except Exception as e:
            logger.error(f"獲取出貨包裝數量失敗: {str(e)}")
            return 0
    
    @classmethod
    def _complete_workorder(cls, workorder):
        """
        執行工單完工流程
        
        Args:
            workorder: WorkOrder 實例
        """
        try:
            # 1. 獲取最後一筆出貨包裝報工的結束時間
            last_packaging_time = cls._get_last_packaging_end_time(workorder)
            
            # 2. 更新工單狀態
            workorder.status = 'completed'
            workorder.completed_at = last_packaging_time
            workorder.save()
            
            logger.info(f"工單 {workorder.order_number} 狀態更新為完工，完工時間: {last_packaging_time}")
            
            # 3. 更新生產記錄（WorkOrder 模型沒有 production_record 屬性，跳過此步驟）
            logger.info(f"工單 {workorder.order_number} 跳過生產記錄更新（WorkOrder 模型沒有 production_record 屬性）")
            
            # 4. 更新所有工序狀態
            from ..models import WorkOrderProcess
            processes = WorkOrderProcess.objects.filter(workorder_id=workorder.id)
            for process in processes:
                process.status = 'completed'
                process.actual_end_time = last_packaging_time
                process.save()
            
            logger.info(f"工單 {workorder.order_number} 所有工序狀態更新為完工")
            
        except Exception as e:
            logger.error(f"執行工單完工流程失敗: {str(e)}")
            import traceback
            logger.error(f"詳細錯誤堆疊: {traceback.format_exc()}")
            raise
    
    @classmethod
    def get_completion_summary(cls, workorder_id):
        """
        獲取工單完工摘要（使用派工單監控資料）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工摘要資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 排除條件：跳過工單號碼是「RD樣品」的工單
            if workorder.order_number == 'RD樣品':
                logger.info(f"工單 {workorder.order_number} 是RD樣品工單，跳過完工摘要檢查")
                return {
                    'can_complete': False,
                    'completion_status': {
                        'status': 'skipped',
                        'reason': 'RD樣品工單不進行完工判斷',
                        'packaging_quantity': 0,
                        'planned_quantity': workorder.quantity,
                        'completion_rate': 0.0
                    },
                    'workorder_info': {
                        'order_number': workorder.order_number,
                        'product_code': workorder.product_code,
                        'company_code': workorder.company_code
                    }
                }
            
            # 查找對應的派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,  # 修正：使用 product_code
                company_code=workorder.company_code
            ).first()
            
            if dispatch:
                # 更新派工單的監控資料
                # 直接更新完工狀態，不使用複雜的統計函數
                dispatch.completion_threshold_met = (dispatch.packaging_total_quantity >= dispatch.planned_quantity and dispatch.planned_quantity > 0)
                dispatch.can_complete = dispatch.completion_threshold_met
                dispatch.save()
                
                # 從派工單取得統計資訊
                total_quantity = dispatch.total_quantity
                packaging_quantity = dispatch.packaging_total_quantity
                completion_rate = float(dispatch.completion_rate)
                packaging_completion_rate = float(dispatch.packaging_completion_rate)
                
                # 簡化完工條件：只檢查數量，不檢查工序
                can_complete = (packaging_quantity >= workorder.quantity and workorder.quantity > 0)
                
                # 計算工序統計
                total_processes = dispatch.total_processes
                completed_processes = dispatch.completed_processes
                
                # 判斷完工原因
                if can_complete:
                    reason = "已達到完工條件"
                elif total_quantity == 0:
                    reason = "尚未有任何報工記錄"
                else:
                    reason = f"出貨包裝數量不足（{packaging_quantity}/{workorder.quantity}）"
                
                return {
                    'workorder_id': workorder_id,
                    'workorder_number': workorder.order_number,
                    'target_quantity': workorder.quantity,
                    'onsite_quantity': dispatch.onsite_completed_count,  # 現場報工記錄數
                    'fillwork_quantity': dispatch.fillwork_approved_count,  # 已核准填報記錄數
                    'current_quantity': total_quantity,
                    'packaging_quantity': packaging_quantity,
                    'can_complete': can_complete,
                    'completion_percentage': completion_rate,
                    'packaging_completion_percentage': packaging_completion_rate,
                    'is_completed': workorder.status == 'completed',
                    'packaging_info': {
                        'packaging_quantity': packaging_quantity,
                        'threshold_quantity': workorder.quantity,
                        'completion_rate': packaging_completion_rate
                    },
                    'config': {
                        'packaging_quantity_threshold': 100  # 100% 為完工閾值
                    },
                    # 新增：符合模板期望的結構
                    'completion_status': {
                        'can_complete': can_complete,
                        'reason': reason,
                        'details': {
                            'total_processes': total_processes,
                            'completed_processes': completed_processes
                        }
                    }
                }
            else:
                # 如果沒有派工單，返回預設值
                return {
                    'workorder_id': workorder_id,
                    'workorder_number': workorder.order_number,
                    'target_quantity': workorder.quantity,
                    'onsite_quantity': 0,
                    'fillwork_quantity': 0,
                    'current_quantity': 0,
                    'packaging_quantity': 0,
                    'can_complete': False,
                    'completion_percentage': 0.0,
                    'packaging_completion_percentage': 0.0,
                    'is_completed': workorder.status == 'completed',
                    'packaging_info': {
                        'packaging_quantity': 0,
                        'threshold_quantity': workorder.quantity,
                        'completion_rate': 0.0
                    },
                    'config': {
                        'packaging_quantity_threshold': 100
                    },
                    # 新增：符合模板期望的結構
                    'completion_status': {
                        'can_complete': False,
                        'reason': '找不到對應的派工單記錄',
                        'details': {
                            'total_processes': 0,
                            'completed_processes': 0
                        }
                    }
                }
            
        except WorkOrder.DoesNotExist:
            return {
                'workorder_id': workorder_id,
                'workorder_number': '未知',
                'target_quantity': 0,
                'onsite_quantity': 0,
                'fillwork_quantity': 0,
                'current_quantity': 0,
                'packaging_quantity': 0,
                'can_complete': False,
                'completion_percentage': 0.0,
                'packaging_completion_percentage': 0.0,
                'is_completed': False,
                'packaging_info': {
                    'packaging_quantity': 0,
                    'threshold_quantity': 0,
                    'completion_rate': 0.0
                },
                'config': {
                    'packaging_quantity_threshold': 100
                },
                'completion_status': {
                    'can_complete': False,
                    'reason': '工單不存在',
                    'details': {
                        'total_processes': 0,
                        'completed_processes': 0
                    }
                }
            }
        except Exception as e:
            logger.error(f"獲取工單 {workorder_id} 完工摘要失敗: {str(e)}")
            return {
                'workorder_id': workorder_id,
                'workorder_number': '未知',
                'target_quantity': 0,
                'onsite_quantity': 0,
                'fillwork_quantity': 0,
                'current_quantity': 0,
                'packaging_quantity': 0,
                'can_complete': False,
                'completion_percentage': 0.0,
                'packaging_completion_percentage': 0.0,
                'is_completed': False,
                'packaging_info': {
                    'packaging_quantity': 0,
                    'threshold_quantity': 0,
                    'completion_rate': 0.0
                },
                'config': {
                    'packaging_quantity_threshold': 100
                },
                'completion_status': {
                    'can_complete': False,
                    'reason': f'獲取完工摘要失敗: {str(e)}',
                    'details': {
                        'total_processes': 0,
                        'completed_processes': 0
                    }
                }
            }
    
    @classmethod
    def _cleanup_production_data(cls, workorder):
        """
        清理生產中相關資料
        
        Args:
            workorder: WorkOrder 實例
        """
        try:
            # 清理工序記錄
            from ..models import WorkOrderProcess
            WorkOrderProcess.objects.filter(workorder_id=workorder.id).delete()
            
            # 清理工單分配記錄
            from ..models import WorkOrderAssignment
            WorkOrderAssignment.objects.filter(workorder_id=workorder.id).delete()
            
            # 清理生產記錄
            from ..models import WorkOrderProduction, WorkOrderProductionDetail
            
            # 先取得所有相關的生產記錄ID，再刪除生產明細
            production_ids = WorkOrderProduction.objects.filter(workorder_id=workorder.id).values_list('id', flat=True)
            if production_ids:
                WorkOrderProductionDetail.objects.filter(workorder_production_id__in=production_ids).delete()
            
            # 最後刪除生產記錄
            WorkOrderProduction.objects.filter(workorder_id=workorder.id).delete()
            
            # 清理派工單記錄
            from ..workorder_dispatch.models import WorkOrderDispatch
            WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                company_code=workorder.company_code
            ).delete()
            
            logger.info(f"工單 {workorder.order_number} 生產中資料清理完成")
            
        except Exception as e:
            logger.error(f"清理工單 {workorder.order_number} 生產中資料失敗: {str(e)}")
            import traceback
            logger.error(f"詳細錯誤堆疊: {traceback.format_exc()}")
            raise

    
    @classmethod
    def auto_complete_workorder(cls, workorder_id):
        """
        自動完工工單
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工結果
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查工單狀態
            if workorder.status == 'completed':
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 已經是完工狀態'
                }
            
            # 獲取完工摘要
            summary = cls.get_completion_summary(workorder_id)
            
            if 'error' in summary:
                return {
                    'success': False,
                    'error': summary['error']
                }
                
            # 檢查是否達到完工條件
            if not summary['can_complete']:
                return {
                    'success': False,
                    'error': f'工單尚未達到完工條件，當前進度: {summary["completion_percentage"]:.1f}%'
                }
            
            # 先執行完工流程（設定正確的完工時間）
            cls._complete_workorder(workorder)
            # 重新載入工單以確保獲取最新的完工時間
            workorder.refresh_from_db()
            
            # 使用統一轉移服務
            from .unified_transfer_service import UnifiedTransferService
            transfer_result = UnifiedTransferService.transfer_workorder_to_completed(
                workorder_id, "自動完工"
            )
            
            if transfer_result.get('success'):
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 自動完工成功',
                    'workorder_id': workorder_id,
                    'completed_workorder_id': transfer_result.get('completed_workorder_id')
                }
            else:
                return {
                    'success': False,
                    'error': f'工單 {workorder.order_number} 資料轉移失敗: {transfer_result.get("error", "未知錯誤")}'
                }
            
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': '工單不存在'
            }
        except Exception as e:
            logger.error(f"自動完工工單 {workorder_id} 失敗: {str(e)}")
            return {
                'success': False,
                'error': f'自動完工失敗: {str(e)}'
            }
    
    @classmethod
    def _get_onsite_quantity(cls, workorder):
        """獲取現場報工數量（從 OnsiteReport 表計算，嚴格按公司分離）"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            # 基本查詢條件
            onsite_reports = OnsiteReport.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                process="出貨包裝",
                status='completed'  # 只統計已完成的現場報工
            )
            
            # 嚴格的公司分離：必須同時檢查公司代號和公司名稱
            if workorder.company_code:
                # 從 CompanyConfig 獲取公司名稱
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    # 同時按公司代號和公司名稱過濾，確保資料分離
                    onsite_reports = onsite_reports.filter(
                        company_code=workorder.company_code
                    )
                    logger.info(f"工單 {workorder.order_number} 現場報工按公司代號 '{workorder.company_code}' 過濾")
                else:
                    # 如果找不到公司配置，清空結果避免資料混淆
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置，清空現場報工結果")
                    onsite_reports = OnsiteReport.objects.none()
            else:
                # 如果工單沒有公司代號，清空結果避免資料混淆
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號，清空現場報工結果避免資料混淆")
                onsite_reports = OnsiteReport.objects.none()
            
            # 計算良品數量
            good_quantity = onsite_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品數量
            defect_quantity = onsite_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            logger.info(f"工單 {workorder.order_number} 現場報工數量: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取現場報工數量失敗: {str(e)}")
            return 0
    
    @classmethod
    def _get_fillwork_quantity(cls, workorder):
        """獲取出貨包裝填報數量（嚴格按公司分離，避免重複計算）"""
        try:
            # 基本查詢條件
            fillwork_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                operation__exact="出貨包裝",  # 修正：使用 operation 欄位而不是 process_name
                approval_status='approved'
            )
            
            # 嚴格的公司分離：必須同時檢查公司代號和公司名稱
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    # 按公司名稱過濾，確保資料分離
                    fillwork_reports = fillwork_reports.filter(
                        company_name=company_config.company_name
                    )
                    logger.info(f"工單 {workorder.order_number} 填報記錄按公司名稱 '{company_config.company_name}' 過濾")
                else:
                    # 如果找不到公司配置，清空結果避免資料混淆
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置，清空填報記錄結果")
                    fillwork_reports = FillWork.objects.none()
            else:
                # 如果工單沒有公司代號，清空結果避免資料混淆
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號，清空填報記錄結果避免資料混淆")
                fillwork_reports = FillWork.objects.none()
            
            # 計算良品數量
            good_quantity = fillwork_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品數量
            defect_quantity = fillwork_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            logger.info(f"工單 {workorder.order_number} 出貨包裝填報數量: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取出貨包裝填報數量失敗: {str(e)}")
            return 0 
    
    
    
    
    @classmethod
    def check_all_workorders_completion(cls):
        """
        檢查所有工單的完工狀態
        這是批量檢查工單完工條件的方法
        
        Returns:
            dict: 檢查結果統計
        """
        try:
            logger.info("開始批量檢查工單完工狀態")
            
            # 獲取所有進行中的工單（排除已完工的）
            active_workorders = WorkOrder.objects.filter(
                status__in=['pending', 'in_progress']
            ).order_by('order_number')
            
            total_checked = 0
            completed_count = 0
            error_count = 0
            errors = []
            
            for workorder in active_workorders:
                try:
                    total_checked += 1
                    
                    # 檢查並完成工單
                    if cls.check_and_complete_workorder(workorder.id):
                        completed_count += 1
                        logger.info(f"工單 {workorder.order_number} 完工檢查成功")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"工單 {workorder.order_number} 完工檢查失敗: {str(e)}"
                    logger.error(error_msg)
                    errors.append({
                        'workorder_id': workorder.id,
                        'order_number': workorder.order_number,
                        'error': str(e)
                    })
            
            result = {
                'total_checked': total_checked,
                'completed_count': completed_count,
                'error_count': error_count,
                'errors': errors[:10],  # 只返回前10個錯誤
                'message': f'批量完工檢查完成：檢查 {total_checked} 個工單，成功完工 {completed_count} 個，錯誤 {error_count} 個'
            }
            
            logger.info(f"批量完工檢查完成：{result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"批量檢查工單完工狀態失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'total_checked': 0,
                'completed_count': 0,
                'error_count': 1
            }
    
    
    @classmethod
    def cleanup_transferred_workorders(cls):
        """
        資料清理程式：在資料成功轉移後，自動從原始工單資料庫中刪除已轉移的工單資料
        觸發條件：工單已成功轉移到已完工工單資料庫
        執行動作：從原始工單資料庫中刪除已轉移的工單資料
        執行方式：支援排程自動執行與手動執行
        
        Returns:
            dict: 清理結果統計
        """
        try:
            logger.info("開始執行已轉移工單資料清理")
            
            # 查找所有已轉移的工單（在已完工工單表中存在，但在原始工單表中仍存在）
            transferred_workorders = []
            
            # 獲取所有已完工工單表中的工單
            completed_workorders = CompletedWorkOrder.objects.all()
            
            for completed_wo in completed_workorders:
                # 檢查原始工單是否仍存在
                original_workorder = WorkOrder.objects.filter(
                    order_number=completed_wo.order_number,
                    product_code=completed_wo.product_code,
                    company_code=completed_wo.company_code
                ).first()
                
                if original_workorder:
                    transferred_workorders.append(original_workorder)
            
            total_found = len(transferred_workorders)
            deleted_count = 0
            error_count = 0
            errors = []
            
            for workorder in transferred_workorders:
                try:
                    # 清理相關的生產中資料
                    cls._cleanup_production_data(workorder)
                    
                    # 刪除原始工單記錄
                    workorder.delete()
                    deleted_count += 1
                    
                    logger.info(f"工單 {workorder.order_number} 資料清理完成")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"工單 {workorder.order_number} 清理失敗: {str(e)}"
                    logger.error(error_msg)
                    errors.append({
                        'workorder_id': workorder.id,
                        'order_number': workorder.order_number,
                        'error': str(e)
                    })
            
            result = {
                'total_found': total_found,
                'deleted_count': deleted_count,
                'error_count': error_count,
                'errors': errors[:10],  # 只返回前10個錯誤
                'message': f'資料清理完成：找到 {total_found} 個已轉移工單，成功清理 {deleted_count} 個，錯誤 {error_count} 個'
            }
            
            logger.info(f"已轉移工單資料清理完成：{result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"執行已轉移工單資料清理失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'total_found': 0,
                'deleted_count': 0,
                'error_count': 1
            }
    

    @classmethod
    def auto_check_completion_on_fillwork_submit(cls, fillwork_instance):
        """
        在填報記錄提交時自動檢查完工條件
        
        Args:
            fillwork_instance: FillWork 實例
            
        Returns:
            dict: 檢查結果
        """
        try:
            logger.info(f"自動檢查工單完工條件：{fillwork_instance.workorder}")
            
            # 查找對應的工單
            workorder = WorkOrder.objects.filter(
                order_number=fillwork_instance.workorder,
                product_code=fillwork_instance.product_id,
                company_code=fillwork_instance.company_code
            ).first()
            
            if not workorder:
                logger.warning(f"找不到對應的工單：{fillwork_instance.workorder}")
                return {
                    'success': False,
                    'message': '找不到對應的工單',
                    'workorder_number': fillwork_instance.workorder
                }
            
            # 排除條件：跳過工單號碼是「RD樣品」的工單
            if workorder.order_number == 'RD樣品':
                logger.info(f"工單 {workorder.order_number} 是RD樣品工單，跳過智能自動完工檢查")
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 是RD樣品工單，跳過自動完工檢查',
                    'workorder_number': workorder.order_number,
                    'is_completed': False,
                    'skipped': True
                }
            
            # 檢查工單是否已經完工
            if workorder.status == 'completed':
                logger.info(f"工單 {workorder.order_number} 已經完工")
                return {
                    'success': True,
                    'message': '工單已經完工',
                    'workorder_number': workorder.order_number,
                    'is_completed': True
                }
            
            # 檢查完工條件
            completion_summary = cls.get_completion_summary(workorder.id)
            
            if completion_summary.get('can_complete', False):
                # 執行智能自動完工流程（使用新的歸檔邏輯）
                try:
                    # 查找對應的派工單
                    from workorder.workorder_dispatch.models import WorkOrderDispatch
                    dispatch = WorkOrderDispatch.objects.filter(
                        company_code=workorder.company_code,
                        order_number=workorder.order_number,
                        product_code=workorder.product_code,
                        status='in_production'
                    ).first()
                    
                    if dispatch:
                        # 執行完整的歸檔流程
                        result = cls.archive_workorders()
                        
                        if result.get('archived_count', 0) > 0:
                            logger.info(f"工單 {workorder.order_number} 智能自動完工並歸檔成功")
                            return {
                                'success': True,
                                'message': f'工單 {workorder.order_number} 智能自動完工並歸檔成功',
                                'workorder_number': workorder.order_number,
                                'is_completed': True,
                                'completion_summary': completion_summary
                            }
                        else:
                            logger.warning(f"工單 {workorder.order_number} 歸檔失敗")
                            return {
                                'success': False,
                                'message': f'工單 {workorder.order_number} 歸檔失敗',
                                'workorder_number': workorder.order_number,
                                'is_completed': False
                            }
                    else:
                        logger.warning(f"找不到對應的派工單：{workorder.order_number}")
                        return {
                            'success': False,
                            'message': f'找不到對應的派工單：{workorder.order_number}',
                            'workorder_number': workorder.order_number,
                            'is_completed': False
                        }
                        
                except Exception as e:
                    logger.error(f"智能自動完工失敗：{str(e)}")
                    return {
                        'success': False,
                        'message': f'智能自動完工失敗：{str(e)}',
                        'workorder_number': workorder.order_number,
                        'is_completed': False
                    }
            else:
                # 未達到完工條件
                reason = completion_summary.get('completion_status', {}).get('reason', '未知原因')
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 尚未達到完工條件：{reason}',
                    'workorder_number': workorder.order_number,
                    'is_completed': False,
                    'completion_summary': completion_summary
                }
                
        except Exception as e:
            logger.error(f"自動檢查完工條件失敗：{str(e)}")
            return {
                'success': False,
                'message': f'檢查失敗：{str(e)}',
                'workorder_number': fillwork_instance.workorder if hasattr(fillwork_instance, 'workorder') else 'unknown'
            }
    
    @classmethod
    def setup_auto_completion_triggers(cls):
        """
        設置自動完工觸發器
        在填報記錄提交時自動檢查完工條件
        """
        try:
            from django.db.models.signals import post_save
            from django.dispatch import receiver
            from workorder.fill_work.models import FillWork
            
            @receiver(post_save, sender=FillWork)
            def auto_check_completion(sender, instance, created, **kwargs):
                """
                填報記錄保存後自動檢查完工條件
                """
                # 只處理已核准的填報記錄
                if instance.approval_status == 'approved':
                    try:
                        # 使用 Celery 異步執行，避免阻塞主線程
                        from django_celery_beat.models import PeriodicTask
                        from celery import shared_task
                        
                        @shared_task
                        def check_completion_task(fillwork_id):
                            try:
                                fillwork = FillWork.objects.get(id=fillwork_id)
                                return cls.auto_check_completion_on_fillwork_submit(fillwork)
                            except Exception as e:
                                logger.error(f"異步檢查完工條件失敗：{str(e)}")
                                return {'success': False, 'message': str(e)}
                        
                        # 異步執行檢查
                        check_completion_task.delay(instance.id)
                        logger.info(f"已安排異步檢查工單完工條件：{instance.workorder}")
                        
                    except Exception as e:
                        logger.error(f"設置自動完工觸發器失敗：{str(e)}")
            
            logger.info("自動完工觸發器設置完成")
            
        except Exception as e:
            logger.error(f"設置自動完工觸發器失敗：{str(e)}")
    
    @classmethod
    def enable_auto_completion(cls):
        """
        啟用自動完工功能
        """
        try:
            # 設置觸發器
            cls.setup_auto_completion_triggers()
            
            # 創建或更新自動完工設定
            from workorder.models import AutoAllocationSettings
            
            settings, created = AutoAllocationSettings.objects.get_or_create(
                id=1,  # 使用固定ID
                defaults={
                    'enabled': True,
                    'completed_workorder_allocation_enabled': True,
                    'completed_workorder_allocation_interval': 5,  # 5分鐘檢查一次
                    'interval_minutes': 5,
                    'start_time': '08:00',
                    'end_time': '18:00'
                }
            )
            
            if not created:
                settings.enabled = True
                settings.completed_workorder_allocation_enabled = True
                settings.save()
            
            logger.info("自動完工功能已啟用")
            return True
            
        except Exception as e:
            logger.error(f"啟用自動完工功能失敗：{str(e)}")
            return False
    
    @classmethod
    def disable_auto_completion(cls):
        """
        停用自動完工功能
        """
        try:
            from workorder.models import AutoAllocationSettings
            
            settings = AutoAllocationSettings.objects.filter(id=1).first()
            if settings:
                settings.enabled = False
                settings.completed_workorder_allocation_enabled = False
                settings.save()
            
            logger.info("自動完工功能已停用")
            return True
            
        except Exception as e:
            logger.error(f"停用自動完工功能失敗：{str(e)}")
            return False
    
    @classmethod
    def force_complete_workorder(cls, workorder_id, force_reason="管理員強制完工"):
        """
        強制完工工單
        除了不檢查完工條件外，其他流程都跟完工判斷機制一樣
        會調用獨立的資料轉移服務
        
        Args:
            workorder_id: 工單ID
            force_reason: 強制完工原因
            
        Returns:
            dict: 強制完工結果
        """
        try:
            with transaction.atomic():
                # 1. 獲取工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                logger.info(f"開始強制完工工單 {workorder.order_number}，原因：{force_reason}")
                
                # 2. 先執行完工流程（設定正確的完工時間）
                cls._complete_workorder(workorder)
                # 重新載入工單以確保獲取最新的完工時間
                workorder.refresh_from_db()
                
                # 3. 使用統一轉移服務
                try:
                    from .unified_transfer_service import UnifiedTransferService
                    transfer_result = UnifiedTransferService.transfer_workorder_to_completed(
                        workorder_id, f"強制完工: {force_reason}"
                    )
                    
                    if transfer_result.get('success'):
                        completed_workorder_id = transfer_result.get('completed_workorder_id')
                        # 4. 更新派工單狀態為已完工（如果存在）
                        from workorder.workorder_dispatch.models import WorkOrderDispatch
                        dispatch = WorkOrderDispatch.objects.filter(
                            order_number=workorder.order_number,
                            product_code=workorder.product_code,
                            company_code=workorder.company_code
                        ).first()
                        
                        if dispatch:
                            dispatch.status = 'completed'
                            dispatch.production_end_date = timezone.now()
                            dispatch.save()
                        
                        # 5. 更新工單狀態為已完工
                        workorder.status = 'completed'
                        workorder.completed_at = timezone.now()
                        workorder.save()
                        
                        # 6. 使用與正常完工相同的資料清除邏輯
                        cls._cleanup_production_data(workorder)
                        workorder.delete()
                        
                        # 7. 獲取完工時的統計資料
                        original_packaging_quantity = 0
                        target_quantity = workorder.quantity
                        original_completion_rate = 0.0
                        
                        if dispatch:
                            original_packaging_quantity = dispatch.packaging_total_quantity
                            original_completion_rate = float(dispatch.completion_rate)
                        
                        result = {
                            'success': True,
                            'message': f'工單 {workorder.order_number} 強制完工成功，已轉移所有相關資料',
                            'workorder_number': workorder.order_number,
                            'force_reason': force_reason,
                            'completed_workorder_id': completed_workorder_id,
                            'was_already_completed': False,
                            'original_packaging_quantity': original_packaging_quantity,
                            'target_quantity': target_quantity,
                            'original_completion_rate': original_completion_rate
                        }
                        
                        logger.info(f"工單 {workorder.order_number} 強制完工流程執行完成")
                        return result
                    else:
                        return {
                            'success': False,
                            'message': f'工單 {workorder.order_number} 資料轉移失敗',
                            'workorder_number': workorder.order_number
                        }
                    
                except Exception as transfer_error:
                    logger.error(f"資料轉移失敗: {str(transfer_error)}")
                    raise transfer_error
                    
        except WorkOrder.DoesNotExist:
            error_msg = f"工單 {workorder_id} 不存在"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"強制完工工單 {workorder_id} 失敗: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"詳細錯誤堆疊: {traceback.format_exc()}")
            return {
                'success': False,
                'error': error_msg,
                'message': error_msg
            } 