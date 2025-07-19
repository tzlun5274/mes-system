import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from .models import (
    ProcessName,
    Operator,
    OperatorSkill,
    ProductProcessRoute,
    ProcessEquipment,
    ProductProcessStandardCapacity,
    CapacityHistory,
)
from .utils import log_user_operation
from .views_process_names import *
from .views_operators import *
from .views_product_routes import *
from django.views.decorators.csrf import csrf_exempt
import csv, io
from django.utils import timezone
import pandas as pd

# 設定製程管理模組的日誌記錄器
process_logger = logging.getLogger("process")
process_handler = logging.FileHandler("/var/log/mes/process.log")
process_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
process_logger.addHandler(process_handler)
process_logger.setLevel(logging.INFO)


# 檢查用戶是否屬於「工序使用者」群組，或者是超級用戶
def process_user_required(user):
    return user.is_superuser or user.groups.filter(name="工序使用者").exists()


@login_required
@user_passes_test(process_user_required, login_url="/accounts/login/")
def index(request):
    log_user_operation(request.user.username, "process", "訪問工序管理模組首頁")
    
    # 計算統計資料
    from .models import ProcessName, Operator, ProductProcessRoute, ProductProcessStandardCapacity
    
    # 工序總數
    process_count = ProcessName.objects.count()
    
    # 作業員總數
    operator_count = Operator.objects.count()
    
    # 產品路線總數（不重複的產品編號）
    product_route_count = ProductProcessRoute.objects.values('product_id').distinct().count()
    
    # 產能設定總數
    capacity_count = ProductProcessStandardCapacity.objects.count()
    
    context = {
        'process_count': process_count,
        'operator_count': operator_count,
        'product_route_count': product_route_count,
        'capacity_count': capacity_count,
    }
    
    return render(request, "process/index.html", context)


# API 視圖：返回所有工序名稱
@login_required
@user_passes_test(process_user_required, login_url="/accounts/login/")
def api_process_names(request):
    log_user_operation(request.user.username, "process", "API 請求: 獲取工序名稱列表")
    processes = []
    for process in ProcessName.objects.all():
        # 獲取設備 ID
        equipment_ids = list(process.equipments.values_list("equipment_id", flat=True))

        processes.append(
            {
                "id": process.id,
                "name": process.name,
                "description": process.description or "",
                "usable_equipment_ids": ",".join(map(str, equipment_ids)),
            }
        )
    return JsonResponse({"process_names": processes})


# API 視圖：返回所有作業員及其技能
@login_required
@user_passes_test(process_user_required, login_url="/accounts/login/")
def api_operators(request):
    log_user_operation(request.user.username, "process", "API 請求: 獲取作業員列表")
    operators = []
    for operator in Operator.objects.all():
        skills = OperatorSkill.objects.filter(operator=operator).values(
            "process_name__id", "process_name__name", "priority"
        )
        operators.append(
            {"id": operator.id, "name": operator.name, "skills": list(skills)}
        )
    return JsonResponse({"operators": operators})


# API 視圖：返回產品工藝路線，可按產品編號過濾
@login_required
@user_passes_test(process_user_required, login_url="/accounts/login/")
def api_product_routes(request):
    log_user_operation(
        request.user.username, "process", "API 請求: 獲取產品工藝路線列表"
    )
    product_id = request.GET.get("product_id", None)
    queryset = ProductProcessRoute.objects.all()
    if product_id:
        queryset = queryset.filter(product_id=product_id)
    routes = queryset.values(
        "product_id",
        "process_name__id",
        "process_name__name",
        "step_order",
        "capacity_per_hour",
        "usable_equipment_ids",
        "dependent_semi_product",
    )
    # 格式化 routes，確保 usable_equipment_ids 為有效格式
    formatted_routes = []
    for route in routes:
        equipment_ids = route["usable_equipment_ids"] or ""
        # 清理設備 ID，確保逗號分隔
        if equipment_ids:
            ids = [eid.strip() for eid in equipment_ids.split(",") if eid.strip()]
            route["usable_equipment_ids"] = ",".join(ids)
        else:
            route["usable_equipment_ids"] = ""
        route["dependent_semi_product"] = route["dependent_semi_product"] or ""
        formatted_routes.append(route)
    return JsonResponse({"product_routes": formatted_routes})


