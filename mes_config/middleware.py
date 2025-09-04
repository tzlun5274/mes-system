"""
自定義中間件，用於處理 session 中斷和資料庫連線問題
"""

import logging
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.exceptions import SessionInterrupted
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger(__name__)


class RobustSessionMiddleware(SessionMiddleware):
    """
    增強版的 Session 中間件，能夠更好地處理 session 中斷問題
    """
    
    def process_response(self, request, response):
        """
        處理響應，如果 session 中斷則重定向到登入頁面
        """
        try:
            # 調用父類的 process_response 方法
            return super().process_response(request, response)
        except SessionInterrupted as e:
            logger.warning(f"Session 中斷，用戶將被重定向到登入頁面: {str(e)}")
            
            # 如果是 AJAX 請求，返回 JSON 響應
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'session_interrupted',
                    'message': '會話已中斷，請重新登入',
                    'redirect_url': '/accounts/login/'
                }, status=401)
            
            # 對於普通請求，重定向到登入頁面
            logout(request)
            return HttpResponseRedirect('/accounts/login/')
        except Exception as e:
            logger.error(f"Session 處理過程中發生未預期的錯誤: {str(e)}")
            
            # 如果是 AJAX 請求，返回 JSON 響應
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'session_error',
                    'message': '會話處理錯誤，請重新登入',
                    'redirect_url': '/accounts/login/'
                }, status=500)
            
            # 對於普通請求，重定向到登入頁面
            logout(request)
            return HttpResponseRedirect('/accounts/login/')


class DatabaseConnectionMiddleware:
    """
    資料庫連線檢查中間件
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 檢查資料庫連線
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            logger.error(f"資料庫連線檢查失敗: {str(e)}")
            # 如果資料庫連線失敗，重定向到錯誤頁面
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect('/database-error/')
        
        response = self.get_response(request)
        return response 


class CompanyCodeMiddleware:
    """
    公司代號中間件
    實現多公司資料隔離
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 為請求添加公司代號屬性
        request.company_code = self._get_company_code(request)
        response = self.get_response(request)
        return response
    
    def _get_company_code(self, request):
        """
        獲取用戶的公司代號
        優先順序：1. 用戶設定 2. 會話 3. 預設值
        """
        if not request.user.is_authenticated:
            return None
        
        # 從用戶設定獲取公司代號
        if hasattr(request.user, 'profile') and request.user.profile.company_code:
            return request.user.profile.company_code
        
        # 從會話獲取公司代號
        company_code = request.session.get('company_code')
        if company_code:
            return company_code
        
        # 預設公司代號（超級用戶可以看到所有公司）
        if request.user.is_superuser:
            return None
        
        # 一般用戶預設為公司代號 10（耀儀科技）
        return '10'


