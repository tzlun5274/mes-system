"""
手動清理備份文件
根據保留天數設定清理過期的備份文件
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from system.models import BackupSchedule
import os
import datetime
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '根據保留天數設定清理過期的備份文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示會刪除的文件，不實際刪除'
        )
        parser.add_argument(
            '--days',
            type=int,
            help='指定保留天數（覆蓋設定檔中的值）'
        )

    def handle(self, *args, **options):
        backup_dir = "/var/www/mes/backups_DB"
        
        if not os.path.exists(backup_dir):
            self.stdout.write(
                self.style.ERROR(f"備份目錄不存在：{backup_dir}")
            )
            return
        
        try:
            schedule = BackupSchedule.objects.get(id=1)
            retention_days = options['days'] if options['days'] else schedule.retention_days
            
            self.stdout.write(f"備份目錄：{backup_dir}")
            self.stdout.write(f"保留天數：{retention_days} 天")
            self.stdout.write(f"當前時間：{timezone.now()}")
            
            cutoff_date = timezone.now() - datetime.timedelta(days=retention_days)
            self.stdout.write(f"截止日期：{cutoff_date}")
            
            # 獲取所有備份文件
            backup_files = [
                f
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f))
                and f.startswith("auto_backup_")
                and f.endswith(".sql")
            ]
            
            if not backup_files:
                self.stdout.write(
                    self.style.WARNING("沒有找到自動備份文件")
                )
                return
            
            self.stdout.write(f"找到 {len(backup_files)} 個備份文件")
            
            # 檢查每個文件
            files_to_delete = []
            files_to_keep = []
            
            for backup_file in backup_files:
                backup_path = os.path.join(backup_dir, backup_file)
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))
                # 將文件時間轉換為時區感知的datetime
                file_mtime = timezone.make_aware(file_mtime)
                file_size = os.path.getsize(backup_path)
                
                if file_mtime < cutoff_date:
                    files_to_delete.append({
                        'name': backup_file,
                        'path': backup_path,
                        'mtime': file_mtime,
                        'size': file_size
                    })
                else:
                    files_to_keep.append({
                        'name': backup_file,
                        'mtime': file_mtime,
                        'size': file_size
                    })
            
            # 顯示結果
            self.stdout.write("\n=== 保留的文件 ===")
            for file_info in files_to_keep:
                self.stdout.write(
                    f"✓ {file_info['name']} "
                    f"({file_info['mtime'].strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"{file_info['size']} bytes)"
                )
            
            self.stdout.write(f"\n=== 將要刪除的文件 ({len(files_to_delete)} 個) ===")
            total_size = 0
            for file_info in files_to_delete:
                self.stdout.write(
                    f"✗ {file_info['name']} "
                    f"({file_info['mtime'].strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"{file_info['size']} bytes)"
                )
                total_size += file_info['size']
            
            if files_to_delete:
                self.stdout.write(f"\n總計將釋放空間：{total_size} bytes ({total_size/1024/1024:.2f} MB)")
                
                if options['dry_run']:
                    self.stdout.write(
                        self.style.WARNING("\n這是預覽模式，沒有實際刪除文件")
                    )
                else:
                    # 實際刪除文件
                    self.stdout.write("\n開始刪除文件...")
                    deleted_count = 0
                    for file_info in files_to_delete:
                        try:
                            os.remove(file_info['path'])
                            deleted_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"✓ 已刪除：{file_info['name']}")
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"✗ 刪除失敗：{file_info['name']} - {str(e)}")
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"\n清理完成！成功刪除 {deleted_count} 個文件")
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS("\n沒有需要刪除的文件")
                )
                
        except BackupSchedule.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("未找到備份排程設定")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"清理過程發生錯誤：{str(e)}")
            ) 