def standard_capacity_list(request):
    """
    標準產能設定管理頁面 - 符合電子製造業行業標準
    顯示所有產品+工序的標準產能，支援多維度查詢、編輯、匯入/匯出
    """
    # 篩選條件
    product_code = request.GET.get("product_code", "")
    process_name = request.GET.get("process_name", "")
    equipment_type = request.GET.get("equipment_type", "")
    operator_level = request.GET.get("operator_level", "")
    is_active = request.GET.get("is_active", "")
    
    # 排序條件
    sort_by = request.GET.get("sort_by", "product_code")
    sort_order = request.GET.get("sort_order", "asc")

    capacities = ProductProcessStandardCapacity.objects.all()

    if product_code:
        capacities = capacities.filter(product_code__icontains=product_code)
    if process_name:
        capacities = capacities.filter(process_name__icontains=process_name)
    if equipment_type:
        capacities = capacities.filter(equipment_type=equipment_type)
    if operator_level:
        capacities = capacities.filter(operator_level=operator_level)
    if is_active != "":
        capacities = capacities.filter(is_active=is_active == "true")

    # 處理排序
    if sort_order == "desc":
        sort_by = f"-{sort_by}"
    
    # 如果是按產品編號排序，需要特殊處理以支援數字排序
    if sort_by == "product_code" or sort_by == "-product_code":
        # 先按產品編號排序，再按其他欄位排序
        if sort_by == "product_code":
            capacities = capacities.order_by(
                "product_code", "process_name", "equipment_type", "operator_level", "-version"
            )
        else:
            capacities = capacities.order_by(
                "-product_code", "process_name", "equipment_type", "operator_level", "-version"
            )
    else:
        # 其他欄位排序
        capacities = capacities.order_by(sort_by, "product_code", "process_name", "equipment_type", "operator_level", "-version")

    # 計算統計數據
    total_capacities = capacities.count()
    active_capacities = capacities.filter(is_active=True).count()
    process_count = capacities.values("process_name").distinct().count()
    product_count = capacities.values("product_code").distinct().count()

    # 取得選項資料
    process_names = ProcessName.objects.values_list("name", flat=True).distinct()
    equipment_types = ProductProcessStandardCapacity._meta.get_field(
        "equipment_type"
    ).choices
    operator_levels = ProductProcessStandardCapacity._meta.get_field(
        "operator_level"
    ).choices

    context = {
        "capacities": capacities,
        "process_names": process_names,
        "equipment_types": equipment_types,
        "operator_levels": operator_levels,
        "filters": {
            "product_code": product_code,
            "process_name": process_name,
            "equipment_type": equipment_type,
            "operator_level": operator_level,
            "is_active": is_active,
        },
        "sort": {
            "sort_by": sort_by.replace("-", "") if sort_by.startswith("-") else sort_by,
            "sort_order": sort_order,
        },
        # 統計數據
        "total_capacities": total_capacities,
        "active_capacities": active_capacities,
        "process_count": process_count,
        "product_count": product_count,
    }

    return render(request, "process/standard_capacity_list.html", context)


