# 報表模組 (Reporting)

## 模組概述

報表模組是 MES 系統的核心報表功能，提供多種報表類型，包括工單報表、評分報表等，幫助管理者全面了解生產狀況和績效表現。

## 主要功能

### 1. 工單報表
- **日報表**：每日工單執行狀況統計
- **週報表**：每週工單完成情況分析
- **月報表**：月度生產績效總結
- **季報表**：季度生產趨勢分析
- **年報表**：年度生產成果報告

### 2. 評分報表系統 ⭐ 新功能

評分報表系統提供全面的績效評估功能，基於多個維度對生產表現進行量化評分。

#### 評分維度

**生產效率 (100%)** - 以工序標準產能為基準 ⭐ 核心指標
- **平均產能評分 (100%)**：基於標準產能的評分

**已移除的維度**：
- ~~品質管理~~ - 已整合到作業員工序產能評分中
- ~~設備管理~~ - 不適用於電子業製造
- ~~安全管理~~ - 不適用於電子業製造
- ~~產能達成率~~ - 已整合到平均產能評分中
- ~~產能穩定性~~ - 概念過於複雜，已簡化
- ~~交期管理~~ - 等排程功能開發完成後再加入
- ~~成本控制~~ - 加班非作業員自願，不應納入評分
- ~~人員管理~~ - 特休是員工權利，不應影響評分

### 3. 作業員工序產能評分系統 ⭐ 全新功能

#### 評分標準

**總評分計算公式：**
- **生產效率 (80%)**：產能評分60% + 品質評分20%
- **主管評分 (20%)**：主管主觀評價

**主管評分機制：**
- **預設分數**：80分（如果主管未主動評分）
- **加分機制**：主管可在報表生成前主動給予更高分數
- **評分時機**：必須在評分報表運作前完成評分，否則使用預設80分

#### 評分等級
- **90-100分**：優秀 - 表現卓越，超出預期
- **80-89分**：良好 - 表現良好，符合標準  
- **70-79分**：及格 - 表現一般，需要改善
- **0-69分**：不及格 - 表現不佳，需要立即改善

#### 評分計算邏輯

1. **標準產能查詢**：
   - 從 `ProductProcessStandardCapacity` 表查詢產品工序的標準產能
   - 支援不同設備類型和作業員等級的標準產能
   - 如果沒有標準產能資料，使用預設值1000 pcs/hr

2. **實際產能計算**：
   - 實際每小時產能 = 完成數量 ÷ 工作時數
   - 產能比率 = (實際產能 ÷ 標準產能) × 100%

3. **綜合評分**：
   - 綜合評分 = 產能評分 × 70% + 品質評分 × 30%

#### 主要功能

1. **自動評分生成**
   - 從填報資料自動生成評分
   - 從現場報工資料自動生成評分
   - 支援批量處理和增量更新

2. **作業員表現分析**
   - 個人產能趨勢分析
   - 工序熟練度評估
   - 品質表現追蹤

3. **工序產能分析**
   - 各工序標準產能對比
   - 產能達成率統計
   - 工序效率排名

4. **產能評分報表**
   - 作業員產能評分報表
   - 工序產能分析報表
   - 產能趨勢分析報表

## 資料模型

### 評分報表相關模型

1. **ScoringCriteria (評分標準)**
   - 定義各項評分指標
   - 設定評分公式和權重
   - 配置等級門檻值

2. **ScoringReport (評分報表)**
   - 儲存評分報表主體資料
   - 記錄各維度分數
   - 統計等級分布

3. **ScoringDetail (評分明細)**
   - 記錄各項指標的詳細評分
   - 儲存計算過程和原始資料

4. **ScoringImprovement (改善建議)**
   - 自動生成改善建議
   - 追蹤改善進度
   - 設定責任人和期限

### 作業員工序產能評分模型 ⭐ 新增

5. **OperatorProcessCapacityScore (作業員工序產能評分)**
   - 記錄每個作業員在每個工序的產能評分
   - 包含標準產能、實際產能、產能比率
   - 記錄品質資料和綜合評分

6. **OperatorCapacityReport (作業員產能評分報表)**
   - 統計作業員產能評分報表
   - 包含等級分布和工序表現統計
   - 支援多種報表週期

## 使用方式

### 1. 生成作業員工序產能評分

```bash
# 從現有報工資料生成評分（最近30天）
python3 manage.py generate_operator_capacity_scores

# 指定日期範圍
python3 manage.py generate_operator_capacity_scores --start-date 2024-01-01 --end-date 2024-01-31

# 指定公司
python3 manage.py generate_operator_capacity_scores --company COMP001

# 強制重新計算
python3 manage.py generate_operator_capacity_scores --force
```

