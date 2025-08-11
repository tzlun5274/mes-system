"""
填報作業管理子模組 - URL 配置
負責填報作業的 URL 路由配置
"""

from django.urls import path
from . import views

app_name = "fill_work"

urlpatterns = [
    # 填報作業首頁
    path("", views.FillWorkIndexView.as_view(), name="fill_work_index"),
    
    # 統一填報作業管理
    path("list/", views.FillWorkListView.as_view(), name="fill_work_list"),
    path("create/", views.FillWorkCreateView.as_view(), name="fill_work_create"),
    path("edit/<int:pk>/", views.FillWorkUpdateView.as_view(), name="fill_work_edit"),
    path("detail/<int:pk>/", views.FillWorkDetailView.as_view(), name="fill_work_detail"),
    path("delete/<int:pk>/", views.FillWorkDeleteView.as_view(), name="fill_work_delete"),
    
    # 作業員填報首頁
    path("operator/", views.OperatorFillWorkIndexView.as_view(), name="operator_fill_index"),
    
    # 四種專門的填報類型
    path("operator/backfill/", views.OperatorBackfillView.as_view(), name="operator_backfill"),
    path("operator/rd-backfill/", views.OperatorRDBackfillView.as_view(), name="operator_rd_backfill"),
    path("smt/backfill/", views.SMTBackfillView.as_view(), name="smt_backfill"),
    path("smt/rd-backfill/", views.SMTRDBackfillView.as_view(), name="smt_rd_backfill"),
    
    # 核准/駁回功能
    path("approve/<int:work_id>/", views.approve_fill_work, name="approve_fill_work"),
    path("reject/<int:work_id>/", views.reject_fill_work, name="reject_fill_work"),
    
    # API 功能
    path("api/workorder-info/", views.get_workorder_info, name="get_workorder_info"),
] 