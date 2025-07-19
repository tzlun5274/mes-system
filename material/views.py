# material/views.py
# 這個檔案定義物料管理模組的視圖函數。
# 專注於 MES 系統的生產用料管理，包括用料需求計算、缺料預警等。

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db import models
from django.utils import timezone
from decimal import Decimal
from .models import (
    Material,
    Product,
    Route,
    Process,
    MaterialRequirement,
    MaterialShortageAlert,
    MaterialSupplyPlan,
    MaterialKanban,
    MaterialInventoryManagement,
    MaterialTransaction,
    MaterialRequirementEstimation,
)
from erp_integration.models import CompanyConfig

# 設定物料管理模組的日誌記錄器
material_logger = logging.getLogger('material')
material_handler = logging.FileHandler('/var/log/mes/material.log')
material_handler.setFormatter(logging.Formatter('%(levelname)s %(asctime)s %(module)s %(message)s'))
material_logger.addHandler(material_handler)
material_logger.setLevel(logging.INFO)

# 物料管理首頁
def index(request):
    """
    物料管理首頁：顯示物料管理的主要功能入口和即時狀況
    """
    try:
        # 統計資料
        material_count = Material.objects.count()
        product_count = Product.objects.count()
        
        # 缺料警告統計
        active_alerts = MaterialShortageAlert.objects.filter(is_resolved=False)
        critical_alerts = active_alerts.filter(alert_level='critical')
        
        # 最近的材料需求
        recent_requirements = MaterialRequirement.objects.select_related('product', 'material').order_by('-id')[:5]

        # 讀取所有公司，並查詢每家公司物料數量、低庫存數量
        company_cards = []
        for company in CompanyConfig.objects.all():
            # 只查該公司物料（假設 Material 有 company_code 欄位，若無請告知）
            company_materials = Material.objects.filter(company_code=company.company_code)
            material_count = company_materials.count()
            # 低庫存（假設有 safety_stock 欄位，若無請告知）
            low_stock_count = MaterialInventoryManagement.objects.filter(material__company_code=company.company_code, current_stock__lt=models.F('safety_stock')).count()
            company_cards.append({
                'company_name': company.company_name,
                'company_code': company.company_code,
                'material_count': material_count,
                'low_stock_count': low_stock_count,
            })

        return render(request, "material/index.html", {
            "material_count": material_count,
            "product_count": product_count,
            "active_alerts": active_alerts.count(),
            "critical_alerts": critical_alerts.count(),
            "recent_requirements": recent_requirements,
            "company_cards": company_cards,
        })
    except Exception as e:
        # 如果資料庫表格不存在，顯示基本資訊
        return render(request, "material/index.html", {
            "material_count": 0,
            "product_count": 0,
            "active_alerts": 0,
            "critical_alerts": 0,
            "recent_requirements": [],
            "company_cards": [],
            "error_message": "資料庫正在重建中，請稍後再試。",
        })


# 材料列表
def material_list(request):
    """
    材料列表：顯示所有材料的基本資料
    """
    try:
        materials = Material.objects.all().order_by('name')
        
        # 搜尋功能
        search = request.GET.get('search', '')
        if search:
            materials = materials.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search) |
                models.Q(category__icontains=search)
            )
        
        return render(request, "material/material_list.html", {
            "materials": materials,
            "search": search,
        })
    except Exception as e:
        # 如果資料庫表格不存在，顯示基本資訊
        return render(request, "material/material_list.html", {
            "materials": [],
            "search": "",
            "error_message": "資料庫正在重建中，請稍後再試。",
        })


# 產品列表
def product_list(request):
    """
    產品列表：顯示所有產品的基本資料
    """
    try:
        products = Product.objects.all().order_by('name')
        
        # 搜尋功能
        search = request.GET.get('search', '')
        if search:
            products = products.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search) |
                models.Q(category__icontains=search)
            )
        
        return render(request, "material/product_list.html", {
            "products": products,
            "search": search,
        })
    except Exception as e:
        # 如果資料庫表格不存在，顯示基本資訊
        return render(request, "material/product_list.html", {
            "products": [],
            "search": "",
            "error_message": "資料庫正在重建中，請稍後再試。",
        })


