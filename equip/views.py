import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Equipment, EquipOperationLog
from django.utils import timezone
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.http import HttpResponse, JsonResponse
import tablib
import json
from production.models import ProductionLine

# 設定設備管理模組的日誌記錄器
equip_logger = logging.getLogger("equip")
equip_handler = logging.FileHandler("/var/log/mes/equip.log")
equip_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
equip_logger.addHandler(equip_handler)
equip_logger.setLevel(logging.INFO)

# 這個檔案是設備管理的主要程式，負責處理設備的新增、編輯、刪除、查詢、匯入、匯出等功能。
# 匯入與匯出功能只會處理「設備名稱、型號、狀態、所屬產線」四個欄位，讓大家操作更簡單。
# 每個功能區塊都會有詳細中文註解，讓完全不懂程式的人也能看懂。


# 定義匯入匯出資源類
class EquipmentResource(resources.ModelResource):
    production_line = fields.Field(
        column_name="production_line",
        attribute="production_line",
        widget=ForeignKeyWidget(ProductionLine, "line_name"),
    )

    class Meta:
        model = Equipment
        fields = ("name", "model", "status", "production_line")
        export_order = ("name", "model", "status", "production_line")
        import_id_fields = ("name",)
        skip_unchanged = True
        report_skipped = False

    def before_import_row(self, row, **kwargs):
        if "production_line" not in row or not row["production_line"]:
            row["production_line"] = None  # 預設為空


# 檢查用戶是否屬於「設備使用者」群組，或者是超級用戶
def equip_user_required(user):
    return user.is_superuser or user.groups.filter(name="設備使用者").exists()


# 檢查是否為超級管理員
def superuser_required(user):
    return user.is_superuser


@login_required
@user_passes_test(equip_user_required, login_url="/accounts/login/")
def index(request):
    """設備管理首頁"""
    equip_logger.info(f"用戶 {request.user.username} 訪問設備管理首頁")
    EquipOperationLog.objects.create(
        user=request.user.username, action="查看設備管理首頁", timestamp=timezone.now()
    )
    equipments = Equipment.objects.select_related("production_line").all()
    return render(request, "equip/index.html", {"equipments": equipments})


@login_required
@user_passes_test(equip_user_required, login_url="/accounts/login/")
def add_equipment(request):
    """新增設備"""
    EquipOperationLog.objects.create(
        user=request.user.username, action="嘗試新增設備", timestamp=timezone.now()
    )

    if request.method == "POST":
        name = request.POST.get("name")
        model = request.POST.get("model", "")
        status = request.POST.get("status", "idle")
        production_line_id = request.POST.get("production_line")

        if not name:
            messages.error(request, "請輸入設備名稱！")
            return render(request, "equip/add_equipment.html", {})

        if Equipment.objects.filter(name__iexact=name).exists():
            messages.error(request, f"設備名稱 '{name}' 已存在（不區分大小寫），請選擇其他名稱！")
            return render(
                request,
                "equip/add_equipment.html",
                {
                    "name": name,
                    "model": model,
                    "status": status,
                    "production_line_id": production_line_id,
                },
            )

        # 處理產線
        production_line = None
        if production_line_id:
            production_line = ProductionLine.objects.filter(
                id=production_line_id, is_active=True
            ).first()

        equipment = Equipment(
            name=name, model=model, status=status, production_line=production_line
        )
        equipment.save()

        messages.success(request, f"設備 {name} 新增成功！")
        EquipOperationLog.objects.create(
            user=request.user.username,
            action=f"成功新增設備 {name}",
            timestamp=timezone.now(),
        )
        return redirect("equip:index")

    production_lines = ProductionLine.objects.filter(is_active=True)
    return render(
        request, "equip/add_equipment.html", {"production_lines": production_lines}
    )


