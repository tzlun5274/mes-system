# 品質計算器模組
# 本檔案負責計算各種品質指標

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
from .base_calculator import BaseCalculator


class QualityCalculator(BaseCalculator):
    """品質計算器 - 負責計算各種品質指標"""
    
    def __init__(self):
        """初始化品質計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def calculate_yield_rate(self, good_quantity: float, total_quantity: float) -> float:
        """
        計算良率
        
        Args:
            good_quantity: 良品數量
            total_quantity: 總數量
            
        Returns:
            float: 良率百分比
        """
        try:
            return self.calculate_percentage(good_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算良率失敗: {str(e)}")
            return 0.0
    
    def calculate_defect_rate(self, defect_quantity: float, total_quantity: float) -> float:
        """
        計算不良率
        
        Args:
            defect_quantity: 不良品數量
            total_quantity: 總數量
            
        Returns:
            float: 不良率百分比
        """
        try:
            return self.calculate_percentage(defect_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算不良率失敗: {str(e)}")
            return 0.0
    
    def calculate_first_pass_yield(self, first_pass_quantity: float, 
                                 total_quantity: float) -> float:
        """
        計算一次通過率
        
        Args:
            first_pass_quantity: 一次通過數量
            total_quantity: 總數量
            
        Returns:
            float: 一次通過率百分比
        """
        try:
            return self.calculate_percentage(first_pass_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算一次通過率失敗: {str(e)}")
            return 0.0
    
    def calculate_rework_rate(self, rework_quantity: float, total_quantity: float) -> float:
        """
        計算重工率
        
        Args:
            rework_quantity: 重工數量
            total_quantity: 總數量
            
        Returns:
            float: 重工率百分比
        """
        try:
            return self.calculate_percentage(rework_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算重工率失敗: {str(e)}")
            return 0.0
    
    def calculate_scrap_rate(self, scrap_quantity: float, total_quantity: float) -> float:
        """
        計算報廢率
        
        Args:
            scrap_quantity: 報廢數量
            total_quantity: 總數量
            
        Returns:
            float: 報廢率百分比
        """
        try:
            return self.calculate_percentage(scrap_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算報廢率失敗: {str(e)}")
            return 0.0
    
    def calculate_customer_complaint_rate(self, complaint_count: int, 
                                        total_orders: int) -> float:
        """
        計算客戶抱怨率
        
        Args:
            complaint_count: 抱怨次數
            total_orders: 總訂單數
            
        Returns:
            float: 客戶抱怨率百分比
        """
        try:
            return self.calculate_percentage(complaint_count, total_orders)
        except Exception as e:
            self.logger.error(f"計算客戶抱怨率失敗: {str(e)}")
            return 0.0
    
    def calculate_ppm(self, defect_quantity: float, total_quantity: float) -> float:
        """
        計算百萬分之不良率 (PPM)
        
        Args:
            defect_quantity: 不良品數量
            total_quantity: 總數量
            
        Returns:
            float: PPM值
        """
        try:
            if total_quantity <= 0:
                return 0.0
            
            ppm = (defect_quantity / total_quantity) * 1000000
            return self.round_decimal(ppm, 2)
        except Exception as e:
            self.logger.error(f"計算PPM失敗: {str(e)}")
            return 0.0
    
    def calculate_dpu(self, total_defects: int, total_units: int) -> float:
        """
        計算每單位缺陷數 (DPU)
        
        Args:
            total_defects: 總缺陷數
            total_units: 總單位數
            
        Returns:
            float: DPU值
        """
        try:
            if total_units <= 0:
                return 0.0
            
            dpu = total_defects / total_units
            return self.round_decimal(dpu, 4)
        except Exception as e:
            self.logger.error(f"計算DPU失敗: {str(e)}")
            return 0.0
    
    def calculate_dpo(self, total_defects: int, total_opportunities: int) -> float:
        """
        計算每機會缺陷數 (DPO)
        
        Args:
            total_defects: 總缺陷數
            total_opportunities: 總機會數
            
        Returns:
            float: DPO值
        """
        try:
            if total_opportunities <= 0:
                return 0.0
            
            dpo = total_defects / total_opportunities
            return self.round_decimal(dpo, 6)
        except Exception as e:
            self.logger.error(f"計算DPO失敗: {str(e)}")
            return 0.0
    
    def calculate_dpmo(self, total_defects: int, total_opportunities: int) -> float:
        """
        計算每百萬機會缺陷數 (DPMO)
        
        Args:
            total_defects: 總缺陷數
            total_opportunities: 總機會數
            
        Returns:
            float: DPMO值
        """
        try:
            if total_opportunities <= 0:
                return 0.0
            
            dpmo = (total_defects / total_opportunities) * 1000000
            return self.round_decimal(dpmo, 2)
        except Exception as e:
            self.logger.error(f"計算DPMO失敗: {str(e)}")
            return 0.0
    
    def calculate_sigma_level(self, dpmo: float) -> float:
        """
        計算西格瑪水準
        
        Args:
            dpmo: 每百萬機會缺陷數
            
        Returns:
            float: 西格瑪水準
        """
        try:
            # 簡化的西格瑪水準計算
            # 實際應用中可能需要更精確的查表或計算方法
            if dpmo <= 3.4:
                return 6.0
            elif dpmo <= 233:
                return 5.0
            elif dpmo <= 6210:
                return 4.0
            elif dpmo <= 66807:
                return 3.0
            elif dpmo <= 308537:
                return 2.0
            else:
                return 1.0
        except Exception as e:
            self.logger.error(f"計算西格瑪水準失敗: {str(e)}")
            return 0.0
    
    def calculate_daily_quality_metrics(self, quality_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算每日品質指標
        
        Args:
            quality_records: 品質記錄列表
            
        Returns:
            Dict[str, Dict[str, float]]: 每日品質指標字典
        """
        try:
            daily_quality = {}
            
            for record in quality_records:
                record_date = record.get('date')
                good_quantity = record.get('good_quantity', 0)
                defect_quantity = record.get('defect_quantity', 0)
                total_quantity = record.get('total_quantity', 0)
                
                if not record_date or total_quantity <= 0:
                    continue
                
                date_key = record_date.strftime('%Y-%m-%d') if isinstance(record_date, date) else str(record_date)
                
                if date_key not in daily_quality:
                    daily_quality[date_key] = {
                        'good_quantity': 0,
                        'defect_quantity': 0,
                        'total_quantity': 0
                    }
                
                daily_quality[date_key]['good_quantity'] += float(good_quantity)
                daily_quality[date_key]['defect_quantity'] += float(defect_quantity)
                daily_quality[date_key]['total_quantity'] += float(total_quantity)
            
            # 計算品質指標
            for date_key, data in daily_quality.items():
                total = data['total_quantity']
                good = data['good_quantity']
                defect = data['defect_quantity']
                
                data['yield_rate'] = self.calculate_yield_rate(good, total)
                data['defect_rate'] = self.calculate_defect_rate(defect, total)
                data['ppm'] = self.calculate_ppm(defect, total)
            
            return daily_quality
        except Exception as e:
            self.logger.error(f"計算每日品質指標失敗: {str(e)}")
            return {}
    
    def calculate_weekly_quality_metrics(self, quality_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算每週品質指標
        
        Args:
            quality_records: 品質記錄列表
            
        Returns:
            Dict[str, Dict[str, float]]: 每週品質指標字典
        """
        try:
            weekly_quality = {}
            
            for record in quality_records:
                record_date = record.get('date')
                good_quantity = record.get('good_quantity', 0)
                defect_quantity = record.get('defect_quantity', 0)
                total_quantity = record.get('total_quantity', 0)
                
                if not record_date or total_quantity <= 0:
                    continue
                
                # 計算週數
                if isinstance(record_date, date):
                    week_number = record_date.isocalendar()[1]
                    week_key = f"{record_date.year}-W{week_number:02d}"
                else:
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        week_number = date_obj.isocalendar()[1]
                        week_key = f"{date_obj.year}-W{week_number:02d}"
                    except:
                        continue
                
                if week_key not in weekly_quality:
                    weekly_quality[week_key] = {
                        'good_quantity': 0,
                        'defect_quantity': 0,
                        'total_quantity': 0
                    }
                
                weekly_quality[week_key]['good_quantity'] += float(good_quantity)
                weekly_quality[week_key]['defect_quantity'] += float(defect_quantity)
                weekly_quality[week_key]['total_quantity'] += float(total_quantity)
            
            # 計算品質指標
            for week_key, data in weekly_quality.items():
                total = data['total_quantity']
                good = data['good_quantity']
                defect = data['defect_quantity']
                
                data['yield_rate'] = self.calculate_yield_rate(good, total)
                data['defect_rate'] = self.calculate_defect_rate(defect, total)
                data['ppm'] = self.calculate_ppm(defect, total)
            
            return weekly_quality
        except Exception as e:
            self.logger.error(f"計算每週品質指標失敗: {str(e)}")
            return {}
    
    def calculate_monthly_quality_metrics(self, quality_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算每月品質指標
        
        Args:
            quality_records: 品質記錄列表
            
        Returns:
            Dict[str, Dict[str, float]]: 每月品質指標字典
        """
        try:
            monthly_quality = {}
            
            for record in quality_records:
                record_date = record.get('date')
                good_quantity = record.get('good_quantity', 0)
                defect_quantity = record.get('defect_quantity', 0)
                total_quantity = record.get('total_quantity', 0)
                
                if not record_date or total_quantity <= 0:
                    continue
                
                # 計算月份
                if isinstance(record_date, date):
                    month_key = f"{record_date.year}-{record_date.month:02d}"
                else:
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        month_key = f"{date_obj.year}-{date_obj.month:02d}"
                    except:
                        continue
                
                if month_key not in monthly_quality:
                    monthly_quality[month_key] = {
                        'good_quantity': 0,
                        'defect_quantity': 0,
                        'total_quantity': 0
                    }
                
                monthly_quality[month_key]['good_quantity'] += float(good_quantity)
                monthly_quality[month_key]['defect_quantity'] += float(defect_quantity)
                monthly_quality[month_key]['total_quantity'] += float(total_quantity)
            
            # 計算品質指標
            for month_key, data in monthly_quality.items():
                total = data['total_quantity']
                good = data['good_quantity']
                defect = data['defect_quantity']
                
                data['yield_rate'] = self.calculate_yield_rate(good, total)
                data['defect_rate'] = self.calculate_defect_rate(defect, total)
                data['ppm'] = self.calculate_ppm(defect, total)
            
            return monthly_quality
        except Exception as e:
            self.logger.error(f"計算每月品質指標失敗: {str(e)}")
            return {}
    
    def calculate_workorder_quality_metrics(self, quality_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算工單品質指標
        
        Args:
            quality_records: 品質記錄列表
            
        Returns:
            Dict[str, Dict[str, float]]: 工單品質指標字典
        """
        try:
            workorder_quality = {}
            
            for record in quality_records:
                workorder_id = record.get('workorder_id')
                good_quantity = record.get('good_quantity', 0)
                defect_quantity = record.get('defect_quantity', 0)
                total_quantity = record.get('total_quantity', 0)
                
                if not workorder_id or total_quantity <= 0:
                    continue
                
                if workorder_id not in workorder_quality:
                    workorder_quality[workorder_id] = {
                        'good_quantity': 0,
                        'defect_quantity': 0,
                        'total_quantity': 0
                    }
                
                workorder_quality[workorder_id]['good_quantity'] += float(good_quantity)
                workorder_quality[workorder_id]['defect_quantity'] += float(defect_quantity)
                workorder_quality[workorder_id]['total_quantity'] += float(total_quantity)
            
            # 計算品質指標
            for workorder_id, data in workorder_quality.items():
                total = data['total_quantity']
                good = data['good_quantity']
                defect = data['defect_quantity']
                
                data['yield_rate'] = self.calculate_yield_rate(good, total)
                data['defect_rate'] = self.calculate_defect_rate(defect, total)
                data['ppm'] = self.calculate_ppm(defect, total)
            
            return workorder_quality
        except Exception as e:
            self.logger.error(f"計算工單品質指標失敗: {str(e)}")
            return {}
    
    def calculate_operator_quality_metrics(self, quality_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算作業員品質指標
        
        Args:
            quality_records: 品質記錄列表
            
        Returns:
            Dict[str, Dict[str, float]]: 作業員品質指標字典
        """
        try:
            operator_quality = {}
            
            for record in quality_records:
                operator_id = record.get('operator_id')
                good_quantity = record.get('good_quantity', 0)
                defect_quantity = record.get('defect_quantity', 0)
                total_quantity = record.get('total_quantity', 0)
                
                if not operator_id or total_quantity <= 0:
                    continue
                
                if operator_id not in operator_quality:
                    operator_quality[operator_id] = {
                        'good_quantity': 0,
                        'defect_quantity': 0,
                        'total_quantity': 0
                    }
                
                operator_quality[operator_id]['good_quantity'] += float(good_quantity)
                operator_quality[operator_id]['defect_quantity'] += float(defect_quantity)
                operator_quality[operator_id]['total_quantity'] += float(total_quantity)
            
            # 計算品質指標
            for operator_id, data in operator_quality.items():
                total = data['total_quantity']
                good = data['good_quantity']
                defect = data['defect_quantity']
                
                data['yield_rate'] = self.calculate_yield_rate(good, total)
                data['defect_rate'] = self.calculate_defect_rate(defect, total)
                data['ppm'] = self.calculate_ppm(defect, total)
            
            return operator_quality
        except Exception as e:
            self.logger.error(f"計算作業員品質指標失敗: {str(e)}")
            return {} 