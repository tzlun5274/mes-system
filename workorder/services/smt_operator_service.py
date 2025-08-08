"""
SMT設備作業員名稱服務
負責處理SMT設備名稱與作業員名稱的對應關係
"""

from typing import Optional, Dict, List
from equip.models import Equipment
from process.models import Operator
from workorder.workorder_reporting.models import BackupSMTSupplementReport as SMTSupplementReport


class SMTOperatorService:
    """
    SMT設備作業員名稱服務類別
    處理SMT設備名稱與作業員名稱的對應關係
    """
    
    @staticmethod
    def get_smt_equipment_operator_name(equipment_name: str) -> str:
        """
        根據SMT設備名稱取得對應的作業員名稱
        
        Args:
            equipment_name: 設備名稱
            
        Returns:
            str: 作業員名稱（通常是設備名稱）
        """
        if not equipment_name:
            return "未指定設備"
        
        # 檢查是否為SMT設備
        if 'SMT' in equipment_name.upper():
            return f"{equipment_name} (SMT設備)"
        else:
            return equipment_name
    
    @staticmethod
    def get_smt_equipment_display_name(equipment_name: str) -> str:
        """
        取得SMT設備的顯示名稱
        
        Args:
            equipment_name: 設備名稱
            
        Returns:
            str: 顯示名稱
        """
        if not equipment_name:
            return "未指定設備"
        
        # 格式化顯示名稱
        if 'SMT' in equipment_name.upper():
            return f"{equipment_name} (SMT設備)"
        else:
            return equipment_name
    
    @staticmethod
    def is_smt_equipment(equipment_name: str) -> bool:
        """
        判斷是否為SMT設備
        
        Args:
            equipment_name: 設備名稱
            
        Returns:
            bool: 是否為SMT設備
        """
        if not equipment_name:
            return False
        
        smt_keywords = ['SMT', '貼片', 'PICK', 'PLACE']
        return any(keyword.upper() in equipment_name.upper() for keyword in smt_keywords)
    
    @staticmethod
    def get_all_smt_equipment() -> List[Dict]:
        """
        取得所有SMT設備及其對應的作業員名稱
        
        Returns:
            List[Dict]: SMT設備列表
        """
        smt_equipment = Equipment.objects.filter(
            name__icontains='SMT'
        ).order_by('name')
        
        result = []
        for equipment in smt_equipment:
            result.append({
                'id': equipment.id,
                'name': equipment.name,
                'operator_name': SMTOperatorService.get_smt_equipment_operator_name(equipment.name),
                'display_name': SMTOperatorService.get_smt_equipment_display_name(equipment.name),
                'status': equipment.status,
                'is_smt': True
            })
        
        return result
    
    @staticmethod
    def create_smt_report_with_operator_name(
        equipment: Equipment,
        **kwargs
    ) -> SMTSupplementReport:
        """
        建立SMT報工記錄，自動設定作業員名稱
        
        Args:
            equipment: 設備物件
            **kwargs: 其他報工參數
            
        Returns:
            SMTSupplementReport: 建立的報工記錄
        """
        # 自動設定設備作業員名稱
        equipment_operator_name = SMTOperatorService.get_smt_equipment_operator_name(equipment.name)
        
        # 建立報工記錄
        report = SMTSupplementReport.objects.create(
            equipment=equipment,
            equipment_operator_name=equipment_operator_name,
            **kwargs
        )
        
        return report
    
    @staticmethod
    def update_smt_report_operator_name(report: SMTSupplementReport) -> None:
        """
        更新SMT報工記錄的作業員名稱
        
        Args:
            report: SMT報工記錄
        """
        if report.equipment:
            equipment_operator_name = SMTOperatorService.get_smt_equipment_operator_name(report.equipment.name)
            report.equipment_operator_name = equipment_operator_name
            report.save()
    
    @staticmethod
    def get_operator_display_name_for_report(report: SMTSupplementReport) -> str:
        """
        取得報工記錄的作業員顯示名稱
        
        Args:
            report: 報工記錄
            
        Returns:
            str: 作業員顯示名稱
        """
        if hasattr(report, 'equipment_operator_name') and report.equipment_operator_name:
            return report.equipment_operator_name
        elif hasattr(report, 'operator') and report.operator:
            if SMTOperatorService.is_smt_equipment(report.operator):
                return f"{report.operator} (SMT設備)"
            else:
                return report.operator
        elif hasattr(report, 'equipment') and report.equipment:
            return SMTOperatorService.get_smt_equipment_display_name(report.equipment.name)
        else:
            return "未指定作業員"
    
    @staticmethod
    def get_operator_statistics() -> Dict:
        """
        取得作業員統計資訊（包含SMT設備）
        
        Returns:
            Dict: 統計資訊
        """
        # 取得真實作業員統計
        real_operators = Operator.objects.exclude(name__icontains='SMT').count()
        
        # 取得SMT設備統計
        smt_equipment = Equipment.objects.filter(name__icontains='SMT').count()
        
        # 取得SMT報工記錄統計
        smt_reports = SMTSupplementReport.objects.filter(
            equipment__name__icontains='SMT'
        ).count()
        
        return {
            'real_operators': real_operators,
            'smt_equipment': smt_equipment,
            'smt_reports': smt_reports,
            'total_operators': real_operators + smt_equipment
        } 