@csrf_exempt
def standard_capacity_create(request):
    """
    處理標準產能單筆新增（AJAX）- 支援多維度設定
    """
    if request.method == "POST":
        try:
            # 基本資訊
            product_code = request.POST.get("product_code", "").strip()
            process_name = request.POST.get("process_name", "").strip()
            equipment_type = request.POST.get("equipment_type", "standard")
            operator_level = request.POST.get("operator_level", "standard")
            # 產能參數
            standard_capacity = request.POST.get(
                "standard_capacity_per_hour", ""
            ).strip()
            min_capacity = request.POST.get("min_capacity_per_hour", "0").strip()
            max_capacity = request.POST.get("max_capacity_per_hour", "0").strip()
            # 時間因素
            setup_time = request.POST.get("setup_time_minutes", "0").strip()
            teardown_time = request.POST.get("teardown_time_minutes", "0").strip()
            cycle_time = request.POST.get("cycle_time_seconds", "0").strip()
            # 批量設定
            optimal_batch = request.POST.get("optimal_batch_size", "1").strip()
            min_batch = request.POST.get("min_batch_size", "1").strip()
            max_batch = request.POST.get("max_batch_size", "1000").strip()
            # 效率因子
            efficiency_factor = request.POST.get("efficiency_factor", "1.00").strip()
            learning_curve = request.POST.get("learning_curve_factor", "1.00").strip()
            # 品質因素
            defect_rate = request.POST.get("expected_defect_rate", "0.0000").strip()
            rework_factor = request.POST.get("rework_time_factor", "1.00").strip()
            # 版本號
            version = request.POST.get("version", "1").strip()
            if not version.isdigit() or int(version) <= 0:
                version = 1
            # 驗證必填欄位
            if not all([product_code, process_name, standard_capacity]):
                return JsonResponse(
                    {"success": False, "message": "請填寫產品編號、工序名稱和標準產能"}
                )
            # 驗證數值
            if not standard_capacity.isdigit() or int(standard_capacity) <= 0:
                return JsonResponse(
                    {"success": False, "message": "標準產能必須為正整數"}
                )
            # 檢查重複
            if ProductProcessStandardCapacity.objects.filter(
                product_code=product_code,
                process_name=process_name,
                equipment_type=equipment_type,
                operator_level=operator_level,
                is_active=True,
            ).exists():
                return JsonResponse(
                    {
                        "success": False,
                        "message": "此產品+工序+設備+作業員等級組合已存在",
                    }
                )
            # 建立新記錄
            obj = ProductProcessStandardCapacity.objects.create(
                product_code=product_code,
                process_name=process_name,
                equipment_type=equipment_type,
                operator_level=operator_level,
                standard_capacity_per_hour=int(standard_capacity),
                min_capacity_per_hour=(
                    int(min_capacity) if min_capacity.isdigit() else 0
                ),
                max_capacity_per_hour=(
                    int(max_capacity) if max_capacity.isdigit() else 0
                ),
                setup_time_minutes=int(setup_time) if setup_time.isdigit() else 0,
                teardown_time_minutes=(
                    int(teardown_time) if teardown_time.isdigit() else 0
                ),
                cycle_time_seconds=(
                    float(cycle_time) if cycle_time.replace(".", "").isdigit() else 0
                ),
                optimal_batch_size=int(optimal_batch) if optimal_batch.isdigit() else 1,
                min_batch_size=int(min_batch) if min_batch.isdigit() else 1,
                max_batch_size=int(max_batch) if max_batch.isdigit() else 1000,
                efficiency_factor=(
                    float(efficiency_factor)
                    if efficiency_factor.replace(".", "").isdigit()
                    else 1.00
                ),
                learning_curve_factor=(
                    float(learning_curve)
                    if learning_curve.replace(".", "").isdigit()
                    else 1.00
                ),
                expected_defect_rate=(
                    float(defect_rate)
                    if defect_rate.replace(".", "").isdigit()
                    else 0.0000
                ),
                rework_time_factor=(
                    float(rework_factor)
                    if rework_factor.replace(".", "").isdigit()
                    else 1.00
                ),
                version=int(version),
                created_by=request.user.username,
                notes=request.POST.get("notes", "").strip(),
            )
            # 記錄歷史
            CapacityHistory.objects.create(
                capacity=obj,
                change_type="created",
                changed_by=request.user.username,
                change_reason="新增標準產能設定",
            )
            return JsonResponse({"success": True, "message": "新增成功"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"新增失敗：{str(e)}"})
    return JsonResponse({"success": False, "message": "不支援的請求方法"})


