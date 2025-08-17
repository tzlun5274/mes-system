#!/usr/bin/env python3
"""
除錯公司分離的查詢邏輯
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

def debug_company_filter():
    """除錯公司分離的查詢邏輯"""
    print("=== 除錯公司分離的查詢邏輯 ===")
    
    # 1. 檢查工單
    workorder = WorkOrder.objects.filter(order_number='331-25220001').first()
    if workorder:
        print(f"\n1. 工單資訊:")
        print(f"   工單號: {workorder.order_number}")
        print(f"   產品代碼: {workorder.product_code}")
        print(f"   公司代號: {workorder.company_code}")
        
        # 2. 檢查公司配置
        if workorder.company_code:
            company_config = CompanyConfig.objects.filter(
                company_code=workorder.company_code
            ).first()
            print(f"\n2. 公司配置:")
            print(f"   公司代號: {company_config.company_code if company_config else 'None'}")
            print(f"   公司名稱: {company_config.company_name if company_config else 'None'}")
        
        # 3. 檢查填報記錄
        print(f"\n3. 填報記錄查詢:")
        
        # 基本查詢
        basic_query = FillWork.objects.filter(
            workorder=workorder.order_number,
            product_id=workorder.product_code
        )
        print(f"   基本查詢結果: {basic_query.count()} 筆")
        
        # 按公司分離
        if workorder.company_code and company_config:
            company_query = basic_query.filter(
                company_name=company_config.company_name
            )
            print(f"   按公司分離後: {company_query.count()} 筆")
            
            # 檢查出貨包裝
            packaging_query = company_query.filter(
                process__name__exact='出貨包裝',
                approval_status='approved'
            )
            print(f"   出貨包裝已核准: {packaging_query.count()} 筆")
            
            for report in packaging_query:
                print(f"     - 數量: {report.work_quantity}, 不良品: {report.defect_quantity}")
            
            # 計算總數量
            total_packaging = packaging_query.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            print(f"   出貨包裝總數量: {total_packaging}")
        
        # 4. 手動建立監控資料
        print(f"\n4. 手動建立監控資料:")
        monitoring_data = ProductionMonitoringData.get_or_create_for_workorder(workorder)
        
        # 5. 手動更新統計
        print(f"   更新前出貨包裝數量: {monitoring_data.packaging_total_quantity}")
        monitoring_data.update_all_statistics()
        monitoring_data.refresh_from_db()
        print(f"   更新後出貨包裝數量: {monitoring_data.packaging_total_quantity}")

if __name__ == "__main__":
    debug_company_filter() 