"""
批次處理排程器
支援大量訂單的批次處理，提升排程效能和用戶體驗
包含進度追蹤、記憶體優化和錯誤處理
"""

import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    Event,
    Unit,
    CompanyView,
    SchedulingOperationLog,
    ProcessIntervalSettings,
)
from .algorithms import OptimizedAutoScheduler
from .semi_auto_algorithms import SemiAutoScheduler
from .hybrid_algorithms import HybridScheduler

logger = logging.getLogger("scheduling.batch_scheduler")


class BatchScheduler:
    """
    批次處理排程器
    支援大量訂單的批次處理，提供進度追蹤和效能優化
    """

    def __init__(self, mode: str = "auto", batch_size: int = 50, max_workers: int = 4):
        """
        初始化批次排程器

        Args:
            mode: 排程模式 (auto, semi_auto, hybrid, manual)
            batch_size: 每批次處理的訂單數量
            max_workers: 最大工作執行緒數
        """
        self.mode = mode
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.progress_key = None
        self.is_cancelled = False

        # 初始化對應的排程器
        if mode == "auto":
            self.scheduler = OptimizedAutoScheduler()
        elif mode == "semi_auto":
            self.scheduler = SemiAutoScheduler()
        elif mode == "hybrid":
            self.scheduler = HybridScheduler()
        else:
            self.scheduler = None

    def generate_progress_key(self, user_id: str) -> str:
        """生成進度追蹤金鑰"""
        timestamp = int(time.time())
        return f"scheduling_progress_{user_id}_{timestamp}"

    def update_progress(
        self, current: int, total: int, status: str = "processing", message: str = ""
    ):
        """更新進度資訊"""
        if self.progress_key:
            progress_data = {
                "current": current,
                "total": total,
                "percentage": int((current / total) * 100) if total > 0 else 0,
                "status": status,
                "message": message,
                "timestamp": timezone.now().isoformat(),
            }
            cache.set(self.progress_key, progress_data, timeout=3600)  # 1小時過期

    def get_progress(self) -> Dict[str, Any]:
        """取得當前進度"""
        if self.progress_key:
            return cache.get(self.progress_key, {})
        return {}

    def cancel_scheduling(self):
        """取消排程"""
        self.is_cancelled = True
        if self.progress_key:
            self.update_progress(0, 100, "cancelled", "排程已取消")

    def schedule_batch(
        self, orders: List[Dict], parameters: Dict, user_id: str
    ) -> Dict[str, Any]:
        """
        批次排程處理

        Args:
            orders: 訂單列表
            parameters: 排程參數
            user_id: 使用者ID

        Returns:
            排程結果
        """
        try:
            # 生成進度追蹤金鑰
            self.progress_key = self.generate_progress_key(user_id)
            self.is_cancelled = False

            # 初始化進度
            total_orders = len(orders)
            self.update_progress(0, total_orders, "processing", "開始批次排程處理...")

            # 分批處理訂單
            batches = self._split_into_batches(orders)
            processed_orders = []
            failed_orders = []

            for batch_index, batch in enumerate(batches):
                if self.is_cancelled:
                    break

                # 更新進度
                current_progress = batch_index * self.batch_size
                self.update_progress(
                    current_progress,
                    total_orders,
                    "processing",
                    f"處理第 {batch_index + 1}/{len(batches)} 批次...",
                )

                # 處理當前批次
                batch_result = self._process_batch(batch, parameters)

                if batch_result["success"]:
                    processed_orders.extend(batch_result["processed"])
                else:
                    failed_orders.extend(batch_result["failed"])

                # 短暫休息，避免系統過載
                time.sleep(0.1)

            # 完成處理
            if self.is_cancelled:
                status = "cancelled"
                message = "排程已取消"
            else:
                status = "completed"
                message = f"批次排程完成，成功處理 {len(processed_orders)} 個訂單"
                if failed_orders:
                    message += f"，失敗 {len(failed_orders)} 個訂單"

            self.update_progress(total_orders, total_orders, status, message)

            return {
                "success": True,
                "processed_count": len(processed_orders),
                "failed_count": len(failed_orders),
                "processed_orders": processed_orders,
                "failed_orders": failed_orders,
                "status": status,
                "message": message,
            }

        except Exception as e:
            logger.error(f"批次排程失敗: {str(e)}")
            self.update_progress(0, total_orders, "error", f"排程失敗: {str(e)}")
            return {"success": False, "error": str(e), "status": "error"}

    def _split_into_batches(self, orders: List[Dict]) -> List[List[Dict]]:
        """將訂單分割成批次"""
        batches = []
        for i in range(0, len(orders), self.batch_size):
            batch = orders[i : i + self.batch_size]
            batches.append(batch)
        return batches

    def _process_batch(self, batch: List[Dict], parameters: Dict) -> Dict[str, Any]:
        """處理單個批次"""
        processed = []
        failed = []

        try:
            # 使用執行緒池並行處理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任務
                future_to_order = {
                    executor.submit(
                        self._process_single_order, order, parameters
                    ): order
                    for order in batch
                }

                # 收集結果
                for future in as_completed(future_to_order):
                    order = future_to_order[future]
                    try:
                        result = future.result()
                        if result["success"]:
                            processed.append(result["data"])
                        else:
                            failed.append({"order": order, "error": result["error"]})
                    except Exception as e:
                        failed.append({"order": order, "error": str(e)})

            return {"success": True, "processed": processed, "failed": failed}

        except Exception as e:
            logger.error(f"批次處理失敗: {str(e)}")
            return {"success": False, "error": str(e), "processed": [], "failed": batch}

    def _process_single_order(self, order: Dict, parameters: Dict) -> Dict[str, Any]:
        """處理單個訂單"""
        try:
            # 根據模式選擇處理方法
            if self.mode == "auto":
                result = self._process_auto_order(order, parameters)
            elif self.mode == "semi_auto":
                result = self._process_semi_auto_order(order, parameters)
            elif self.mode == "hybrid":
                result = self._process_hybrid_order(order, parameters)
            else:
                result = self._process_manual_order(order, parameters)

            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"處理訂單失敗 {order.get('order_no', 'unknown')}: {str(e)}")
            return {"success": False, "error": str(e)}

    def _process_auto_order(self, order: Dict, parameters: Dict) -> Dict[str, Any]:
        """處理全自動排程訂單"""
        # 這裡實現全自動排程邏輯
        # 實際實現會調用 AutoScheduler 的方法

        # 模擬處理時間
        time.sleep(0.01)

        return {
            "order_no": order.get("order_no"),
            "scheduled_start": order.get("pre_in_date"),
            "scheduled_end": order.get("pre_in_date"),
            "assigned_unit": parameters.get("default_unit"),
            "status": "scheduled",
        }

    def _process_semi_auto_order(self, order: Dict, parameters: Dict) -> Dict[str, Any]:
        """處理半自動排程訂單"""
        # 這裡實現半自動排程邏輯
        # 實際實現會調用 SemiAutoScheduler 的方法

        time.sleep(0.01)

        return {
            "order_no": order.get("order_no"),
            "scheduled_start": order.get("pre_in_date"),
            "scheduled_end": order.get("pre_in_date"),
            "assigned_unit": parameters.get("default_unit"),
            "status": "semi_scheduled",
        }

    def _process_hybrid_order(self, order: Dict, parameters: Dict) -> Dict[str, Any]:
        """處理混合排程訂單"""
        # 這裡實現混合排程邏輯
        # 實際實現會調用 HybridScheduler 的方法

        time.sleep(0.01)

        return {
            "order_no": order.get("order_no"),
            "scheduled_start": order.get("pre_in_date"),
            "scheduled_end": order.get("pre_in_date"),
            "assigned_unit": parameters.get("default_unit"),
            "status": "hybrid_scheduled",
        }

    def _process_manual_order(self, order: Dict, parameters: Dict) -> Dict[str, Any]:
        """處理手動排程訂單"""
        # 手動排程通常不需要自動處理
        # 這裡只是預留位置

        return {"order_no": order.get("order_no"), "status": "manual_required"}


