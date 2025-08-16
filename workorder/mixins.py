"""
工單模組的 Mixin 類別
提供資料隔離和公司代號管理功能
"""

from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin


class CompanyCodeMixin:
    """
    公司代號 Mixin
    為視圖提供公司代號管理功能
    """
    
    def get_company_code(self):
        """
        獲取當前請求的公司代號
        """
        if hasattr(self.request, 'company_code'):
            return self.request.company_code
        return None
    
    def get_user_company_code(self):
        """
        獲取用戶的公司代號
        """
        if not self.request.user.is_authenticated:
            return None
        
        # 超級用戶可以看到所有公司
        if self.request.user.is_superuser:
            return None
        
        # 從用戶設定獲取公司代號
        if hasattr(self.request.user, 'profile') and self.request.user.profile.company_code:
            return self.request.user.profile.company_code
        
        # 從會話獲取公司代號
        company_code = self.request.session.get('company_code')
        if company_code:
            return company_code
        
        # 預設公司代號
        return '01'


class DataIsolationMixin(CompanyCodeMixin):
    """
    資料隔離 Mixin
    確保用戶只能看到自己公司的資料
    """
    
    def get_queryset(self):
        """
        重寫 get_queryset 方法，實現資料隔離
        """
        queryset = super().get_queryset()
        
        # 如果啟用資料隔離
        if hasattr(self.request, 'data_isolation_enabled') and self.request.data_isolation_enabled:
            company_code = self.get_user_company_code()
            if company_code:
                # 根據模型類型添加公司代號篩選
                if hasattr(queryset.model, 'company_code'):
                    queryset = queryset.filter(company_code=company_code)
                elif hasattr(queryset.model, 'company_name'):
                    # 如果模型只有 company_name，需要從 CompanyConfig 獲取對應的公司代號
                    from erp_integration.models import CompanyConfig
                    try:
                        company_config = CompanyConfig.objects.filter(company_code=company_code).first()
                        if company_config:
                            queryset = queryset.filter(company_name=company_config.company_name)
                    except Exception:
                        pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        重寫 get_context_data 方法，添加公司代號到上下文
        """
        context = super().get_context_data(**kwargs)
        context['company_code'] = self.get_user_company_code()
        context['data_isolation_enabled'] = getattr(self.request, 'data_isolation_enabled', False)
        return context


class WorkOrderQueryMixin(CompanyCodeMixin):
    """
    工單查詢 Mixin
    提供標準化的工單查詢方法
    """
    
    def get_workorder_by_number(self, order_number, company_code=None):
        """
        根據工單號碼和公司代號獲取工單
        """
        from .models import WorkOrder
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return WorkOrder.objects.filter(
                company_code=company_code,
                order_number=order_number
            ).first()
        else:
            # 如果沒有公司代號，使用舊方式查詢（向後相容）
            return WorkOrder.objects.filter(order_number=order_number).first()
    
    def get_workorders_by_company(self, company_code=None):
        """
        根據公司代號獲取工單列表
        """
        from .models import WorkOrder
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return WorkOrder.objects.filter(company_code=company_code)
        else:
            # 如果沒有公司代號，返回所有工單（超級用戶）
            return WorkOrder.objects.all()


class FillWorkQueryMixin(CompanyCodeMixin):
    """
    填報記錄查詢 Mixin
    提供標準化的填報記錄查詢方法
    """
    
    def get_fillwork_by_company(self, company_code=None):
        """
        根據公司代號獲取填報記錄列表
        """
        from .fill_work.models import FillWork
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return FillWork.objects.filter(company_code=company_code)
        else:
            # 如果沒有公司代號，返回所有填報記錄（超級用戶）
            return FillWork.objects.all()
    
    def get_fillwork_by_workorder(self, workorder_number, company_code=None):
        """
        根據工單號碼和公司代號獲取填報記錄
        """
        from .fill_work.models import FillWork
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return FillWork.objects.filter(
                company_code=company_code,
                workorder=workorder_number
            )
        else:
            # 如果沒有公司代號，使用舊方式查詢（向後相容）
            return FillWork.objects.filter(workorder=workorder_number)


class DispatchQueryMixin(CompanyCodeMixin):
    """
    派工單查詢 Mixin
    提供標準化的派工單查詢方法
    """
    
    def get_dispatch_by_company(self, company_code=None):
        """
        根據公司代號獲取派工單列表
        """
        from .workorder_dispatch.models import WorkOrderDispatch
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return WorkOrderDispatch.objects.filter(company_code=company_code)
        else:
            # 如果沒有公司代號，返回所有派工單（超級用戶）
            return WorkOrderDispatch.objects.all()
    
    def get_dispatch_by_workorder(self, workorder_number, company_code=None):
        """
        根據工單號碼和公司代號獲取派工單
        """
        from .workorder_dispatch.models import WorkOrderDispatch
        
        if not company_code:
            company_code = self.get_user_company_code()
        
        if company_code:
            return WorkOrderDispatch.objects.filter(
                company_code=company_code,
                order_number=workorder_number
            )
        else:
            # 如果沒有公司代號，使用舊方式查詢（向後相容）
            return WorkOrderDispatch.objects.filter(order_number=workorder_number) 