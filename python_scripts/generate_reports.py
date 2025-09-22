#!/usr/bin/env python3
"""
報表生成服務執行腳本
使用現有的工單、填報作業、設備、作業員資料來生成報表
"""

import os
import django
from datetime import date, timedelta

# 設定Django環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

def generate_reports():
    """執行報表生成服務"""
    print("🚀 開始執行報表生成服務")
    print("=" * 60)
    
    try:
        from reporting.work_hour_report_service import WorkHourReportService
        from reporting.report_generator import ReportGenerator
        from reporting.models import WorkTimeReportSummary, ReportSchedule, OperatorProcessCapacityScore
        from workorder.models import WorkOrder
        from workorder.fill_work.models import FillWork
        from process.models import Operator
        from equip.models import Equipment
        
        # 初始化服務
        work_time_service = WorkTimeReportService()
        report_generator = ReportGeneratorService()
        
        print("📊 檢查現有資料...")
        
        # 檢查現有資料
        workorder_count = WorkOrder.objects.count()
        fillwork_count = FillWork.objects.count()
        operator_count = Operator.objects.count()
        equipment_count = Equipment.objects.count()
        
        print(f"  工單數量: {workorder_count}")
        print(f"  填報作業數量: {fillwork_count}")
        print(f"  作業員數量: {operator_count}")
        print(f"  設備數量: {equipment_count}")
        
        if workorder_count == 0 or fillwork_count == 0:
            print("❌ 沒有足夠的資料來生成報表")
            return
        
        print("\n📈 開始生成報表...")
        
        # 生成最近7天的日報表
        for i in range(7):
            report_date = date.today() - timedelta(days=i)
            print(f"  生成 {report_date} 的日報表...")
            
            try:
                # 為每個公司生成報表
                companies = ['001', '002', '003']  # 假設的公司代號
                
                for company_code in companies:
                    # 檢查該公司該日期是否已有報表
                    existing_report = WorkTimeReportSummary.objects.filter(
                        report_date=report_date,
                        company_code=company_code,
                        report_type='work_time',
                        time_dimension='daily'
                    ).first()
                    
                    if existing_report:
                        print(f"    {company_code} 公司 {report_date} 報表已存在，跳過")
                        continue
                    
                    # 生成日報表
                    summary = work_time_service.generate_daily_work_time_report(
                        report_date=report_date,
                        company_code=company_code
                    )
                    
                    if summary:
                        print(f"    ✓ {company_code} 公司 {report_date} 日報表生成成功")
                    else:
                        print(f"    ⚠️ {company_code} 公司 {report_date} 日報表生成失敗")
                        
            except Exception as e:
                print(f"    ❌ 生成 {report_date} 報表時發生錯誤: {e}")
        
        print("\n👥 開始生成作業員評分...")
        
        # 生成作業員評分
        try:
            # 獲取最近的填報作業資料
            recent_fillworks = FillWork.objects.filter(
                work_date__gte=date.today() - timedelta(days=30)
            ).order_by('-work_date')[:100]  # 最近100筆
            
            for fillwork in recent_fillworks:
                # 檢查是否已有評分
                existing_score = OperatorProcessCapacityScore.objects.filter(
                    operator_name=fillwork.operator,
                    work_date=fillwork.work_date,
                    workorder_id=fillwork.workorder,
                    product_code=fillwork.product_id
                ).first()
                
                if existing_score:
                    continue
                
                # 生成評分
                try:
                    score = work_time_service.generate_operator_score(
                        operator_name=fillwork.operator,
                        operator_id=fillwork.operator,  # 假設作業員編號與姓名相同
                        company_code=fillwork.company_code or '001',
                        product_code=fillwork.product_id,
                        process_name=fillwork.operation or '一般作業',
                        workorder_id=fillwork.workorder,
                        work_date=fillwork.work_date,
                        work_hours=float(fillwork.work_hours_calculated or 0),
                        completed_quantity=int(fillwork.work_quantity or 0),
                        defect_quantity=0  # 假設沒有不良品
                    )
                    
                    if score:
                        print(f"  ✓ {fillwork.operator} {fillwork.work_date} 評分生成成功")
                    
                except Exception as e:
                    print(f"  ❌ 生成 {fillwork.operator} 評分時發生錯誤: {e}")
                    
        except Exception as e:
            print(f"❌ 生成作業員評分時發生錯誤: {e}")
        
        print("\n📋 建立報表排程...")
        
        # 建立一些預設的報表排程
        try:
            # 檢查是否已有排程
            if ReportSchedule.objects.count() == 0:
                schedules = [
                    {
                        'name': '每日工作時數報表',
                        'company_code': '001',
                        'report_type': 'work_time',
                        'time_dimension': 'daily',
                        'schedule_time': '08:00:00',
                        'is_active': True,
                        'email_recipients': 'manager@company.com,admin@company.com'
                    },
                    {
                        'name': '週工作時數報表',
                        'company_code': '001',
                        'report_type': 'work_time',
                        'time_dimension': 'weekly',
                        'schedule_time': '09:00:00',
                        'schedule_day': 1,  # 週一
                        'is_active': True,
                        'email_recipients': 'manager@company.com'
                    },
                    {
                        'name': '月工作時數報表',
                        'company_code': '001',
                        'report_type': 'work_time',
                        'time_dimension': 'monthly',
                        'schedule_time': '10:00:00',
                        'schedule_day': 1,  # 每月1號
                        'is_active': True,
                        'email_recipients': 'manager@company.com,finance@company.com'
                    }
                ]
                
                for schedule_data in schedules:
                    schedule = ReportSchedule.objects.create(**schedule_data)
                    print(f"  ✓ 排程 '{schedule.name}' 建立成功")
            else:
                print("  排程已存在，跳過建立")
                
        except Exception as e:
            print(f"❌ 建立排程時發生錯誤: {e}")
        
        print("\n📊 統計結果...")
        
        # 統計結果
        total_reports = WorkTimeReportSummary.objects.count()
        total_scores = OperatorProcessCapacityScore.objects.count()
        total_schedules = ReportSchedule.objects.count()
        
        print(f"  總報表數量: {total_reports}")
        print(f"  總評分數量: {total_scores}")
        print(f"  總排程數量: {total_schedules}")
        
        print("\n✅ 報表生成服務執行完成！")
        
    except Exception as e:
        print(f"❌ 報表生成服務執行失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    generate_reports()
