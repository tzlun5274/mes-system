"""
填報作業管理子模組 - 服務層
負責填報作業的業務邏輯處理
"""

from django.db import transaction
from django.utils import timezone
from django.contrib import messages
import logging
from datetime import datetime

from .models import FillWork
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)


class RDSampleWorkOrderService:
    """
    RD樣品工單自動建立服務
    當主管核准RD樣品時，自動查找或建立MES工單和派工單
    """
    
    @staticmethod
    def is_rd_sample_record(fill_work_record):
        """
        判斷是否為RD樣品記錄
        
        Args:
            fill_work_record: FillWork記錄
            
        Returns:
            bool: 是否為RD樣品記錄
        """
        # 使用與 FillWork._is_rd_sample() 相同的邏輯
        # 只有工單號碼是 "RD樣品" 且產品編號以 "PFP-CCT" 開頭，才被識別為RD樣品
        return (fill_work_record.workorder == 'RD樣品' and 
                fill_work_record.product_id and 
                fill_work_record.product_id.startswith('PFP-CCT'))
    
    @staticmethod
    def find_or_create_rd_workorder(fill_work_record):
        """
        查找或建立RD樣品MES工單
        
        Args:
            fill_work_record: FillWork記錄
            
        Returns:
            tuple: (WorkOrder, bool) - 工單物件和是否為新建
        """
        try:
            # 工單號碼就是 'RD樣品'，不加上任何其他文字
            company_code = fill_work_record.company_code or '10'
            rd_workorder_number = 'RD樣品'
            product_code = fill_work_record.product_id
            
            # 查找現有工單
            existing_workorder = WorkOrder.objects.filter(
                company_code=company_code,
                order_number=rd_workorder_number,
                product_code=product_code
            ).first()
            
            if existing_workorder:
                logger.info(f"找到現有RD樣品工單: {existing_workorder}")
                return existing_workorder, False
            
            # 建立新工單
            with transaction.atomic():
                new_workorder = WorkOrder.objects.create(
                    company_code=company_code,
                    order_number=rd_workorder_number,
                    product_code=product_code,
                    quantity=fill_work_record.planned_quantity or 0,
                    status='pending',
                    order_source='mes',  # 標記為MES手動建立
                    created_at=timezone.now()
                )
                
                logger.info(f"建立新RD樣品工單: {new_workorder}")
                return new_workorder, True
                
        except Exception as e:
            logger.error(f"建立RD樣品工單失敗: {str(e)}")
            raise
    
    @staticmethod
    def find_or_create_rd_dispatch(workorder, fill_work_record):
        """
        查找或建立RD樣品派工單
        
        Args:
            workorder: WorkOrder物件
            fill_work_record: FillWork記錄
            
        Returns:
            tuple: (WorkOrderDispatch, bool) - 派工單物件和是否為新建
        """
        try:
            # 查找現有派工單
            existing_dispatch = WorkOrderDispatch.objects.filter(
                company_code=workorder.company_code,
                order_number=workorder.order_number,
                product_code=workorder.product_code
            ).first()
            
            if existing_dispatch:
                logger.info(f"找到現有RD樣品派工單: {existing_dispatch}")
                return existing_dispatch, False
            
            # 建立新派工單
            with transaction.atomic():
                new_dispatch = WorkOrderDispatch.objects.create(
                    company_code=workorder.company_code,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    product_name=f"RD樣品-{workorder.product_code}",
                    planned_quantity=workorder.quantity,
                    status='in_production',  # 直接設為生產中
                    dispatch_date=fill_work_record.work_date,
                    assigned_operator=fill_work_record.operator,
                    assigned_equipment=fill_work_record.equipment,
                    process_name='',  # RD樣品不設定預定工序
                    notes=f"RD樣品自動建立 - 核准時間: {timezone.now()} - 注意：RD樣品無預定工序流程",
                    created_by='system'
                )
                
                logger.info(f"建立新RD樣品派工單: {new_dispatch}")
                return new_dispatch, True
                
        except Exception as e:
            logger.error(f"建立RD樣品派工單失敗: {str(e)}")
            raise
    
    @staticmethod
    def process_rd_sample_approval(fill_work_record, approved_by):
        """
        處理RD樣品核准流程
        
        Args:
            fill_work_record: FillWork記錄
            approved_by: 核准人員
            
        Returns:
            dict: 處理結果
        """
        try:
            # 檢查是否為RD樣品記錄
            if not RDSampleWorkOrderService.is_rd_sample_record(fill_work_record):
                return {
                    'success': True,
                    'message': '非RD樣品記錄，跳過工單建立流程',
                    'workorder_created': False,
                    'dispatch_created': False
                }
            
            logger.info(f"開始處理RD樣品核准: {fill_work_record.id}")
            
            # 查找或建立工單
            workorder, workorder_created = RDSampleWorkOrderService.find_or_create_rd_workorder(fill_work_record)
            
            # 查找或建立派工單
            dispatch, dispatch_created = RDSampleWorkOrderService.find_or_create_rd_dispatch(workorder, fill_work_record)
            
            # 不修改填報記錄的工單號碼，保持原樣
            # 填報記錄的工單號碼應該是 'RD樣品'
            # 只有建立的MES工單才使用新的格式
            
            result = {
                'success': True,
                'message': 'RD樣品核准處理完成',
                'workorder_created': workorder_created,
                'dispatch_created': dispatch_created,
                'workorder': workorder,
                'dispatch': dispatch
            }
            
            logger.info(f"RD樣品核准處理完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"RD樣品核准處理失敗: {str(e)}")
            return {
                'success': False,
                'message': f'RD樣品核准處理失敗: {str(e)}',
                'workorder_created': False,
                'dispatch_created': False
            }


class FillWorkApprovalService:
    """
    填報核准服務
    處理填報記錄的核准相關業務邏輯
    """
    
    @staticmethod
    def approve_fill_work_record(fill_work_record, approved_by, approval_remarks=''):
        """
        核准填報記錄
        
        Args:
            fill_work_record: FillWork記錄
            approved_by: 核准人員
            approval_remarks: 核准備註
            
        Returns:
            dict: 核准結果
        """
        try:
            with transaction.atomic():
                # 核准前驗證派工單（RD樣品除外）
                if not fill_work_record._is_rd_sample():
                    validation_result = FillWorkApprovalService._validate_workorder_dispatch(fill_work_record)
                    if not validation_result['success']:
                        return validation_result
                
                # 更新核准狀態
                fill_work_record.approval_status = 'approved'
                fill_work_record.approved_by = approved_by
                fill_work_record.approved_at = timezone.now()
                fill_work_record.approval_remarks = approval_remarks
                fill_work_record.save(update_fields=[
                    'approval_status', 'approved_by', 'approved_at', 
                    'approval_remarks', 'updated_at'
                ])
                
                # 處理RD樣品工單建立
                rd_result = RDSampleWorkOrderService.process_rd_sample_approval(
                    fill_work_record, approved_by
                )
                
                # 更新工單狀態
                try:
                    from workorder.services.workorder_status_service import WorkOrderStatusService
                    from workorder.models import WorkOrder
                    from erp_integration.models import CompanyConfig
                    
                    # 查找對應的工單
                    company_config = CompanyConfig.objects.filter(
                        company_name=fill_work_record.company_name
                    ).first()
                    
                    if company_config:
                        workorder = WorkOrder.objects.filter(
                            company_code=company_config.company_code,
                            order_number=fill_work_record.workorder,
                            product_code=fill_work_record.product_id
                        ).first()
                    else:
                        workorder = WorkOrder.objects.filter(
                            order_number=fill_work_record.workorder,
                            product_code=fill_work_record.product_id
                        ).first()
                    
                    if workorder:
                        WorkOrderStatusService.update_workorder_status(workorder.id)
                        logger.info(f"工單 {workorder.order_number} 狀態更新成功")
                    else:
                        logger.warning(f"找不到對應的工單: {fill_work_record.workorder}")
                        
                except Exception as status_error:
                    logger.error(f"工單狀態更新失敗: {str(status_error)}")
                
                result = {
                    'success': True,
                    'message': '填報記錄核准成功',
                    'rd_sample_processed': rd_result['success'],
                    'rd_message': rd_result['message'],
                    'workorder_created': rd_result.get('workorder_created', False),
                    'dispatch_created': rd_result.get('dispatch_created', False)
                }
                
                logger.info(f"填報記錄核准完成: {result}")
                return result
                
        except Exception as e:
            logger.error(f"填報記錄核准失敗: {str(e)}")
            return {
                'success': False,
                'message': f'填報記錄核准失敗: {str(e)}'
            }
    
    @staticmethod
    def _validate_workorder_dispatch(fill_work_record):
        """
        驗證派工單
        
        Args:
            fill_work_record: FillWork記錄
            
        Returns:
            dict: 驗證結果
        """
        try:
            from workorder.workorder_dispatch.models import WorkOrderDispatch
            from erp_integration.models import CompanyConfig
            
            # 查找對應的派工單
            company_config = CompanyConfig.objects.filter(
                company_name=fill_work_record.company_name
            ).first()
            
            if company_config:
                dispatch = WorkOrderDispatch.objects.filter(
                    company_code=company_config.company_code,
                    order_number=fill_work_record.workorder,
                    product_code=fill_work_record.product_id
                ).first()
            else:
                dispatch = WorkOrderDispatch.objects.filter(
                    order_number=fill_work_record.workorder,
                    product_code=fill_work_record.product_id
                ).first()
            
            if not dispatch:
                return {
                    'success': False,
                    'message': f'找不到對應的派工單：工單號碼={fill_work_record.workorder}, 產品編號={fill_work_record.product_id}'
                }
            
            # 驗證公司名稱是否一致
            company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
            dispatch_company_name = company_config.company_name if company_config else None
            
            if dispatch_company_name != fill_work_record.company_name:
                return {
                    'success': False,
                    'message': f'公司名稱不一致：填報記錄={fill_work_record.company_name}, 派工單={dispatch_company_name}'
                }
            
            # 驗證產品編號是否一致
            if dispatch.product_code != fill_work_record.product_id:
                return {
                    'success': False,
                    'message': f'產品編號不一致：填報記錄={fill_work_record.product_id}, 派工單={dispatch.product_code}'
                }
            
            return {
                'success': True,
                'message': '派工單驗證通過'
            }
                
        except ImportError:
            # 如果派工單模組不存在，跳過驗證
            return {
                'success': True,
                'message': '派工單模組不存在，跳過驗證'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'派工單驗證失敗: {str(e)}'
            }
    
    @staticmethod
    def batch_approve_fill_work_records(record_ids, approved_by):
        """
        批量核准填報記錄
        
        Args:
            record_ids: 記錄ID列表
            approved_by: 核准人員
            
        Returns:
            dict: 批量核准結果
        """
        try:
            # 查詢待核准的記錄
            pending_records = FillWork.objects.filter(
                id__in=record_ids,
                approval_status='pending'
            )
            
            if not pending_records.exists():
                return {
                    'success': False,
                    'message': '沒有找到需要核准的記錄',
                    'approved_count': 0,
                    'rd_workorders_created': 0,
                    'rd_dispatches_created': 0
                }
            
            approved_count = 0
            rd_workorders_created = 0
            rd_dispatches_created = 0
            
            for record in pending_records:
                result = FillWorkApprovalService.approve_fill_work_record(
                    record, approved_by
                )
                
                if result['success']:
                    approved_count += 1
                    if result.get('workorder_created'):
                        rd_workorders_created += 1
                    if result.get('dispatch_created'):
                        rd_dispatches_created += 1
            
            return {
                'success': True,
                'message': f'成功核准 {approved_count} 筆填報記錄',
                'approved_count': approved_count,
                'rd_workorders_created': rd_workorders_created,
                'rd_dispatches_created': rd_dispatches_created
            }
            
        except Exception as e:
            logger.error(f"批量核准填報記錄失敗: {str(e)}")
            return {
                'success': False,
                'message': f'批量核准失敗: {str(e)}',
                'approved_count': 0,
                'rd_workorders_created': 0,
                'rd_dispatches_created': 0
            }


class MultiFilterService:
    """
    多重過濾服務
    結合原本的SMT/作業員過濾和使用者權限過濾
    """
    
    @staticmethod
    def get_multi_filtered_process_queryset(user, form_type='operator', permission_type='both'):
        """
        多重過濾工序查詢集：結合SMT/作業員過濾和使用者權限過濾
        
        Args:
            user: 當前使用者
            form_type: 表單類型 ('operator', 'smt')
            permission_type: 權限類型
            
        Returns:
            QuerySet: 多重過濾後的工序查詢集
        """
        try:
            from process.models import ProcessName
            from system.utils import get_user_allowed_processes
            from django.db import models
            
            # 第一步：根據表單類型進行SMT/作業員過濾
            if form_type == 'smt':
                # SMT表單：只顯示SMT相關工序
                base_queryset = ProcessName.objects.filter(
                    models.Q(name__icontains='SMT') | 
                    models.Q(name__icontains='貼片') | 
                    models.Q(name__icontains='Pick') | 
                    models.Q(name__icontains='Place')
                )
            else:
                # 作業員表單：排除SMT相關工序
                base_queryset = ProcessName.objects.exclude(
                    models.Q(name__icontains='SMT') | 
                    models.Q(name__icontains='貼片') | 
                    models.Q(name__icontains='Pick') | 
                    models.Q(name__icontains='Place')
                )
            
            # 第二步：根據使用者權限進行進一步過濾
            allowed_processes = get_user_allowed_processes(user, permission_type)
            
            if allowed_processes:
                # 有權限設定，只顯示權限內的工序
                return base_queryset.filter(name__in=allowed_processes).order_by('name')
            else:
                # 沒有權限設定，顯示所有符合表單類型的工序
                return base_queryset.order_by('name')
                
        except Exception as e:
            logger.error(f"多重過濾工序查詢集失敗: {str(e)}")
            # 異常時返回基本的SMT/作業員過濾
            if form_type == 'smt':
                return ProcessName.objects.filter(name__icontains='SMT').order_by('name')
            else:
                return ProcessName.objects.exclude(name__icontains='SMT').order_by('name')

    @staticmethod
    def get_multi_filtered_equipment_queryset(user, form_type='operator', permission_type='both'):
        """
        多重過濾設備查詢集：結合SMT/作業員過濾和使用者權限過濾
        
        Args:
            user: 當前使用者
            form_type: 表單類型 ('operator', 'smt')
            permission_type: 權限類型
            
        Returns:
            QuerySet: 多重過濾後的設備查詢集
        """
        try:
            from equip.models import Equipment
            from django.db import models
            
            # 第一步：根據表單類型進行SMT/作業員過濾
            if form_type == 'smt':
                # SMT表單：只顯示SMT相關設備
                base_queryset = Equipment.objects.filter(
                    models.Q(name__icontains='SMT') | 
                    models.Q(name__icontains='貼片') | 
                    models.Q(name__icontains='Pick') | 
                    models.Q(name__icontains='Place')
                )
            else:
                # 作業員表單：排除SMT相關設備
                base_queryset = Equipment.objects.exclude(
                    models.Q(name__icontains='SMT') | 
                    models.Q(name__icontains='貼片') | 
                    models.Q(name__icontains='Pick') | 
                    models.Q(name__icontains='Place')
                )
            
            # 第二步：根據使用者權限進行進一步過濾
            from system.utils import get_user_allowed_equipments
            allowed_equipments = get_user_allowed_equipments(user, permission_type)
            
            if allowed_equipments is None:
                # 禁用所有設備，返回空查詢集
                return Equipment.objects.none()
            elif allowed_equipments:
                # 有權限設定，只顯示權限內的設備
                return base_queryset.filter(name__in=allowed_equipments).order_by('name')
            else:
                # 沒有權限設定，顯示所有符合表單類型的設備
                return base_queryset.order_by('name')
                
        except Exception as e:
            logger.error(f"多重過濾設備查詢集失敗: {str(e)}")
            # 異常時返回基本的SMT/作業員過濾
            if form_type == 'smt':
                return Equipment.objects.filter(name__icontains='SMT').order_by('name')
            else:
                return Equipment.objects.exclude(name__icontains='SMT').order_by('name')

    @staticmethod
    def get_multi_filtered_operator_queryset(user, form_type='operator', permission_type='both'):
        """
        多重過濾作業員查詢集：結合SMT/作業員過濾和使用者權限過濾
        
        Args:
            user: 當前使用者
            form_type: 表單類型 ('operator', 'smt')
            permission_type: 權限類型
            
        Returns:
            QuerySet: 多重過濾後的作業員查詢集
        """
        try:
            from process.models import Operator
            from system.utils import get_user_allowed_operators
            
            # 第一步：根據表單類型進行SMT/作業員過濾
            if form_type == 'smt':
                # SMT表單：顯示所有作業員（因為SMT設備會自動填入作業員）
                base_queryset = Operator.objects.all()
            else:
                # 作業員表單：排除SMT相關的作業員
                base_queryset = Operator.objects.exclude(name__icontains='SMT')
            
            # 第二步：根據使用者權限進行進一步過濾
            allowed_operators = get_user_allowed_operators(user, permission_type)
            
            if allowed_operators:
                # 有權限設定，只顯示權限內的作業員
                return base_queryset.filter(name__in=allowed_operators).order_by('name')
            else:
                # 沒有權限設定，顯示所有符合表單類型的作業員
                return base_queryset.order_by('name')
                
        except Exception as e:
            logger.error(f"多重過濾作業員查詢集失敗: {str(e)}")
            # 異常時返回基本的SMT/作業員過濾
            if form_type == 'smt':
                return Operator.objects.all().order_by('name')
            else:
                return Operator.objects.exclude(name__icontains='SMT').order_by('name')

    @staticmethod
    def get_multi_filtered_choices(user, form_type='operator', permission_type='both'):
        """
        獲取多重過濾後的選項列表
        
        Args:
            user: 當前使用者
            form_type: 表單類型 ('operator', 'smt')
            permission_type: 權限類型
            
        Returns:
            dict: 包含作業員、工序、設備選項的字典
        """
        try:
            # 獲取多重過濾後的查詢集
            operator_queryset = MultiFilterService.get_multi_filtered_operator_queryset(
                user, form_type, permission_type
            )
            process_queryset = MultiFilterService.get_multi_filtered_process_queryset(
                user, form_type, permission_type
            )
            equipment_queryset = MultiFilterService.get_multi_filtered_equipment_queryset(
                user, form_type, permission_type
            )
            
            # 轉換為選項列表
            operator_choices = [("", "請選擇作業員")] + [
                (op.name, op.name) for op in operator_queryset
            ]
            process_choices = [("", "請選擇工序")] + [
                (proc.name, proc.name) for proc in process_queryset
            ]
            equipment_choices = [("", "請選擇使用的設備")] + [
                (eq.name, eq.name) for eq in equipment_queryset
            ]
            
            return {
                'operators': operator_choices,
                'processes': process_choices,
                'equipments': equipment_choices
            }
            
        except Exception as e:
            logger.error(f"獲取多重過濾選項失敗: {str(e)}")
            # 異常時返回空選項
            return {
                'operators': [("", "請選擇作業員")],
                'processes': [("", "請選擇工序")],
                'equipments': [("", "請選擇使用的設備")]
            } 