# 基礎驗證器
# 本檔案定義了報表系統的基礎驗證器類別
# 提供統一的數據驗證介面和錯誤處理機制

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, datetime
from decimal import Decimal
import logging
import re

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """驗證錯誤例外類別"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class BaseValidator(ABC):
    """報表驗證器基礎類別 - 所有驗證器的基礎類別"""
    
    def __init__(self):
        """初始化驗證器"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.errors = []
        self.warnings = []
        
    @abstractmethod
    def validate(self, data: Any) -> bool:
        """
        驗證數據（抽象方法）
        
        Args:
            data: 要驗證的數據
            
        Returns:
            bool: 驗證是否通過
        """
        raise NotImplementedError
    
    def add_error(self, message: str, field: str = None, value: Any = None) -> None:
        """
        添加驗證錯誤
        
        Args:
            message: 錯誤訊息
            field: 欄位名稱
            value: 錯誤值
        """
        error = {
            'message': message,
            'field': field,
            'value': value,
            'type': 'error'
        }
        self.errors.append(error)
        self.logger.error(f"驗證錯誤 - 欄位: {field}, 值: {value}, 訊息: {message}")
    
    def add_warning(self, message: str, field: str = None, value: Any = None) -> None:
        """
        添加驗證警告
        
        Args:
            message: 警告訊息
            field: 欄位名稱
            value: 警告值
        """
        warning = {
            'message': message,
            'field': field,
            'value': value,
            'type': 'warning'
        }
        self.warnings.append(warning)
        self.logger.warning(f"驗證警告 - 欄位: {field}, 值: {value}, 訊息: {message}")
    
    def clear_errors(self) -> None:
        """清除所有錯誤和警告"""
        self.errors.clear()
        self.warnings.clear()
    
    def has_errors(self) -> bool:
        """
        檢查是否有錯誤
        
        Returns:
            bool: 是否有錯誤
        """
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """
        檢查是否有警告
        
        Returns:
            bool: 是否有警告
        """
        return len(self.warnings) > 0
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        取得驗證摘要
        
        Returns:
            Dict[str, Any]: 驗證摘要
        """
        return {
            'is_valid': not self.has_errors(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def validate_required_field(self, data: Dict[str, Any], field: str) -> bool:
        """
        驗證必填欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            
        Returns:
            bool: 驗證是否通過
        """
        if field not in data or data[field] is None:
            self.add_error(f"欄位 '{field}' 為必填項目", field)
            return False
        
        if isinstance(data[field], str) and not data[field].strip():
            self.add_error(f"欄位 '{field}' 不能為空字串", field, data[field])
            return False
        
        return True
    
    def validate_string_field(self, data: Dict[str, Any], field: str, 
                            max_length: int = None, min_length: int = None,
                            pattern: str = None) -> bool:
        """
        驗證字串欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            max_length: 最大長度
            min_length: 最小長度
            pattern: 正則表達式模式
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if not isinstance(value, str):
            self.add_error(f"欄位 '{field}' 必須是字串類型", field, value)
            return False
        
        # 檢查長度
        if min_length is not None and len(value) < min_length:
            self.add_error(f"欄位 '{field}' 長度不能少於 {min_length} 個字元", field, value)
            return False
        
        if max_length is not None and len(value) > max_length:
            self.add_error(f"欄位 '{field}' 長度不能超過 {max_length} 個字元", field, value)
            return False
        
        # 檢查正則表達式
        if pattern is not None:
            if not re.match(pattern, value):
                self.add_error(f"欄位 '{field}' 格式不正確", field, value)
                return False
        
        return True
    
    def validate_integer_field(self, data: Dict[str, Any], field: str,
                             min_value: int = None, max_value: int = None) -> bool:
        """
        驗證整數欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if not isinstance(value, int):
            self.add_error(f"欄位 '{field}' 必須是整數類型", field, value)
            return False
        
        # 檢查範圍
        if min_value is not None and value < min_value:
            self.add_error(f"欄位 '{field}' 不能小於 {min_value}", field, value)
            return False
        
        if max_value is not None and value > max_value:
            self.add_error(f"欄位 '{field}' 不能大於 {max_value}", field, value)
            return False
        
        return True
    
    def validate_float_field(self, data: Dict[str, Any], field: str,
                           min_value: float = None, max_value: float = None,
                           precision: int = None) -> bool:
        """
        驗證浮點數欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            min_value: 最小值
            max_value: 最大值
            precision: 精度位數
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if not isinstance(value, (int, float, Decimal)):
            self.add_error(f"欄位 '{field}' 必須是數值類型", field, value)
            return False
        
        # 檢查範圍
        if min_value is not None and value < min_value:
            self.add_error(f"欄位 '{field}' 不能小於 {min_value}", field, value)
            return False
        
        if max_value is not None and value > max_value:
            self.add_error(f"欄位 '{field}' 不能大於 {max_value}", field, value)
            return False
        
        # 檢查精度
        if precision is not None:
            str_value = str(value)
            if '.' in str_value:
                decimal_places = len(str_value.split('.')[1])
                if decimal_places > precision:
                    self.add_warning(f"欄位 '{field}' 精度超過 {precision} 位小數", field, value)
        
        return True
    
    def validate_date_field(self, data: Dict[str, Any], field: str,
                          min_date: date = None, max_date: date = None,
                          format_str: str = '%Y-%m-%d') -> bool:
        """
        驗證日期欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            min_date: 最小日期
            max_date: 最大日期
            format_str: 日期格式
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        
        # 處理字串日期
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, format_str).date()
            except ValueError:
                self.add_error(f"欄位 '{field}' 日期格式不正確，應為 {format_str}", field, value)
                return False
        
        # 檢查是否為日期類型
        if not isinstance(value, (date, datetime)):
            self.add_error(f"欄位 '{field}' 必須是日期類型", field, value)
            return False
        
        # 如果是datetime，轉換為date
        if isinstance(value, datetime):
            value = value.date()
        
        # 檢查日期範圍
        if min_date is not None and value < min_date:
            self.add_error(f"欄位 '{field}' 不能早於 {min_date}", field, value)
            return False
        
        if max_date is not None and value > max_date:
            self.add_error(f"欄位 '{field}' 不能晚於 {max_date}", field, value)
            return False
        
        return True
    
    def validate_choice_field(self, data: Dict[str, Any], field: str,
                            choices: List[Any]) -> bool:
        """
        驗證選擇欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            choices: 可選值列表
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if value not in choices:
            self.add_error(f"欄位 '{field}' 的值必須是以下之一: {choices}", field, value)
            return False
        
        return True
    
    def validate_list_field(self, data: Dict[str, Any], field: str,
                          min_length: int = None, max_length: int = None,
                          item_validator: callable = None) -> bool:
        """
        驗證列表欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            min_length: 最小長度
            max_length: 最大長度
            item_validator: 項目驗證函數
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if not isinstance(value, list):
            self.add_error(f"欄位 '{field}' 必須是列表類型", field, value)
            return False
        
        # 檢查長度
        if min_length is not None and len(value) < min_length:
            self.add_error(f"欄位 '{field}' 長度不能少於 {min_length} 個項目", field, value)
            return False
        
        if max_length is not None and len(value) > max_length:
            self.add_error(f"欄位 '{field}' 長度不能超過 {max_length} 個項目", field, value)
            return False
        
        # 驗證每個項目
        if item_validator is not None:
            for i, item in enumerate(value):
                if not item_validator(item):
                    self.add_error(f"欄位 '{field}' 第 {i+1} 個項目驗證失敗", f"{field}[{i}]", item)
                    return False
        
        return True
    
    def validate_dict_field(self, data: Dict[str, Any], field: str,
                           required_keys: List[str] = None,
                           key_validator: callable = None,
                           value_validator: callable = None) -> bool:
        """
        驗證字典欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            required_keys: 必填鍵列表
            key_validator: 鍵驗證函數
            value_validator: 值驗證函數
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_required_field(data, field):
            return False
        
        value = data[field]
        if not isinstance(value, dict):
            self.add_error(f"欄位 '{field}' 必須是字典類型", field, value)
            return False
        
        # 檢查必填鍵
        if required_keys is not None:
            for key in required_keys:
                if key not in value:
                    self.add_error(f"欄位 '{field}' 缺少必填鍵 '{key}'", field, value)
                    return False
        
        # 驗證鍵和值
        for key, val in value.items():
            if key_validator is not None and not key_validator(key):
                self.add_error(f"欄位 '{field}' 的鍵 '{key}' 驗證失敗", f"{field}.{key}", key)
                return False
            
            if value_validator is not None and not value_validator(val):
                self.add_error(f"欄位 '{field}' 的值 '{val}' 驗證失敗", f"{field}.{key}", val)
                return False
        
        return True
    
    def validate_percentage_field(self, data: Dict[str, Any], field: str,
                                min_value: float = 0.0, max_value: float = 100.0) -> bool:
        """
        驗證百分比欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            min_value: 最小值（0-100）
            max_value: 最大值（0-100）
            
        Returns:
            bool: 驗證是否通過
        """
        if not self.validate_float_field(data, field, min_value, max_value):
            return False
        
        value = data[field]
        if not (0.0 <= value <= 100.0):
            self.add_error(f"欄位 '{field}' 必須在 0-100 之間", field, value)
            return False
        
        return True
    
    def validate_email_field(self, data: Dict[str, Any], field: str) -> bool:
        """
        驗證電子郵件欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            
        Returns:
            bool: 驗證是否通過
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return self.validate_string_field(data, field, pattern=email_pattern)
    
    def validate_phone_field(self, data: Dict[str, Any], field: str) -> bool:
        """
        驗證電話號碼欄位
        
        Args:
            data: 數據字典
            field: 欄位名稱
            
        Returns:
            bool: 驗證是否通過
        """
        phone_pattern = r'^[\d\s\-\+\(\)]+$'
        return self.validate_string_field(data, field, pattern=phone_pattern)
    
    def cross_validate_fields(self, data: Dict[str, Any], 
                            validation_rules: List[Tuple[str, str, Any]]) -> bool:
        """
        跨欄位驗證
        
        Args:
            data: 數據字典
            validation_rules: 驗證規則列表，格式為 [(field1, operator, field2), ...]
            
        Returns:
            bool: 驗證是否通過
        """
        for field1, operator, field2 in validation_rules:
            if field1 not in data or field2 not in data:
                continue
            
            value1 = data[field1]
            value2 = data[field2]
            
            if operator == '>':
                if not (isinstance(value1, (int, float)) and isinstance(value2, (int, float)) and value1 > value2):
                    self.add_error(f"欄位 '{field1}' 必須大於 '{field2}'", field1, value1)
                    return False
            
            elif operator == '>=':
                if not (isinstance(value1, (int, float)) and isinstance(value2, (int, float)) and value1 >= value2):
                    self.add_error(f"欄位 '{field1}' 必須大於等於 '{field2}'", field1, value1)
                    return False
            
            elif operator == '<':
                if not (isinstance(value1, (int, float)) and isinstance(value2, (int, float)) and value1 < value2):
                    self.add_error(f"欄位 '{field1}' 必須小於 '{field2}'", field1, value1)
                    return False
            
            elif operator == '<=':
                if not (isinstance(value1, (int, float)) and isinstance(value2, (int, float)) and value1 <= value2):
                    self.add_error(f"欄位 '{field1}' 必須小於等於 '{field2}'", field1, value1)
                    return False
            
            elif operator == '==':
                if value1 != value2:
                    self.add_error(f"欄位 '{field1}' 必須等於 '{field2}'", field1, value1)
                    return False
        
        return True 