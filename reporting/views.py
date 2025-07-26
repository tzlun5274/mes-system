import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from .models import (
    ProductionDailyReport,
    OperatorPerformance,
    ReportSyncSettings,
    ReportEmailSchedule,
    ReportEmailLog,
    ReportingOperationLog,
)
from .utils import log_user_operation  # 導入 log_user_operation
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime
from .tasks import sync_operator_performance_task
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from reporting.models import ManufacturingWorkHour
import pandas as pd
from django.db import models

# 設定報表模組的日誌記錄器
reporting_logger = logging.getLogger("reporting")
reporting_handler = logging.FileHandler("/var/log/mes/reporting.log")
reporting_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
reporting_logger.addHandler(reporting_handler)
reporting_logger.setLevel(logging.INFO)


# 檢查用戶是否屬於「報表使用者」群組，或者是超級用戶
def reporting_user_required(user):
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def index(request):
    # 記錄用戶操作
    log_user_operation(request.user.username, "reporting", "訪問報表模組首頁")
    production_reports = ProductionDailyReport.objects.all()[:5]
    operator_reports = OperatorPerformance.objects.all()[:5]
    return render(
        request,
        "reporting/index.html",
        {
            "production_reports": production_reports,
            "operator_reports": operator_reports,
        },
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def production_daily(request):
    # 記錄用戶操作
    log_user_operation(request.user.username, "reporting", "查看生產日報表")
    production_reports = ProductionDailyReport.objects.all().order_by(
        "-date", "operator_name"
    )

    if "download" in request.GET:
        # 記錄下載操作
        log_user_operation(
            request.user.username, "reporting", "下載生產日報表 Excel 文件"
        )
        # 創建 Excel 文件
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "生產日報表"

        # 寫入表頭
        headers = [
            "日期",
            "作業員姓名",
            "設備名稱",
            "生產線",
            "工序名稱",
            "完成數量",
            "工作時數",
            "效率 (件/小時)",
            "完成率 (%)",
        ]
        for col_num, header in enumerate(headers, 1):
            col_letter = get_column_letter(col_num)
            worksheet[f"{col_letter}1"] = header

        # 寫入數據
        for row_num, report in enumerate(production_reports, 2):
            worksheet[f"A{row_num}"] = report.date.strftime("%Y-%m-%d")
            worksheet[f"B{row_num}"] = report.operator_name
            worksheet[f"C{row_num}"] = report.equipment_name
            worksheet[f"D{row_num}"] = report.get_line_display()
            worksheet[f"E{row_num}"] = report.process_name
            worksheet[f"F{row_num}"] = report.completed_quantity
            worksheet[f"G{row_num}"] = report.work_hours
            worksheet[f"H{row_num}"] = report.efficiency_rate
            worksheet[f"I{row_num}"] = report.completion_rate

        # 設置響應頭以下載 Excel 文件
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            "attachment; filename=production_daily_report.xlsx"
        )
        workbook.save(response)
        return response

    return render(
        request,
        "reporting/production_daily.html",
        {
            "production_reports": production_reports,
        },
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def operator_performance(request):
    # 顯示所有欄位
    log_user_operation(request.user.username, "reporting", "查看作業員生產報表")
    operator_reports = OperatorPerformance.objects.all()

    if "download" in request.GET:
        log_user_operation(
            request.user.username, "reporting", "下載作業員生產報表 Excel 文件"
        )
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "作業員生產報表"
        # 新增詳細欄位
        headers = [
            "作業員名稱",
            "工單",
            "產品名稱",
            "生產數量",
            "開始時間",
            "結束時間",
            "日期",
            "工序",
            "設備名稱",
        ]
        for col_num, header in enumerate(headers, 1):
            col_letter = get_column_letter(col_num)
            worksheet[f"{col_letter}1"] = header
        for row_num, report in enumerate(operator_reports, 2):
            worksheet[f"A{row_num}"] = report.operator_name
            worksheet[f"B{row_num}"] = report.work_order
            worksheet[f"C{row_num}"] = report.product_name
            worksheet[f"D{row_num}"] = report.production_quantity
            worksheet[f"E{row_num}"] = (
                report.start_time.strftime("%Y-%m-%d %H:%M:%S")
                if report.start_time
                else ""
            )
            worksheet[f"F{row_num}"] = (
                report.end_time.strftime("%Y-%m-%d %H:%M:%S") if report.end_time else ""
            )
            worksheet[f"G{row_num}"] = report.date.strftime("%Y-%m-%d")
            worksheet[f"H{row_num}"] = report.process_name
            worksheet[f"I{row_num}"] = report.equipment_name
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            "attachment; filename=operator_performance_report.xlsx"
        )
        workbook.save(response)
        return response
    return render(
        request,
        "reporting/operator_performance.html",
        {
            "operator_reports": operator_reports,
        },
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def get_production_daily(request):
    # 記錄用戶操作
    log_user_operation(
        request.user.username, "reporting", "通過 API 獲取生產日報表數據"
    )
    production_reports = ProductionDailyReport.objects.all()
    production_reports_data = [
        {
            "id": report.id,
            "date": report.date.strftime("%Y-%m-%d"),
            "line": report.line,
            "production_quantity": report.production_quantity,
            "completed_quantity": report.completed_quantity,
            "completion_rate": report.completion_rate,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }
        for report in production_reports
    ]
    return JsonResponse({"production_reports": production_reports_data})


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def get_operator_performance(request):
    # 回傳所有欄位
    log_user_operation(
        request.user.username, "reporting", "通過 API 獲取作業員生產報表數據"
    )
    operator_reports = OperatorPerformance.objects.all()
    operator_reports_data = [
        {
            "id": report.id,
            "operator_name": report.operator_name,
            "equipment_name": report.equipment_name,
            "production_quantity": report.production_quantity,
            "equipment_usage_rate": report.equipment_usage_rate,
            "date": report.date.strftime("%Y-%m-%d"),
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }
        for report in operator_reports
    ]
    return JsonResponse({"operator_reports": operator_reports_data})


@csrf_exempt
@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def manual_sync_smt_report(request):
    """
    手動觸發SMT生產報表同步的API
    """
    sync_smt_report_task.delay()
    return JsonResponse(
        {"success": True, "message": "已開始同步SMT生產報表，請稍後刷新頁面"}
    )


@csrf_exempt
@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def manual_sync_operator_performance(request):
    """
    手動觸發作業員生產報表同步的API
    """
    sync_operator_performance_task.delay()
    return JsonResponse(
        {"success": True, "message": "已開始同步作業員生產報表，請稍後刷新頁面"}
    )


@csrf_exempt
@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def update_sync_interval(request):
    """
    更新報表同步間隔設定的API
    """
    if request.method == "POST":
        try:
            report_type = request.POST.get("report_type")
            sync_interval_hours = int(request.POST.get("sync_interval_hours", 24))

            # 驗證輸入
            if report_type not in ["smt", "operator"]:
                return JsonResponse({"success": False, "message": "無效的報表類型"})

            if sync_interval_hours < 1 or sync_interval_hours > 168:  # 1小時到7天
                return JsonResponse(
                    {"success": False, "message": "同步間隔必須在1-168小時之間"}
                )

            # 更新或創建設定
            setting, created = ReportSyncSettings.objects.update_or_create(
                report_type=report_type,
                defaults={
                    "sync_interval_hours": sync_interval_hours,
                    "is_active": True,
                },
            )

            # 記錄操作
            action = f"更新{setting.get_report_type_display()}同步間隔為{sync_interval_hours}小時"
            log_user_operation(request.user.username, "reporting", action)

            return JsonResponse(
                {
                    "success": True,
                    "message": f"{setting.get_report_type_display()}同步間隔已更新為{sync_interval_hours}小時",
                }
            )

        except ValueError:
            return JsonResponse(
                {"success": False, "message": "同步間隔必須是有效的數字"}
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": f"更新失敗：{str(e)}"})

    return JsonResponse({"success": False, "message": "只支援POST請求"})


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def get_sync_settings(request):
    """
    取得報表同步設定的API
    """
    try:
        smt_setting = ReportSyncSettings.objects.filter(report_type="smt").first()
        operator_setting = ReportSyncSettings.objects.filter(
            report_type="operator"
        ).first()

        settings = {
            "smt": {
                "sync_interval_hours": (
                    smt_setting.sync_interval_hours if smt_setting else 24
                ),
                "is_active": smt_setting.is_active if smt_setting else True,
            },
            "operator": {
                "sync_interval_hours": (
                    operator_setting.sync_interval_hours if operator_setting else 24
                ),
                "is_active": operator_setting.is_active if operator_setting else True,
            },
        }

        return JsonResponse({"success": True, "settings": settings})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"取得設定失敗：{str(e)}"})


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def email_schedule_list(request):
    """
    報表郵件發送設定列表頁面
    """
    log_user_operation(request.user.username, "reporting", "查看報表郵件發送設定")
    schedules = ReportEmailSchedule.objects.all().order_by(
        "report_type", "schedule_type"
    )
    return render(
        request,
        "reporting/email_schedule_list.html",
        {
            "schedules": schedules,
        },
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def email_schedule_create(request):
    """
    創建報表郵件發送設定
    """
    if request.method == "POST":
        try:
            schedule = ReportEmailSchedule.objects.create(
                report_type=request.POST.get("report_type"),
                schedule_type=request.POST.get("schedule_type", "daily"),
                send_time=request.POST.get("send_time"),
                recipients=request.POST.get("recipients", ""),
                cc_recipients=request.POST.get("cc_recipients", ""),
                subject_template=request.POST.get(
                    "subject_template", "MES 系統 - {report_type} - {date}"
                ),
                is_active=request.POST.get("is_active") == "on",
            )
            log_user_operation(
                request.user.username, "reporting", f"創建報表郵件發送設定: {schedule}"
            )
            messages.success(request, f"報表郵件發送設定已創建：{schedule}")
            return redirect("reporting:email_schedule_list")
        except Exception as e:
            messages.error(request, f"創建設定失敗：{str(e)}")

    return render(
        request,
        "reporting/email_schedule_form.html",
        {"title": "創建報表郵件發送設定", "action": "create"},
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def email_schedule_edit(request, schedule_id):
    """
    編輯報表郵件發送設定
    """
    try:
        schedule = ReportEmailSchedule.objects.get(id=schedule_id)
    except ReportEmailSchedule.DoesNotExist:
        messages.error(request, "找不到指定的設定")
        return redirect("reporting:email_schedule_list")

    if request.method == "POST":
        try:
            schedule.report_type = request.POST.get("report_type")
            schedule.schedule_type = request.POST.get("schedule_type", "daily")
            schedule.send_time = request.POST.get("send_time")
            schedule.recipients = request.POST.get("recipients", "")
            schedule.cc_recipients = request.POST.get("cc_recipients", "")
            schedule.subject_template = request.POST.get(
                "subject_template", "MES 系統 - {report_type} - {date}"
            )
            schedule.is_active = request.POST.get("is_active") == "on"
            schedule.save()

            log_user_operation(
                request.user.username, "reporting", f"更新報表郵件發送設定: {schedule}"
            )
            messages.success(request, f"報表郵件發送設定已更新：{schedule}")
            return redirect("reporting:email_schedule_list")
        except Exception as e:
            messages.error(request, f"更新設定失敗：{str(e)}")

    return render(
        request,
        "reporting/email_schedule_form.html",
        {"title": "編輯報表郵件發送設定", "action": "edit", "schedule": schedule},
    )


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def email_schedule_delete(request, schedule_id):
    """
    刪除報表郵件發送設定
    """
    try:
        schedule = ReportEmailSchedule.objects.get(id=schedule_id)
        schedule_name = str(schedule)
        schedule.delete()

        log_user_operation(
            request.user.username, "reporting", f"刪除報表郵件發送設定: {schedule_name}"
        )
        messages.success(request, f"報表郵件發送設定已刪除：{schedule_name}")
    except ReportEmailSchedule.DoesNotExist:
        messages.error(request, "找不到指定的設定")
    except Exception as e:
        messages.error(request, f"刪除設定失敗：{str(e)}")

    return redirect("reporting:email_schedule_list")


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def email_log_list(request):
    """
    報表郵件發送記錄列表
    """
    log_user_operation(request.user.username, "reporting", "查看報表郵件發送記錄")
    logs = ReportEmailLog.objects.all().order_by("-sent_at")[:100]  # 只顯示最近100筆
    return render(
        request,
        "reporting/email_log_list.html",
        {
            "logs": logs,
        },
    )


@csrf_exempt
@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def test_send_report_email(request):
    """
    測試發送報表郵件
    """
    if request.method == "POST":
        try:
            schedule_id = request.POST.get("schedule_id")
            schedule = ReportEmailSchedule.objects.get(id=schedule_id)

            # 執行測試發送
            from .tasks import send_daily_reports_email

            send_daily_reports_email.delay()

            log_user_operation(
                request.user.username, "reporting", f"測試發送報表郵件: {schedule}"
            )
            return JsonResponse(
                {"success": True, "message": f"測試郵件已發送：{schedule}"}
            )
        except ReportEmailSchedule.DoesNotExist:
            return JsonResponse({"success": False, "message": "找不到指定的設定"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"發送失敗：{str(e)}"})

    return JsonResponse({"success": False, "message": "只支援POST請求"})


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def clear_report_data(request):
    """
    清除報表資料的視圖函數
    GET：顯示清除頁面
    POST：執行清除
    """
    if request.method == "GET":
        return render(request, "reporting/clear_data.html")
    try:
        clear_type = request.POST.get("clear_type", "reports_only")
        date_range = request.POST.get("date_range", "").strip()
        with transaction.atomic():
            cleared_count = 0
            # 處理日期範圍
            date_filter = {}
            if date_range:
                try:
                    start_date, end_date = date_range.split(",")
                    from datetime import datetime

                    start_date = datetime.strptime(
                        start_date.strip(), "%Y-%m-%d"
                    ).date()
                    end_date = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
                    date_filter = {"date__range": [start_date, end_date]}
                except ValueError:
                    messages.error(
                        request, "日期格式錯誤，請使用 YYYY-MM-DD,YYYY-MM-DD 格式"
                    )
                    return redirect("reporting:index")
            # 根據清除類型執行相應操作
            if clear_type == "all":
                cleared_count += _clear_all_report_data(date_filter)
                message = f"成功清除所有報表資料，共 {cleared_count} 筆記錄"
            elif clear_type == "reports_only":
                cleared_count += _clear_reports_only(date_filter)
                message = f"成功清除報表資料，共 {cleared_count} 筆記錄"
            elif clear_type == "logs_only":
                cleared_count += _clear_logs_only()
                message = f"成功清除日誌資料，共 {cleared_count} 筆記錄"
            elif clear_type == "settings_only":
                cleared_count += _clear_settings_only()
                message = f"成功清除設定資料，共 {cleared_count} 筆記錄"
            else:
                messages.error(request, "無效的清除類型")
                return redirect("reporting:index")
            # 記錄操作日誌
            _log_operation(
                f"用戶 {request.user.username} 清除報表資料，類型：{clear_type}，共清除 {cleared_count} 筆記錄"
            )
            messages.success(request, message)
    except Exception as e:
        messages.error(request, f"清除資料時發生錯誤：{str(e)}")
    return redirect("reporting:index")


def _clear_all_report_data(date_filter):
    """清除所有報表相關資料"""
    count = 0
    count += _clear_reports_only(date_filter)
    count += _clear_logs_only()
    count += _clear_settings_only()
    return count


def _clear_reports_only(date_filter):
    """只清除報表資料"""
    count = 0

    # 清除生產日報表
    if date_filter:
        count += ProductionDailyReport.objects.filter(**date_filter).delete()[0]
    else:
        count += ProductionDailyReport.objects.all().delete()[0]

    # 清除作業員績效報表
    if date_filter:
        count += OperatorPerformance.objects.filter(**date_filter).delete()[0]
    else:
        count += OperatorPerformance.objects.all().delete()[0]

    return count


def _clear_logs_only():
    """只清除日誌資料"""
    count = 0
    count += ReportingOperationLog.objects.all().delete()[0]
    count += ReportEmailLog.objects.all().delete()[0]
    return count


def _clear_settings_only():
    """只清除設定資料"""
    count = 0
    count += ReportSyncSettings.objects.all().delete()[0]
    count += ReportEmailSchedule.objects.all().delete()[0]
    return count


def _log_operation(action):
    """記錄操作到日誌"""
    try:
        ReportingOperationLog.objects.create(user="system", action=action)
    except Exception:
        pass


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def manufacturing_workhour_list(request):
    """
    製造工時單資料查詢頁面，可查詢、篩選、匯出 Excel
    """
    qs = ManufacturingWorkHour.objects.all().order_by("-date", "operator")
    # 支援簡單查詢
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            models.Q(operator__icontains=search)
            | models.Q(company__icontains=search)
            | models.Q(order_number__icontains=search)
            | models.Q(equipment_name__icontains=search)
            | models.Q(work_content__icontains=search)
        )
    # 匯出 Excel
    if "download" in request.GET:
        df = pd.DataFrame(list(qs.values()))
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            "attachment; filename=manufacturing_workhour.xlsx"
        )
        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return response
    return render(
        request,
        "reporting/manufacturing_workhour_list.html",
        {
            "workhours": qs,
            "search": search,
        },
    )
