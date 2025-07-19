import logging
from django.utils import timezone
import importlib

logger = logging.getLogger(__name__)

# 定義模組與操作日誌模型的映射，與 system/views.py 的 MODULE_LOG_MODELS 保持一致
MODULE_LOG_MODELS = {
    'equip': 'equip.models.EquipOperationLog',
    'material': 'material.models.MaterialOperationLog',
    'scheduling': 'scheduling.models.SchedulingOperationLog',
    'process': 'process.models.ProcessOperationLog',
    'quality': 'quality.models.QualityOperationLog',
    'work_order': 'workorder.models.WorkOrderOperationLog',
    'reporting': 'reporting.models.ReportingOperationLog',
    'kanban': 'kanban.models.KanbanOperationLog',
    'erp_integration': 'erp_integration.models.ERPIntegrationOperationLog',
    'ai': 'ai.models.AIOperationLog',
}

def log_user_operation(username, module, action):
    """
    記錄用戶操作日誌
    :param username: 用戶名
    :param module: 模組名稱
    :param action: 操作描述
    """
    timestamp = timezone.now()
    log_message = f"[{timestamp}] User: {username}, Module: {module}, Action: {action}"
    logger.info(log_message)

    # 根據模組名稱查找對應的操作日誌模型
    model_path = MODULE_LOG_MODELS.get(module)
    if not model_path:
        logger.error(f"未找到模組 {module} 的操作日誌模型，無法記錄操作日誌")
        return

    try:
        # 動態導入模型
        module_path, class_name = model_path.rsplit('.', 1)
        model_module = importlib.import_module(module_path)
        log_model = getattr(model_module, class_name)
        
        # 創建操作日誌記錄
        log_model.objects.create(
            user=username,
            action=log_message,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"記錄操作日誌失敗，模組: {module}, 錯誤: {str(e)}")
