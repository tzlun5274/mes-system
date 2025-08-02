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


@shared_task
def restore_database_task(backup_file_path, backup_name):
    """
    背景任務：執行資料庫還原
    """
    import os
    import subprocess
    import logging
    from urllib.parse import urlparse
    
    logger = logging.getLogger(__name__)
    logger.info(f"開始執行資料庫還原任務: {backup_name}")
    
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("環境變數 DATABASE_URL 未設置")

        parsed_url = urlparse(database_url)
        db_user = parsed_url.username
        db_password = parsed_url.password
        db_host = parsed_url.hostname
        db_port = parsed_url.port
        db_name = parsed_url.path.lstrip("/")
        os.environ["PGPASSWORD"] = db_password
        
        # 步驟1: 先清空資料庫（斷開所有連線並重建）
        logger.info("開始清空資料庫...")
        drop_cmd = [
            "psql",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "-d", "postgres",  # 連接到 postgres 資料庫
            "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();"
        ]
        result = subprocess.run(drop_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"斷開資料庫連線時出現警告: {result.stderr}")
        
        drop_db_cmd = [
            "dropdb",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "--if-exists",
            db_name
        ]
        result = subprocess.run(drop_db_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"刪除資料庫時出現警告: {result.stderr}")
        
        # 步驟2: 重新建立資料庫
        logger.info("重新建立資料庫...")
        create_cmd = [
            "createdb",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            db_name
        ]
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"建立資料庫失敗: {result.stderr}")
        
        # 步驟3: 還原備份檔案
        logger.info("開始還原備份檔案...")
        restore_cmd = [
            "psql",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "-d", db_name,
            "-f", backup_file_path,
        ]
        result = subprocess.run(restore_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"psql 恢復失敗: {result.stderr}")
        
        # 步驟4: 直接建立必要的資料表
        logger.info("建立必要的 Django 資料表...")
        
        # 建立 django_session 資料表
        session_table_sql = """
        CREATE TABLE IF NOT EXISTS django_session (
            session_key VARCHAR(40) NOT NULL PRIMARY KEY,
            session_data TEXT NOT NULL,
            expire_date TIMESTAMP WITH TIME ZONE NOT NULL
        );
        """
        
        # 建立 django_migrations 資料表
        migrations_table_sql = """
        CREATE TABLE IF NOT EXISTS django_migrations (
            id BIGSERIAL PRIMARY KEY,
            app VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied TIMESTAMP WITH TIME ZONE NOT NULL
        );
        """
        
        try:
            # 執行 SQL 建立資料表
            create_tables_cmd = [
                "psql",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                "-d", db_name,
                "-c", session_table_sql + migrations_table_sql
            ]
            result = subprocess.run(create_tables_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Django 必要資料表建立成功")
            else:
                logger.warning(f"建立資料表時出現警告: {result.stderr}")
                
        except Exception as e:
            logger.warning(f"建立 Django 資料表失敗: {str(e)}")
        
        del os.environ["PGPASSWORD"]
        logger.info(f"資料庫恢復成功: {backup_name}")
        
        return {
            'status': 'success',
            'message': f'資料庫恢復成功：{backup_name}',
            'backup_name': backup_name
        }
        
    except Exception as e:
        logger.error(f"資料庫恢復失敗: {str(e)}")
        return {
            'status': 'error',
            'message': f'資料庫恢復失敗：{str(e)}',
            'backup_name': backup_name
        }
