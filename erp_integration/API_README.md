# ERP 整合模組 API 文件

## 概述
ERP 整合模組提供完整的 RESTful API 介面，讓其他模組可以透過 API 獲取公司配置、ERP 設定和操作日誌等資訊。

## API 端點列表

### 1. 公司配置 API

#### 1.1 獲取所有公司配置
- **URL**: `/erp_integration/api/company-config/`
- **方法**: `GET`
- **說明**: 獲取所有公司的配置資訊
- **回應範例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "company_code": "02",
            "company_name": "中儀科技",
            "database": "",
            "mssql_database": "CHIComp02",
            "mes_database": "CHIComp02",
            "notes": "",
            "sync_tables": "TraBillMain,TraBillSub,comCustomer,comProduct,impPurchaseMain,impPurchaseMergeSub,impPurchaseSub,ordBillMain,ordBillSub,prdMKOrdMain,prdMkOrdMats,stkBorrowSub,stkYearMonthQty",
            "last_sync_version": 11443124,
            "last_sync_time": "2025-09-10T14:29:11.085324+00:00",
            "sync_interval_minutes": 30
        }
    ],
    "count": 1,
    "message": "公司配置列表獲取成功"
}
```

#### 1.2 獲取單一公司配置
- **URL**: `/erp_integration/api/company-config/{id}/`
- **方法**: `GET`
- **參數**: `id` - 公司配置 ID
- **說明**: 根據 ID 獲取特定公司的配置資訊

#### 1.3 根據公司代號查詢
- **URL**: `/erp_integration/api/company-by-code/`
- **方法**: `GET`
- **參數**: `company_code` - 公司代號
- **說明**: 根據公司代號獲取公司資訊
- **範例**: `/erp_integration/api/company-by-code/?company_code=10`

#### 1.4 獲取所有公司
- **URL**: `/erp_integration/api/active-companies/`
- **方法**: `GET`
- **說明**: 獲取所有公司的基本資訊

### 2. ERP 配置 API

#### 2.1 獲取所有 ERP 配置
- **URL**: `/erp_integration/api/erp-config/`
- **方法**: `GET`
- **說明**: 獲取所有 ERP 連線配置
- **回應範例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "server": "192.168.1.100",
            "username": "sa",
            "last_updated": "2025-09-10T14:29:11.085324+00:00"
        }
    ],
    "count": 1,
    "message": "ERP 配置列表獲取成功"
}
```

#### 2.2 獲取單一 ERP 配置
- **URL**: `/erp_integration/api/erp-config/{id}/`
- **方法**: `GET`
- **參數**: `id` - ERP 配置 ID
- **說明**: 根據 ID 獲取特定 ERP 配置

#### 2.3 獲取所有 ERP 配置
- **URL**: `/erp_integration/api/active-erp-configs/`
- **方法**: `GET`
- **說明**: 獲取所有 ERP 配置的基本資訊

### 3. 操作日誌 API

#### 3.1 獲取操作日誌
- **URL**: `/erp_integration/api/erp-operation-logs/`
- **方法**: `GET`
- **參數**: `limit` - 限制返回筆數（預設 50）
- **說明**: 獲取 ERP 整合操作日誌
- **範例**: `/erp_integration/api/erp-operation-logs/?limit=10`
- **回應範例**:
```json
{
    "success": true,
    "data": [
        {
            "id": 26,
            "user": "system",
            "action": "公司 中儀科技 資料增量同步成功，同步資料表：TraBillMain, TraBillSub, comCustomer, comProduct, impPurchaseMain, impPurchaseMergeSub, impPurchaseSub, ordBillMain, ordBillSub, prdMKOrdMain, prdMkOrdMats, stkBorrowSub, stkYearMonthQty",
            "timestamp": "2025-09-10T14:29:11.089943+00:00"
        }
    ],
    "count": 1,
    "message": "ERP 整合操作日誌獲取成功"
}
```

## 資料欄位說明

### CompanyConfig 欄位
- `id`: 公司配置 ID
- `company_code`: 公司代號
- `company_name`: 公司名稱
- `database`: 資料庫名稱（舊欄位）
- `mssql_database`: MSSQL 資料庫名稱
- `mes_database`: MES 資料庫名稱
- `notes`: 備註
- `sync_tables`: 需要同步的資料表（逗號分隔）
- `last_sync_version`: 最後同步版本號
- `last_sync_time`: 最後同步時間
- `sync_interval_minutes`: 自動同步間隔（分鐘）

### ERPConfig 欄位
- `id`: ERP 配置 ID
- `server`: MSSQL 伺服器地址
- `username`: 使用者名稱
- `last_updated`: 最後更新時間

### ERPIntegrationOperationLog 欄位
- `id`: 日誌 ID
- `user`: 操作者
- `action`: 操作描述
- `timestamp`: 操作時間

## 錯誤處理

所有 API 都會返回統一的錯誤格式：
```json
{
    "success": false,
    "message": "錯誤訊息描述"
}
```

常見的 HTTP 狀態碼：
- `200`: 成功
- `400`: 請求參數錯誤
- `404`: 資源不存在
- `500`: 伺服器內部錯誤

## 使用範例

### JavaScript 範例
```javascript
// 獲取所有公司配置
fetch('/erp_integration/api/company-config/')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('公司列表:', data.data);
        } else {
            console.error('錯誤:', data.message);
        }
    });

// 根據公司代號查詢
fetch('/erp_integration/api/company-by-code/?company_code=10')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('公司資訊:', data.data);
        }
    });
```

### Python 範例
```python
import requests

# 獲取所有公司配置
response = requests.get('http://localhost:8000/erp_integration/api/company-config/')
data = response.json()

if data['success']:
    companies = data['data']
    for company in companies:
        print(f"公司: {company['company_name']} ({company['company_code']})")
```

## 注意事項

1. 所有 API 都是唯讀的，不提供修改功能
2. API 不需要認證，但建議在生產環境中加上適當的權限控制
3. 回應中的時間格式為 ISO 8601 格式
4. 所有 API 都支援 CORS，可以從前端直接調用
5. 建議使用適當的錯誤處理機制來處理 API 回應

## 測試頁面

系統提供了 API 測試頁面，可以透過以下 URL 訪問：
- **URL**: `/erp_integration/api_test/`
- **說明**: 提供互動式的 API 測試介面，可以測試所有 API 端點
