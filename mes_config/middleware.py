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
                from django.http import JsonResponse
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
                from django.http import JsonResponse
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