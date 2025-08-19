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

    # 作業員填報作業
    path("operator/", views.OperatorIndexView.as_view(), name="operator_index"),
    path("operator/backfill/create/", views.OperatorBackfillCreateView.as_view(), name="operator_backfill_create"),
    path("operator/rd-backfill/create/", views.OperatorRDBackfillCreateView.as_view(), name="operator_rd_backfill_create"),
    path("operator/list/", views.FillWorkListView.as_view(), name="fill_work_list"),

    # SMT填報作業
    path("smt/", views.SMTIndexView.as_view(), name="smt_index"),
    path("smt/backfill/create/", views.SMTBackfillCreateView.as_view(), name="smt_backfill_create"),
    path("smt/rd-backfill/create/", views.SMTRDBackfillCreateView.as_view(), name="smt_rd_backfill_create"),

    # 主管審核
    path("supervisor/", views.SupervisorApprovalIndexView.as_view(), name="supervisor_approval_index"),
    path("supervisor/pending/", views.SupervisorPendingListView.as_view(), name="supervisor_pending_list"),
    path("supervisor/reviewed/", views.SupervisorReviewedListView.as_view(), name="supervisor_reviewed_list"),

    # 審核操作
    path("supervisor/<int:pk>/approve/", views.approve_fill_work, name="approve_fill_work"),
    path("supervisor/<int:pk>/reject/", views.reject_fill_work, name="reject_fill_work"),
    path("supervisor/<int:pk>/cancel-approve/", views.cancel_approve_fill_work, name="cancel_approve_fill_work"),

    # 填報記錄詳情
    path("<int:pk>/detail/", views.FillWorkDetailView.as_view(), name="fill_work_detail"),
    path("<int:pk>/delete/", views.FillWorkDeleteView.as_view(), name="fill_work_delete"),

    # 功能設定
    path("settings/", views.FillWorkSettingsView.as_view(), name="fill_work_settings"),
    path("settings/data/", views.FillWorkDataSettingsView.as_view(), name="fill_work_settings_data"),
    path("settings/data/operator/", views.FillWorkDataOperatorView.as_view(), name="fill_work_settings_data_operator"),
    path("settings/data/smt/", views.FillWorkDataSMTView.as_view(), name="fill_work_settings_data_smt"),

    # 模板下載
    path("settings/data/operator/template/", views.download_fill_work_template_operator, name="fill_work_template_operator"),
    path("settings/data/smt/template/", views.download_fill_work_template_smt, name="fill_work_template_smt"),
    path("settings/data/operator/template-xlsx/", views.download_fill_work_template_operator_xlsx, name="fill_work_template_operator_xlsx"),
    path("settings/data/smt/template-xlsx/", views.download_fill_work_template_smt_xlsx, name="fill_work_template_smt_xlsx"),

    # 資料匯入
    path("settings/data/operator/import/", views.import_fill_work_records_operator, name="fill_work_import_operator"),
    path("settings/data/smt/import/", views.import_fill_work_records_smt, name="fill_work_import_smt"),

    # 資料匯出功能
    path("settings/data/operator/export/", views.export_fill_work_records_operator, name="fill_work_export_operator"),
    path("settings/data/smt/export/", views.export_fill_work_records_smt, name="fill_work_export_smt"),
    path("settings/data/operator/export-xlsx/", views.export_fill_work_records_operator_xlsx, name="fill_work_export_operator_xlsx"),
    path("settings/data/smt/export-xlsx/", views.export_fill_work_records_smt_xlsx, name="fill_work_export_smt_xlsx"),

    # 批次操作
    path("batch/delete/", views.batch_delete_fill_work, name="batch_delete_fill_work"),
    path("batch/approve/", views.batch_approve_fill_work, name="batch_approve_fill_work"),
    path("batch/unapprove/", views.batch_unapprove_fill_work, name="batch_unapprove_fill_work"),

    # 測試路由
    path('test_multi_filter/', views.test_multi_filter, name='test_multi_filter'),
] 