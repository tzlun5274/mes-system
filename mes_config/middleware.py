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
        
        # 一般用戶預設為公司代號 01
        return '01'


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