"""
資料同步服務
簡單的 A 到 B 資料同步
"""

import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


def create_report_data_from_fill_work(fill_work):
    """從填報資料建立報表資料 - 純粹同步，不計算"""
    try:
        from reporting.models import WorkOrderReportData
        
        # 純粹的資料複製，不做任何計算
        report_data = WorkOrderReportData.objects.create(
            workorder_id=fill_work.workorder,
            company=fill_work.company_name,
            operator_name=fill_work.operator or '',
            product_code=fill_work.product_id or '',
            process_name=fill_work.operation or fill_work.process_name or '',
            work_date=fill_work.work_date,
            work_week=0,  # 預設值，不計算
            work_month=0,  # 預設值，不計算
            work_quarter=0,  # 預設值，不計算
            work_year=0,  # 預設值，不計算
            start_time=fill_work.start_time,
            end_time=fill_work.end_time,
            work_hours=fill_work.work_hours_calculated or 0,
            overtime_hours=fill_work.overtime_hours_calculated or 0,
            total_hours=0,  # 預設值，不計算
            daily_work_hours=0,  # 預設值，不計算
            weekly_work_hours=0,  # 預設值，不計算
            monthly_work_hours=0,  # 預設值，不計算
            operator_count=1,  # 預設值
            equipment_hours=0,  # 預設值，不計算
            work_quantity=fill_work.work_quantity or 0,
            defect_quantity=fill_work.defect_quantity or 0,
        )
        
        return report_data
        
    except Exception as e:
        logger.error(f"建立報表資料失敗 {fill_work.id}: {str(e)}")
        return None


def sync_data():
    """同步資料 - 簡單的 A 到 B"""
    try:
        from workorder.fill_work.models import FillWork
        from reporting.models import WorkOrderReportData
        
        logger.info("開始同步資料")
        
        # 同步填報資料
        fill_works = FillWork.objects.filter(approval_status='approved')
        fill_synced = 0
        fill_failed = 0
        
        logger.info(f"找到 {fill_works.count()} 筆填報資料需要同步")
        
        for fill_work in fill_works:
            try:
                # 檢查必要欄位
                if not fill_work.work_date or not fill_work.workorder or not fill_work.company_name:
                    fill_failed += 1
                    logger.warning(f"跳過填報資料 {fill_work.id}: 缺少必要欄位")
                    continue
                
                # 檢查是否已存在（使用更精確的唯一性檢查）
                existing = WorkOrderReportData.objects.filter(
                    workorder_id=fill_work.workorder,
                    company=fill_work.company_name,
                    work_date=fill_work.work_date,
                    operator_name=fill_work.operator or '',
                    start_time=fill_work.start_time
                ).exists()
                
                if existing:
                    # 已存在，跳過
                    continue
                
                # 使用專用的同步函數
                report_data = create_report_data_from_fill_work(fill_work)
                
                if report_data:
                    fill_synced += 1
                    logger.info(f"新增報表資料: {fill_work.workorder}")
                else:
                    fill_failed += 1
                    logger.warning(f"同步填報資料失敗 {fill_work.id}: 無法建立報表資料")
            except Exception as e:
                fill_failed += 1
                logger.error(f"同步填報資料失敗 {fill_work.id}: {str(e)}")
                import traceback
                logger.error(f"詳細錯誤: {traceback.format_exc()}")
        
        # 暫時不同步現場報工資料，先測試填報資料
        onsite_synced = 0
        
        total_synced = fill_synced + onsite_synced
        message = f"資料同步完成：填報成功 {fill_synced} 筆，失敗 {fill_failed} 筆，現場報工 {onsite_synced} 筆，總計 {total_synced} 筆"
        logger.info(message)
        
        return {
            'success': True,
            'message': message,
            'total_synced': total_synced,
            'fill_synced': fill_synced,
            'fill_failed': fill_failed
        }
        
    except Exception as e:
        error_msg = f"資料同步失敗: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"詳細錯誤: {traceback.format_exc()}")
        return {
            'success': False,
            'error': error_msg
        }


# 直接執行資料同步
if __name__ == "__main__":
    """
    直接執行資料同步
    使用方法：
    python data_sync.py
    """
    import sys
    import os
    
    # 添加 Django 專案路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
    
    # 初始化 Django
    import django
    django.setup()
    
    # 執行資料同步
    print("開始執行資料同步...")
    result = sync_data()
    
    if result['success']:
        print(f"資料同步成功: {result['message']}")
    else:
        print(f"資料同步失敗: {result.get('error', '未知錯誤')}")
        sys.exit(1)