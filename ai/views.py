import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from .utils import log_user_operation
from .models import AIPrediction, AIOptimization, AIAnomaly
from django.utils import timezone

import os
# 設定AI模組的日誌記錄器
ai_logger = logging.getLogger("ai")
from django.conf import settings
ai_handler = logging.FileHandler(os.path.join(settings.AI_LOG_DIR, "ai.log"))
ai_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
ai_logger.addHandler(ai_handler)
ai_logger.setLevel(logging.INFO)


# 檢查用戶是否屬於「AI使用者」群組，或者是超級用戶
def ai_user_required(user):
    return user.is_superuser or user.groups.filter(name="AI使用者").exists()


# 檢查是否為超級管理員
def superuser_required(user):
    return user.is_superuser


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def index(request):
    if not request.user.has_perm("ai.can_view_ai_prediction"):
        messages.error(request, "您沒有查看 AI 功能的權限！")
        return redirect("home_page")
    log_user_operation(request.user.username, "ai", "查看 AI 模組首頁")
    predictions = AIPrediction.objects.all().order_by("-created_at")[:10]
    optimizations = AIOptimization.objects.all().order_by("-created_at")[:10]
    anomalies = AIAnomaly.objects.all().order_by("-created_at")[:10]
    return render(
        request,
        "ai/index.html",
        {
            "predictions": predictions,
            "optimizations": optimizations,
            "anomalies": anomalies,
        },
    )


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_production_prediction(request):
    if not request.user.has_perm("ai.can_run_ai_prediction"):
        messages.error(request, "您沒有執行生產預測的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行生產預測")
    if request.method == "POST":
        production_line = request.POST.get("production_line")
        current_output = request.POST.get("current_output")
        try:
            current_output = float(current_output)
            prediction = AIPrediction.objects.create(
                prediction_type="production",
                production_line=production_line,
                current_output=current_output,
                created_at=timezone.now(),
            )
            # 模擬 AI 預測
            predicted_output = current_output * 2
            confidence = 0.95
            prediction.predicted_output = predicted_output
            prediction.confidence = confidence
            prediction.save()
            messages.success(request, "生產預測任務已提交！")
            log_user_operation(request.user.username, "ai", "完成生產預測")
        except ValueError:
            messages.error(request, "當前產量必須是數字！")
        return redirect("ai:index")
    return render(request, "ai/run_production_prediction.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_demand_prediction(request):
    if not request.user.has_perm("ai.can_run_ai_prediction"):
        messages.error(request, "您沒有執行需求預測的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行需求預測")
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        historical_demand = request.POST.get("historical_demand")
        try:
            historical_demand = float(historical_demand)
            prediction = AIPrediction.objects.create(
                prediction_type="demand",
                product_name=product_name,
                historical_demand=historical_demand,
                created_at=timezone.now(),
            )
            # 模擬 AI 預測
            predicted_output = historical_demand * 1.5
            confidence = 0.90
            prediction.predicted_output = predicted_output
            prediction.confidence = confidence
            prediction.save()
            messages.success(request, "需求預測任務已提交！")
            log_user_operation(request.user.username, "ai", "完成需求預測")
        except ValueError:
            messages.error(request, "歷史需求量必須是數字！")
        return redirect("ai:index")
    return render(request, "ai/run_demand_prediction.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_quality_prediction(request):
    if not request.user.has_perm("ai.can_run_ai_prediction"):
        messages.error(request, "您沒有執行品質預測的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行品質預測")
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        production_temperature = request.POST.get("production_temperature")
        production_pressure = request.POST.get("production_pressure")
        try:
            production_temperature = float(production_temperature)
            production_pressure = float(production_pressure)
            prediction = AIPrediction.objects.create(
                prediction_type="quality",
                product_name=product_name,
                production_temperature=production_temperature,
                production_pressure=production_pressure,
                created_at=timezone.now(),
            )
            # 模擬 AI 預測
            predicted_output = 0.98  # 模擬品質分數
            confidence = 0.92
            prediction.predicted_output = predicted_output
            prediction.confidence = confidence
            prediction.save()
            messages.success(request, "品質預測任務已提交！")
            log_user_operation(request.user.username, "ai", "完成品質預測")
        except ValueError:
            messages.error(request, "生產溫度和壓力必須是數字！")
        return redirect("ai:index")
    return render(request, "ai/run_quality_prediction.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_production_optimization(request):
    if not request.user.has_perm("ai.can_run_ai_optimization"):
        messages.error(request, "您沒有執行生產優化的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行生產優化")
    if request.method == "POST":
        production_line = request.POST.get("production_line")
        current_capacity = request.POST.get("current_capacity")
        try:
            current_capacity = float(current_capacity)
            optimization = AIOptimization.objects.create(
                optimization_type="production",
                production_line=production_line,
                current_capacity=current_capacity,
                created_at=timezone.now(),
            )
            # 模擬 AI 優化
            optimized_result = f"優化後產能：{current_capacity * 1.2}"
            efficiency_gain = 0.15
            optimization.optimized_result = optimized_result
            optimization.efficiency_gain = efficiency_gain
            optimization.save()
            messages.success(request, "生產優化任務已提交！")
            log_user_operation(request.user.username, "ai", "完成生產優化")
        except ValueError:
            messages.error(request, "當前產能必須是數字！")
        return redirect("ai:index")
    return render(request, "ai/run_production_optimization.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_auto_scheduling(request):
    if not request.user.has_perm("ai.can_run_ai_optimization"):
        messages.error(request, "您沒有執行自動化調度的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行自動化調度")
    if request.method == "POST":
        task_name = request.POST.get("task_name")
        resource_available = request.POST.get("resource_available")
        optimization = AIOptimization.objects.create(
            optimization_type="scheduling",
            task_name=task_name,
            resource_available=resource_available,
            created_at=timezone.now(),
        )
        # 模擬 AI 調度
        optimized_result = (
            f"任務 {task_name} 安排在 {resource_available}，預計完成時間：2025-04-26"
        )
        efficiency_gain = 0.20
        optimization.optimized_result = optimized_result
        optimization.efficiency_gain = efficiency_gain
        optimization.save()
        messages.success(request, "自動化調度任務已提交！")
        log_user_operation(request.user.username, "ai", "完成自動化調度")
        return redirect("ai:index")
    return render(request, "ai/run_auto_scheduling.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_production_anomaly_detection(request):
    if not request.user.has_perm("ai.can_run_ai_anomaly"):
        messages.error(request, "您沒有執行生產異常檢測的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行生產異常檢測")
    if request.method == "POST":
        production_line = request.POST.get("production_line")
        production_rate = request.POST.get("production_rate")
        try:
            production_rate = float(production_rate)
            anomaly = AIAnomaly.objects.create(
                anomaly_type="production",
                production_line=production_line,
                production_rate=production_rate,
                created_at=timezone.now(),
            )
            # 模擬 AI 異常檢測
            anomaly_detected = production_rate < 5  # 簡單模擬
            anomaly_details = "生產速率過低" if anomaly_detected else "無異常"
            anomaly.anomaly_detected = anomaly_detected
            anomaly.anomaly_details = anomaly_details
            anomaly.save()
            messages.success(request, "生產異常檢測任務已提交！")
            log_user_operation(request.user.username, "ai", "完成生產異常檢測")
        except ValueError:
            messages.error(request, "生產速率必須是數字！")
        return redirect("ai:index")
    return render(request, "ai/run_production_anomaly_detection.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def run_defect_detection(request):
    if not request.user.has_perm("ai.can_run_ai_anomaly"):
        messages.error(request, "您沒有執行缺陷檢測的權限！")
        return redirect("ai:index")
    log_user_operation(request.user.username, "ai", "執行缺陷檢測")
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        defect_type = request.POST.get("defect_type")
        anomaly = AIAnomaly.objects.create(
            anomaly_type="defect",
            product_name=product_name,
            defect_type=defect_type,
            created_at=timezone.now(),
        )
        # 模擬 AI 缺陷檢測
        anomaly_detected = True  # 簡單模擬
        anomaly_details = f"{defect_type} 缺陷已檢測到"
        anomaly.anomaly_detected = anomaly_detected
        anomaly.anomaly_details = anomaly_details
        anomaly.save()
        messages.success(request, "缺陷檢測任務已提交！")
        log_user_operation(request.user.username, "ai", "完成缺陷檢測")
        return redirect("ai:index")
    return render(request, "ai/run_defect_detection.html", {})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def get_predictions(request):
    if not request.user.has_perm("ai.can_view_ai_prediction"):
        return JsonResponse({"error": "您沒有查看 AI 預測的權限！"}, status=403)
    log_user_operation(request.user.username, "ai", "通過 API 獲取 AI 預測列表")
    predictions = AIPrediction.objects.all()
    predictions_data = [
        {
            "id": prediction.id,
            "prediction_type": prediction.prediction_type,
            "production_line": prediction.production_line,
            "current_output": prediction.current_output,
            "product_name": prediction.product_name,
            "historical_demand": prediction.historical_demand,
            "production_temperature": prediction.production_temperature,
            "production_pressure": prediction.production_pressure,
            "predicted_output": prediction.predicted_output,
            "confidence": prediction.confidence,
            "created_at": prediction.created_at.isoformat(),
            "updated_at": prediction.updated_at.isoformat(),
        }
        for prediction in predictions
    ]
    return JsonResponse({"predictions": predictions_data})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def get_optimizations(request):
    if not request.user.has_perm("ai.can_view_ai_optimization"):
        return JsonResponse({"error": "您沒有查看 AI 優化的權限！"}, status=403)
    log_user_operation(request.user.username, "ai", "通過 API 獲取 AI 優化列表")
    optimizations = AIOptimization.objects.all()
    optimizations_data = [
        {
            "id": optimization.id,
            "optimization_type": optimization.optimization_type,
            "production_line": optimization.production_line,
            "current_capacity": optimization.current_capacity,
            "task_name": optimization.task_name,
            "resource_available": optimization.resource_available,
            "optimized_result": optimization.optimized_result,
            "efficiency_gain": optimization.efficiency_gain,
            "created_at": optimization.created_at.isoformat(),
            "updated_at": optimization.updated_at.isoformat(),
        }
        for optimization in optimizations
    ]
    return JsonResponse({"optimizations": optimizations_data})


@login_required
@user_passes_test(ai_user_required, login_url="/accounts/login/")
def get_anomalies(request):
    if not request.user.has_perm("ai.can_view_ai_anomaly"):
        return JsonResponse({"error": "您沒有查看 AI 異常檢測的權限！"}, status=403)
    log_user_operation(request.user.username, "ai", "通過 API 獲取 AI 異常檢測列表")
    anomalies = AIAnomaly.objects.all()
    anomalies_data = [
        {
            "id": anomaly.id,
            "anomaly_type": anomaly.anomaly_type,
            "production_line": anomaly.production_line,
            "production_rate": anomaly.production_rate,
            "product_name": anomaly.product_name,
            "defect_type": anomaly.defect_type,
            "anomaly_detected": anomaly.anomaly_detected,
            "anomaly_details": anomaly.anomaly_details,
            "created_at": anomaly.created_at.isoformat(),
            "updated_at": anomaly.updated_at.isoformat(),
        }
        for anomaly in anomalies
    ]
    return JsonResponse({"anomalies": anomalies_data})
