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
            retention_days = schedule.retention_days
            cutoff_date = timezone.now() - datetime.timedelta(days=retention_days)
            
            # 清理超過保留天數的備份文件
            backup_files = [
                f
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f))
                and f.startswith("auto_backup_")
                and f.endswith(".sql")
            ]
            
            deleted_count = 0
            for backup_file in backup_files:
                backup_path = os.path.join(backup_dir, backup_file)
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))
                # 將文件時間轉換為時區感知的datetime
                file_mtime = timezone.make_aware(file_mtime)
                if file_mtime < cutoff_date:
                    os.remove(backup_path)
                    deleted_count += 1
                    logger.info(f"刪除超過保留天數的備份文件: {backup_file}")
            
            if deleted_count > 0:
                logger.info(f"清理完成，共刪除 {deleted_count} 個超過 {retention_days} 天的備份文件")
            else:
                logger.info(f"沒有需要清理的備份文件（保留天數：{retention_days}天）")
                
        except BackupSchedule.DoesNotExist:
            logger.error("未找到自動備份排程設定，無法管理保留天數")
    except Exception as e:
        logger.error(f"自動資料庫備份失敗: {str(e)}")


@shared_task
def auto_approve_work_reports():
    """
    自動審核報工記錄
    根據設定的條件自動審核符合條件的報工
    """
    from system.models import AutoApprovalSettings
    from workorder.fill_work.models import FillWork
    from django.db.models import Q
    from decimal import Decimal
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 取得自動審核設定
        try:
            settings = AutoApprovalSettings.objects.first()
            if not settings:
                logger.info("未找到自動審核設定，跳過自動審核")
                return {
                    'success': False,
                    'message': '未找到自動審核設定'
                }
            
            if not settings.is_enabled:
                logger.info("自動審核功能未啟用，跳過自動審核")
                return {
                    'success': False,
                    'message': '自動審核功能未啟用'
                }
        except Exception as e:
            logger.error(f"取得自動審核設定失敗: {str(e)}")
            return {
                'success': False,
                'error': f'取得自動審核設定失敗: {str(e)}'
            }
        
        # 查詢待審核的報工記錄
        pending_reports = FillWork.objects.filter(
            approval_status='pending'  # 待審核狀態
        )
        
        # 排除設定的作業員和工序
        if settings.exclude_operators:
            pending_reports = pending_reports.exclude(operator__in=settings.exclude_operators)
        
        if settings.exclude_processes:
            pending_reports = pending_reports.exclude(operation__in=settings.exclude_processes)
        
        total_pending = pending_reports.count()
        if total_pending == 0:
            logger.info("沒有待審核的報工記錄")
            return {
                'success': True,
                'message': '沒有待審核的報工記錄',
                'approved_count': 0,
                'rejected_count': 0
            }
        
        approved_count = 0
        rejected_count = 0
        approved_reports = []
        rejected_reports = []
        
        for report in pending_reports:
            should_approve = True
            rejection_reason = []
            
            # 檢查工作時數
            if settings.auto_approve_work_hours:
                work_hours = float(report.work_hours_calculated or 0)
                if work_hours > float(settings.max_work_hours):
                    should_approve = False
                    rejection_reason.append(f"工作時數({work_hours}小時)超過限制({settings.max_work_hours}小時)")
            
            # 檢查不良率
            if settings.auto_approve_defect_rate and should_approve:
                if hasattr(report, 'defect_quantity') and hasattr(report, 'completed_quantity'):
                    if report.completed_quantity > 0:
                        defect_rate = (report.defect_quantity / report.completed_quantity) * 100
                        if defect_rate > float(settings.max_defect_rate):
                            should_approve = False
                            rejection_reason.append(f"不良率({defect_rate:.2f}%)超過限制({settings.max_defect_rate}%)")
            
            # 檢查加班時數
            if settings.auto_approve_overtime and should_approve:
                overtime_hours = float(report.overtime_hours_calculated or 0)
                if overtime_hours > float(settings.max_overtime_hours):
                    should_approve = False
                    rejection_reason.append(f"加班時數({overtime_hours}小時)超過限制({settings.max_overtime_hours}小時)")
            
            # 執行審核
            if should_approve:
                report.approval_status = 'approved'
                report.approved_at = timezone.now()
                report.approved_by = '自動審核系統'
                report.approval_remarks = '自動審核通過'
                report.save()
                approved_count += 1
                approved_reports.append(report.id)
                logger.info(f"自動審核通過: 報工記錄 {report.id} (作業員: {report.operator}, 工序: {report.operation})")
            else:
                report.approval_status = 'rejected'
                report.rejected_at = timezone.now()
                report.rejected_by = '自動審核系統'
                report.rejection_reason = '; '.join(rejection_reason)
                report.save()
                rejected_count += 1
                rejected_reports.append(report.id)
                logger.info(f"自動審核拒絕: 報工記錄 {report.id} (作業員: {report.operator}, 工序: {report.operation}) - 原因: {'; '.join(rejection_reason)}")
        
        # 發送通知（如果啟用）
        if settings.notification_enabled and (approved_count > 0 or rejected_count > 0):
            try:
                # 取得通知設定
                from workorder.models import SystemConfig
                notification_enabled = SystemConfig.objects.filter(key='auto_approval_notification_enabled').first()
                recipients = SystemConfig.objects.filter(key='auto_approval_notification_recipients').first()
                
                if notification_enabled and notification_enabled.value == 'True' and recipients:
                    # 發送郵件通知
                    from django.core.mail import send_mail
                    from system.models import EmailConfig
                    
                    # 取得郵件設定
                    email_config = EmailConfig.objects.first()
                    if email_config:
                        subject = f"[MES系統] 自動審核完成通知 - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                        
                        message = f"""
自動審核完成通知

執行時間: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
總計處理: {total_pending} 筆報工記錄
審核通過: {approved_count} 筆
審核拒絕: {rejected_count} 筆

詳細資訊:
- 通過的報工記錄ID: {', '.join(map(str, approved_reports)) if approved_reports else '無'}
- 拒絕的報工記錄ID: {', '.join(map(str, rejected_reports)) if rejected_reports else '無'}

此為系統自動發送的通知，請勿直接回覆。
                        """
                        
                        recipient_list = [email.strip() for email in recipients.value.split(',') if email.strip()]
                        
                        if recipient_list:
                            send_mail(
                                subject,
                                message,
                                email_config.default_from_email,
                                recipient_list,
                                fail_silently=False,
                            )
                            logger.info(f"自動審核通知郵件已發送給: {', '.join(recipient_list)}")
                        else:
                            logger.warning("自動審核通知收件人清單為空")
                    else:
                        logger.error("未找到郵件設定，無法發送自動審核通知")
                else:
                    logger.info("自動審核通知功能未啟用或收件人未設定")
                    
            except Exception as e:
                logger.error(f"發送自動審核通知失敗: {str(e)}")
        
        logger.info(f"自動審核完成: 總計 {total_pending} 筆，通過 {approved_count} 筆，拒絕 {rejected_count} 筆")
        
        return {
            'success': True,
            'message': f'自動審核完成，通過: {approved_count}，拒絕: {rejected_count}',
            'total_pending': total_pending,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'approved_reports': approved_reports,
            'rejected_reports': rejected_reports
        }
        
    except Exception as e:
        logger.error(f"自動審核任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動審核任務執行失敗: {str(e)}'
        }


