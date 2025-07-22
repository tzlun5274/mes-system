# 欄位錯誤修復說明

## 問題描述

在測試 RD 樣品報工功能時，遇到了以下錯誤：

```
FieldError: Cannot resolve keyword 'is_active' into field. 
Choices are: created_at, dispatchlog, id, managerproductionreport, name, operatorsupplementreport, production_line, production_line_id, skills, updated_at
```

## 錯誤原因

在 `workorder/forms.py` 的 `OperatorSupplementReportForm` 類別中，嘗試對 `Operator`、`ProcessName` 和 `Equipment` 模型使用 `is_active` 欄位進行過濾，但這些模型實際上沒有 `is_active` 欄位。

## 修復內容

### 1. Operator 模型查詢修復

**修復前：**
```python
self.fields['operator'].queryset = Operator.objects.filter(is_active=True).order_by('name')
```

**修復後：**
```python
self.fields['operator'].queryset = Operator.objects.all().order_by('name')
```

### 2. ProcessName 模型查詢修復

**修復前：**
```python
self.fields['process'].queryset = ProcessName.objects.filter(
    is_active=True
).exclude(
    name__icontains='SMT'
).exclude(
    name__icontains='表面貼裝'
).exclude(
    name__icontains='貼片'
).order_by('name')
```

**修復後：**
```python
self.fields['process'].queryset = ProcessName.objects.all().exclude(
    name__icontains='SMT'
).exclude(
    name__icontains='表面貼裝'
).exclude(
    name__icontains='貼片'
).order_by('name')
```

### 3. Equipment 模型查詢修復

**修復前：**
```python
self.fields['equipment'].queryset = Equipment.objects.filter(
    is_active=True
).exclude(
    name__icontains='SMT'
).exclude(
    name__icontains='表面貼裝'
).exclude(
    name__icontains='貼片'
).order_by('name')
```

**修復後：**
```python
self.fields['equipment'].queryset = Equipment.objects.all().exclude(
    name__icontains='SMT'
).exclude(
    name__icontains='表面貼裝'
).exclude(
    name__icontains='貼片'
).order_by('name')
```

## 模型欄位確認

經過檢查，確認以下模型的實際欄位：

### Operator 模型 (process/models.py)
```python
class Operator(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="作業員名稱")
    production_line = models.ForeignKey('production.ProductionLine', ...)
    created_at = models.DateTimeField("建立時間", auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True, null=True, blank=True)
    # 沒有 is_active 欄位
```

### ProcessName 模型 (process/models.py)
```python
class ProcessName(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="工序名稱")
    description = models.TextField(blank=True, verbose_name="描述")
    # 沒有 is_active 欄位
```

### Equipment 模型 (equip/models.py)
```python
class Equipment(models.Model):
    # 檢查結果：沒有 is_active 欄位
```

## 影響範圍

### 功能影響
- ✅ 作業員補登報工功能現在可以正常載入
- ✅ RD 樣品報工和正式報工功能都能正常使用
- ✅ 所有相關的下拉選單都能正確顯示選項

### 資料影響
- ✅ 不會影響現有的資料
- ✅ 所有作業員、工序、設備都會顯示在選項中
- ✅ 如果需要過濾特定狀態的記錄，建議在模型層面加入 `is_active` 欄位

## 建議改進

### 1. 模型層面改進
如果需要在這些模型中加入啟用/停用功能，建議：

```python
# 在 Operator 模型中加入
is_active = models.BooleanField("是否啟用", default=True)

# 在 ProcessName 模型中加入
is_active = models.BooleanField("是否啟用", default=True)

# 在 Equipment 模型中加入
is_active = models.BooleanField("是否啟用", default=True)
```

### 2. 表單層面改進
如果模型有 `is_active` 欄位，可以恢復過濾：

```python
# 只顯示啟用的作業員
self.fields['operator'].queryset = Operator.objects.filter(is_active=True).order_by('name')

# 只顯示啟用的工序
self.fields['process'].queryset = ProcessName.objects.filter(is_active=True).exclude(...)

# 只顯示啟用的設備
self.fields['equipment'].queryset = Equipment.objects.filter(is_active=True).exclude(...)
```

## 測試結果

### 修復前
- ❌ 頁面載入失敗
- ❌ FieldError 錯誤
- ❌ 無法使用報工功能

### 修復後
- ✅ 頁面正常載入
- ✅ 所有下拉選單正常顯示
- ✅ RD 樣品報工功能正常
- ✅ 正式報工功能正常

## 修復完成

**修復時間**：2025-07-22  
**修復狀態**：已完成並測試通過  
**影響範圍**：作業員補登報工功能

---

本次修復解決了欄位不存在的問題，讓 RD 樣品報工功能能夠正常使用。 