"""
工單分析服務
提供已完工工單的詳細分析功能，包括時間分析、工序分析、作業員分析等
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
        分析單一已完工工單
        
        Args:
            workorder_id: 工單編號
            company_code: 公司代號
            product_code: 產品編號（可選）
            force: 是否強制重新分析，即使已經分析過
            
        Returns:
            dict: 分析結果
        """
        from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess
        from .models import CompletedWorkOrderAnalysis
        
        try:
            # 檢查是否已經分析過
            if not force:
                existing_analysis = CompletedWorkOrderAnalysis.objects.filter(
                    workorder_id=workorder_id,
                    company_code=company_code
                ).first()
                
                if existing_analysis:
                    return {
                        'success': True,
                        'message': f'工單 {workorder_id} 已經分析過，跳過分析',
                        'analysis_id': existing_analysis.id,
                        'created': False,
                        'skipped': True
                    }
            
            # 取得已完工工單（使用公司名稱+工單號碼+產品編號作為唯一識別）
            filter_kwargs = {
                'order_number': workorder_id,
                'company_code': company_code
            }
            if product_code:
                filter_kwargs['product_code'] = product_code
                
            completed_workorder = CompletedWorkOrder.objects.filter(**filter_kwargs).first()
            
            if not completed_workorder:
                return {
                    'success': False,
                    'error': f'找不到工單 {workorder_id}'
                }
            
            # 從填報記錄取得詳細資料
            from workorder.fill_work.models import FillWork
            
            # 查詢填報記錄（填報記錄的 company_code 可能為 None，所以不加入公司代號條件）
            work_records = FillWork.objects.filter(
                workorder=workorder_id,
                product_id=completed_workorder.product_code
            ).order_by('work_date', 'start_time')
            
            if not work_records.exists():
                return {
                    'success': False,
                    'error': f'工單 {workorder_id} 沒有找到填報記錄'
                }
            
            # 計算時間分析
            first_record = work_records.first()
            last_record = work_records.last()
            first_date = first_record.work_date
            last_date = last_record.work_date
            
            # 計算真正的完工日期：出貨包裝工序的最後一個日期
            packaging_records = work_records.filter(operation='出貨包裝')
            if packaging_records.exists():
                completion_date = packaging_records.order_by('work_date', 'start_time').last().work_date
            else:
                # 如果沒有出貨包裝記錄，使用最後一筆記錄的日期
                completion_date = last_date
            
            total_execution_days = (last_date - first_date).days + 1
            
            # 計算總工作時數
            total_work_hours = sum(float(record.work_hours_calculated or 0) for record in work_records)
            total_overtime_hours = sum(float(record.overtime_hours_calculated or 0) for record in work_records)
            average_daily_hours = total_work_hours / total_execution_days if total_execution_days > 0 else 0
            
            # 計算效率比率（假設標準工時為8小時/天）
            standard_hours = total_execution_days * 8
            efficiency_rate = min(999.99, (total_work_hours / standard_hours * 100) if standard_hours > 0 else 0)
            
            # 工序分析
            process_records = {}
            process_order = []  # 記錄工序的出現順序
            
            for record in work_records:
                process_name = record.operation or '未知工序'
                if process_name not in process_records:
                    process_records[process_name] = {
                        'total_hours': 0,
                        'total_overtime_hours': 0,
                        'total_quantity': 0,
                        'records': [],
                        'operators': set(),
                        'first_appearance_order': len(process_order)  # 記錄第一次出現的順序
                    }
                    process_order.append(process_name)
                process_records[process_name]['total_hours'] += float(record.work_hours_calculated or 0)
                process_records[process_name]['total_overtime_hours'] += float(record.overtime_hours_calculated or 0)
                process_records[process_name]['total_quantity'] += float(record.work_quantity or 0)
                process_records[process_name]['records'].append({
                    'date': record.work_date.strftime('%Y-%m-%d'),
                    'operator': record.operator,
                    'hours': float(record.work_hours_calculated or 0),
                    'overtime': float(record.overtime_hours_calculated or 0),
                    'quantity': float(record.work_quantity or 0),
                    'work_date': record.work_date.strftime('%Y-%m-%d'),
                    'start_time': getattr(record, 'start_time', None).strftime('%H:%M') if getattr(record, 'start_time', None) else None
                })
                if record.operator:
                    process_records[process_name]['operators'].add(record.operator)
            
            # 對每個工序的記錄按時間排序，並記錄第一筆時間，計算每小時產能
            # 使用與已完工工單詳情頁面相同的排序邏輯：按 report_date 和 start_time 排序
            for process_name in process_records:
                # 按工作日期和開始時間排序（與已完工工單詳情頁面一致）
                def sort_key(record):
                    from datetime import datetime, time
                    work_date_str = record['work_date']
                    start_time_str = record.get('start_time')
                    
                    # 將字串轉換為日期物件
                    work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()
                    
                    if start_time_str:
                        # 如果有開始時間，使用日期+時間排序
                        start_time = datetime.strptime(start_time_str, '%H:%M').time()
                        return datetime.combine(work_date, start_time)
                    else:
                        # 如果沒有開始時間，只按日期排序
                        return datetime.combine(work_date, time.min)
                
                process_records[process_name]['records'].sort(key=sort_key)
                
                # 記錄第一筆記錄的時間，用於排序
                if process_records[process_name]['records']:
                    first_record = process_records[process_name]['records'][0]
                    process_records[process_name]['first_record_date'] = first_record['date']
                else:
                    process_records[process_name]['first_record_date'] = '9999-12-31'  # 沒有記錄的工序排在最後
                
                # 計算每小時產能
                total_all_hours = process_records[process_name]['total_hours'] + process_records[process_name]['total_overtime_hours']
                if total_all_hours > 0 and process_records[process_name]['total_quantity'] > 0:
                    process_records[process_name]['hourly_capacity'] = process_records[process_name]['total_quantity'] / total_all_hours
                else:
                    process_records[process_name]['hourly_capacity'] = 0
            
            # 作業員分析
            operator_records = {}
            for record in work_records:
                operator_name = record.operator or '未知作業員'
                if operator_name not in operator_records:
                    operator_records[operator_name] = {
                        'total_hours': 0,
                        'overtime_hours': 0,
                        'processes': set(),
                        'work_days': set()
                    }
                operator_records[operator_name]['total_hours'] += float(record.work_hours_calculated or 0)
                operator_records[operator_name]['overtime_hours'] += float(record.overtime_hours_calculated or 0)
                if record.operation:
                    operator_records[operator_name]['processes'].add(record.operation)
                operator_records[operator_name]['work_days'].add(record.work_date)
            
            # 準備分析資料
            analysis_data = {
                'workorder_id': workorder_id,
                'company_code': company_code,
                'company_name': completed_workorder.company_name,
                'product_code': completed_workorder.product_code,
                'product_name': completed_workorder.product_code,  # CompletedWorkOrder 沒有 product_name 欄位
                'order_quantity': completed_workorder.completed_quantity,
                'first_record_date': first_date.strftime('%Y-%m-%d'),
                'last_record_date': last_date.strftime('%Y-%m-%d'),
                'total_execution_days': total_execution_days,
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'average_daily_hours': average_daily_hours,
                'efficiency_rate': efficiency_rate,
                'total_processes': len(process_records),
                'unique_processes': len(set(record.operation for record in work_records if record.operation)),
                'total_operators': len(operator_records),
                'process_details': {
                    name: {
                        'total_hours': data['total_hours'],
                        'total_overtime_hours': data['total_overtime_hours'],
                        'total_quantity': data['total_quantity'],
                        'hourly_capacity': data['hourly_capacity'],
                        'records': data['records'][:5],  # 只保留前5筆記錄
                        'operators': list(data['operators']),
                        'first_record_date': data.get('first_record_date', '9999-12-31'),
                        'first_appearance_order': data.get('first_appearance_order', 999)  # 記錄工序第一次出現的順序
                    }
                    for name, data in process_records.items()
                },
                'operator_details': {
                    name: {
                        'total_hours': data['total_hours'],
                        'overtime_hours': data['overtime_hours'],
                        'processes': list(data['processes']),
                        'work_days': len(data['work_days'])
                    }
                    for name, data in operator_records.items()
                },
                'completion_date': completion_date.strftime('%Y-%m-%d'),
                'completion_status': 'completed'
            }
            
            # 儲存或更新分析資料
            analysis, created = CompletedWorkOrderAnalysis.objects.update_or_create(
                workorder_id=workorder_id,
                company_code=company_code,
                product_code=completed_workorder.product_code,
                defaults=analysis_data
            )
            
            return {
                'success': True,
                'message': f'工單 {workorder_id} 分析完成',
                'analysis_id': analysis.id,
                'created': created
            }
            
        except CompletedWorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': f'找不到工單 {workorder_id}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'分析工單時發生錯誤: {str(e)}'
            }
    
    @staticmethod
    def analyze_completed_workorders_batch(start_date=None, end_date=None, company_code=None):
        """
        批量分析已完工工單
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD 格式)
            end_date: 結束日期 (YYYY-MM-DD 格式)
            company_code: 公司代號
            
        Returns:
            dict: 批量分析結果
        """
        from workorder.models import CompletedWorkOrder
        
        try:
            logger.info(f"開始批量分析 - 公司代號: {company_code}, 開始日期: {start_date}, 結束日期: {end_date}")
            
            # 查詢已完工工單，排除 RD樣品
            queryset = CompletedWorkOrder.objects.exclude(order_number__icontains='RD樣品')
            logger.info(f"初始查詢結果數量（排除RD樣品）: {queryset.count()}")
            
            if company_code:
                queryset = queryset.filter(company_code=company_code)
                logger.info(f"按公司代號過濾後數量: {queryset.count()}")
            
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
            
            logger.info(f"開始分析 {len(completed_workorders)} 筆工單")
            
            for completed_workorder in completed_workorders:
                order_number = completed_workorder.order_number
                company_code = completed_workorder.company_code
                product_code = completed_workorder.product_code
                logger.info(f"分析工單: {order_number} ({company_code}) - {product_code}")
                result = WorkOrderAnalysisService.analyze_completed_workorder(order_number, company_code, product_code, force=True)
                if result['success']:
                    success_count += 1
                    logger.info(f"工單 {order_number} 分析成功")
                else:
                    error_count += 1
                    error_msg = f'工單 {order_number}-{product_code}: {result["error"]}'
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                'success': True,
                'message': f'批量分析完成，成功: {success_count}，失敗: {error_count}',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'批量分析時發生錯誤: {str(e)}'
            }
