"""
公司生產製造命令管理子模組 - 服務層
負責公司生產製造命令的同步、轉換和業務邏輯
"""

import logging
from datetime import datetime
from django.utils import timezone
from .models import CompanyOrder

logger = logging.getLogger(__name__)



class CompanyOrderConvertService:
    """公司生產製造命令轉換服務"""
    
    @classmethod
    def convert_to_workorder(cls, company_order_ids=None):
        """
        將生產製造命令轉換成MES工單（完整版本，包含自動分配作業員和設備）
        """
        try:
            from process.models import ProductProcessRoute, ProductProcessStandardCapacity, Operator, OperatorSkill, ProcessEquipment
            from equip.models import Equipment
            from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderAssignment
            
            if company_order_ids:
                orders = CompanyOrder.objects.filter(
                    id__in=company_order_ids,
                    is_converted=False
                )
            else:
                orders = CompanyOrder.objects.filter(is_converted=False)
            
            converted_count = 0
            processes_created = 0
            auto_assigned = 0
            
            for company_order in orders:
                # 檢查工單是否已存在
                existing_workorder = WorkOrder.objects.filter(
                    company_code=company_order.company_code,
                    order_number=company_order.mkordno
                ).first()
                
                if existing_workorder:
                    # 如果工單已存在，跳過並標記為已轉換
                    company_order.is_converted = True
                    company_order.save()
                    continue
                
                # 建立工單
                workorder = WorkOrder.objects.create(
                    order_number=company_order.mkordno,
                    product_code=company_order.product_id,
                    quantity=company_order.prodt_qty,
                    status="pending",
                    company_code=company_order.company_code,
                )
                converted_count += 1

                # 建立工序明細
                try:
                    routes = ProductProcessRoute.objects.filter(
                        product_id=workorder.product_code
                    ).order_by("step_order")

                    if routes.exists():
                        for route in routes:
                            capacity_data = ProductProcessStandardCapacity.objects.filter(
                                product_code=workorder.product_code,
                                process_name=route.process_name.name,
                                is_active=True
                            ).order_by('-version').first()
                            
                            target_hourly_output = (
                                capacity_data.standard_capacity_per_hour 
                                if capacity_data else 1000
                            )
                            
                            process = WorkOrderProcess.objects.create(
                                workorder=workorder,
                                process_name=route.process_name.name,
                                sequence=route.step_order,
                                estimated_hours=8,
                                target_hourly_output=target_hourly_output,
                                status="pending"
                            )
                            processes_created += 1
                            
                            # 自動分配作業員和設備
                            if cls._auto_assign_operator_and_equipment(process):
                                auto_assigned += 1
                    else:
                        # 如果沒有工藝路線，建立預設工序
                        WorkOrderProcess.objects.create(
                            workorder=workorder,
                            process_name="預設工序",
                            sequence=1,
                            estimated_hours=8,
                            status="pending"
                        )
                        processes_created += 1
                        
                except Exception as e:
                    logger.error(f"建立工序明細失敗：{str(e)}")

                # 標記為已轉換
                company_order.is_converted = True
                company_order.save()
            
            logger.info(f"轉換完成：成功轉換 {converted_count} 筆生產製造命令，建立 {processes_created} 個工序，自動分配 {auto_assigned} 筆")
            return {
                'success': True,
                'converted': converted_count,
                'processes_created': processes_created,
                'auto_assigned': auto_assigned
            }
            
        except Exception as e:
            logger.error(f"轉換生產製造命令失敗：{str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _auto_assign_operator_and_equipment(cls, process):
        """自動分配作業員和設備"""
        try:
            from process.models import Operator, OperatorSkill, ProcessEquipment
            from equip.models import Equipment
            from workorder.models import WorkOrderAssignment
            
            # 查找有該工序技能的作業員
            skilled_operators = Operator.objects.filter(
                operatorskill__process_name=process.process_name,
                operatorskill__skill_level__gte=3,  # 技能等級3以上
                is_active=True
            ).distinct()
            
            if skilled_operators.exists():
                # 選擇第一個有技能的作業員
                operator = skilled_operators.first()
                
                # 查找適合的設備
                suitable_equipment = Equipment.objects.filter(
                    processequipment__process_name=process.process_name,
                    status='available'
                ).first()
                
                if suitable_equipment:
                    # 建立分配記錄
                    WorkOrderAssignment.objects.create(
                        workorder_process=process,
                        operator=operator,
                        equipment=suitable_equipment,
                        assigned_by='system',
                        assignment_type='auto'
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"自動分配作業員和設備失敗：{str(e)}")
            return False
    
    @classmethod
    def _create_workorder_from_order(cls, company_order):
        """從生產製造命令創建工單"""
        try:
            from workorder.models import WorkOrder, WorkOrderProcess
            
            # 創建工單
            workorder = WorkOrder.objects.create(
                workorder_no=company_order.mkordno,
                product_id=company_order.product_id,
                planned_quantity=company_order.prodt_qty,
                company_code=company_order.company_code,
                company_name=company_order.company_code,  # 可以從 CompanyConfig 取得完整名稱
                start_date=cls._parse_date(company_order.est_take_mat_date),
                due_date=cls._parse_date(company_order.est_stock_out_date),
                status='pending',
                order_source='erp_company_order'
            )
            
            # 創建預設工序
            WorkOrderProcess.objects.create(
                workorder=workorder,
                process_name='預設工序',
                sequence=1,
                estimated_hours=8,
                status='pending'
            )
            
            # 標記為已轉換
            company_order.is_converted = True
            company_order.save()
            
            return True
            
        except Exception as e:
            logger.error(f"創建工單失敗：{str(e)}")
            return False
    
    @classmethod
    def _parse_date(cls, date_str):
        """解析日期字串"""
        if not date_str:
            return timezone.now().date()
        
        try:
            # 嘗試解析不同格式的日期
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return timezone.now().date()
        except:
            return timezone.now().date()


class CompanyOrderQueryService:
    """公司生產製造命令查詢服務"""
    
    @classmethod
    def get_company_statistics(cls):
        """取得各公司生產製造命令統計"""
        from django.db.models import Count, Q
        
        stats = CompanyOrder.objects.values('company_code').annotate(
            total_orders=Count('id'),
            converted_orders=Count('id', filter=Q(is_converted=True)),
            pending_orders=Count('id', filter=Q(is_converted=False))
        ).order_by('company_code')
        
        return stats
    
    @classmethod
    def get_order_by_product(cls, product_id, company_code=None):
        """根據產品編號取得生產製造命令資訊"""
        queryset = CompanyOrder.objects.filter(product_id=product_id)
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        return queryset.order_by('-est_stock_out_date')
    
    @classmethod
    def search_orders(cls, company_code=None, mkordno=None, product_id=None):
        """搜尋生產製造命令"""
        queryset = CompanyOrder.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        if mkordno:
            queryset = queryset.filter(mkordno__icontains=mkordno)
        
        if product_id:
            queryset = queryset.filter(product_id__icontains=product_id)
        
        return queryset.order_by('-est_stock_out_date')
