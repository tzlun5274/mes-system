import os
import subprocess
import datetime
from celery import shared_task
import logging
from django.utils import timezone
from system.models import OperationLogConfig

logger = logging.getLogger("django")

# 定義所有模組及其對應的 OperationLog 模型
MODULE_LOG_MODELS = {
    "equip": "equip.models.EquipOperationLog",
    "material": "material.models.MaterialOperationLog",
    "scheduling": "scheduling.models.SchedulingOperationLog",
    "process": "process.models.ProcessOperationLog",
    "quality": "quality.models.QualityOperationLog",
    "work_order": "workorder.models.WorkOrderOperationLog",
    "reporting": "reporting.models.ReportingOperationLog",
    "kanban": "kanban.models.KanbanOperationLog",
    "erp_integration": "erp_integration.models.ERPIntegrationOperationLog",
    "ai": "ai.models.AIOperationLog",
}


@shared_task
def auto_backup_database():
    backup_dir = "/var/www/mes/backups_DB"
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("環境變數 DATABASE_URL 未設置")
        from urllib.parse import urlparse

        parsed_url = urlparse(database_url)
        db_user = parsed_url.username
        db_password = parsed_url.password
        db_host = parsed_url.hostname
        db_port = parsed_url.port
        db_name = parsed_url.path.lstrip("/")
        os.environ["PGPASSWORD"] = db_password
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"auto_backup_{db_name}_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        cmd = [
            "pg_dump",
            "-h",
            db_host,
            "-p",
            str(db_port),
            "-U",
            db_user,
            "-F",
            "p",
            "-f",
            backup_path,
            db_name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"pg_dump 失敗: {result.stderr}")
        del os.environ["PGPASSWORD"]
        logger.info(f"自動資料庫備份成功: {backup_filename}")
        from system.models import BackupSchedule

        try:
            schedule = BackupSchedule.objects.get(id=1)
            retain_count = schedule.retain_count
            backup_files = [
                f
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f))
                and f.startswith("auto_backup_")
                and f.endswith(".sql")
            ]
            backup_files.sort(
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x))
            )
            while len(backup_files) > retain_count:
                oldest_file = backup_files.pop(0)
                os.remove(os.path.join(backup_dir, oldest_file))
                logger.info(f"刪除舊備份文件以符合保留份數: {oldest_file}")
        except BackupSchedule.DoesNotExist:
            logger.error("未找到自動備份排程設定，無法管理保留份數")
    except Exception as e:
        logger.error(f"自動資料庫備份失敗: {str(e)}")


@shared_task
def clean_operation_logs_task():
    try:
        config = OperationLogConfig.objects.get(id=1)
        cutoff_date = timezone.now() - datetime.timedelta(days=config.retain_days)
        total_deleted = 0
        for module, model_path in MODULE_LOG_MODELS.items():
            try:
                module_name, class_name = model_path.rsplit(".", 1)
                module = __import__(module_name, fromlist=[class_name])
                log_model = getattr(module, class_name)
                deleted_count, _ = log_model.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
                total_deleted += deleted_count
                logger.info(
                    f"清理模組 {module} 的過期操作紀錄，刪除 {deleted_count} 條記錄"
                )
            except Exception as e:
                logger.error(f"清理模組 {module} 的操作紀錄失敗: {str(e)}")
        logger.info(f"自動清理過期操作紀錄完成，共刪除 {total_deleted} 條記錄")
    except Exception as e:
        logger.error(f"自動清理操作紀錄失敗: {str(e)}")
