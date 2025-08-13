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
    path("cancel-approve/<int:pk>/", views.cancel_approve_fill_work, name="cancel_approve_fill_work"),
    path("reject/<int:pk>/", views.reject_fill_work, name="reject_fill_work"),
    path("delete/<int:pk>/", views.delete_fill_work, name="fill_work_delete"),
    path("delete-all/", views.delete_all_fill_work_records, name="fill_work_delete_all"),
    
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
    path("supervisor/pending/", views.SupervisorPendingListView.as_view(), name="supervisor_pending_list"),
    path("supervisor/reviewed/", views.SupervisorReviewedListView.as_view(), name="supervisor_reviewed_list"),
    # 填報功能設定
    path("settings/", views.FillWorkSettingsView.as_view(), name="fill_work_settings"),
    path("settings/data/", views.FillWorkDataSettingsView.as_view(), name="fill_work_settings_data"),
    path("settings/data/operator/", views.FillWorkDataOperatorView.as_view(), name="fill_work_settings_data_operator"),
    path("settings/data/smt/", views.FillWorkDataSMTView.as_view(), name="fill_work_settings_data_smt"),
    # 匯入/匯出與範本
    path("settings/data/operator/download-template/", views.download_fill_work_template_operator, name="fill_work_template_operator"),
    path("settings/data/smt/download-template/", views.download_fill_work_template_smt, name="fill_work_template_smt"),
    path("settings/data/operator/download-template-xlsx/", views.download_fill_work_template_operator_xlsx, name="fill_work_template_operator_xlsx"),
    path("settings/data/smt/download-template-xlsx/", views.download_fill_work_template_smt_xlsx, name="fill_work_template_smt_xlsx"),
    path("settings/data/operator/import/", views.import_fill_work_records_operator, name="fill_work_import_operator"),
    path("settings/data/smt/import/", views.import_fill_work_records_smt, name="fill_work_import_smt"),
    path("settings/data/operator/export/", views.export_fill_work_records_operator, name="fill_work_export_operator"),
    path("settings/data/smt/export/", views.export_fill_work_records_smt, name="fill_work_export_smt"),
    path("settings/data/operator/export-xlsx/", views.export_fill_work_records_operator_xlsx, name="fill_work_export_operator_xlsx"),
    path("settings/data/smt/export-xlsx/", views.export_fill_work_records_smt_xlsx, name="fill_work_export_smt_xlsx"),
    
    # API 功能
    path("api/workorder-data/", views.get_workorder_data, name="get_workorder_data"),
    path("api/workorder-list/", views.get_workorder_list, name="get_workorder_list"),
    path("api/product-list/", views.get_product_list, name="get_product_list"),
    path("api/workorder-by-product/", views.get_workorder_by_product, name="get_workorder_by_product"),
    path("api/workorder-info/", views.get_workorder_info, name="get_workorder_info"),
    path("api/products-by-company/", views.get_products_by_company, name="get_products_by_company"),
    path("api/all-workorder-numbers/", views.get_all_workorder_numbers, name="get_all_workorder_numbers"),
] 