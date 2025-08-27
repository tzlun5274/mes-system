#!/usr/bin/env python3
"""
簡化報表生成腳本
避免數值溢位問題，直接建立測試報表資料
"""

import os
import django
from datetime import date, timedelta
from decimal import Decimal

# 設定Django環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

def generate_simple_reports():
    """生成簡化的報表資料"""
    print("🚀 開始生成簡化報表資料")
    print("=" * 60)
    
    try:
        from reporting.models import WorkTimeReportSummary, WorkTimeReportDetail, OperatorProcessCapacityScore
        from workorder.fill_work.models import FillWork
        
        print("📊 檢查現有資料...")
        
        # 檢查現有資料
        fillwork_count = FillWork.objects.count()
        print(f"  填報作業數量: {fillwork_count}")
        
        if fillwork_count == 0:
            print("❌ 沒有填報作業資料")
            return
        
        print("\n📈 開始生成日報表...")
        
        # 生成最近7天的日報表
        for i in range(7):
            report_date = date.today() - timedelta(days=i)
            print(f"  生成 {report_date} 的日報表...")
            
            # 查詢該日期的填報作業
            daily_fillworks = FillWork.objects.filter(work_date=report_date)
            
            if not daily_fillworks.exists():
                print(f"    {report_date} 沒有填報作業資料，跳過")
                continue
            
            # 計算統計資料
            total_work_hours = sum(float(record.work_hours_calculated or 0) for record in daily_fillworks)
            total_overtime_hours = sum(float(record.overtime_hours_calculated or 0) for record in daily_fillworks)
            total_work_quantity = sum(int(record.work_quantity or 0) for record in daily_fillworks)
            
            # 統計作業員和工單
            operators = set(record.operator for record in daily_fillworks if record.operator)
            workorders = set(record.workorder for record in daily_fillworks if record.workorder)
            
            # 計算效率指標
            efficiency_rate = 85.5 if total_work_hours > 0 else 0.0
            defect_rate = 2.5
            completion_rate = 95.0
            
            # 為每個公司生成報表
            companies = ['001', '002', '003']
            
            for company_code in companies:
                # 檢查是否已有報表
                existing_report = WorkTimeReportSummary.objects.filter(
                    report_date=report_date,
                    company_code=company_code,
                    report_type='work_time',
                    time_dimension='daily'
                ).first()
                
                if existing_report:
                    print(f"    {company_code} 公司 {report_date} 報表已存在，跳過")
                    continue
                
                # 建立報表彙總
                summary = WorkTimeReportSummary.objects.create(
                    report_date=report_date,
                    company_code=company_code,
                    company_name=f"測試公司{company_code}",
                    report_type='work_time',
                    time_dimension='daily',
                    total_work_hours=total_work_hours,
                    total_overtime_hours=total_overtime_hours,
                    total_work_quantity=total_work_quantity,
                    total_defect_quantity=int(total_work_quantity * 0.025),  # 2.5%不良率
                    total_good_quantity=int(total_work_quantity * 0.975),    # 97.5%良品率
                    efficiency_rate=efficiency_rate,
                    defect_rate=defect_rate,
                    completion_rate=completion_rate,
                    unique_operators_count=len(operators),
                    unique_equipment_count=5,  # 假設值
                    total_workorders_count=len(workorders)
                )
                
                # 建立詳細資料
                detailed_data = {
                    'fill_work_records': [
                        {
                            'operator_name': record.operator,
                            'workorder_id': record.workorder,
                            'work_hours': float(record.work_hours_calculated or 0),
                            'status': record.approval_status
                        }
                        for record in daily_fillworks[:10]  # 只取前10筆
                    ],
                    'generated_at': '2025-08-24T12:00:00Z',
                    'data_source': 'workorder_fill_work'
                }
                
                detail = WorkTimeReportDetail.objects.create(
                    summary=summary,
                    detailed_data=detailed_data,
                    data_source='workorder_fill_work',
                    calculation_method='daily_aggregation'
                )
                
                print(f"    ✓ {company_code} 公司 {report_date} 日報表生成成功")
        
        print("\n👥 開始生成作業員評分...")
        
        # 生成作業員評分（避免數值溢位）
        try:
            # 獲取最近的填報作業資料
            recent_fillworks = FillWork.objects.filter(
                work_date__gte=date.today() - timedelta(days=30)
            ).order_by('-work_date')[:50]  # 只取最近50筆
            
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
                
                # 生成評分（使用安全的數值）
                try:
                    work_hours = float(fillwork.work_hours_calculated or 0)
                    completed_qty = int(fillwork.work_quantity or 0)
                    
                    # 避免除零和數值溢位
                    if work_hours <= 0:
                        work_hours = 1.0
                    
                    if completed_qty <= 0:
                        completed_qty = 1
                    
                    # 限制數值範圍
                    work_hours = min(work_hours, 24.0)  # 最大24小時
                    completed_qty = min(completed_qty, 1000)  # 最大1000個
                    
                    standard_capacity = Decimal('12.5')
                    actual_capacity = Decimal(str(completed_qty)) / Decimal(str(work_hours))
                    actual_capacity = min(actual_capacity, Decimal('50.0'))  # 限制最大產能
                    
                    capacity_ratio = actual_capacity / standard_capacity
                    capacity_ratio = min(capacity_ratio, Decimal('5.0'))  # 限制最大比率
                    
                    capacity_score = capacity_ratio * 100
                    capacity_score = min(capacity_score, Decimal('500.0'))  # 限制最大評分
                    
                    # 計算等級
                    if capacity_score >= 90:
                        grade = 'A'
                    elif capacity_score >= 80:
                        grade = 'B'
                    elif capacity_score >= 70:
                        grade = 'C'
                    else:
                        grade = 'D'
                    
                    # 建立評分記錄
                    score = OperatorProcessCapacityScore.objects.create(
                        operator_name=fillwork.operator,
                        operator_id=fillwork.operator,
                        company_code=fillwork.company_code or '001',
                        product_code=fillwork.product_id,
                        process_name=fillwork.operation or '一般作業',
                        workorder_id=fillwork.workorder,
                        work_date=fillwork.work_date,
                        work_hours=work_hours,
                        standard_capacity_per_hour=standard_capacity,
                        actual_capacity_per_hour=actual_capacity,
                        completed_quantity=completed_qty,
                        capacity_ratio=capacity_ratio,
                        capacity_score=capacity_score,
                        grade=grade,
                        defect_quantity=0,
                        efficiency_factor=Decimal('1.0'),
                        learning_curve_factor=Decimal('1.0')
                    )
                    
                    print(f"  ✓ {fillwork.operator} {fillwork.work_date} 評分生成成功")
                    
                except Exception as e:
                    print(f"  ❌ 生成 {fillwork.operator} 評分時發生錯誤: {e}")
                    
        except Exception as e:
            print(f"❌ 生成作業員評分時發生錯誤: {e}")
        
        print("\n📊 統計結果...")
        
        # 統計結果
        total_reports = WorkTimeReportSummary.objects.count()
        total_scores = OperatorProcessCapacityScore.objects.count()
        
        print(f"  總報表數量: {total_reports}")
        print(f"  總評分數量: {total_scores}")
        
        print("\n✅ 簡化報表生成完成！")
        
    except Exception as e:
        print(f"❌ 簡化報表生成失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    generate_simple_reports()
