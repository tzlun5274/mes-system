# 工單模組視圖初始化檔案
# 用於統一管理所有工單相關的視圖類別 

# 已完工工單視圖
from .completed_workorder_views import (
    CompletedWorkOrderListView,
    CompletedWorkOrderDetailView,
    transfer_workorder_to_completed,
    batch_transfer_completed_workorders
) 