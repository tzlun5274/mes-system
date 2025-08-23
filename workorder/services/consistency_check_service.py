"""
填報紀錄相符性檢查服務
負責執行各種相符性檢查並記錄結果，排除RD樣品工單
"""

import logging
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder, ConsistencyCheckResult
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.fill_work.models import FillWork
from erp_integration.models import CompanyConfig

logger = logging.getLogger('workorder')

class ConsistencyCheckService:
    """
    相符性檢查服務類別
    提供各種相符性檢查功能，排除RD樣品工單
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def clear_old_results(self, check_type=None):
        """
        清除舊的檢查結果
        
        Args:
            check_type: 指定檢查類型，如果為None則清除所有類型
        """
        try:
            if check_type:
                ConsistencyCheckResult.objects.filter(check_type=check_type).delete()
            else:
                ConsistencyCheckResult.objects.all().delete()
            self.logger.info(f"已清除舊的相符性檢查結果")
        except Exception as e:
            self.logger.error(f"清除舊檢查結果失敗：{str(e)}")
            raise
    

    
    def check_missing_dispatch(self):
        """
        檢查缺失派工單
        比對條件：公司代號或公司名稱+工單號碼+產品編號
        排除RD樣品工單
        """
        try:
            self.clear_old_results('missing_dispatch')
            
            # 排除RD樣品工單的填報紀錄
            fill_works = FillWork.objects.exclude(workorder='RD樣品')
            missing_count = 0
            
            for fill_work in fill_works:
                # 檢查是否有對應的派工單
                # 修正：當 company_code 為 None 時，只比對工單號碼和產品編號
                if fill_work.company_code:
                    dispatch_exists = WorkOrderDispatch.objects.filter(
                        company_code=fill_work.company_code,
                        order_number=fill_work.workorder,
                        product_code=fill_work.product_id
                    ).exists()
                else:
                    # 當 company_code 為 None 時，只比對工單號碼和產品編號
                    dispatch_exists = WorkOrderDispatch.objects.filter(
                        order_number=fill_work.workorder,
                        product_code=fill_work.product_id
                    ).exists()
                
                if not dispatch_exists:
                    ConsistencyCheckResult.objects.create(
                        check_type='missing_dispatch',
                        company_code=fill_work.company_code,
                        company_name=fill_work.company_name,
                        workorder=fill_work.workorder,
                        product_code=fill_work.product_id,
                        operator=fill_work.operator,
                        work_date=fill_work.work_date,
                    )
                    missing_count += 1
            
            self.logger.info(f"缺失派工單檢查完成，發現 {missing_count} 筆問題")
            return missing_count
            
        except Exception as e:
            self.logger.error(f"檢查缺失派工單失敗：{str(e)}")
            raise
    
    def check_wrong_product_code(self):
        """
        檢查產品編號錯誤
        比對條件：公司代號或公司名稱+工單號碼一樣，產品編號跟工單不一樣
        排除RD樣品工單
        """
        try:
            self.clear_old_results('wrong_product_code')
            
            # 排除RD樣品工單
            workorders = WorkOrder.objects.exclude(order_number='RD樣品')
            wrong_count = 0
            
            for workorder in workorders:
                # 從 CompanyConfig 取得正確的公司名稱
                try:
                    company_config = CompanyConfig.objects.get(company_code=workorder.company_code)
                    correct_company_name = company_config.company_name
                except CompanyConfig.DoesNotExist:
                    # 如果找不到公司配置，使用公司代號作為公司名稱
                    correct_company_name = workorder.company_code
                
                # 修正：比對條件：公司代號或公司名稱+工單號碼一樣，產品編號跟工單不一樣
                # 檢查該公司該工單的填報紀錄，且產品編號不匹配的記錄
                fill_works = FillWork.objects.filter(
                    company_name=correct_company_name,
                    workorder=workorder.order_number
                )
                
                # 如果沒有填報紀錄，跳過（這屬於缺失填報紀錄問題）
                if not fill_works.exists():
                    continue
                
                # 檢查是否有產品編號不匹配的記錄
                wrong_product_fill_works = fill_works.exclude(product_id=workorder.product_code)
                
                for fill_work in wrong_product_fill_works:
                    ConsistencyCheckResult.objects.create(
                        check_type='wrong_product_code',
                        company_code=workorder.company_code,
                        company_name=correct_company_name,
                        workorder=workorder.order_number,
                        product_code=workorder.product_code,
                        wrong_product_code=fill_work.product_id,
                        operator=fill_work.operator,
                        work_date=fill_work.work_date,
                    )
                    wrong_count += 1
            
            self.logger.info(f"產品編號錯誤檢查完成，發現 {wrong_count} 筆問題")
            return wrong_count
            
        except Exception as e:
            self.logger.error(f"檢查產品編號錯誤失敗：{str(e)}")
            raise
    
    def check_wrong_company(self):
        """
        檢查公司代號/名稱錯誤
        比對條件：先根據工單號碼+產品編號找到對應的工單，再檢查該工單的公司代號與填報紀錄的公司名稱是否一致
        排除RD樣品工單
        """
        try:
            self.clear_old_results('wrong_company')
            
            # 排除RD樣品工單
            workorders = WorkOrder.objects.exclude(order_number='RD樣品')
            wrong_count = 0
            
            for workorder in workorders:
                # 從 CompanyConfig 取得正確的公司名稱
                try:
                    company_config = CompanyConfig.objects.get(company_code=workorder.company_code)
                    correct_company_name = company_config.company_name
                except CompanyConfig.DoesNotExist:
                    # 如果找不到公司配置，使用公司代號作為公司名稱
                    correct_company_name = workorder.company_code
                
                # 正確的比對邏輯：先根據工單號碼+產品編號找到對應的工單
                # 再檢查該工單的公司代號與填報紀錄的公司名稱是否一致
                # 如果不一致，才算是錯誤
                fill_works = FillWork.objects.filter(
                    workorder=workorder.order_number,
                    product_id=workorder.product_code
                )
                
                # 檢查填報紀錄的公司名稱是否與工單對應的公司名稱一致
                for fill_work in fill_works:
                    if fill_work.company_name != correct_company_name:
                        ConsistencyCheckResult.objects.create(
                            check_type='wrong_company',
                            company_code=workorder.company_code,
                            company_name=correct_company_name,
                            workorder=workorder.order_number,
                            product_code=workorder.product_code,
                            wrong_company_code=fill_work.company_code,
                            wrong_company_name=fill_work.company_name,
                            operator=fill_work.operator,
                            work_date=fill_work.work_date,
                        )
                        wrong_count += 1
            
            self.logger.info(f"公司代號/名稱錯誤檢查完成，發現 {wrong_count} 筆問題")
            return wrong_count
            
        except Exception as e:
            self.logger.error(f"檢查公司代號/名稱錯誤失敗：{str(e)}")
            raise
    
    def check_wrong_workorder(self):
        """
        檢查工單號碼錯誤
        比對條件：公司代號或公司名稱+產品編號，工單號碼不同
        排除RD樣品工單
        """
        try:
            self.clear_old_results('wrong_workorder')
            
            # 排除RD樣品工單
            workorders = WorkOrder.objects.exclude(order_number='RD樣品')
            wrong_count = 0
            
            for workorder in workorders:
                # 從 CompanyConfig 取得正確的公司名稱
                try:
                    company_config = CompanyConfig.objects.get(company_code=workorder.company_code)
                    correct_company_name = company_config.company_name
                except CompanyConfig.DoesNotExist:
                    # 如果找不到公司配置，使用公司代號作為公司名稱
                    correct_company_name = workorder.company_code
                
                # 檢查填報紀錄中工單號碼錯誤的記錄
                # 修正：只檢查有填報紀錄的工單，且工單號碼不匹配的記錄
                fill_works = FillWork.objects.filter(
                    company_name=correct_company_name,
                    product_id=workorder.product_code
                )
                
                # 如果沒有填報紀錄，跳過
                if not fill_works.exists():
                    continue
                
                # 檢查是否有工單號碼不匹配的記錄
                wrong_workorder_fill_works = fill_works.exclude(workorder=workorder.order_number)
                
                for fill_work in wrong_workorder_fill_works:
                    ConsistencyCheckResult.objects.create(
                        check_type='wrong_workorder',
                        company_code=workorder.company_code,
                        company_name=correct_company_name,
                        workorder=workorder.order_number,
                        product_code=workorder.product_code,
                        wrong_workorder=fill_work.workorder,
                        operator=fill_work.operator,
                        work_date=fill_work.work_date,
                    )
                    wrong_count += 1
            
            self.logger.info(f"工單號碼錯誤檢查完成，發現 {wrong_count} 筆問題")
            return wrong_count
            
        except Exception as e:
            self.logger.error(f"檢查工單號碼錯誤失敗：{str(e)}")
            raise
    
    def run_all_checks(self):
        """
        執行所有相符性檢查
        """
        try:
            self.logger.info("開始執行所有相符性檢查")
            
            results = {
                'missing_dispatch': self.check_missing_dispatch(),
                'wrong_product_code': self.check_wrong_product_code(),
                'wrong_company': self.check_wrong_company(),
                'wrong_workorder': self.check_wrong_workorder(),
            }
            
            total_issues = sum(results.values())
            self.logger.info(f"所有相符性檢查完成，總共發現 {total_issues} 筆問題")
            
            return results
            
        except Exception as e:
            self.logger.error(f"執行相符性檢查失敗：{str(e)}")
            raise
    
    def fix_issue(self, result_id, fix_method, fixed_by):
        """
        修復相符性問題
        
        Args:
            result_id: 檢查結果ID
            fix_method: 修復方式
            fixed_by: 修復人員
        """
        try:
            result = ConsistencyCheckResult.objects.get(id=result_id)
            
            if result.check_type == 'missing_dispatch':
                self._fix_missing_dispatch(result, fix_method)
            elif result.check_type == 'wrong_product_code':
                self._fix_wrong_product_code(result, fix_method)
            elif result.check_type == 'wrong_company':
                self._fix_wrong_company(result, fix_method)
            elif result.check_type == 'wrong_workorder':
                self._fix_wrong_workorder(result, fix_method)
            
            result.mark_as_fixed(fixed_by, fix_method)
            self.logger.info(f"已修復相符性問題：{result}")
            
        except Exception as e:
            self.logger.error(f"修復相符性問題失敗：{str(e)}")
            raise
    

    
    def _fix_missing_dispatch(self, result, fix_method):
        """修復缺失派工單"""
        # 這裡可以實作自動建立派工單的邏輯
        pass
    
    def _fix_wrong_product_code(self, result, fix_method):
        """修復產品編號錯誤 - 將填報紀錄的產品編號更新為工單的正確產品編號"""
        # 不管修復方式，都統一更新填報紀錄的產品編號
        from workorder.fill_work.models import FillWork
        
        # 更新填報紀錄的產品編號，讓它與工單的產品編號一致
        updated_count = FillWork.objects.filter(
            company_name=result.company_name,
            workorder=result.workorder,
            product_id=result.wrong_product_code
        ).update(product_id=result.product_code)
        
        self.logger.info(f"已更新 {updated_count} 筆填報紀錄的產品編號：{result.wrong_product_code} → {result.product_code}")
    
    def _fix_wrong_company(self, result, fix_method):
        """修復公司代號/名稱錯誤"""
        if fix_method == 'update_fill_work':
            # 更新填報紀錄的公司名稱
            FillWork.objects.filter(
                workorder=result.workorder,
                product_id=result.product_code,
                company_name=result.wrong_company_name
            ).update(
                company_code=result.company_code,
                company_name=result.company_name
            )
    
    def _fix_wrong_workorder(self, result, fix_method):
        """修復工單號碼錯誤"""
        if fix_method == 'update_fill_work':
            # 更新填報紀錄的工單號碼
            FillWork.objects.filter(
                company_name=result.company_name,
                product_id=result.product_code,
                workorder=result.wrong_workorder
            ).update(workorder=result.workorder) 