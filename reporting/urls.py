"""
報表模組 URL 配置 - 佔位符版本
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表模組首頁
    path('', views.ReportingIndexView.as_view(), name='index'),
    
    # 通用佔位符 - 用於所有未實現的功能
    path('<str:function_name>/', views.placeholder_view, name='placeholder'),
] 