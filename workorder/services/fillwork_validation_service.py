"""
填報紀錄與工單相符性檢查服務
負責檢查填報紀錄與工單資料的一致性，分成三種獨立檢查類型
"""

from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FillWorkValidationService:
    """
    填報紀錄與工單相符性檢查服務
    提供三種獨立檢查功能：
    1. 檢查產品編號不匹配（公司代號+工單號碼匹配）
    2. 檢查工單號碼不匹配（公司代號+產品編號匹配）
    3. 檢查公司代號不匹配（工單號碼+產品編號匹配）
    """
    
    @staticmethod
    def check_fillwork_workorder_consistency():
        """
        檢查填報紀錄與工單的相符性
        排除RD樣品，只檢查正式工單
        返回檢查結果統計
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        from erp_integration.models import CompanyConfig
        
        # 統計結果
        results = {
            'total_fillwork': 0,
            'rd_samples_excluded': 0,
            'matched_workorders': 0,
            'missing_workorders': 0,
            'product_mismatch': 0,  # 產品編號不匹配
            'workorder_mismatch': 0,  # 工單號碼不匹配
            'company_mismatch': 0,  # 公司代號不匹配
            'errors': [],
            'missing_details': [],
            'product_mismatch_details': [],
            'workorder_mismatch_details': [],
            'company_mismatch_details': []
        }
        
        try:
            # 取得所有填報紀錄，排除RD樣品
            fillwork_records = FillWork.objects.exclude(
                Q(workorder='RD樣品') | 
                Q(workorder__icontains='RD') |
                Q(product_id='PFP-CCT')
            )
            
            results['total_fillwork'] = fillwork_records.count()
            
            # 計算排除的RD樣品數量
            rd_samples = FillWork.objects.filter(
                Q(workorder='RD樣品') | 
                Q(workorder__icontains='RD') |
                Q(product_id='PFP-CCT')
            ).count()
            results['rd_samples_excluded'] = rd_samples
            
            for fillwork in fillwork_records:
                try:
                    # 檢查必要欄位
                    if not fillwork.workorder or not fillwork.product_id or not fillwork.company_name:
                        results['errors'].append({
                            'fillwork_id': fillwork.id,
                            'operator': fillwork.operator,
                            'workorder': fillwork.workorder,
                            'product_id': fillwork.product_id,
                            'company_name': fillwork.company_name,
                            'issue': '缺少必要欄位'
                        })
                        continue
                    
                    # 取得公司配置
                    company_config = CompanyConfig.objects.filter(
                        company_name__icontains=fillwork.company_name
                    ).first()
                    
                    if not company_config:
                        results['errors'].append({
                            'fillwork_id': fillwork.id,
                            'operator': fillwork.operator,
                            'workorder': fillwork.workorder,
                            'product_id': fillwork.product_id,
                            'company_name': fillwork.company_name,
                            'issue': '找不到對應的公司配置'
                        })
                        continue
                    
                    # 檢查工單是否存在
                    # 根據多公司架構，需要同時檢查公司代號、工單號碼和產品編號
                    workorder = WorkOrder.objects.filter(
                        order_number=fillwork.workorder,
                        product_code=fillwork.product_id
                    ).first()
                    
                    # 如果找到工單，進一步檢查公司代號是否匹配
                    if workorder and workorder.company_code:
                        if workorder.company_code != company_config.company_code:
                            # 公司代號不匹配，視為找不到工單
                            workorder = None
                    
                    if not workorder:
                        # 工單號碼不存在
                        results['missing_workorders'] += 1
                        results['missing_details'].append({
                            'fillwork_id': fillwork.id,
                            'operator': fillwork.operator,
                            'workorder': fillwork.workorder,
                            'product_id': fillwork.product_id,
                            'company_name': fillwork.company_name,
                            'issue': '工單號碼不存在'
                        })
                        continue
                    
                    # 檢查三種不匹配情況
                    mismatches = FillWorkValidationService._check_mismatches(
                        fillwork, workorder, company_config
                    )
                    
                    if not mismatches:
                        # 完全匹配
                        results['matched_workorders'] += 1
                    else:
                        # 記錄各種不匹配
                        for mismatch_type, details in mismatches.items():
                            if mismatch_type == 'product_mismatch':
                                results['product_mismatch'] += 1
                                results['product_mismatch_details'].append({
                                    'fillwork_id': fillwork.id,
                                    'operator': fillwork.operator,
                                    'workorder': fillwork.workorder,
                                    'company_code': company_config.company_code,
                                    'old_product': fillwork.product_id,
                                    'new_product': workorder.product_code,
                                    'work_date': fillwork.work_date,
                                    'issue': '產品編號不匹配'
                                })
                            elif mismatch_type == 'workorder_mismatch':
                                results['workorder_mismatch'] += 1
                                results['workorder_mismatch_details'].append({
                                    'fillwork_id': fillwork.id,
                                    'operator': fillwork.operator,
                                    'product_id': fillwork.product_id,
                                    'company_code': company_config.company_code,
                                    'old_workorder': fillwork.workorder,
                                    'new_workorder': details['correct_workorder'],
                                    'work_date': fillwork.work_date,
                                    'issue': '工單號碼不匹配'
                                })
                            elif mismatch_type == 'company_mismatch':
                                results['company_mismatch'] += 1
                                results['company_mismatch_details'].append({
                                    'fillwork_id': fillwork.id,
                                    'operator': fillwork.operator,
                                    'workorder': fillwork.workorder,
                                    'product_id': fillwork.product_id,
                                    'old_company_code': company_config.company_code,
                                    'new_company_code': workorder.company_code,
                                    'work_date': fillwork.work_date,
                                    'issue': '公司代號不匹配'
                                })
                except Exception as e:
                    logger.error(f"檢查填報紀錄時發生錯誤: {e}")
                    results['errors'].append({
                        'fillwork_id': fillwork.id if hasattr(fillwork, 'id') else 'Unknown',
                        'error': str(e)
                    })
        
        except Exception as e:
            logger.error(f"檢查填報紀錄相符性時發生錯誤: {e}")
            results['errors'].append({
                'fillwork_id': 'System',
                'error': str(e)
            })
        
        return results
    
    @staticmethod
    def _check_mismatches(fillwork, workorder, company_config):
        """
        檢查填報紀錄與工單之間的不匹配情況
        返回不匹配類型的字典
        """
        mismatches = {}
        
        # 檢查產品編號不匹配（公司代號+工單號碼匹配）
        if (workorder.company_code == company_config.company_code and
            workorder.product_code != fillwork.product_id):
            mismatches['product_mismatch'] = True
        
        # 檢查工單號碼不匹配（公司代號+產品編號匹配）
        if workorder.company_code == company_config.company_code:
            # 查找相同公司代號和產品編號的工單
            from workorder.models import WorkOrder
            correct_workorder = WorkOrder.objects.filter(
                company_code=company_config.company_code,
                product_code=fillwork.product_id
            ).first()
            
            if correct_workorder and correct_workorder.order_number != fillwork.workorder:
                mismatches['workorder_mismatch'] = {
                    'correct_workorder': correct_workorder.order_number
                }
        
        # 檢查公司代號不匹配（工單號碼+產品編號匹配）
        if (workorder.order_number == fillwork.workorder and
            workorder.product_code == fillwork.product_id and
            workorder.company_code != company_config.company_code):
            mismatches['company_mismatch'] = True
        
        return mismatches
    
    @staticmethod
    def get_rd_sample_statistics():
        """
        取得RD樣品的統計資訊
        """
        from workorder.fill_work.models import FillWork
        
        rd_samples = FillWork.objects.filter(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        return {
            'total_rd_samples': rd_samples.count(),
            'by_operator': rd_samples.values('operator').annotate(
                count=models.Count('id')
            ).order_by('-count'),
            'by_date': rd_samples.values('work_date').annotate(
                count=models.Count('id')
            ).order_by('-work_date'),
            'by_process': rd_samples.values('process__name').annotate(
                count=models.Count('id')
            ).order_by('-count'),
        }
    
    @staticmethod
    def get_missing_workorders_report():
        """
        取得缺失工單的詳細報告
        只報告工單號碼完全不存在的記錄
        """
        from workorder.fill_work.models import FillWork
        from workorder.models import WorkOrder
        
        # 取得所有非RD樣品的填報紀錄
        fillwork_records = FillWork.objects.exclude(
            Q(workorder='RD樣品') | 
            Q(workorder__icontains='RD') |
            Q(product_id='PFP-CCT')
        )
        
        missing_workorders = []
        
        for fillwork in fillwork_records:
            # 檢查工單號碼是否存在（使用多公司架構唯一識別）
            workorder = WorkOrder.objects.filter(
                order_number=fillwork.workorder,
                product_code=fillwork.product_id
            ).first()
            
            # 只有工單號碼完全不存在才算是缺失工單
            if not workorder:
                missing_workorders.append({
                    'fillwork_id': fillwork.id,
                    'operator': fillwork.operator,
                    'workorder': fillwork.workorder,
                    'product_id': fillwork.product_id,
                    'company_name': fillwork.company_name,
                    'work_date': fillwork.work_date,
                    'process': fillwork.process.name if fillwork.process else '',
                    'work_quantity': fillwork.work_quantity,
                    'created_at': fillwork.created_at
                })
        
        return missing_workorders
    
    @staticmethod
    def get_product_mismatch_report():
        """
        取得產品編號不匹配的詳細報告
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
        
        product_mismatches = []
        
        for fillwork in fillwork_records:
            # 取得公司配置
            company_config = CompanyConfig.objects.filter(
                company_name__icontains=fillwork.company_name
            ).first()
            
            if not company_config:
                continue
            
            # 查找工單
            workorder = WorkOrder.objects.filter(
                order_number=fillwork.workorder
            ).first()
            
            if (workorder and 
                workorder.company_code == company_config.company_code and
                workorder.product_code != fillwork.product_id):
                
                product_mismatches.append({
                    'fillwork_id': fillwork.id,
                    'operator': fillwork.operator,
                    'workorder': fillwork.workorder,
                    'company_code': company_config.company_code,
                    'old_product': fillwork.product_id,
                    'new_product': workorder.product_code,
                    'work_date': fillwork.work_date,
                    'issue': '產品編號不匹配'
                })
        
        return product_mismatches
    
    @staticmethod
    def get_workorder_mismatch_report():
        """
        取得工單號碼不匹配的詳細報告
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
        
        workorder_mismatches = []
        
        for fillwork in fillwork_records:
            # 取得公司配置
            company_config = CompanyConfig.objects.filter(
                company_name__icontains=fillwork.company_name
            ).first()
            
            if not company_config:
                continue
            
            # 查找相同公司代號和產品編號的工單
            workorder = WorkOrder.objects.filter(
                company_code=company_config.company_code,
                product_code=fillwork.product_id
            ).first()
            
            if workorder and workorder.order_number != fillwork.workorder:
                workorder_mismatches.append({
                    'fillwork_id': fillwork.id,
                    'operator': fillwork.operator,
                    'product_id': fillwork.product_id,
                    'company_code': company_config.company_code,
                    'old_workorder': fillwork.workorder,
                    'new_workorder': workorder.order_number,
                    'work_date': fillwork.work_date,
                    'issue': '工單號碼不匹配'
                })
        
        return workorder_mismatches
    
    @staticmethod
    def get_company_mismatch_report():
        """
        取得公司代號不匹配的詳細報告
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
        
        company_mismatches = []
        
        for fillwork in fillwork_records:
            # 查找工單
            workorder = WorkOrder.objects.filter(
                order_number=fillwork.workorder,
                product_code=fillwork.product_id
            ).first()
            
            if not workorder:
                continue
            
            # 取得公司配置
            company_config = CompanyConfig.objects.filter(
                company_name__icontains=fillwork.company_name
            ).first()
            
            if (company_config and 
                workorder.company_code != company_config.company_code):
                
                # 查找正確的公司名稱
                correct_company = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                company_mismatches.append({
                    'fillwork_id': fillwork.id,
                    'operator': fillwork.operator,
                    'workorder': fillwork.workorder,
                    'product_id': fillwork.product_id,
                    'old_company_name': fillwork.company_name,
                    'new_company_name': correct_company.company_name if correct_company else 'Unknown',
                    'old_company_code': company_config.company_code,
                    'new_company_code': workorder.company_code,
                    'work_date': fillwork.work_date,
                    'issue': '公司代號不匹配'
                })
        
        return company_mismatches 