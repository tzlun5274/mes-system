"""
自動同步權限的管理命令
根據現有的模型自動生成和同步權限，移除不存在的模型的權限
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.db import transaction
from system.views import PERMISSION_NAME_TRANSLATIONS
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "自動同步權限，根據現有模型生成權限並移除不存在的模型的權限"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬執行，不實際修改資料庫',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行，即使有風險',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("開始自動同步權限..."))
        
        # 獲取所有已安裝的應用
        installed_apps = apps.get_app_configs()
        
        # 定義需要管理權限的應用
        target_apps = [
            'equip', 'material', 'scheduling', 'process', 'quality', 
            'workorder', 'kanban', 'erp_integration', 'ai', 'system'
        ]
        
        self.stdout.write(f"目標應用: {', '.join(target_apps)}")
        
        # 收集現有的模型
        existing_models = {}
        for app_config in installed_apps:
            if app_config.label in target_apps:
                models = app_config.get_models()
                existing_models[app_config.label] = []
                for model in models:
                    # 只處理有權限的模型（排除代理模型等）
                    if hasattr(model, '_meta') and model._meta.app_label == app_config.label:
                        existing_models[app_config.label].append(model)
                        self.stdout.write(f"  ✓ {app_config.label}.{model.__name__}")
        
        # 分析現有權限
        existing_permissions = Permission.objects.all()
        existing_permission_map = {}
        
        for perm in existing_permissions:
            app_label = perm.content_type.app_label
            model_name = perm.content_type.model
            key = f"{app_label}.{model_name}"
            
            if key not in existing_permission_map:
                existing_permission_map[key] = []
            existing_permission_map[key].append(perm)
        
        # 找出需要新增的權限
        permissions_to_add = []
        permissions_to_remove = []
        
        for app_label, models in existing_models.items():
            for model in models:
                model_name = model._meta.model_name
                key = f"{app_label}.{model_name}"
                
                # 檢查是否需要為此模型生成權限
                if hasattr(model._meta, 'permissions') or not model._meta.proxy:
                    # 標準權限：add, change, delete, view
                    standard_permissions = ['add', 'change', 'delete', 'view']
                    
                    for action in standard_permissions:
                        permission_name = f"Can {action} {model_name}"
                        
                        # 檢查權限是否已存在
                        existing_perm = Permission.objects.filter(
                            content_type__app_label=app_label,
                            content_type__model=model_name,
                            codename=f"{action}_{model_name}"
                        ).first()
                        
                        if not existing_perm:
                            permissions_to_add.append({
                                'name': permission_name,
                                'codename': f"{action}_{model_name}",
                                'app_label': app_label,
                                'model_name': model_name
                            })
                            self.stdout.write(f"  + 需要新增: {permission_name}")
        
        # 找出需要移除的權限（模型已不存在）
        for key, permissions in existing_permission_map.items():
            app_label, model_name = key.split('.', 1)
            
            # 檢查模型是否仍然存在
            model_exists = False
            if app_label in existing_models:
                for model in existing_models[app_label]:
                    if model._meta.model_name == model_name:
                        model_exists = True
                        break
            
            if not model_exists:
                for perm in permissions:
                    permissions_to_remove.append(perm)
                    self.stdout.write(f"  - 需要移除: {perm.name} (模型已不存在)")
        
        # 顯示統計
        self.stdout.write(f"\n權限同步統計:")
        self.stdout.write(f"  需要新增: {len(permissions_to_add)} 個權限")
        self.stdout.write(f"  需要移除: {len(permissions_to_remove)} 個權限")
        
        if not permissions_to_add and not permissions_to_remove:
            self.stdout.write(self.style.SUCCESS("所有權限都是最新的，無需同步！"))
            return
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("模擬執行模式，不會實際修改資料庫"))
            return
        
        # 確認執行
        if not options['force']:
            confirm = input("\n確定要執行權限同步嗎？這將修改資料庫 (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("操作已取消")
                return
        
        # 執行同步
        try:
            with transaction.atomic():
                # 移除不存在的權限
                if permissions_to_remove:
                    self.stdout.write("\n開始移除不存在的權限...")
                    for perm in permissions_to_remove:
                        self.stdout.write(f"  移除: {perm.name}")
                        perm.delete()
                    
                    self.stdout.write(self.style.SUCCESS(f"已移除 {len(permissions_to_remove)} 個權限"))
                
                # 新增需要的權限
                if permissions_to_add:
                    self.stdout.write("\n開始新增權限...")
                    added_count = 0
                    
                    for perm_info in permissions_to_add:
                        # 獲取或創建 ContentType
                        content_type, created = ContentType.objects.get_or_create(
                            app_label=perm_info['app_label'],
                            model=perm_info['model_name']
                        )
                        
                        # 創建權限
                        permission, created = Permission.objects.get_or_create(
                            content_type=content_type,
                            codename=perm_info['codename'],
                            defaults={'name': perm_info['name']}
                        )
                        
                        if created:
                            added_count += 1
                            self.stdout.write(f"  新增: {perm_info['name']}")
                    
                    self.stdout.write(self.style.SUCCESS(f"已新增 {added_count} 個權限"))
                
                # 更新權限翻譯
                self.stdout.write("\n更新權限翻譯...")
                updated_count = 0
                
                for perm in Permission.objects.all():
                    if perm.name in PERMISSION_NAME_TRANSLATIONS:
                        # 檢查是否需要更新
                        if perm.name != PERMISSION_NAME_TRANSLATIONS[perm.name]:
                            old_name = perm.name
                            perm.name = PERMISSION_NAME_TRANSLATIONS[perm.name]
                            perm.save()
                            updated_count += 1
                            self.stdout.write(f"  更新翻譯: {old_name} → {perm.name}")
                
                self.stdout.write(self.style.SUCCESS(f"已更新 {updated_count} 個權限翻譯"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"同步過程中發生錯誤: {str(e)}"))
            logger.error(f"權限同步失敗: {str(e)}")
            raise
        
        # 顯示最終統計
        self.stdout.write("\n權限同步完成！")
        total_permissions = Permission.objects.count()
        translated_permissions = sum(
            1 for perm in Permission.objects.all()
            if perm.name in PERMISSION_NAME_TRANSLATIONS
        )
        
        self.stdout.write(f"總權限數: {total_permissions}")
        self.stdout.write(f"有翻譯的權限數: {translated_permissions}")
        self.stdout.write(f"翻譯覆蓋率: {translated_permissions/total_permissions*100:.1f}%")
        
        # 建議
        self.stdout.write("\n建議:")
        self.stdout.write("1. 定期執行此命令來保持權限同步")
        self.stdout.write("2. 新增模型後執行此命令來生成權限")
        self.stdout.write("3. 刪除模型後執行此命令來清理權限")
        self.stdout.write("4. 使用 --dry-run 參數來預覽變更")
