"""
報表排程同步服務
負責將報表排程同步到 Celery Beat
"""

import logging

logger = logging.getLogger(__name__)


class ReportScheduleSyncService:
    """報表排程同步服務 - 負責將報表排程同步到 Celery Beat"""
    
    @staticmethod
    def sync_report_schedules_to_celery():
        """將所有報表排程同步到 Celery Beat"""
        try:
            from django_celery_beat.models import PeriodicTask, CrontabSchedule
            from .models import ReportSchedule
            
            logger.info("開始同步報表排程到 Celery Beat")
            
            # 取得所有啟用的報表排程
            schedules = ReportSchedule.objects.filter(status='active')
            
            # 清理舊的報表排程任務
            old_tasks = PeriodicTask.objects.filter(name__startswith='report_schedule_')
            for task in old_tasks:
                logger.info(f"刪除舊的報表排程任務: {task.name}")
                task.delete()
            
            # 為每個排程建立 Celery 任務
            for schedule in schedules:
                try:
                    # 根據排程類型建立不同的 Cron 排程
                    if schedule.report_type == 'data_sync':
                        # 填報與現場記錄資料同步：根據執行方式設定
                        if schedule.sync_execution_type == 'interval':
                            # 間隔執行：每小時檢查一次，實際執行由服務邏輯判斷
                            cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                minute=0,  # 每小時的0分執行
                                hour='*',
                                day_of_week='*',
                                day_of_month='*',
                                month_of_year='*',
                            )
                        elif schedule.sync_execution_type == 'fixed_time':
                            # 固定時間執行
                            if schedule.sync_fixed_time:
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.sync_fixed_time.hour,
                                    minute=schedule.sync_fixed_time.minute,
                                    day_of_week='*',
                                    day_of_month='*',
                                    month_of_year='*',
                                )
                            else:
                                # 如果沒有設定固定時間，預設每小時執行
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    minute=0,
                                    hour='*',
                                    day_of_week='*',
                                    day_of_month='*',
                                    month_of_year='*',
                                )
                        else:
                            # 預設每小時執行
                            cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                minute=0,
                                hour='*',
                                day_of_week='*',
                                day_of_month='*',
                                month_of_year='*',
                            )
                    else:
                        # 其他報表類型：根據報表類型設定不同的執行日期
                        if schedule.report_type == 'previous_workday':
                            # 前一個工作日報表：每天執行，由執行時檢查行事曆
                            cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                hour=schedule.schedule_time.hour,
                                minute=schedule.schedule_time.minute,
                                day_of_week='*',  # 每天執行
                                day_of_month='*',
                                month_of_year='*',
                            )
                        elif schedule.report_type == 'previous_week':
                            # 上週報表：根據 schedule_day 設定星期幾執行
                            if schedule.schedule_day and 1 <= schedule.schedule_day <= 7:
                                # 將 schedule_day (1-7) 轉換為 day_of_week (0-6, 0=週日)
                                day_of_week = schedule.schedule_day % 7
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week=day_of_week,
                                    day_of_month='*',
                                    month_of_year='*',
                                )
                            else:
                                # 如果沒有設定星期幾，預設週一執行
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week=1,  # 週一
                                    day_of_month='*',
                                    month_of_year='*',
                                )
                        elif schedule.report_type == 'previous_month':
                            # 上月報表：根據 schedule_day 設定每月第幾天執行
                            if schedule.schedule_day and 1 <= schedule.schedule_day <= 30:
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=schedule.schedule_day,
                                    month_of_year='*',
                                )
                            else:
                                # 如果沒有設定日期，預設每月1號執行
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=1,
                                    month_of_year='*',
                                )
                        elif schedule.report_type == 'previous_quarter':
                            # 上季報表：根據 schedule_day 設定每季第幾天執行
                            if schedule.schedule_day and 1 <= schedule.schedule_day <= 30:
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=schedule.schedule_day,
                                    month_of_year='1,4,7,10',  # 每季第一個月
                                )
                            else:
                                # 如果沒有設定，預設每季1號執行
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=1,
                                    month_of_year='1,4,7,10',  # 每季第一個月
                                )
                        elif schedule.report_type == 'previous_year':
                            # 去年報表：根據 schedule_day 設定每年1月第幾天執行
                            if schedule.schedule_day and 1 <= schedule.schedule_day <= 30:
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=schedule.schedule_day,
                                    month_of_year=1,
                                )
                            else:
                                # 如果沒有設定日期，預設每年1月1號執行
                                cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                    hour=schedule.schedule_time.hour,
                                    minute=schedule.schedule_time.minute,
                                    day_of_week='*',
                                    day_of_month=1,
                                    month_of_year=1,
                                )
                        else:
                            # 預設：每天執行
                            cron_schedule, created = CrontabSchedule.objects.get_or_create(
                                hour=schedule.schedule_time.hour,
                                minute=schedule.schedule_time.minute,
                                day_of_week='*',
                                day_of_month='*',
                                month_of_year='*',
                            )
                    
                    # 建立週期任務
                    task_name = f'report_schedule_{schedule.id}'
                    task, created = PeriodicTask.objects.get_or_create(
                        name=task_name,
                        defaults={
                            'task': 'reporting.tasks.execute_scheduled_report',
                            'crontab': cron_schedule,
                            'enabled': True,
                            'args': f'[{schedule.id}]',
                        }
                    )
                    
                    if created:
                        logger.info(f"建立新的報表排程任務: {task_name}")
                    else:
                        logger.info(f"更新現有的報表排程任務: {task_name}")
                        task.crontab = cron_schedule
                        task.enabled = True
                        task.args = f'[{schedule.id}]'
                        task.save()
                        
                except Exception as e:
                    logger.error(f"同步排程 {schedule.name} 時發生錯誤: {str(e)}")
                    continue
            
            logger.info("報表排程同步完成")
            return {
                'success': True,
                'message': f'成功同步 {schedules.count()} 個報表排程'
            }
            
        except Exception as e:
            logger.error(f"同步報表排程到 Celery Beat 時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def remove_report_schedule_from_celery(schedule_id):
        """從 Celery Beat 中移除指定的報表排程"""
        try:
            from django_celery_beat.models import PeriodicTask
            
            task_name = f'report_schedule_{schedule_id}'
            task = PeriodicTask.objects.filter(name=task_name).first()
            
            if task:
                task.delete()
                logger.info(f"已從 Celery Beat 中移除報表排程任務: {task_name}")
                return True
            else:
                logger.warning(f"找不到要移除的報表排程任務: {task_name}")
                return False
                
        except Exception as e:
            logger.error(f"移除報表排程任務時發生錯誤: {str(e)}")
            return False
