"""
自定義 Django 管理命令：跳過遷移檢查的 runserver
"""
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.management.base import CommandError
from django.db import connection
import os
import sys


class Command(RunserverCommand):
    help = '啟動開發伺服器，跳過所有遷移檢查'

    def handle(self, *args, **options):
        # 跳過所有遷移檢查
        self.stdout.write(
            self.style.WARNING('⚠️  跳過遷移檢查，直接啟動伺服器...')
        )
        
        # 檢查資料庫連線
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(
                self.style.SUCCESS('✓ 資料庫連線正常')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ 資料庫連線失敗: {e}')
            )
            return
        
        # 直接啟動伺服器
        super().handle(*args, **options)
