#!/usr/bin/env python3
"""
監控資料表查詢除錯腳本
檢查為什麼監控資料表查詢不到出貨包裝記錄
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django.db.models import Sum
from workorder.models import WorkOrder
from workorder.production_monitoring.models import ProductionMonitoringData
from workorder.fill_work.models import FillWork
from erp_integration.models import CompanyConfig

def debug_monitoring_query():
    """除錯監控資料表查詢"""
    print("=== 監控資料表查詢除錯 ===")
    
    # 1. 檢查出貨包裝填報記錄
    print("\n1. 所有出貨包裝填報記錄:")
    all_packaging = FillWork.objects.filter(
        process__name__exact='出貨包裝',
        approval_status='approved'
    )
    print(f"   總數: {all_packaging.count()}")
    
    for report in all_packaging[:5]:  # 只顯示前5筆
        print(f"   - 工單: {report.workorder}, 產品: {report.product_id}, 公司: {report.company_name}, 數量: {report.work_quantity}")
    
    # 2. 檢查第一個進行中的工單
    workorder = WorkOrder.objects.filter(status__in=['pending', 'in_progress']).first()
    if workorder:
        print(f"\n2. 測試工單: {workorder.order_number} - {workorder.product_code} - {workorder.company_code}")
        
        # 3. 檢查該工單的填報記錄
        workorder_fillwork = FillWork.objects.filter(
            workorder=workorder.order_number,
            product_id=workorder.product_code
        )
        print(f"   該工單的填報記錄: {workorder_fillwork.count()} 筆")
        
        for report in workorder_fillwork:
            print(f"   - 工序: {report.process.name}, 狀態: {report.approval_status}, 數量: {report.work_quantity}")
        
        # 4. 檢查公司分離
        if workorder.company_code:
            company_config = CompanyConfig.objects.filter(
                company_code=workorder.company_code
            ).first()
            print(f"\n3. 公司配置: {company_config}")
            
            if company_config:
                company_fillwork = workorder_fillwork.filter(
                    company_name=company_config.company_name
                )
                print(f"   按公司分離後的填報記錄: {company_fillwork.count()} 筆")
                
                for report in company_fillwork:
                    print(f"   - 工序: {report.process.name}, 狀態: {report.approval_status}, 數量: {report.work_quantity}")
        
        # 5. 檢查出貨包裝記錄
        packaging_reports = workorder_fillwork.filter(
            process__name__exact='出貨包裝',
            approval_status='approved'
        )
        print(f"\n4. 該工單的出貨包裝記錄: {packaging_reports.count()} 筆")
        
        for report in packaging_reports:
            print(f"   - 數量: {report.work_quantity}, 不良品: {report.defect_quantity}")
        
        # 6. 手動計算出貨包裝數量
        total_packaging = packaging_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        print(f"   手動計算出貨包裝總數量: {total_packaging}")
        
        # 7. 檢查監控資料
        monitoring_data = ProductionMonitoringData.objects.filter(workorder=workorder).first()
        if monitoring_data:
            print(f"\n5. 監控資料:")
            print(f"   出貨包裝總數量: {monitoring_data.packaging_total_quantity}")
            print(f"   出貨包裝良品: {monitoring_data.packaging_good_quantity}")
            print(f"   出貨包裝不良品: {monitoring_data.packaging_defect_quantity}")
            
            # 8. 重新更新監控資料
            print(f"\n6. 重新更新監控資料...")
            monitoring_data.update_all_statistics()
            monitoring_data.refresh_from_db()
            
            print(f"   更新後出貨包裝總數量: {monitoring_data.packaging_total_quantity}")
            print(f"   更新後出貨包裝良品: {monitoring_data.packaging_good_quantity}")
            print(f"   更新後出貨包裝不良品: {monitoring_data.packaging_defect_quantity}")

if __name__ == "__main__":
    debug_monitoring_query() 