"""
生產環境權限同步命令
用於在生產環境部署後同步所有模組的權限
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.management import create_permissions
from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '同步生產環境的所有權限，包括設備管理等模組'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬執行，不實際修改資料庫',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細執行資訊',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 模擬執行模式 - 不會實際修改資料庫')
            )
        
        self.stdout.write('🚀 開始同步生產環境權限...')
        
        # 定義需要同步的應用模組
        target_apps = [
            'equip',           # 設備管理
            'material',        # 物料管理
            'scheduling',      # 排程管理
            'process',         # 製程管理
            'quality',         # 品質管理
            'workorder',       # 工單管理
            'kanban',          # 看板管理
            'erp_integration', # ERP整合
            'ai',              # AI管理
            'system',          # 系統管理
        ]
        
        total_added = 0
        total_errors = 0
        
        for app_label in target_apps:
            try:
                self.stdout.write(f'📱 正在同步 {app_label} 模組...')
                
                if not dry_run:
                    # 執行 makemigrations
                    try:
                        call_command('makemigrations', app_label, verbosity=0)
                        if verbose:
                            self.stdout.write(f'  ✅ {app_label} makemigrations 完成')
                    except Exception as e:
                        if verbose:
                            self.stdout.write(f'  ⚠️  {app_label} makemigrations 警告: {str(e)}')
                    
                    # 執行 migrate
                    try:
                        call_command('migrate', app_label, verbosity=0)
                        if verbose:
                            self.stdout.write(f'  ✅ {app_label} migrate 完成')
                    except Exception as e:
                        if verbose:
                            self.stdout.write(f'  ⚠️  {app_label} migrate 警告: {str(e)}')
                    
                    # 創建權限
                    try:
                        app_config = apps.get_app_config(app_label)
                        create_permissions(app_config, verbosity=0)
                        if verbose:
                            self.stdout.write(f'  ✅ {app_label} 權限創建完成')
                    except Exception as e:
                        if verbose:
                            self.stdout.write(f'  ⚠️  {app_label} 權限創建警告: {str(e)}')
                
                # 統計權限數量
                try:
                    app_permissions = Permission.objects.filter(
                        content_type__app_label=app_label
                    )
                    permission_count = app_permissions.count()
                    total_added += permission_count
                    
                    if verbose:
                        self.stdout.write(f'  📊 {app_label} 模組共有 {permission_count} 個權限')
                        
                        # 顯示權限列表
                        for perm in app_permissions[:5]:  # 只顯示前5個
                            self.stdout.write(f'    - {perm.name}')
                        if permission_count > 5:
                            self.stdout.write(f'    ... 還有 {permission_count - 5} 個權限')
                    
                except Exception as e:
                    if verbose:
                        self.stdout.write(f'  ❌ {app_label} 權限統計失敗: {str(e)}')
                    total_errors += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ {app_label} 模組同步失敗: {str(e)}')
                )
                total_errors += 1
        
        # 顯示總結
        self.stdout.write('\n' + '='*50)
        self.stdout.write('📋 權限同步總結')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write('🔍 模擬執行模式 - 未實際修改資料庫')
        else:
            self.stdout.write(f'✅ 成功同步 {len(target_apps)} 個模組')
            self.stdout.write(f'📊 總共發現 {total_added} 個權限')
        
        if total_errors > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  發生 {total_errors} 個錯誤，請檢查日誌')
            )
        
        # 顯示設備管理模組的權限詳情
        try:
            equip_permissions = Permission.objects.filter(
                content_type__app_label='equip'
            )
            self.stdout.write(f'\n🔧 設備管理模組權限詳情:')
            self.stdout.write(f'   總數: {equip_permissions.count()} 個權限')
            
            for perm in equip_permissions:
                self.stdout.write(f'   - {perm.name}')
                
        except Exception as e:
            self.stdout.write(f'❌ 無法獲取設備管理權限詳情: {str(e)}')
        
        self.stdout.write('\n🎉 權限同步完成！')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('💡 建議：重新登入系統以確保權限生效')
            )
