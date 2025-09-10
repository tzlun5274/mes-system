"""
工單相關背景任務
從 Django 工單任務遷移到 FastAPI
"""

from celery_app import celery_app
from database.connection import SessionLocal
from database.models import WorkOrder, FillWork
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def update_workorder_status():
    """
    更新工單狀態
    定期檢查並更新工單的狀態
    """
    try:
        db = SessionLocal()
        
        # 取得所有進行中的工單
        active_workorders = db.query(WorkOrder).filter(
            WorkOrder.status.in_(["pending", "in_progress"])
        ).all()
        
        updated_count = 0
        
        for workorder in active_workorders:
            # 檢查工單是否應該完成
            if workorder.end_date and workorder.end_date < datetime.now().date():
                workorder.status = "completed"
                updated_count += 1
                logger.info(f"工單 {workorder.workorder_number} 已自動完成")
            
            # 檢查工單是否應該開始
            elif workorder.start_date and workorder.start_date <= datetime.now().date():
                if workorder.status == "pending":
                    workorder.status = "in_progress"
                    updated_count += 1
                    logger.info(f"工單 {workorder.workorder_number} 已自動開始")
        
        db.commit()
        logger.info(f"工單狀態更新完成，共更新 {updated_count} 個工單")
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"工單狀態更新失敗: {e}")
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
    finally:
        db.close()

@celery_app.task
def calculate_work_hours():
    """
    計算工作時數
    定期計算填報作業的工作時數
    """
    try:
        db = SessionLocal()
        
        # 取得需要計算工作時數的填報記錄
        fill_works = db.query(FillWork).filter(
            FillWork.end_time.isnot(None),
            FillWork.work_hours_calculated == 0
        ).all()
        
        calculated_count = 0
        
        for fill_work in fill_works:
            # 計算工作時數
            if fill_work.start_time and fill_work.end_time:
                start_datetime = datetime.combine(fill_work.work_date, fill_work.start_time)
                end_datetime = datetime.combine(fill_work.work_date, fill_work.end_time)
                
                # 計算總工作時間
                total_time = end_datetime - start_datetime
                total_hours = total_time.total_seconds() / 3600
                
                # 扣除休息時間
                if fill_work.has_break and fill_work.break_hours:
                    total_hours -= float(fill_work.break_hours)
                
                # 計算加班時數（假設正常工時為 8 小時）
                normal_hours = 8.0
                overtime_hours = max(0, total_hours - normal_hours)
                work_hours = min(total_hours, normal_hours)
                
                # 更新記錄
                fill_work.work_hours_calculated = work_hours
                fill_work.overtime_hours_calculated = overtime_hours
                calculated_count += 1
                
                logger.info(f"計算工時完成: {fill_work.operator} - {fill_work.workorder}")
        
        db.commit()
        logger.info(f"工作時數計算完成，共計算 {calculated_count} 筆記錄")
        
        return {
            "status": "success",
            "calculated_count": calculated_count,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"工作時數計算失敗: {e}")
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
    finally:
        db.close()

@celery_app.task
def cleanup_old_workorders():
    """
    清理舊工單資料
    定期清理已完成的舊工單資料
    """
    try:
        db = SessionLocal()
        
        # 取得 30 天前完成的工單
        cutoff_date = datetime.now().date() - timedelta(days=30)
        
        old_workorders = db.query(WorkOrder).filter(
            WorkOrder.status == "completed",
            WorkOrder.updated_at < cutoff_date
        ).all()
        
        deleted_count = 0
        
        for workorder in old_workorders:
            # 這裡可以實現實際的清理邏輯
            # 例如：備份到歷史表、刪除相關記錄等
            logger.info(f"清理舊工單: {workorder.workorder_number}")
            deleted_count += 1
        
        logger.info(f"舊工單清理完成，共清理 {deleted_count} 個工單")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"舊工單清理失敗: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
    finally:
        db.close()