@csrf_exempt
def standard_capacity_update(request, pk):
    """
    處理標準產能更新（AJAX）
    """
    if request.method == "POST":
        try:
            obj = ProductProcessStandardCapacity.objects.get(pk=pk)
            # 儲存舊值
            old_values = {
                "standard_capacity_per_hour": obj.standard_capacity_per_hour,
                "efficiency_factor": float(obj.efficiency_factor),
                "setup_time_minutes": obj.setup_time_minutes,
                "cycle_time_seconds": float(obj.cycle_time_seconds),
                "optimal_batch_size": obj.optimal_batch_size,
            }
            # 更新欄位
            obj.standard_capacity_per_hour = int(
                request.POST.get(
                    "standard_capacity_per_hour", obj.standard_capacity_per_hour
                )
            )
            obj.efficiency_factor = float(
                request.POST.get("efficiency_factor", obj.efficiency_factor)
            )
            obj.learning_curve_factor = float(
                request.POST.get("learning_curve_factor", obj.learning_curve_factor)
            )
            obj.setup_time_minutes = int(
                request.POST.get("setup_time_minutes", obj.setup_time_minutes)
            )
            obj.cycle_time_seconds = float(
                request.POST.get("cycle_time_seconds", obj.cycle_time_seconds)
            )
            obj.optimal_batch_size = int(
                request.POST.get("optimal_batch_size", obj.optimal_batch_size)
            )
            obj.notes = request.POST.get("notes", obj.notes)
            obj.save()
            # 記錄歷史
            new_values = {
                "standard_capacity_per_hour": obj.standard_capacity_per_hour,
                "efficiency_factor": float(obj.efficiency_factor),
                "setup_time_minutes": obj.setup_time_minutes,
                "cycle_time_seconds": float(obj.cycle_time_seconds),
                "optimal_batch_size": obj.optimal_batch_size,
            }
            CapacityHistory.objects.create(
                capacity=obj,
                change_type="updated",
                old_values=old_values,
                new_values=new_values,
                changed_by=request.user.username,
                change_reason="更新標準產能設定",
            )
            return JsonResponse({"success": True, "message": "更新成功"})
        except ProductProcessStandardCapacity.DoesNotExist:
            return JsonResponse({"success": False, "message": "找不到指定的產能設定"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"更新失敗：{str(e)}"})
    elif request.method == "GET":
        try:
            obj = ProductProcessStandardCapacity.objects.get(pk=pk)
            return JsonResponse(
                {
                    "success": True,
                    "data": {
                        "product_code": obj.product_code,
                        "process_name": obj.process_name,
                        "equipment_type": obj.equipment_type,
                        "operator_level": obj.operator_level,
                        "standard_capacity_per_hour": obj.standard_capacity_per_hour,
                        "efficiency_factor": float(obj.efficiency_factor),
                        "learning_curve_factor": obj.learning_curve_factor,
                        "setup_time_minutes": obj.setup_time_minutes,
                        "cycle_time_seconds": float(obj.cycle_time_seconds),
                        "optimal_batch_size": obj.optimal_batch_size,
                        "notes": obj.notes,
                    },
                }
            )
        except ProductProcessStandardCapacity.DoesNotExist:
            return JsonResponse({"success": False, "message": "找不到指定的產能設定"})
    return JsonResponse({"success": False, "message": "不支援的請求方法"})


@csrf_exempt
def standard_capacity_delete(request, pk):
    """
    處理標準產能刪除（AJAX）
    """
    if request.method == "POST":
        try:
            obj = ProductProcessStandardCapacity.objects.get(pk=pk)
            # 記錄歷史
            CapacityHistory.objects.create(
                capacity=obj,
                change_type="deactivated",
                changed_by=request.user.username,
                change_reason="刪除標準產能設定",
            )
            obj.delete()
            return JsonResponse({"success": True, "message": "刪除成功"})
        except ProductProcessStandardCapacity.DoesNotExist:
            return JsonResponse({"success": False, "message": "找不到指定的產能設定"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"刪除失敗：{str(e)}"})
    return JsonResponse({"success": False, "message": "不支援的請求方法"})


