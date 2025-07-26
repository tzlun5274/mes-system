# quality/views.py
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import (
    InspectionItem,
    InspectionRecord,
    DefectiveProduct,
    FinalInspectionReport,
    AOITestReport,
)
from .utils import log_user_operation

# 設定品質管理模組的日誌記錄器
quality_logger = logging.getLogger("quality")
quality_handler = logging.FileHandler("/var/log/mes/quality.log")
quality_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
quality_logger.addHandler(quality_handler)
quality_logger.setLevel(logging.INFO)


# 檢查用戶是否屬於「品質使用者」群組，或者是超級用戶
def quality_user_required(user):
    return user.is_superuser or user.groups.filter(name="品質使用者").exists()


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def index(request):
    log_user_operation(request.user.username, "quality", "訪問品質管理模組首頁")
    inspection_items = InspectionItem.objects.all()[:5]
    inspection_records = InspectionRecord.objects.all()[:5]
    defective_products = DefectiveProduct.objects.all()[:5]
    final_inspections = FinalInspectionReport.objects.all()[:5]
    aoi_test_reports = AOITestReport.objects.all()[:5]

    return render(
        request,
        "quality/index.html",
        {
            "inspection_items": inspection_items,
            "inspection_records": inspection_records,
            "defective_products": defective_products,
            "final_inspections": final_inspections,
            "aoi_test_reports": aoi_test_reports,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def inspection_items(request):
    log_user_operation(request.user.username, "quality", "查看檢驗項目定義")
    inspection_items = InspectionItem.objects.all()
    return render(
        request,
        "quality/inspection_items.html",
        {
            "inspection_items": inspection_items,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def inspection_records(request):
    log_user_operation(request.user.username, "quality", "查看檢驗記錄")
    inspection_records = InspectionRecord.objects.all()
    return render(
        request,
        "quality/inspection_records.html",
        {
            "inspection_records": inspection_records,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def defective_products(request):
    log_user_operation(request.user.username, "quality", "查看不良品記錄")
    defective_products = DefectiveProduct.objects.all()
    return render(
        request,
        "quality/defective_products.html",
        {
            "defective_products": defective_products,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def final_inspection(request):
    log_user_operation(request.user.username, "quality", "查看製成檢驗/入庫檢驗表")
    final_inspections = FinalInspectionReport.objects.all()
    return render(
        request,
        "quality/final_inspection.html",
        {
            "final_inspections": final_inspections,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def aoi_test_report(request):
    log_user_operation(request.user.username, "quality", "查看 AOI 測試報告")
    aoi_test_reports = AOITestReport.objects.all()
    return render(
        request,
        "quality/aoi_test_report.html",
        {
            "aoi_test_reports": aoi_test_reports,
        },
    )


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def get_inspection_items(request):
    log_user_operation(request.user.username, "quality", "通過 API 獲取檢驗項目列表")
    inspection_items = InspectionItem.objects.all()
    inspection_items_data = [
        {
            "id": item.id,
            "name": item.name,
            "standard": item.standard,
            "requirement": item.requirement,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in inspection_items
    ]
    return JsonResponse({"inspection_items": inspection_items_data})


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def get_inspection_records(request):
    log_user_operation(request.user.username, "quality", "通過 API 獲取檢驗記錄列表")
    inspection_records = InspectionRecord.objects.all()
    inspection_records_data = [
        {
            "id": record.id,
            "inspection_item": record.inspection_item.name,
            "product_name": record.product_name,
            "inspection_date": record.inspection_date.isoformat(),
            "result": record.result,
            "remarks": record.remarks,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }
        for record in inspection_records
    ]
    return JsonResponse({"inspection_records": inspection_records_data})


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def get_defective_products(request):
    log_user_operation(request.user.username, "quality", "通過 API 獲取不良品記錄列表")
    defective_products = DefectiveProduct.objects.all()
    defective_products_data = [
        {
            "id": product.id,
            "product_name": product.product_name,
            "defect_reason": product.defect_reason,
            "quantity": product.quantity,
            "defect_date": product.defect_date.isoformat(),
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
        }
        for product in defective_products
    ]
    return JsonResponse({"defective_products": defective_products_data})


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def get_final_inspections(request):
    log_user_operation(
        request.user.username, "quality", "通過 API 獲取製成檢驗/入庫檢驗表列表"
    )
    final_inspections = FinalInspectionReport.objects.all()
    final_inspections_data = [
        {
            "id": inspection.id,
            "product_name": inspection.product_name,
            "inspection_date": inspection.inspection_date.isoformat(),
            "meets_standards": inspection.meets_standards,
            "remarks": inspection.remarks,
            "created_at": inspection.created_at.isoformat(),
            "updated_at": inspection.updated_at.isoformat(),
        }
        for inspection in final_inspections
    ]
    return JsonResponse({"final_inspections": final_inspections_data})


@login_required
@user_passes_test(quality_user_required, login_url="/accounts/login/")
def get_aoi_test_reports(request):
    log_user_operation(
        request.user.username, "quality", "通過 API 獲取 AOI 測試報告列表"
    )
    aoi_test_reports = AOITestReport.objects.all()
    aoi_test_reports_data = [
        {
            "id": report.id,
            "product_name": report.product_name,
            "test_date": report.test_date.isoformat(),
            "defect_detected": report.defect_detected,
            "defect_details": report.defect_details,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }
        for report in aoi_test_reports
    ]
    return JsonResponse({"aoi_test_reports": aoi_test_reports_data})
