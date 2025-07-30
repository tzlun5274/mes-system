"""
設備查詢器
提供設備相關數據的查詢功能
"""

from typing import List, Dict, Any
from datetime import date

from .base_query import BaseQuery


class EquipmentQuery(BaseQuery):
    """設備查詢器"""
    
    def get_equipment_reports_by_date_range(self, date_range: Dict[str, date]) -> List[Any]:
        """
        根據日期範圍獲取設備運行數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            設備運行記錄列表
        """
        try:
            # 嘗試從 equip 模組獲取設備運行記錄
            from equip.models import EquipmentReport
            
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return []
            
            return self.get_data_by_date_range(
                EquipmentReport,
                'report_date',
                start_date,
                end_date
            )
            
        except ImportError:
            # 如果沒有 EquipmentReport 模型，嘗試從 workorder 模組獲取 SMT 報工數據
            try:
                from workorder.models import SMTProductionReport
                
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                
                if not start_date or not end_date:
                    self.logger.error("日期範圍不完整")
                    return []
                
                return self.get_data_by_date_range(
                    SMTProductionReport,
                    'report_date',
                    start_date,
                    end_date
                )
                
            except ImportError:
                self.logger.warning("無法導入設備相關模型，返回空列表")
                return []
        except Exception as e:
            self.logger.error(f"獲取設備運行數據失敗: {str(e)}")
            return []
    
    def get_equipment_by_id(self, equipment_id: int) -> Any:
        """
        根據設備ID獲取設備資訊
        
        Args:
            equipment_id: 設備ID
        
        Returns:
            設備記錄或 None
        """
        try:
            from equip.models import Equipment
            
            return self.get_data_by_id(Equipment, equipment_id)
            
        except ImportError:
            self.logger.warning("無法導入 Equipment 模型，返回 None")
            return None
        except Exception as e:
            self.logger.error(f"獲取設備資訊失敗: {str(e)}")
            return None
    
    def get_equipment_reports_by_equipment(self, equipment_id: int, date_range: Dict[str, date] = None) -> List[Any]:
        """
        根據設備ID獲取運行記錄
        
        Args:
            equipment_id: 設備ID
            date_range: 可選的日期範圍
        
        Returns:
            設備運行記錄列表
        """
        try:
            # 嘗試從 equip 模組獲取
            try:
                from equip.models import EquipmentReport
                
                filters = {'equipment_id': equipment_id}
                
                if date_range:
                    start_date = date_range.get('start_date')
                    end_date = date_range.get('end_date')
                    if start_date and end_date:
                        filters.update({
                            'report_date__gte': start_date,
                            'report_date__lte': end_date
                        })
                
                return list(EquipmentReport.objects.filter(**filters))
                
            except ImportError:
                # 如果沒有 EquipmentReport，嘗試從 workorder 模組獲取
                from workorder.models import SMTProductionReport
                
                filters = {'equipment_id': equipment_id}
                
                if date_range:
                    start_date = date_range.get('start_date')
                    end_date = date_range.get('end_date')
                    if start_date and end_date:
                        filters.update({
                            'report_date__gte': start_date,
                            'report_date__lte': end_date
                        })
                
                return list(SMTProductionReport.objects.filter(**filters))
                
        except ImportError:
            self.logger.warning("無法導入設備相關模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取設備運行記錄失敗: {str(e)}")
            return []
    
    def get_equipment_summary_by_date_range(self, date_range: Dict[str, date]) -> List[Dict[str, Any]]:
        """
        獲取設備摘要統計數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            設備摘要統計列表
        """
        try:
            # 嘗試從 equip 模組獲取
            try:
                from equip.models import EquipmentReport
                from django.db.models import Sum, Count, Avg
                
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                
                if not start_date or not end_date:
                    self.logger.error("日期範圍不完整")
                    return []
                
                # 按設備分組統計
                summary_data = EquipmentReport.objects.filter(
                    report_date__gte=start_date,
                    report_date__lte=end_date
                ).values('equipment__name').annotate(
                    total_run_hours=Sum('run_hours'),
                    total_down_hours=Sum('down_hours'),
                    report_count=Count('id'),
                    avg_efficiency=Avg('efficiency_rate')
                )
                
                return list(summary_data)
                
            except ImportError:
                # 如果沒有 EquipmentReport，嘗試從 workorder 模組獲取
                from workorder.models import SMTProductionReport
                from django.db.models import Sum, Count
                
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                
                if not start_date or not end_date:
                    self.logger.error("日期範圍不完整")
                    return []
                
                # 按設備分組統計 SMT 報工數據
                summary_data = SMTProductionReport.objects.filter(
                    report_date__gte=start_date,
                    report_date__lte=end_date
                ).values('equipment__name').annotate(
                    report_count=Count('id'),
                    total_quantity=Sum('quantity')
                )
                
                return list(summary_data)
                
        except ImportError:
            self.logger.warning("無法導入設備相關模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取設備摘要統計失敗: {str(e)}")
            return []
    
    def get_equipment_utilization_data(self, equipment_id: int, date_range: Dict[str, date]) -> Dict[str, Any]:
        """
        獲取設備利用率數據
        
        Args:
            equipment_id: 設備ID
            date_range: 日期範圍
        
        Returns:
            設備利用率數據字典
        """
        try:
            # 獲取設備資訊
            equipment = self.get_equipment_by_id(equipment_id)
            if not equipment:
                return {}
            
            # 獲取運行記錄
            reports = self.get_equipment_reports_by_equipment(equipment_id, date_range)
            
            # 計算利用率
            total_run_hours = 0
            total_down_hours = 0
            
            for report in reports:
                if hasattr(report, 'run_hours'):
                    total_run_hours += report.run_hours or 0
                if hasattr(report, 'down_hours'):
                    total_down_hours += report.down_hours or 0
            
            # 假設標準運行時間為24小時/天
            days_in_range = (date_range['end_date'] - date_range['start_date']).days + 1
            standard_hours = days_in_range * 24
            
            utilization_rate = 0
            if standard_hours > 0:
                utilization_rate = round((total_run_hours / standard_hours) * 100, 2)
            
            return {
                'equipment_id': equipment_id,
                'equipment_name': getattr(equipment, 'name', f'Equipment_{equipment_id}'),
                'total_run_hours': total_run_hours,
                'total_down_hours': total_down_hours,
                'standard_hours': standard_hours,
                'utilization_rate': utilization_rate,
                'report_count': len(reports)
            }
            
        except Exception as e:
            self.logger.error(f"獲取設備利用率數據失敗: {str(e)}")
            return {} 