@csrf_exempt
def standard_capacity_delete_all(request):
    """
    處理標準產能全部刪除（AJAX）
    """
    if request.method == "POST":
        try:
            # 取得篩選條件
            product_code = request.POST.get("product_code", "").strip()
            process_name = request.POST.get("process_name", "").strip()
            equipment_type = request.POST.get("equipment_type", "").strip()
            operator_level = request.POST.get("operator_level", "").strip()
            is_active = request.POST.get("is_active", "").strip()
            
            # 建立查詢條件
            capacities = ProductProcessStandardCapacity.objects.all()
            
            if product_code:
                capacities = capacities.filter(product_code__icontains=product_code)
            if process_name:
                capacities = capacities.filter(process_name__icontains=process_name)
            if equipment_type:
                capacities = capacities.filter(equipment_type=equipment_type)
            if operator_level:
                capacities = capacities.filter(operator_level=operator_level)
            if is_active != "":
                capacities = capacities.filter(is_active=is_active == "true")
            
            # 計算要刪除的數量
            delete_count = capacities.count()
            
            if delete_count == 0:
                return JsonResponse({"success": False, "message": "沒有符合條件的資料可刪除"})
            
            # 記錄歷史（批次記錄）
            for obj in capacities:
                CapacityHistory.objects.create(
                    capacity=obj,
                    change_type="deactivated",
                    changed_by=request.user.username,
                    change_reason="批次刪除標準產能設定",
                )
            
            # 批次刪除
            capacities.delete()
            
            return JsonResponse({
                "success": True, 
                "message": f"批次刪除成功！共刪除 {delete_count} 筆資料"
            })
            
        except Exception as e:
            return JsonResponse({"success": False, "message": f"批次刪除失敗：{str(e)}"})
    
    return JsonResponse({"success": False, "message": "不支援的請求方法"})


@csrf_exempt
def standard_capacity_export(request):
    """
    匯出標準產能資料為 Excel
    """
    # 取得所有啟用的產能設定
    capacities = ProductProcessStandardCapacity.objects.filter(is_active=True).order_by(
        "product_code", "process_name", "equipment_type", "operator_level"
    )

    # 準備資料
    data = []
    for obj in capacities:
        data.append(
            {
                "產品編號": obj.product_code,
                "工序名稱": obj.process_name,
                "設備類型": obj.get_equipment_type_display(),
                "作業員等級": obj.get_operator_level_display(),
                "標準產能(pcs/hr)": obj.standard_capacity_per_hour,
                "效率因子": float(obj.efficiency_factor),
                "學習曲線因子": float(obj.learning_curve_factor),
                "換線時間(分鐘)": obj.setup_time_minutes,
                "週期時間(秒)": float(obj.cycle_time_seconds),
                "最佳批量": obj.optimal_batch_size,
                "預期不良率": float(obj.expected_defect_rate),
                "版本號": obj.version,
                "生效日期": obj.effective_date.strftime("%Y-%m-%d"),
                "建立者": obj.created_by,
                "備註": obj.notes,
            }
        )

    # 建立 DataFrame
    df = pd.DataFrame(data)

    # 建立 Excel 檔案
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="標準產能設定.xlsx"'

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="標準產能設定", index=False)

        # 格式化工作表
        worksheet = writer.sheets["標準產能設定"]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    return response


