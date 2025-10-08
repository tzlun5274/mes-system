"""
工單分析服務
提供已完工工單的分析功能，所有分析都基於批量分析核心函數
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class WorkOrderAnalysisService:
    """工單分析服務"""
    
    @staticmethod
    def analyze_completed_workorder(workorder_id, company_code, product_code=None, force=False):
        """
        分析單一已完工工單（調用批量分析核心函數）
        
        Args:
            workorder_id: 工單編號
            company_code: 公司代號
            product_code: 產品編號（可選）
            force: 是否強制重新分析，即使已經分析過
            
        Returns:
            dict: 分析結果
        """
        try:
            logger.info(f"開始分析單一工單: {workorder_id} ({company_code})")
            
            # 調用批量分析核心函數，但只分析指定的工單
            result = WorkOrderAnalysisService.analyze_completed_workorders_batch(
                start_date=None,  # 不限制日期
                end_date=None,    # 不限制日期
                company_code=company_code,
                specific_workorder_id=workorder_id,  # 指定特定工單
                force=force
            )
            
            if result['success']:
                if result['success_count'] > 0:
                    return {
                        'success': True,
                        'message': f'工單 {workorder_id} 分析完成',
                        'analysis_id': result.get('analysis_id'),
                        'created': result.get('created', False)
                    }
                else:
                    return {
                        'success': False,
                        'error': f'工單 {workorder_id} 沒有找到或無法分析'
                    }
            else:
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f'分析工單時發生錯誤: {str(e)}'
            }
    
    @staticmethod
    def analyze_completed_workorders_batch(start_date=None, end_date=None, company_code=None, specific_workorder_id=None, force=False):
        """
        批量分析已完工工單（核心分析函數）
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD 格式)
            end_date: 結束日期 (YYYY-MM-DD 格式)
            company_code: 公司代號
            specific_workorder_id: 指定特定工單編號（用於單一工單分析）
            force: 是否強制重新分析
            
        Returns:
            dict: 批量分析結果
        """
        from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess
        from .models import CompletedWorkOrderAnalysis
        
        try:
            logger.info(f"開始批量分析 - 公司代號: {company_code}, 開始日期: {start_date}, 結束日期: {end_date}")
            
            # 查詢已完工工單，排除 RD樣品
            queryset = CompletedWorkOrder.objects.exclude(order_number__icontains='RD樣品')
            logger.info(f"初始查詢結果數量（排除RD樣品）: {queryset.count()}")
            
            if company_code:
                queryset = queryset.filter(company_code=company_code)
                logger.info(f"按公司代號過濾後數量: {queryset.count()}")
            
            # 如果指定特定工單，只分析該工單
            if specific_workorder_id:
                queryset = queryset.filter(order_number=specific_workorder_id)
                logger.info(f"指定工單過濾後數量: {queryset.count()}")
            
            # 處理日期格式轉換
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(completed_at__date__gte=start_date_obj)
                    logger.info(f"按開始日期過濾後數量: {queryset.count()}")
                except ValueError:
                    logger.error(f"開始日期格式錯誤: {start_date}")
                    return {
                        'success': False,
                        'error': f'開始日期格式錯誤: {start_date}，請使用 YYYY-MM-DD 格式'
                    }
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(completed_at__date__lte=end_date_obj)
                    logger.info(f"按結束日期過濾後數量: {queryset.count()}")
                except ValueError:
                    logger.error(f"結束日期格式錯誤: {end_date}")
                    return {
                        'success': False,
                        'error': f'結束日期格式錯誤: {end_date}，請使用 YYYY-MM-DD 格式'
                    }
            
            # 獲取所有已完工工單
            completed_workorders = list(queryset)
            
            if not completed_workorders:
                return {
                    'success': False,
                    'error': '沒有找到符合條件的已完工工單'
                }
            
            # 批量分析
            success_count = 0
            error_count = 0
            errors = []
            analysis_id = None
            created = False
            
            logger.info(f"開始分析 {len(completed_workorders)} 筆工單")
            
            for completed_workorder in completed_workorders:
                order_number = completed_workorder.order_number
                workorder_company_code = completed_workorder.company_code
                product_code = completed_workorder.product_code
                logger.info(f"分析工單: {order_number} ({workorder_company_code}) - {product_code}")
                
                # 檢查是否已經分析過
                if not force:
                    existing_analysis = CompletedWorkOrderAnalysis.objects.filter(
                        workorder_id=order_number,
                        company_code=workorder_company_code
                    ).first()
                    
                    if existing_analysis:
                        logger.info(f'工單 {order_number} 已經分析過，跳過分析')
                        success_count += 1
                        continue
                
                # 執行工單分析
                try:
                    # 檢查必要欄位
                    if not completed_workorder.completed_at:
                        raise ValueError("工單沒有完工時間")
                    
                    # 使用計劃數量作為完成數量的替代
                    order_quantity = completed_workorder.completed_quantity or completed_workorder.planned_quantity
                    if not order_quantity:
                        raise ValueError("工單沒有完成數量且沒有計劃數量")
                    
                    # 收集工序詳細資料
                    process_details = {}
                    operator_details = {}
                    total_processes = 0
                    unique_processes = set()
                    total_operators = set()
                    
                    # 主要從已完工生產報工記錄收集資料（工序表可能為空）
                    from workorder.models import CompletedProductionReport
                    production_reports = CompletedProductionReport.objects.filter(
                        completed_workorder_id=completed_workorder.id
                    ).order_by('report_date', 'start_time')
                    
                    # 按工序分組統計
                    process_stats = {}
                    operator_stats = {}
                    
                    for report in production_reports:
                        process_name = report.process_name
                        operator = report.operator
                        
                        # 統計工序資料
                        if process_name not in process_stats:
                            process_stats[process_name] = {
                                'total_hours': 0,
                                'total_quantity': 0,
                                'total_defect': 0,
                                'operators': set(),
                                'equipment': set(),
                                'report_count': 0
                            }
                        
                        process_stats[process_name]['total_hours'] += float(report.work_hours)
                        process_stats[process_name]['total_quantity'] += report.work_quantity
                        process_stats[process_name]['total_defect'] += report.defect_quantity
                        process_stats[process_name]['operators'].add(operator)
                        if report.equipment:
                            process_stats[process_name]['equipment'].add(report.equipment)
                        process_stats[process_name]['report_count'] += 1
                        
                        # 統計作業員資料
                        if operator not in operator_stats:
                            operator_stats[operator] = {
                                'total_hours': 0,
                                'total_quantity': 0,
                                'processes': set(),
                                'report_count': 0,
                                'overtime_hours': 0
                            }
                        
                        operator_stats[operator]['total_hours'] += float(report.work_hours)
                        operator_stats[operator]['total_quantity'] += report.work_quantity
                        operator_stats[operator]['processes'].add(process_name)
                        operator_stats[operator]['report_count'] += 1
                        
                        # 計算加班時數（假設超過8小時為加班）
                        if float(report.work_hours) > 8:
                            operator_stats[operator]['overtime_hours'] += float(report.work_hours) - 8
                    
                    # 建立工序詳細資料
                    for process_name, stats in process_stats.items():
                        unique_processes.add(process_name)
                        total_processes += 1
                        
                        process_details[process_name] = {
                            'process_order': 999,  # 未知順序
                            'planned_quantity': 0,
                            'completed_quantity': stats['total_quantity'],
                            'status': 'completed',
                            'assigned_operator': list(stats['operators'])[0] if stats['operators'] else '',
                            'assigned_equipment': list(stats['equipment'])[0] if stats['equipment'] else '',
                            'total_work_hours': stats['total_hours'],
                            'total_hours': stats['total_hours'],  # 模板期望的欄位名稱
                            'total_good_quantity': stats['total_quantity'],
                            'total_defect_quantity': stats['total_defect'],
                            'report_count': stats['report_count'],
                            'operators': list(stats['operators']),
                            'equipment': list(stats['equipment']),
                            'hourly_capacity': stats['total_quantity'] / max(1, stats['total_hours']) if stats['total_hours'] > 0 else 0
                        }
                    
                    # 建立作業員詳細資料
                    for operator, stats in operator_stats.items():
                        total_operators.add(operator)
                        
                        # 計算作業員的實際工作天數
                        operator_reports = production_reports.filter(operator=operator)
                        if operator_reports.exists():
                            # 判斷是否為SMT作業員（根據作業員名稱或設備判斷）
                            is_smt_operator = any('SMT' in operator or 'SMT' in str(report.equipment) for report in operator_reports)
                            
                            # 設定工作時間參數
                            normal_hours_per_day = 8  # 一般工作時間：8小時
                            overtime_hours_per_day = 4 if is_smt_operator else 3  # SMT加班時間：4小時，一般：3小時
                            
                            # 計算工作天數（考慮一般工作時間和加班時間）
                            total_hours = stats['total_hours']
                            max_hours_per_day = normal_hours_per_day + overtime_hours_per_day  # 一天最多的工作時數
                            
                            if total_hours <= max_hours_per_day:
                                # 不超過一天的最大工作時數，算1天
                                work_days = 1
                            else:
                                # 超過一天的最大工作時數，計算需要多少天
                                work_days = int(total_hours // max_hours_per_day)
                                remaining_hours = total_hours % max_hours_per_day
                                
                                if remaining_hours > 0:
                                    # 還有剩餘時數，需要額外1天
                                    work_days += 1
                        else:
                            work_days = 1
                        
                        operator_details[operator] = {
                            'processes': list(stats['processes']),
                            'total_work_hours': stats['total_hours'],
                            'total_hours': stats['total_hours'],  # 模板期望的欄位名稱
                            'total_quantity': stats['total_quantity'],
                            'report_count': stats['report_count'],
                            'work_days': work_days,  # 根據實際工作日期計算
                            'overtime_hours': stats['overtime_hours']
                        }
                    
                    # 從報工記錄計算正確的日期範圍（使用實際工作時間，不是填報日期）
                    if production_reports.exists():
                        # 使用實際的工作時間來計算，不是填報日期
                        first_work_time = min(report.start_time for report in production_reports if report.start_time)
                        last_work_time = max(report.end_time for report in production_reports if report.end_time)
                        
                        if first_work_time and last_work_time:
                            first_record_date = first_work_time.date()
                            last_record_date = last_work_time.date()
                            total_execution_days = (last_record_date - first_record_date).days + 1
                        else:
                            # 如果沒有實際工作時間，使用填報日期
                            first_record_date = min(report.report_date for report in production_reports)
                            last_record_date = max(report.report_date for report in production_reports)
                            total_execution_days = (last_record_date - first_record_date).days + 1
                    else:
                        # 如果沒有報工記錄，使用已完工工單的時間
                        first_record_date = completed_workorder.started_at.date() if completed_workorder.started_at else completed_workorder.created_at.date()
                        last_record_date = completed_workorder.completed_at.date()
                        total_execution_days = (completed_workorder.completed_at.date() - (completed_workorder.started_at.date() if completed_workorder.started_at else completed_workorder.created_at.date())).days + 1
                    
                    # 建立分析記錄
                    analysis_data = {
                        'workorder_id': order_number,
                        'company_code': workorder_company_code,
                        'company_name': completed_workorder.company_name,
                        'product_code': product_code,
                        'product_name': product_code,  # 使用產品編號作為產品名稱
                        'order_quantity': order_quantity,
                        'first_record_date': first_record_date,
                        'last_record_date': last_record_date,
                        'total_execution_days': total_execution_days,
                        'total_work_hours': completed_workorder.total_work_hours or 0,
                        'total_overtime_hours': completed_workorder.total_overtime_hours or 0,
                        'average_daily_hours': (completed_workorder.total_work_hours or 0) / max(1, total_execution_days),
                        'efficiency_rate': min(999.99, ((completed_workorder.total_work_hours or 0) / max(1, total_execution_days) * 8) * 100),
                        'total_processes': total_processes,
                        'unique_processes': len(unique_processes),
                        'total_operators': len(total_operators),
                        'completion_date': completed_workorder.completed_at.date(),
                        'completion_status': 'completed',
                        'process_details': process_details,
                        'operator_details': operator_details
                    }
                    
                    # 儲存分析資料
                    analysis, created = CompletedWorkOrderAnalysis.objects.update_or_create(
                        workorder_id=order_number,
                        company_code=workorder_company_code,
                        defaults=analysis_data
                    )
                    
                    analysis_id = analysis.id
                    success_count += 1
                    logger.info(f"工單 {order_number} 分析成功")
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f'工單 {order_number}-{product_code}: {str(e)}'
                    errors.append(error_msg)
                    logger.error(f"工單 {order_number} 分析失敗: {str(e)}")
                    
                    # 記錄詳細錯誤資訊到資料庫
                    try:
                        from .models import AnalysisErrorLog
                        AnalysisErrorLog.objects.create(
                            workorder_id=order_number,
                            company_code=workorder_company_code,
                            product_code=product_code,
                            error_message=str(e),
                            error_type=type(e).__name__,
                            analysis_date=datetime.now()
                        )
                    except Exception as log_error:
                        logger.error(f"無法記錄錯誤日誌: {str(log_error)}")
            
            return {
                'success': True,
                'message': f'批量分析完成，成功: {success_count}，失敗: {error_count}',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors,
                'analysis_id': analysis_id,
                'created': created
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'批量分析時發生錯誤: {str(e)}'
            }