@login_required
@user_passes_test(equip_user_required, login_url="/accounts/login/")
def equipment_detail(request, equipment_id):
    """設備詳細資訊"""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    EquipOperationLog.objects.create(
        user=request.user.username,
        action=f"查看設備詳細資訊 {equipment.name}",
        timestamp=timezone.now(),
    )
    return render(request, "equip/equipment_detail.html", {"equipment": equipment})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def export_equipment(request):
    """
    匯出設備資料到 Excel
    只會匯出「設備名稱、型號、狀態、所屬產線」四個欄位
    """
    resource = EquipmentResource()
    dataset = resource.export()
    # 產生 xlsx 格式的 Excel 檔案
    response = HttpResponse(
        dataset.export("xlsx"),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="equipment_export.xlsx"'
    # 記錄操作日誌
    EquipOperationLog.objects.create(
        user=request.user.username, action="匯出設備資料", timestamp=timezone.now()
    )
    return response


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def import_equipment(request):
    """
    匯入設備資料（只允許 name, model, status, production_line 四個欄位）
    會自動檢查欄位與資料格式，錯誤會顯示友善訊息
    """
    if request.method == "POST":
        try:
            file = request.FILES["file"]
            if not file.name.endswith(".xls") and not file.name.endswith(".xlsx"):
                messages.error(request, "請上傳 Excel 檔案！")
                return render(request, "equip/import_equipment.html", {})
            # 只允許這四個欄位
            required_headers = ["name", "model", "status", "production_line"]
            resource = EquipmentResource()
            dataset = tablib.Dataset()
            dataset.load(file.read())
            # 檢查欄位是否正確
            headers = [str(header).strip() for header in dataset.headers]
            missing_headers = [h for h in required_headers if h not in headers]
            if missing_headers:
                messages.error(request, f'缺少必要欄位：{", ".join(missing_headers)}')
                return render(request, "equip/import_equipment.html", {})
            # 匯入資料
            result = resource.import_data(dataset, dry_run=False)
            if result.has_errors():
                messages.error(request, "匯入過程中發生錯誤，請檢查資料格式！")
            else:
                messages.success(request, f"成功匯入 {result.total_rows} 筆設備資料！")
                EquipOperationLog.objects.create(
                    user=request.user.username,
                    action=f"匯入設備資料 {result.total_rows} 筆",
                    timestamp=timezone.now(),
                )
        except Exception as e:
            messages.error(request, f"匯入失敗：{str(e)}")
    return render(request, "equip/import_equipment.html", {})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def edit_equipment(request, equipment_id):
    """編輯設備"""
    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        name = request.POST.get("name")
        model = request.POST.get("model", "")
        status = request.POST.get("status", "idle")
        production_line_id = request.POST.get("production_line")

        if not name:
            messages.error(request, "請輸入設備名稱！")
            return render(
                request, "equip/edit_equipment.html", {"equipment": equipment}
            )

        if name != equipment.name and Equipment.objects.filter(name__iexact=name).exists():
            messages.error(request, f"設備名稱 '{name}' 已存在（不區分大小寫），請選擇其他名稱！")
            return render(
                request, "equip/edit_equipment.html", {"equipment": equipment}
            )

        # 處理產線
        production_line = None
        if production_line_id:
            production_line = ProductionLine.objects.filter(
                id=production_line_id, is_active=True
            ).first()

        equipment.name = name
        equipment.model = model
        equipment.status = status
        equipment.production_line = production_line
        equipment.save()

        messages.success(request, f"設備 {name} 修改成功！")
        EquipOperationLog.objects.create(
            user=request.user.username,
            action=f"修改設備 {name}",
            timestamp=timezone.now(),
        )
        return redirect("equip:index")

    production_lines = ProductionLine.objects.filter(is_active=True)
    return render(
        request,
        "equip/edit_equipment.html",
        {"equipment": equipment, "production_lines": production_lines},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def delete_equipment(request, equipment_id):
    """刪除設備"""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    name = equipment.name

    equipment.delete()
    messages.success(request, f"設備 {name} 已刪除！")
    EquipOperationLog.objects.create(
        user=request.user.username, action=f"刪除設備 {name}", timestamp=timezone.now()
    )
    return redirect("equip:index")


@login_required
@user_passes_test(equip_user_required, login_url="/accounts/login/")
def get_equipments(request):
    """API：取得設備列表"""
    equipments = Equipment.objects.select_related("production_line").all()
    data = []
    for equipment in equipments:
        data.append(
            {
                "id": equipment.id,
                "name": equipment.name,
                "model": equipment.model,
                "status": equipment.get_status_display(),
                "production_line": (
                    equipment.production_line.line_name
                    if equipment.production_line
                    else None
                ),
            }
        )
    return JsonResponse({"equipments": data})