@shared_task
def sync_scheduled_tasks_to_celery():
    """
    同步 ScheduledTask 到 Celery Beat
    確保所有定時任務都正確地同步到 Celery Beat 系統
    """
    from system.models import ScheduledTask
    from django_celery_beat.models import PeriodicTask, CrontabSchedule
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        synced_count = 0
        error_count = 0
        
        for scheduled_task in ScheduledTask.objects.all():
            try:
                # 解析 Cron 表達式
                cron_parts = scheduled_task.cron_expression.split()
                if len(cron_parts) != 5:
                    logger.error(f"任務 {scheduled_task.name} 的 Cron 表達式格式錯誤: {scheduled_task.cron_expression}")
                    error_count += 1
                    continue
                
                minute, hour, day_of_month, month_of_year, day_of_week = cron_parts
                
                # 創建或取得 Crontab 排程
                crontab, created = CrontabSchedule.objects.get_or_create(
                    minute=minute,
                    hour=hour,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                    day_of_week=day_of_week,
                )
                
                # 創建或更新定時任務
                task, created = PeriodicTask.objects.get_or_create(
                    name=f"scheduled_task_{scheduled_task.id}",
                    defaults={
                        'task': scheduled_task.task_function,
                        'crontab': crontab,
                        'enabled': scheduled_task.is_enabled,
                        'description': scheduled_task.description
                    }
                )
                
                if not created:
                    # 更新現有任務
                    task.task = scheduled_task.task_function
                    task.crontab = crontab
                    task.enabled = scheduled_task.is_enabled
                    task.description = scheduled_task.description
                    task.save()
                
                synced_count += 1
                logger.info(f"成功同步任務: {scheduled_task.name}")
                
            except Exception as e:
                logger.error(f"同步任務 {scheduled_task.name} 失敗: {str(e)}")
                error_count += 1
        
        logger.info(f"定時任務同步完成: 成功 {synced_count} 個，失敗 {error_count} 個")
        
        return {
            'success': True,
            'synced_count': synced_count,
            'error_count': error_count,
            'message': f'同步完成: 成功 {synced_count} 個，失敗 {error_count} 個'
        }
        
    except Exception as e:
        logger.error(f"同步定時任務失敗: {str(e)}")
        return {
            'success': False,
            'error': f'同步定時任務失敗: {str(e)}'
        }


@shared_task
def clean_operation_logs_task():
    try:
        config = OperationLogConfig.objects.get(id=1)
        cutoff_date = timezone.now() - datetime.timedelta(days=config.retention_days)
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