class DataIsolationMiddleware:
    """
    資料隔離中間件
    確保用戶只能看到自己公司的資料
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 為請求添加資料隔離屬性
        request.data_isolation_enabled = self._should_enable_isolation(request)
        response = self.get_response(request)
        return response
    
    def _should_enable_isolation(self, request):
        """
        判斷是否啟用資料隔離
        """
        # 超級用戶不啟用資料隔離
        if request.user.is_superuser:
            return False
        
        # 管理員不啟用資料隔離
        if request.user.is_staff:
            return False
        
        # 一般用戶啟用資料隔離
        return True


class PermissionCheckMiddleware:
    """
    權限檢查中間件
    實現細分化權限管理功能
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 為請求添加權限檢查屬性
        request.permission_check_enabled = self._should_enable_permission_check(request)
        
        if request.permission_check_enabled:
            # 載入用戶的權限細分設定
            self._load_user_permissions(request)
        
        response = self.get_response(request)
        return response
    
    def _should_enable_permission_check(self, request):
        """
        判斷是否啟用權限檢查
        """
        # 檢查用戶是否已登入
        if not request.user.is_authenticated:
            return False
        
        # 所有已登入用戶都啟用權限檢查
        return True
    
    def _load_user_permissions(self, request):
        """
        載入用戶的權限細分設定
        """
        try:
            from system.models import UserPermissionDetail
            
            # 獲取用戶的權限細分設定
            permission_detail, created = UserPermissionDetail.objects.get_or_create(
                user=request.user,
                defaults={
                    'can_operate_all_operators': True,
                    'can_operate_all_processes': True,
                    'can_operate_all_equipments': True,
                    'can_fill_work': True,
                    'can_onsite_reporting': True,
                    'can_smt_reporting': False,
                    'can_access_equip': True,
                    'can_access_workorder': True,
                    'can_access_quality': True,
                    'can_access_material': True,
                    'can_access_scheduling': True,
                    'can_access_process': True,
                    'can_access_reporting': True,
                    'can_access_kanban': True,
                    'can_access_ai': True,
                    'can_view': True,
                    'can_add': True,
                    'can_edit': True,
                    'can_delete': False,
                    'can_export': True,
                    'can_import': False,
                    'can_approve': False,
                    'data_scope': 'own',
                    'can_manage_users': False,
                    'can_manage_permissions': False,
                    'can_view_logs': False,
                    'can_system_config': False,
                    'can_access_24h': True,
                    'can_access_worktime': True,
                }
            )
            
            # 超級管理員和管理員強制擁有完整權限
            if request.user.is_superuser or request.user.is_staff:
                permission_detail.can_operate_all_operators = True
                permission_detail.can_operate_all_processes = True
                permission_detail.can_operate_all_equipments = True
                permission_detail.can_fill_work = True
                permission_detail.can_onsite_reporting = True
                permission_detail.can_smt_reporting = True
                permission_detail.can_access_equip = True
                permission_detail.can_access_workorder = True
                permission_detail.can_access_quality = True
                permission_detail.can_access_material = True
                permission_detail.can_access_scheduling = True
                permission_detail.can_access_process = True
                permission_detail.can_access_reporting = True
                permission_detail.can_access_kanban = True
                permission_detail.can_access_ai = True
                permission_detail.can_view = True
                permission_detail.can_add = True
                permission_detail.can_edit = True
                permission_detail.can_delete = True
                permission_detail.can_export = True
                permission_detail.can_import = True
                permission_detail.can_approve = True
                permission_detail.data_scope = 'all'
                permission_detail.can_manage_users = True
                permission_detail.can_manage_permissions = True
                permission_detail.can_view_logs = True
                permission_detail.can_system_config = True
                permission_detail.can_access_24h = True
                permission_detail.can_access_worktime = True
                
                # 保存權限設定
                permission_detail.save()
            
            # 將權限設定添加到請求對象中
            request.user_permissions = permission_detail
            
        except Exception as e:
            # 如果載入權限失敗，記錄錯誤但不阻擋請求
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"載入用戶權限失敗: {str(e)}")
            
            # 創建一個預設的權限設定
            class DefaultPermissions:
                def __init__(self):
                    self.can_operate_all_operators = True
                    self.can_operate_all_processes = True
                    self.can_operate_all_equipments = True
                    self.can_fill_work = True
                    self.can_onsite_reporting = True
                    self.can_smt_reporting = False
                    self.can_access_equip = True
                    self.can_access_workorder = True
                    self.can_access_quality = True
                    self.can_access_material = True
                    self.can_access_scheduling = True
                    self.can_access_process = True
                    self.can_access_reporting = True
                    self.can_access_kanban = True
                    self.can_access_ai = True
                    self.can_view = True
                    self.can_add = True
                    self.can_edit = True
                    self.can_delete = False
                    self.can_export = True
                    self.can_import = False
                    self.can_approve = False
                    self.data_scope = 'own'
                    self.can_manage_users = False
                    self.can_manage_permissions = False
                    self.can_view_logs = False
                    self.can_system_config = False
                    self.can_access_24h = True
                    self.can_access_worktime = True
                    self.allowed_operators = []
                    self.allowed_processes = []
                    self.allowed_equipments = []
            
            request.user_permissions = DefaultPermissions() 