@csrf_exempt
def standard_capacity_import(request):
    """
    從 Excel 匯入標準產能資料
    """
    if request.method == "POST":
        try:
            file = request.FILES.get("file")
            if not file:
                return JsonResponse({"success": False, "message": "請選擇檔案"})

            # 讀取 Excel 檔案
            if file.name.endswith(".csv"):
                df = pd.read_csv(file, encoding="utf-8")
            else:
                df = pd.read_excel(file)

            # 驗證必要欄位
            required_columns = ["產品編號", "工序名稱", "標準產能(pcs/hr)"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f'缺少必要欄位：{", ".join(missing_columns)}',
                    }
                )

            # 處理每一行資料
            success_count = 0
            error_count = 0
            skip_count = 0
            errors = []
            
            # 檢查是否為覆蓋模式
            overwrite_mode = request.POST.get("overwrite_mode", "false") == "true"

            for index, row in df.iterrows():
                try:
                    # 基本資料
                    product_code = str(row["產品編號"]).strip()
                    process_name = str(row["工序名稱"]).strip()
                    
                    # 安全處理標準產能
                    try:
                        standard_capacity = int(row["標準產能(pcs/hr)"]) if pd.notna(row["標準產能(pcs/hr)"]) else 0
                    except (ValueError, TypeError):
                        standard_capacity = 0
                    
                    # 安全處理版本號
                    try:
                        version = int(row["版本號"]) if pd.notna(row.get("版本號")) else 1
                    except (ValueError, TypeError):
                        version = 1

                    # 可選欄位
                    equipment_type = str(row.get("設備類型", "標準設備")).strip()
                    operator_level = str(row.get("作業員等級", "標準")).strip()
                    
                    # 安全地處理數值欄位，使用 pandas 的 pd.notna() 來檢查是否為空值
                    try:
                        efficiency_factor = float(row["效率因子"]) if pd.notna(row.get("效率因子")) else 1.00
                    except (ValueError, TypeError):
                        efficiency_factor = 1.00
                    
                    try:
                        setup_time = int(row["換線時間(分鐘)"]) if pd.notna(row.get("換線時間(分鐘)")) else 0
                    except (ValueError, TypeError):
                        setup_time = 0
                    
                    try:
                        cycle_time = float(row["週期時間(秒)"]) if pd.notna(row.get("週期時間(秒)")) else 0
                    except (ValueError, TypeError):
                        cycle_time = 0
                    
                    try:
                        optimal_batch = int(row["最佳批量"]) if pd.notna(row.get("最佳批量")) else 1
                    except (ValueError, TypeError):
                        optimal_batch = 1
                    
                    notes = str(row.get("備註", "")).strip()
                    
                    # 處理可能為空的欄位，給予預設值
                    try:
                        min_capacity = int(row["最低產能"]) if pd.notna(row.get("最低產能")) else 0
                    except (ValueError, TypeError):
                        min_capacity = 0
                    
                    try:
                        max_capacity = int(row["最高產能"]) if pd.notna(row.get("最高產能")) else 0
                    except (ValueError, TypeError):
                        max_capacity = 0
                    
                    try:
                        teardown_time = int(row["收線時間(分鐘)"]) if pd.notna(row.get("收線時間(分鐘)")) else 0
                    except (ValueError, TypeError):
                        teardown_time = 0
                    
                    try:
                        min_batch = int(row["最小批量"]) if pd.notna(row.get("最小批量")) else 1
                    except (ValueError, TypeError):
                        min_batch = 1
                    
                    try:
                        max_batch = int(row["最大批量"]) if pd.notna(row.get("最大批量")) else 1000
                    except (ValueError, TypeError):
                        max_batch = 1000
                    
                    try:
                        learning_curve = float(row["學習曲線因子"]) if pd.notna(row.get("學習曲線因子")) else 1.00
                    except (ValueError, TypeError):
                        learning_curve = 1.00
                    
                    try:
                        defect_rate = float(row["預期不良率"]) if pd.notna(row.get("預期不良率")) else 0.0000
                    except (ValueError, TypeError):
                        defect_rate = 0.0000
                    
                    try:
                        rework_factor = float(row["重工時間因子"]) if pd.notna(row.get("重工時間因子")) else 1.00
                    except (ValueError, TypeError):
                        rework_factor = 1.00

                    # 檢查是否已存在
                    existing_record = ProductProcessStandardCapacity.objects.filter(
                        product_code=product_code,
                        process_name=process_name,
                        equipment_type=equipment_type,
                        operator_level=operator_level,
                        is_active=True,
                    ).first()
                    
                    if existing_record:
                        if overwrite_mode:
                            # 覆蓋模式：更新現有記錄
                            existing_record.standard_capacity_per_hour = standard_capacity
                            existing_record.min_capacity_per_hour = min_capacity
                            existing_record.max_capacity_per_hour = max_capacity
                            existing_record.efficiency_factor = efficiency_factor
                            existing_record.learning_curve_factor = learning_curve
                            existing_record.setup_time_minutes = setup_time
                            existing_record.teardown_time_minutes = teardown_time
                            existing_record.cycle_time_seconds = cycle_time
                            existing_record.optimal_batch_size = optimal_batch
                            existing_record.min_batch_size = min_batch
                            existing_record.max_batch_size = max_batch
                            existing_record.expected_defect_rate = defect_rate
                            existing_record.rework_time_factor = rework_factor
                            existing_record.notes = notes
                            existing_record.version = version
                            existing_record.save()
                            success_count += 1
                        else:
                            # 一般模式：跳過已存在的記錄
                            skip_count += 1
                            continue
                    else:
                        # 建立新記錄
                        ProductProcessStandardCapacity.objects.create(
                            product_code=product_code,
                            process_name=process_name,
                            equipment_type=equipment_type,
                            operator_level=operator_level,
                            standard_capacity_per_hour=standard_capacity,
                            min_capacity_per_hour=min_capacity,
                            max_capacity_per_hour=max_capacity,
                            efficiency_factor=efficiency_factor,
                            learning_curve_factor=learning_curve,
                            setup_time_minutes=setup_time,
                            teardown_time_minutes=teardown_time,
                            cycle_time_seconds=cycle_time,
                            optimal_batch_size=optimal_batch,
                            min_batch_size=min_batch,
                            max_batch_size=max_batch,
                            expected_defect_rate=defect_rate,
                            rework_time_factor=rework_factor,
                            created_by=request.user.username,
                            notes=notes,
                            version=version,
                        )
                        success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"第 {index + 2} 行：{str(e)}")

            # 回傳結果
            message = f"匯入完成！成功：{success_count} 筆，跳過：{skip_count} 筆，失敗：{error_count} 筆"
            if skip_count > 0:
                message += "\n💡 跳過的記錄是因為已存在相同的產品+工序+設備+作業員等級組合"
            if errors:
                message += f'\n❌ 錯誤詳情：{"; ".join(errors[:5])}'  # 只顯示前5個錯誤
            if success_count == 0 and skip_count > 0:
                message += "\n⚠️ 所有記錄都已存在，如需更新請先刪除舊記錄或使用覆蓋模式"

            return JsonResponse(
                {"success": True, "message": message, "count": success_count}
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"匯入失敗：{str(e)}"})

    return JsonResponse({"success": False, "message": "不支援的請求方法"})


def capacity_calculator(request):
    """
    產能計算器頁面 - 提供互動式產能計算功能
    """
    return render(request, "process/capacity_calculator.html", {})


# 確保所有視圖可導出
__all__ = [
    "index",
    "process_names",
    "add_process_name",
    "edit_process_name",
    "delete_process_name",
    "export_process_names",
    "import_process_names",
    "operators",
    "add_operator",
    "edit_operator",
    "delete_operator",
    "export_operators",
    "import_operators",
    "product_routes",
    "add_product_route",
    "edit_product_route",
    "delete_product_route",
    "export_product_routes",
    "import_product_routes",
    "api_process_names",
    "api_operators",
    "api_product_routes",
]