### 2. 程式化生成評分

```python
from reporting.operator_capacity_service import OperatorCapacityService
from datetime import date

# 計算單筆作業員工序產能評分
score_record = OperatorCapacityService.calculate_operator_process_score(
    operator_id=1,
    workorder_id='WO2024001',
    process_name='SMT',
    work_date=date(2024, 1, 15),
    completed_quantity=500,
    work_hours=8.0,
    defect_quantity=5
)

# 生成作業員產能評分報表
report = OperatorCapacityService.generate_operator_capacity_report(
    company_code='COMP001',
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31)
)
```

### 3. 生成評分報表

```python
from reporting.scoring_service import ScoringService
from datetime import date

# 生成月度評分報表
scoring_report = ScoringService.generate_scoring_report(
    company_code='COMP001',
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    report_period='monthly'
)

# 生成改善建議
improvements = ScoringService.generate_improvement_suggestions(scoring_report)
```

## 網頁介面

### 評分報表相關頁面

1. **評分儀表板** (`/reporting/scoring/`)
   - 顯示最新評分概覽
   - 提供趨勢圖表
   - 列出待處理改善建議

2. **評分報表清單** (`/reporting/scoring/reports/`)
   - 瀏覽所有評分報表
   - 支援搜尋和篩選
   - 提供匯出功能

3. **生成評分報表** (`/reporting/scoring/reports/generate/`)
   - 設定評分期間
   - 選擇報表類型
   - 一鍵生成報表

4. **評分報表詳情** (`/reporting/scoring/reports/<id>/`)
   - 查看詳細評分資料
   - 分析各維度表現
   - 檢視改善建議

5. **評分標準管理** (`/reporting/scoring/criteria/`)
   - 管理評分指標
   - 調整評分公式
   - 設定權重和門檻

### 作業員產能評分相關頁面 ⭐ 新增

6. **作業員產能評分清單** (`/reporting/operator-capacity/`)
   - 瀏覽作業員產能評分記錄
   - 按作業員、工序、日期篩選
   - 查看詳細評分資料

7. **作業員產能分析** (`/reporting/operator-capacity/analysis/`)
   - 作業員表現趨勢分析
   - 工序熟練度評估
   - 產能達成率統計

8. **工序產能分析** (`/reporting/process-capacity/analysis/`)
   - 各工序標準產能對比
   - 工序效率排名
   - 產能穩定性分析

## 技術特點

1. **標準產能基準評分**
   - 以工序標準產能為唯一基準
   - 支援不同產品、工序、設備類型的標準產能
   - 自動查詢最新版本的標準產能資料

2. **自動化評分生成**
   - 從現有報工資料自動生成評分
   - 支援批量處理和增量更新
   - 避免重複計算

3. **多維度評分分析**
   - 產能評分：基於標準產能的達成率
   - 品質評分：基於不良率的評分
   - 綜合評分：產能和品質的加權評分

4. **視覺化呈現**
   - 使用Chart.js繪製圖表
   - 提供雷達圖和趨勢圖
   - 支援響應式設計

5. **改善建議系統**
   - 自動識別問題點
   - 生成具體改善建議
   - 追蹤改善進度

6. **多公司支援**
   - 支援多公司資料隔離
   - 可設定公司專屬評分標準

7. **匯出功能**
   - 支援Excel格式匯出
   - 包含完整評分資料
   - 格式化報表樣式

## 初始化

### 建立評分標準

```bash
python3 manage.py init_scoring_criteria
```

### 生成作業員工序產能評分

```bash
# 從現有資料生成評分
python3 manage.py generate_operator_capacity_scores

# 指定日期範圍生成評分
python3 manage.py generate_operator_capacity_scores --start-date 2024-01-01 --end-date 2024-01-31
```

## 注意事項

1. **標準產能資料完整性**：確保 `ProductProcessStandardCapacity` 表中有完整的標準產能資料
2. **報工資料準確性**：評分結果依賴於報工資料的準確性
3. **評分基準調整**：可根據實際需求調整產能和品質的評分基準
4. **資料更新頻率**：建議定期執行評分生成命令以保持資料最新
5. **評分權重設定**：產能評分權重70%，品質評分權重30%，可根據需求調整

## 未來擴展

1. **學習曲線分析**：分析作業員在不同工序的學習進度
2. **產能預測**：基於歷史資料預測未來產能表現
3. **技能認證**：結合評分結果進行技能等級認證
4. **培訓建議**：基於評分結果生成個人化培訓建議
5. **績效獎勵**：結合評分結果設計績效獎勵機制 