# 物料需求計算
def material_requirement_calculation(request):
    """
    物料需求計算：根據產品和數量計算所需材料
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        
        if product_id and quantity:
            try:
                product = Product.objects.get(id=product_id)
                quantity = int(quantity)
                
                # 取得產品的材料需求
                requirements = MaterialRequirement.objects.filter(product=product)
                
                # 計算總需求
                total_requirements = []
                
                for req in requirements:
                    total_qty = req.quantity_per_unit * quantity
                    
                    requirement_info = {
                        'material': req.material,
                        'unit_qty': req.quantity_per_unit,
                        'total_qty': total_qty,
                        'unit': req.material.unit,
                    }
                    
                    total_requirements.append(requirement_info)
                
                return render(request, "material/material_requirement_calculation.html", {
                    "product": product,
                    "quantity": quantity,
                    "requirements": total_requirements,
                })
            except (Product.DoesNotExist, ValueError):
                messages.error(request, "產品不存在或數量格式錯誤")
    
    # GET 請求：顯示表單
    products = Product.objects.all().order_by('name')
    return render(request, "material/material_requirement_calculation.html", {
        "products": products,
    })


# 缺料警告管理
def shortage_alerts(request):
    """
    缺料警告管理：顯示和管理缺料警告
    """
    alerts = MaterialShortageAlert.objects.select_related('material').all().order_by('-created_at')
    
    # 篩選功能
    alert_level = request.GET.get('alert_level', '')
    is_resolved = request.GET.get('is_resolved', '')
    
    if alert_level:
        alerts = alerts.filter(alert_level=alert_level)
    
    if is_resolved:
        is_resolved_bool = is_resolved.lower() == 'true'
        alerts = alerts.filter(is_resolved=is_resolved_bool)
    
    return render(request, "material/shortage_alerts.html", {
        "alerts": alerts,
        "alert_level": alert_level,
        "is_resolved": is_resolved,
    })


# 解決缺料警告
def resolve_shortage_alert(request, alert_id):
    """
    解決缺料警告：標記警告為已解決
    """
    alert = get_object_or_404(MaterialShortageAlert, id=alert_id)
    
    if request.method == 'POST':
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()
        
        messages.success(request, f"缺料警告 '{alert.material.name}' 已標記為已解決")
        return redirect('material:shortage_alerts')
    
    return render(request, "material/resolve_shortage_alert.html", {
        "alert": alert,
    })


# 供應計劃管理
def supply_plan_list(request):
    """
    供應計劃管理：顯示和管理材料供應計劃
    """
    try:
        supply_plans = MaterialSupplyPlan.objects.select_related('material').all().order_by('-created_at')
        
        # 篩選功能
        status = request.GET.get('status', '')
        priority = request.GET.get('priority', '')
        
        if status:
            supply_plans = supply_plans.filter(status=status)
        
        if priority:
            supply_plans = supply_plans.filter(priority=priority)
        
        # 統計資料
        completed_plans = supply_plans.filter(status='completed')
        in_progress_plans = supply_plans.filter(status='in_progress')
        delayed_plans = supply_plans.filter(status='delayed')
        
        return render(request, "material/supply_plan_list.html", {
            "supply_plans": supply_plans,
            "completed_plans": completed_plans,
            "in_progress_plans": in_progress_plans,
            "delayed_plans": delayed_plans,
            "status": status,
            "priority": priority,
        })
    except Exception as e:
        # 如果資料庫表格不存在，顯示基本資訊
        return render(request, "material/supply_plan_list.html", {
            "supply_plans": [],
            "completed_plans": [],
            "in_progress_plans": [],
            "delayed_plans": [],
            "status": "",
            "priority": "",
            "error_message": "資料庫正在重建中，請稍後再試。",
        })


# 看板管理
def kanban_list(request):
    """
    看板管理：顯示材料看板狀態
    """
    try:
        kanbans = MaterialKanban.objects.select_related('material').all().order_by('material__name')
        
        # 篩選功能
        status = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')
        
        if status:
            kanbans = kanbans.filter(status=status)
        
        if type_filter:
            kanbans = kanbans.filter(kanban_type=type_filter)
        
        # 統計資料
        normal_kanbans = kanbans.filter(status='normal')
        warning_kanbans = kanbans.filter(status='warning')
        emergency_kanbans = kanbans.filter(status='emergency')
        
        return render(request, "material/kanban_list.html", {
            "kanbans": kanbans,
            "normal_kanbans": normal_kanbans,
            "warning_kanbans": warning_kanbans,
            "emergency_kanbans": emergency_kanbans,
            "status": status,
            "type": type_filter,
        })
    except Exception as e:
        # 如果資料庫表格不存在，顯示基本資訊
        return render(request, "material/kanban_list.html", {
            "kanbans": [],
            "normal_kanbans": [],
            "warning_kanbans": [],
            "emergency_kanbans": [],
            "status": "",
            "type": "",
            "error_message": "資料庫正在重建中，請稍後再試。",
        })


# 更新看板狀態
def update_kanban_status(request, kanban_id):
    """
    更新看板狀態：更新材料看板的狀態
    """
    kanban = get_object_or_404(MaterialKanban, id=kanban_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['normal', 'warning', 'critical']:
            kanban.status = new_status
            kanban.updated_at = timezone.now()
            kanban.save()
            
            messages.success(request, f"看板 '{kanban.material.name}' 狀態已更新為 {new_status}")
            return redirect('material:kanban_list')
    
    return render(request, "material/update_kanban_status.html", {
        "kanban": kanban,
    })


# API: 取得材料資訊
@csrf_exempt
@require_GET
def api_material_inventory(request, material_id):
    """
    API: 取得指定材料的資訊（從 ERP 同步的資料）
    """
    try:
        material = Material.objects.get(id=material_id)
        
        # 這裡可以從 ERP 同步的資料中取得庫存資訊
        # 由於 MES 不負責實際庫存異動，這裡返回基本材料資訊
        
        data = {
            'id': material.id,
            'name': material.name,
            'code': material.code,
            'category': material.category,
            'unit': material.unit,
            'sync_status': 'synced',  # 假設同步狀態
        }
        
        return JsonResponse(data)
    except Material.DoesNotExist:
        return JsonResponse({'error': '材料不存在'}, status=404)


# API: 檢查缺料狀況
@csrf_exempt
@require_GET
def api_check_shortage(request):
    """
    API: 檢查缺料狀況
    """
    material_id = request.GET.get('material_id')
    
    if not material_id:
        return JsonResponse({'error': '缺少材料 ID'}, status=400)
    
    try:
        material = Material.objects.get(id=material_id)
        
        # 檢查是否有相關的缺料警告
        alerts = MaterialShortageAlert.objects.filter(
            material=material,
            is_resolved=False
        )
        
        data = {
            'material_id': material.id,
            'material_name': material.name,
            'has_shortage': alerts.exists(),
            'alerts': list(alerts.values('alert_level', 'message', 'created_at'))
        }
        
        return JsonResponse(data)
    except Material.DoesNotExist:
        return JsonResponse({'error': '材料不存在'}, status=404)


# 庫存管理功能
def inventory_management(request):
    """
    庫存管理：顯示和管理所有材料的庫存狀況
    """
    inventories = MaterialInventoryManagement.objects.select_related('material').all().order_by('material__name')
    
    # 搜尋和篩選功能
    search = request.GET.get('search', '')
    stock_status = request.GET.get('stock_status', '')
    warehouse = request.GET.get('warehouse', '')
    
    if search:
        inventories = inventories.filter(
            models.Q(material__name__icontains=search) |
            models.Q(material__code__icontains=search) |
            models.Q(warehouse__icontains=search)
        )
    
    if stock_status:
        inventories = inventories.filter(stock_status=stock_status)
    
    if warehouse:
        inventories = inventories.filter(warehouse=warehouse)
    
    # 統計資料
    total_materials = inventories.count()
    low_stock_count = inventories.filter(stock_status='low').count()
    out_of_stock_count = inventories.filter(stock_status='out').count()
    excess_stock_count = inventories.filter(stock_status='excess').count()
    
    return render(request, "material/inventory_management.html", {
        "inventories": inventories,
        "search": search,
        "stock_status": stock_status,
        "warehouse": warehouse,
        "total_materials": total_materials,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "excess_stock_count": excess_stock_count,
    })


def inventory_detail(request, inventory_id):
    """
    庫存詳情：顯示特定材料的詳細庫存資訊
    """
    inventory = get_object_or_404(MaterialInventoryManagement, id=inventory_id)
    
    # 取得最近的交易記錄
    transactions = MaterialTransaction.objects.filter(material=inventory.material).order_by('-created_at')[:20]
    
    return render(request, "material/inventory_detail.html", {
        "inventory": inventory,
        "transactions": transactions,
    })


def add_inventory_transaction(request):
    """
    新增庫存交易：新增入庫、出庫等交易記錄
    """
    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        transaction_type = request.POST.get('transaction_type')
        quantity = request.POST.get('quantity')
        unit_cost = request.POST.get('unit_cost', 0)
        warehouse = request.POST.get('warehouse')
        reference_no = request.POST.get('reference_no')
        notes = request.POST.get('notes')
        
        try:
            material = Material.objects.get(id=material_id)
            quantity = Decimal(quantity)
            unit_cost = Decimal(unit_cost)
            
            # 建立交易記錄
            transaction = MaterialTransaction.objects.create(
                material=material,
                transaction_type=transaction_type,
                quantity=quantity,
                unit_cost=unit_cost,
                to_location=warehouse if transaction_type == 'in' else None,
                from_location=warehouse if transaction_type == 'out' else None,
                reference_no=reference_no,
                notes=notes,
                created_by=request.user.username if request.user.is_authenticated else 'system'
            )
            
            # 更新庫存
            inventory, created = MaterialInventoryManagement.objects.get_or_create(
                material=material,
                warehouse=warehouse,
                defaults={
                    'current_stock': 0,
                    'safety_stock': 0,
                    'max_stock': 0,
                    'reorder_point': 0,
                    'reorder_quantity': 0,
                    'unit_cost': unit_cost,
                }
            )
            
            if transaction_type == 'in':
                inventory.current_stock += quantity
            elif transaction_type == 'out':
                inventory.current_stock -= quantity
            
            inventory.unit_cost = unit_cost
            inventory.stock_status = inventory.calculate_stock_status()
            inventory.save()
            
            messages.success(request, f"交易記錄已新增：{material.name} {transaction_type} {quantity}")
            return redirect('material:inventory_detail', inventory_id=inventory.id)
            
        except (Material.DoesNotExist, ValueError) as e:
            messages.error(request, f"資料錯誤：{str(e)}")
    
    # GET 請求：顯示表單
    materials = Material.objects.all().order_by('name')
    warehouses = MaterialInventoryManagement.objects.values_list('warehouse', flat=True).distinct()
    
    return render(request, "material/add_inventory_transaction.html", {
        "materials": materials,
        "warehouses": warehouses,
    })


# 物料需求估算功能
def requirement_estimation(request):
    """
    物料需求估算：顯示和管理物料需求估算
    """
    estimations = MaterialRequirementEstimation.objects.select_related('material').all().order_by('-estimation_date')
    
    # 搜尋和篩選功能
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    estimation_method = request.GET.get('estimation_method', '')
    
    if search:
        estimations = estimations.filter(
            models.Q(material__name__icontains=search) |
            models.Q(material__code__icontains=search)
        )
    
    if status:
        estimations = estimations.filter(status=status)
    
    if estimation_method:
        estimations = estimations.filter(estimation_method=estimation_method)
    
    # 統計資料
    total_estimations = estimations.count()
    draft_count = estimations.filter(status='draft').count()
    confirmed_count = estimations.filter(status='confirmed').count()
    completed_count = estimations.filter(status='completed').count()
    
    return render(request, "material/requirement_estimation.html", {
        "estimations": estimations,
        "search": search,
        "status": status,
        "estimation_method": estimation_method,
        "total_estimations": total_estimations,
        "draft_count": draft_count,
        "confirmed_count": confirmed_count,
        "completed_count": completed_count,
    })


def create_requirement_estimation(request):
    """
    建立物料需求估算：建立新的需求估算
    """
    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        estimated_demand = request.POST.get('estimated_demand')
        estimation_method = request.POST.get('estimation_method')
        notes = request.POST.get('notes')
        
        try:
            material = Material.objects.get(id=material_id)
            estimated_demand = Decimal(estimated_demand)
            
            # 建立需求估算
            estimation = MaterialRequirementEstimation.objects.create(
                material=material,
                estimation_date=date.today(),
                period_start=period_start,
                period_end=period_end,
                estimated_demand=estimated_demand,
                estimation_method=estimation_method,
                notes=notes,
                status='draft'
            )
            
            messages.success(request, f"需求估算已建立：{material.name}")
            return redirect('material:requirement_estimation')
            
        except (Material.DoesNotExist, ValueError) as e:
            messages.error(request, f"資料錯誤：{str(e)}")
    
    # GET 請求：顯示表單
    materials = Material.objects.all().order_by('name')
    default_start = date.today()
    default_end = default_start + timedelta(days=30)
    
    return render(request, "material/create_requirement_estimation.html", {
        "materials": materials,
        "default_start": default_start,
        "default_end": default_end,
    })


def estimation_detail(request, estimation_id):
    """
    需求估算詳情：顯示特定需求估算的詳細資訊
    """
    estimation = get_object_or_404(MaterialRequirementEstimation, id=estimation_id)
    
    if request.method == 'POST':
        # 更新實際需求
        actual_demand = request.POST.get('actual_demand')
        if actual_demand:
            try:
                estimation.actual_demand = Decimal(actual_demand)
                estimation.forecast_accuracy = estimation.calculate_forecast_accuracy()
                estimation.save()
                messages.success(request, "實際需求已更新")
            except ValueError:
                messages.error(request, "數量格式錯誤")
        
        # 更新狀態
        new_status = request.POST.get('status')
        if new_status and new_status != estimation.status:
            estimation.status = new_status
            estimation.save()
            messages.success(request, f"狀態已更新為：{new_status}")
    
    return render(request, "material/estimation_detail.html", {
        "estimation": estimation,
    })


# API 功能
@csrf_exempt
@require_GET
def api_inventory_status(request):
    """
    API：取得庫存狀態統計
    """
    try:
        total = MaterialInventoryManagement.objects.count()
        low_stock = MaterialInventoryManagement.objects.filter(stock_status='low').count()
        out_of_stock = MaterialInventoryManagement.objects.filter(stock_status='out').count()
        excess_stock = MaterialInventoryManagement.objects.filter(stock_status='excess').count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': total,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'excess_stock': excess_stock,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_GET
def api_requirement_estimation_summary(request):
    """
    API：取得需求估算摘要
    """
    try:
        total = MaterialRequirementEstimation.objects.count()
        draft = MaterialRequirementEstimation.objects.filter(status='draft').count()
        confirmed = MaterialRequirementEstimation.objects.filter(status='confirmed').count()
        completed = MaterialRequirementEstimation.objects.filter(status='completed').count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': total,
                'draft': draft,
                'confirmed': confirmed,
                'completed': completed,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
