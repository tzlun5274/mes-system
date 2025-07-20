# SMT 補登報工核准功能說明

## 功能概述

SMT 補登報工核准功能為補登記錄添加了完整的核准流程，確保資料的準確性和可追溯性。一旦記錄被核准，將無法修改，只有超級管理員可以強制刪除。

## 主要特色

### 1. 核准狀態管理
- **待核准**：新建立的補登記錄預設狀態
- **已核准**：經過核准的記錄，不可修改
- **已駁回**：被駁回的記錄，可重新編輯

### 2. 權限控制
- **一般用戶**：只能編輯待核准和已駁回的記錄
- **超級管理員**：可以編輯和刪除所有記錄，包括已核准的記錄

### 3. 完整的核准流程
- **核准**：確認記錄正確性，核准後不可修改
- **駁回**：標記記錄有問題，需要重新修正
- **備註記錄**：核准和駁回時可添加備註說明

## 資料模型更新

### 新增欄位
```python
class SMTProductionReport(models.Model):
    # 核准狀態
    APPROVAL_STATUS_CHOICES = [
        ('pending', '待核准'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
    ]
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        verbose_name="核准狀態"
    )
    
    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="核准時間"
    )
    
    approval_remarks = models.TextField(
        blank=True,
        verbose_name="核准備註"
    )
```

### 新增方法
```python
def can_edit(self, user):
    """檢查記錄是否可以編輯"""
    if self.approval_status == 'approved':
        return user.is_superuser
    return True

def can_delete(self, user):
    """檢查記錄是否可以刪除"""
    if self.approval_status == 'approved':
        return user.is_superuser
    return True

def approve(self, user, remarks=''):
    """核准補登記錄"""
    self.approval_status = 'approved'
    self.approved_by = user.username
    self.approved_at = timezone.now()
    self.approval_remarks = remarks
    self.save()

def reject(self, user, remarks=''):
    """駁回補登記錄"""
    self.approval_status = 'rejected'
    self.approved_by = user.username
    self.approved_at = timezone.now()
    self.approval_remarks = remarks
    self.save()
```

## 使用流程

### 1. 建立補登記錄
- 新建立的補登記錄預設為「待核准」狀態
- 可以正常編輯和刪除

### 2. 核准記錄
- 在記錄詳情頁面點擊「核准記錄」按鈕
- 進入核准確認頁面，查看記錄詳細資訊
- 可選擇性添加核准備註
- 確認核准後，記錄狀態變更為「已核准」

### 3. 駁回記錄
- 在記錄詳情頁面點擊「駁回記錄」按鈕
- 進入駁回確認頁面，查看記錄詳細資訊
- 必須輸入駁回原因
- 確認駁回後，記錄狀態變更為「已駁回」

### 4. 編輯權限
- **待核准**：所有用戶都可以編輯
- **已核准**：只有超級管理員可以編輯
- **已駁回**：所有用戶都可以編輯（重新修正）

### 5. 刪除權限
- **待核准**：所有用戶都可以刪除
- **已核准**：只有超級管理員可以刪除
- **已駁回**：所有用戶都可以刪除

## 介面更新

### 列表頁面
- 新增「核准狀態」欄位顯示
- 根據核准狀態顯示不同顏色的標籤
- 根據權限顯示/隱藏編輯和刪除按鈕

### 詳情頁面
- 新增核准狀態顯示區域
- 顯示核准人員、時間和備註
- 根據核准狀態顯示相應的操作按鈕

### 編輯頁面
- 已核准記錄的欄位會被禁用（超級管理員除外）
- 顯示當前核准狀態

## 新增頁面

### 核准確認頁面 (`approve_confirm.html`)
- 顯示記錄詳細資訊
- 提供核准備註輸入
- 確認核准操作

### 駁回確認頁面 (`reject_confirm.html`)
- 顯示記錄詳細資訊
- 強制輸入駁回原因
- 確認駁回操作

## 新增 URL 路由

```python
# 核准和駁回功能
path('report/smt/supplement/approve/<int:report_id>/', views.smt_supplement_report_approve, name='smt_supplement_report_approve'),
path('report/smt/supplement/reject/<int:report_id>/', views.smt_supplement_report_reject, name='smt_supplement_report_reject'),
```

## 新增視圖函數

### `smt_supplement_report_approve`
- 處理核准操作
- 更新記錄狀態
- 記錄核准人員和時間

### `smt_supplement_report_reject`
- 處理駁回操作
- 更新記錄狀態
- 記錄駁回人員和時間

## 安全性設計

### 1. 權限驗證
- 所有操作都會檢查用戶權限
- 已核准記錄的編輯和刪除限制

### 2. 資料完整性
- 核准後記錄不可修改，確保資料一致性
- 完整的操作記錄和時間戳記

### 3. 用戶體驗
- 清晰的狀態顯示
- 友善的錯誤訊息
- 直觀的操作流程

## 與其他功能的整合

### 1. 報表功能
- 可根據核准狀態篩選記錄
- 只統計已核准的記錄

### 2. 資料匯出
- 可選擇匯出已核准的記錄
- 包含核准相關資訊

### 3. 審計追蹤
- 完整的核准歷史記錄
- 可追蹤每個記錄的核准流程

## 技術實現

### 1. 資料庫遷移
- 新增核准相關欄位
- 保持向後相容性

### 2. 表單驗證
- 根據核准狀態動態調整表單
- 權限檢查和欄位禁用

### 3. 前端互動
- JavaScript 權限檢查
- 動態按鈕顯示/隱藏

## 注意事項

1. **核准後不可修改**：已核准的記錄只有超級管理員可以強制刪除
2. **駁回需要原因**：駁回記錄時必須輸入駁回原因
3. **權限檢查**：所有操作都會進行權限驗證
4. **資料備份**：建議定期備份已核准的記錄

## 未來擴展

1. **批量核准**：支援批量核准多筆記錄
2. **核准流程**：支援多級核准流程
3. **通知功能**：核准狀態變更時發送通知
4. **審計報表**：核准歷史和統計報表 