class ResourceConflictChecker:
    """
    資源衝突檢查器
    提供高效的資源衝突檢查功能
    """

    def __init__(self):
        self.cache_timeout = 300  # 5分鐘快取

    def check_conflicts(
        self,
        start_date: datetime,
        end_date: datetime,
        unit_ids: List[int],
        exclude_event_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        檢查資源衝突

        Args:
            start_date: 開始日期
            end_date: 結束日期
            unit_ids: 設備ID列表
            exclude_event_ids: 排除的事件ID列表

        Returns:
            衝突檢查結果
        """
        try:
            # 生成快取金鑰
            cache_key = f"conflict_check_{start_date.date()}_{end_date.date()}_{'_'.join(map(str, unit_ids))}"

            # 檢查快取
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result

            # 檢查事件衝突
            event_conflicts = self._check_event_conflicts(
                start_date, end_date, unit_ids, exclude_event_ids
            )

            # 檢查生產事件衝突
            production_conflicts = self._check_production_conflicts(
                start_date, end_date, unit_ids, exclude_event_ids
            )

            # 檢查設備可用性
            unit_availability = self._check_unit_availability(
                start_date, end_date, unit_ids
            )

            result = {
                "has_conflicts": bool(event_conflicts or production_conflicts),
                "event_conflicts": event_conflicts,
                "production_conflicts": production_conflicts,
                "unit_availability": unit_availability,
                "total_conflicts": len(event_conflicts) + len(production_conflicts),
            }

            # 儲存到快取
            cache.set(cache_key, result, timeout=self.cache_timeout)

            return result

        except Exception as e:
            logger.error(f"衝突檢查失敗: {str(e)}")
            return {"has_conflicts": False, "error": str(e)}

    def _check_event_conflicts(
        self,
        start_date: datetime,
        end_date: datetime,
        unit_ids: List[int],
        exclude_event_ids: List[int] = None,
    ) -> List[Dict]:
        """檢查事件衝突"""
        conflicts = []

        try:
            query = Event.objects.filter(
                unit_id__in=unit_ids, start__lt=end_date, end__gt=start_date
            ).exclude(type="workday")

            if exclude_event_ids:
                query = query.exclude(id__in=exclude_event_ids)

            for event in query.select_related("unit"):
                conflicts.append(
                    {
                        "type": "event",
                        "id": event.id,
                        "title": event.title,
                        "unit_name": event.unit.name,
                        "start": event.start.isoformat(),
                        "end": event.end.isoformat(),
                        "severity": "high" if event.type == "production" else "medium",
                    }
                )

        except Exception as e:
            logger.error(f"檢查事件衝突失敗: {str(e)}")

        return conflicts

    def _check_production_conflicts(
        self,
        start_date: datetime,
        end_date: datetime,
        unit_ids: List[int],
        exclude_event_ids: List[int] = None,
    ) -> List[Dict]:
        """檢查生產事件衝突"""
        conflicts = []

        try:
            # 由於 ProductionEvent 模型不存在，這裡檢查 Event 中的生產類型事件
            query = Event.objects.filter(
                unit_id__in=unit_ids,
                start__lt=end_date,
                end__gt=start_date,
                type="production",  # 假設生產事件的類型是 'production'
            )

            if exclude_event_ids:
                query = query.exclude(id__in=exclude_event_ids)

            for event in query.select_related("unit"):
                conflicts.append(
                    {
                        "type": "production",
                        "id": event.id,
                        "title": event.title,
                        "unit_name": event.unit.name,
                        "start_time": event.start.isoformat(),
                        "end_time": event.end.isoformat(),
                        "severity": "high",
                    }
                )

        except Exception as e:
            logger.error(f"檢查生產衝突失敗: {str(e)}")

        return conflicts

    def _check_unit_availability(
        self, start_date: datetime, end_date: datetime, unit_ids: List[int]
    ) -> Dict[int, Dict]:
        """檢查設備可用性"""
        availability = {}

        try:
            for unit_id in unit_ids:
                unit = Unit.objects.get(id=unit_id)

                # 計算可用時間
                total_hours = (end_date - start_date).total_seconds() / 3600

                # 計算已排程時間
                scheduled_events = Event.objects.filter(
                    unit=unit, start__gte=start_date, end__lte=end_date
                ).exclude(type="workday")

                scheduled_hours = sum(
                    [
                        (event.end - event.start).total_seconds() / 3600
                        for event in scheduled_events
                    ]
                )

                availability[unit_id] = {
                    "unit_name": unit.name,
                    "total_hours": total_hours,
                    "scheduled_hours": scheduled_hours,
                    "available_hours": total_hours - scheduled_hours,
                    "utilization_rate": (
                        (scheduled_hours / total_hours * 100) if total_hours > 0 else 0
                    ),
                }

        except Exception as e:
            logger.error(f"檢查設備可用性失敗: {str(e)}")

        return availability


class SchedulingOptimizer:
    """
    排程優化器
    提供排程結果的優化建議和效能分析
    """

    def __init__(self):
        self.optimization_rules = self._load_optimization_rules()

    def _load_optimization_rules(self) -> Dict[str, Any]:
        """載入優化規則"""
        return {
            "utilization_threshold": 0.8,  # 設備利用率閾值
            "setup_time_weight": 0.3,  # 換線時間權重
            "makespan_weight": 0.7,  # 完工時間權重
            "resource_balance_weight": 0.5,  # 資源平衡權重
        }

    def analyze_schedule(self, schedule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析排程結果

        Args:
            schedule_result: 排程結果

        Returns:
            分析結果
        """
        try:
            analysis = {
                "overall_score": 0,
                "metrics": {},
                "recommendations": [],
                "warnings": [],
            }

            # 計算設備利用率
            utilization_score = self._calculate_utilization_score(schedule_result)
            analysis["metrics"]["utilization"] = utilization_score

            # 計算換線時間
            setup_time_score = self._calculate_setup_time_score(schedule_result)
            analysis["metrics"]["setup_time"] = setup_time_score

            # 計算完工時間
            makespan_score = self._calculate_makespan_score(schedule_result)
            analysis["metrics"]["makespan"] = makespan_score

            # 計算資源平衡
            balance_score = self._calculate_resource_balance_score(schedule_result)
            analysis["metrics"]["resource_balance"] = balance_score

            # 計算總分
            analysis["overall_score"] = (
                utilization_score * 0.3
                + setup_time_score * 0.2
                + makespan_score * 0.3
                + balance_score * 0.2
            )

            # 生成建議
            analysis["recommendations"] = self._generate_recommendations(analysis)

            # 生成警告
            analysis["warnings"] = self._generate_warnings(analysis)

            return analysis

        except Exception as e:
            logger.error(f"排程分析失敗: {str(e)}")
            return {"overall_score": 0, "error": str(e)}

    def _calculate_utilization_score(self, schedule_result: Dict[str, Any]) -> float:
        """計算設備利用率分數"""
        # 這裡實現設備利用率計算邏輯
        return 0.85  # 模擬分數

    def _calculate_setup_time_score(self, schedule_result: Dict[str, Any]) -> float:
        """計算換線時間分數"""
        # 這裡實現換線時間計算邏輯
        return 0.75  # 模擬分數

    def _calculate_makespan_score(self, schedule_result: Dict[str, Any]) -> float:
        """計算完工時間分數"""
        # 這裡實現完工時間計算邏輯
        return 0.90  # 模擬分數

    def _calculate_resource_balance_score(
        self, schedule_result: Dict[str, Any]
    ) -> float:
        """計算資源平衡分數"""
        # 這裡實現資源平衡計算邏輯
        return 0.80  # 模擬分數

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """生成優化建議"""
        recommendations = []

        if analysis["metrics"]["utilization"] < 0.7:
            recommendations.append("建議提高設備利用率，可考慮合併小批量訂單")

        if analysis["metrics"]["setup_time"] < 0.6:
            recommendations.append("建議優化換線順序，減少換線時間")

        if analysis["metrics"]["makespan"] < 0.8:
            recommendations.append("建議調整排程順序，縮短完工時間")

        if analysis["metrics"]["resource_balance"] < 0.7:
            recommendations.append("建議平衡各設備負載，避免資源閒置")

        return recommendations

    def _generate_warnings(self, analysis: Dict[str, Any]) -> List[str]:
        """生成警告訊息"""
        warnings = []

        if analysis["overall_score"] < 0.6:
            warnings.append("排程品質較低，建議重新調整參數")

        if analysis["metrics"]["utilization"] < 0.5:
            warnings.append("設備利用率過低，可能影響生產效率")

        return warnings
