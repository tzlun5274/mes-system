"""
填報作業管理子模組 - URL 配置
負責填報作業的 URL 路由配置
"""

from django.urls import path
from . import views

app_name = "fill_work"

urlpatterns = [
    # 填報管理首頁
    path("", views.FillWorkIndexView.as_view(), name="fill_work_index"),
    
    # 填報記錄列表
    path("list/", views.FillWorkListView.as_view(), name="fill_work_list"),
    
    # 記錄詳情 / 核准 / 駁回
    path("detail/<int:pk>/", views.FillWorkDetailView.as_view(), name="fill_work_detail"),
    path("approve/<int:pk>/", views.approve_fill_work, name="approve_fill_work"),
    path("reject/<int:pk>/", views.reject_fill_work, name="reject_fill_work"),
    path("delete/<int:pk>/", views.delete_fill_work, name="fill_work_delete"),
    
    # 作業員填報首頁
    path("operator/", views.OperatorIndexView.as_view(), name="operator_index"),
    
    # 作業員填報功能
    path("operator/backfill/create/", views.OperatorBackfillCreateView.as_view(), name="operator_backfill_create"),
    path("operator/backfill/edit/<int:pk>/", views.OperatorBackfillUpdateView.as_view(), name="operator_backfill_edit"),
    path("operator/rd-backfill/create/", views.OperatorRDBackfillCreateView.as_view(), name="operator_rd_backfill_create"),
    
    # SMT填報首頁
    path("smt/", views.SMTIndexView.as_view(), name="smt_index"),
    
    # SMT填報功能
    path("smt/backfill/create/", views.SMTBackfillCreateView.as_view(), name="smt_backfill_create"),
    path("smt/rd-backfill/create/", views.SMTRDBackfillCreateView.as_view(), name="smt_rd_backfill_create"),
    path("smt/backfill/edit/<int:pk>/", views.SMTBackfillUpdateView.as_view(), name="smt_backfill_edit"),
    
    # 主管審核首頁
    path("supervisor/", views.SupervisorApprovalIndexView.as_view(), name="supervisor_approval_index"),
    
    # API 功能
    path("api/workorder-data/", views.get_workorder_data, name="get_workorder_data"),
    path("api/workorder-list/", views.get_workorder_list, name="get_workorder_list"),
    path("api/product-list/", views.get_product_list, name="get_product_list"),
    path("api/workorder-by-product/", views.get_workorder_by_product, name="get_workorder_by_product"),
    path("api/workorder-info/", views.get_workorder_info, name="get_workorder_info"),
    path("api/products-by-company/", views.get_products_by_company, name="get_products_by_company"),
    path("api/all-workorder-numbers/", views.get_all_workorder_numbers, name="get_all_workorder_numbers"),
] 