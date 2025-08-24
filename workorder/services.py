"""
工單服務模組
提供工單相關的業務邏輯服務
"""

import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail
from workorder.fill_work.models import FillWork
# 移除主管報工引用，避免混淆
# 主管職責：監督、審核、管理，不代為報工

logger = logging.getLogger(__name__)

# WorkOrderCompletionService 已移除，功能已整合到 FillWorkCompletionService

def create_missing_workorders_from_fillwork():
    """
    從填報資料創建缺失的工單
    以公司名稱/代號+製令號碼+產品編號作為唯一性識別
    """
    from .fill_work.models import FillWork
    from .models import WorkOrder
    from erp_integration.models import CompanyConfig
    from .company_order.models import CompanyOrder
    from .models import SystemConfig
    from django.db import transaction
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 統計資訊
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    try:
        # 取得所有填報資料
        fill_works = FillWork.objects.all()
        
        for fill_work in fill_works:
            try:
                # 檢查必要欄位
                if not fill_work.company_name or not fill_work.workorder or not fill_work.product_id:
                    logger.warning(f"填報資料缺少必要欄位: ID={fill_work.id}")
                    error_count += 1
                    continue
                
                # 從公司名稱查找公司代號
                company_code = None
                try:
                    company_config = CompanyConfig.objects.filter(
                        company_name__icontains=fill_work.company_name
                    ).first()
                    
                    if company_config:
                        company_code = company_config.company_code
                    else:
                        # 如果找不到公司配置，嘗試從製令資料中查找
                        # 移除對 PrdMKOrdMain 的引用，改用 CompanyOrder
                        company_order = CompanyOrder.objects.filter(
                            MKOrdNO=fill_work.workorder,
                            ProductID=fill_work.product_id
                        ).first()
                        
                        if company_order:
                            company_code = company_order.company_code
                
                except Exception as e:
                    logger.error(f"查找公司代號時發生錯誤: {e}")
                    error_count += 1
                    continue
                
                if not company_code:
                    logger.warning(f"無法找到公司代號: 公司名稱={fill_work.company_name}, 工單號={fill_work.workorder}")
                    error_count += 1
                    continue
                
                # 檢查工單是否已存在
                existing_workorder = WorkOrder.objects.filter(
                    company_code=company_code,
                    order_number=fill_work.workorder,
                    product_code=fill_work.product_id
                ).first()
                
                if existing_workorder:
                    logger.info(f"工單已存在，跳過: {company_code}-{fill_work.workorder}-{fill_work.product_id}")
                    skipped_count += 1
                    continue
                
                # 創建新工單
                with transaction.atomic():
                    new_workorder = WorkOrder.objects.create(
                        company_code=company_code,
                        order_number=fill_work.workorder,
                        product_code=fill_work.product_id,
                        quantity=fill_work.planned_quantity or 0,
                        status='pending',
                        order_source='mes'  # 從填報資料創建的工單標記為MES來源
                    )
                    
                    created_count += 1
                    logger.info(f"成功創建工單: {new_workorder}")
                
            except Exception as e:
                logger.error(f"處理填報資料時發生錯誤 (ID={fill_work.id}): {e}")
                error_count += 1
                errors.append({
                    'fill_work_id': fill_work.id,
                    'error': str(e)
                })
        
        # 記錄統計結果
        logger.info(f"工單創建完成 - 成功: {created_count}, 跳過: {skipped_count}, 錯誤: {error_count}")
        
        return {
            'success': True,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"創建缺失工單時發生嚴重錯誤: {e}")
        return {
            'success': False,
            'error': str(e),
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        } 