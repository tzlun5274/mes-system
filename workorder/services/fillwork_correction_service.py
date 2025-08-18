"""
填報紀錄修正服務
負責修正填報紀錄中的不一致資料，分成三種獨立修正類型
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class FillWorkCorrectionService:
    """
    填報紀錄修正服務
    提供三種獨立修正功能：
    1. 公司代號+工單號碼一樣，修復產品編號
    2. 公司代號+產品編號一樣，修復工單號碼
    3. 工單號碼+產品編號一樣，修復公司代號
    """
    
    @staticmethod
    def get_correction_analysis():
        """
        取得三種修正類型的分析報告
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        from erp_integration.models import CompanyConfig
        
        # 取得所有非RD樣品的填報紀錄
        fillwork_records = FillWork.objects.exclude(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        analysis = {
            'type1_product': {'count': 0, 'items': []},  # 修復產品編號
            'type2_workorder': {'count': 0, 'items': []},  # 修復工單號碼
            'type3_company': {'count': 0, 'items': []},  # 修復公司代號
            'total_records': fillwork_records.count()
        }
        
        for fillwork in fillwork_records:
            try:
                # 類型1: 公司代號+工單號碼一樣，修復產品編號
                # 先根據工單號碼查找工單
                workorder_by_number = WorkOrder.objects.filter(
                    order_number=fillwork.workorder
                ).first()
                
                if workorder_by_number:
                    # 取得公司配置
                    company_config = CompanyConfig.objects.filter(
                        company_code=workorder_by_number.company_code
                    ).first()
                    
                    if company_config and workorder_by_number.product_code != fillwork.product_id:
                        analysis['type1_product']['count'] += 1
                        analysis['type1_product']['items'].append({
                            'fillwork_id': fillwork.id,
                            'workorder': fillwork.workorder,
                            'operator': fillwork.operator,
                            'work_date': fillwork.work_date,
                            'company_code': workorder_by_number.company_code,
                            'old_product': fillwork.product_id,
                            'new_product': workorder_by_number.product_code
                        })
                
                # 類型2: 公司代號+產品編號一樣，修復工單號碼
                # 先根據公司名稱查找公司配置
                company_config = CompanyConfig.objects.filter(
                    company_name__icontains=fillwork.company_name
                ).first()
                
                if company_config:
                    workorder_by_product = WorkOrder.objects.filter(
                        company_code=company_config.company_code,
                        product_code=fillwork.product_id
                    ).first()
                    
                    if (workorder_by_product and 
                        workorder_by_product.order_number != fillwork.workorder):
                        
                        analysis['type2_workorder']['count'] += 1
                        analysis['type2_workorder']['items'].append({
                            'fillwork_id': fillwork.id,
                            'operator': fillwork.operator,
                            'work_date': fillwork.work_date,
                            'company_code': company_config.company_code,
                            'product_code': fillwork.product_id,
                            'old_workorder': fillwork.workorder,
                            'new_workorder': workorder_by_product.order_number
                        })
                
                # 類型3: 工單號碼+產品編號一樣，修復公司代號
                workorder_by_both = WorkOrder.objects.filter(
                    order_number=fillwork.workorder,
                    product_code=fillwork.product_id
                ).first()
                
                if workorder_by_both:
                    # 取得公司配置
                    company_config = CompanyConfig.objects.filter(
                        company_name__icontains=fillwork.company_name
                    ).first()
                    
                    if (company_config and 
                        workorder_by_both.company_code != company_config.company_code):
                        
                        analysis['type3_company']['count'] += 1
                        analysis['type3_company']['items'].append({
                            'fillwork_id': fillwork.id,
                            'workorder': fillwork.workorder,
                            'operator': fillwork.operator,
                            'work_date': fillwork.work_date,
                            'product_code': fillwork.product_id,
                            'old_company_code': company_config.company_code,
                            'new_company_code': workorder_by_both.company_code
                        })
                    
            except Exception as e:
                logger.error(f"分析填報紀錄 {fillwork.id} 時發生錯誤: {e}")
        
        return analysis
    
    @staticmethod
    def correct_product_codes(dry_run=True):
        """
        類型1: 公司代號+工單號碼一樣，修復產品編號
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        from erp_integration.models import CompanyConfig
        
        fillwork_records = FillWork.objects.exclude(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        results = {
            'total_checked': 0,
            'total_corrected': 0,
            'total_skipped': 0,
            'corrections': [],
            'errors': [],
            'dry_run': dry_run,
            'correction_type': 'product_codes'
        }
        
        try:
            with transaction.atomic():
                for fillwork in fillwork_records:
                    results['total_checked'] += 1
                    
                    try:
                        # 先根據工單號碼查找工單
                        workorder = WorkOrder.objects.filter(
                            order_number=fillwork.workorder
                        ).first()
                        
                        if not workorder:
                            results['total_skipped'] += 1
                            continue
                        
                        # 檢查產品編號是否不匹配
                        if workorder.product_code != fillwork.product_id:
                            correction_info = {
                                'fillwork_id': fillwork.id,
                                'workorder': fillwork.workorder,
                                'operator': fillwork.operator,
                                'work_date': fillwork.work_date,
                                'company_code': workorder.company_code,
                                'old_product': fillwork.product_id,
                                'new_product': workorder.product_code,
                                'reason': '根據工單號碼找到對應工單，修正產品編號'
                            }
                            
                            if not dry_run:
                                fillwork.product_id = workorder.product_code
                                fillwork.save(update_fields=['product_id'])
                                
                                if hasattr(fillwork, 'updated_at'):
                                    fillwork.updated_at = timezone.now()
                                    fillwork.save(update_fields=['updated_at'])
                            
                            results['total_corrected'] += 1
                            results['corrections'].append(correction_info)
                        else:
                            results['total_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"修正產品編號時發生錯誤: {e}")
                        results['total_skipped'] += 1
                        results['errors'].append({
                            'fillwork_id': fillwork.id,
                            'error': str(e)
                        })
                
                if dry_run:
                    raise Exception("試運行模式，回滾所有變更")
                    
        except Exception as e:
            if dry_run and "試運行模式" in str(e):
                pass
            else:
                logger.error(f"修正產品編號時發生錯誤: {e}")
                results['errors'].append({
                    'fillwork_id': 'System',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def correct_workorder_numbers(dry_run=True):
        """
        類型2: 公司代號+產品編號一樣，修復工單號碼
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        from erp_integration.models import CompanyConfig
        
        fillwork_records = FillWork.objects.exclude(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        results = {
            'total_checked': 0,
            'total_corrected': 0,
            'total_skipped': 0,
            'corrections': [],
            'errors': [],
            'dry_run': dry_run,
            'correction_type': 'workorder_numbers'
        }
        
        try:
            with transaction.atomic():
                for fillwork in fillwork_records:
                    results['total_checked'] += 1
                    
                    try:
                        # 取得公司配置
                        company_config = CompanyConfig.objects.filter(
                            company_name__icontains=fillwork.company_name
                        ).first()
                        
                        if not company_config:
                            results['total_skipped'] += 1
                            continue
                        
                        # 查找相同公司代號和產品編號的工單
                        workorder = WorkOrder.objects.filter(
                            company_code=company_config.company_code,
                            product_code=fillwork.product_id
                        ).first()
                        
                        if not workorder:
                            results['total_skipped'] += 1
                            continue
                        
                        # 檢查工單號碼是否不匹配
                        if workorder.order_number != fillwork.workorder:
                            correction_info = {
                                'fillwork_id': fillwork.id,
                                'operator': fillwork.operator,
                                'work_date': fillwork.work_date,
                                'company_code': company_config.company_code,
                                'product_code': fillwork.product_id,
                                'old_workorder': fillwork.workorder,
                                'new_workorder': workorder.order_number,
                                'reason': '公司代號和產品編號匹配，修正工單號碼'
                            }
                            
                            if not dry_run:
                                fillwork.workorder = workorder.order_number
                                fillwork.save(update_fields=['workorder'])
                                
                                if hasattr(fillwork, 'updated_at'):
                                    fillwork.updated_at = timezone.now()
                                    fillwork.save(update_fields=['updated_at'])
                            
                            results['total_corrected'] += 1
                            results['corrections'].append(correction_info)
                        else:
                            results['total_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"修正工單號碼時發生錯誤: {e}")
                        results['total_skipped'] += 1
                        results['errors'].append({
                            'fillwork_id': fillwork.id,
                            'error': str(e)
                        })
                
                if dry_run:
                    raise Exception("試運行模式，回滾所有變更")
                    
        except Exception as e:
            if dry_run and "試運行模式" in str(e):
                pass
            else:
                logger.error(f"修正工單號碼時發生錯誤: {e}")
                results['errors'].append({
                    'fillwork_id': 'System',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def correct_company_codes(dry_run=True):
        """
        類型3: 工單號碼+產品編號一樣，修復公司代號
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        from erp_integration.models import CompanyConfig
        
        fillwork_records = FillWork.objects.exclude(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        results = {
            'total_checked': 0,
            'total_corrected': 0,
            'total_skipped': 0,
            'corrections': [],
            'errors': [],
            'dry_run': dry_run,
            'correction_type': 'company_codes'
        }
        
        try:
            with transaction.atomic():
                for fillwork in fillwork_records:
                    results['total_checked'] += 1
                    
                    try:
                        # 查找工單
                        workorder = WorkOrder.objects.filter(
                            order_number=fillwork.workorder,
                            product_code=fillwork.product_id
                        ).first()
                        
                        if not workorder:
                            results['total_skipped'] += 1
                            continue
                        
                        # 取得公司配置
                        company_config = CompanyConfig.objects.filter(
                            company_name__icontains=fillwork.company_name
                        ).first()
                        
                        if not company_config:
                            results['total_skipped'] += 1
                            continue
                        
                        # 檢查公司代號是否不匹配
                        if workorder.company_code != company_config.company_code:
                            # 查找正確的公司名稱
                            correct_company = CompanyConfig.objects.filter(
                                company_code=workorder.company_code
                            ).first()
                            
                            if correct_company:
                                correction_info = {
                                    'fillwork_id': fillwork.id,
                                    'workorder': fillwork.workorder,
                                    'operator': fillwork.operator,
                                    'work_date': fillwork.work_date,
                                    'product_code': fillwork.product_id,
                                    'old_company_name': fillwork.company_name,
                                    'new_company_name': correct_company.company_name,
                                    'old_company_code': company_config.company_code,
                                    'new_company_code': workorder.company_code,
                                    'reason': '工單號碼和產品編號匹配，修正公司名稱'
                                }
                                
                                if not dry_run:
                                    fillwork.company_name = correct_company.company_name
                                    fillwork.save(update_fields=['company_name'])
                                    
                                    if hasattr(fillwork, 'updated_at'):
                                        fillwork.updated_at = timezone.now()
                                        fillwork.save(update_fields=['updated_at'])
                                
                                results['total_corrected'] += 1
                                results['corrections'].append(correction_info)
                            else:
                                results['total_skipped'] += 1
                        else:
                            results['total_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"修正公司代號時發生錯誤: {e}")
                        results['total_skipped'] += 1
                        results['errors'].append({
                            'fillwork_id': fillwork.id,
                            'error': str(e)
                        })
                
                if dry_run:
                    raise Exception("試運行模式，回滾所有變更")
                    
        except Exception as e:
            if dry_run and "試運行模式" in str(e):
                pass
            else:
                logger.error(f"修正公司代號時發生錯誤: {e}")
                results['errors'].append({
                    'fillwork_id': 'System',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def get_correction_preview(correction_type):
        """
        取得指定類型修正的預覽
        """
        if correction_type == 'product_codes':
            return FillWorkCorrectionService.correct_product_codes(dry_run=True)
        elif correction_type == 'workorder_numbers':
            return FillWorkCorrectionService.correct_workorder_numbers(dry_run=True)
        elif correction_type == 'company_codes':
            return FillWorkCorrectionService.correct_company_codes(dry_run=True)
        else:
            raise ValueError(f"無效的修正類型: {correction_type}")
    
    @staticmethod
    def execute_correction(correction_type):
        """
        執行指定類型的修正
        """
        if correction_type == 'product_codes':
            return FillWorkCorrectionService.correct_product_codes(dry_run=False)
        elif correction_type == 'workorder_numbers':
            return FillWorkCorrectionService.correct_workorder_numbers(dry_run=False)
        elif correction_type == 'company_codes':
            return FillWorkCorrectionService.correct_company_codes(dry_run=False)
        else:
            raise ValueError(f"無效的修正類型: {correction_type}") 