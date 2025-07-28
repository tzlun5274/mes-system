# 基礎快取管理
# 本檔案定義了報表系統的基礎快取管理類別
# 提供統一的快取介面和清理機制

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import logging
import hashlib
import json

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class BaseCache(ABC):
    """報表快取管理基礎類別 - 所有快取管理的基礎類別"""
    
    def __init__(self):
        """初始化快取管理器"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_prefix = 'report_'
        self.default_timeout = 24 * 60 * 60  # 24小時
        
    @abstractmethod
    def get_cache_key(self, **kwargs) -> str:
        """
        生成快取鍵值（抽象方法）
        
        Args:
            **kwargs: 快取參數
            
        Returns:
            str: 快取鍵值
        """
        raise NotImplementedError
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        取得快取數據
        
        Args:
            key: 快取鍵值
            default: 預設值
            
        Returns:
            Any: 快取數據或預設值
        """
        try:
            cached_data = cache.get(key)
            if cached_data is not None:
                self.logger.info(f"快取命中: {key}")
            return cached_data if cached_data is not None else default
        except Exception as e:
            self.logger.error(f"取得快取失敗: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """
        設定快取數據
        
        Args:
            key: 快取鍵值
            value: 要快取的數據
            timeout: 過期時間（秒）
            
        Returns:
            bool: 是否成功設定
        """
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            cache.set(key, value, timeout)
            self.logger.info(f"快取已設定: {key}, 過期時間: {timeout}秒")
            return True
        except Exception as e:
            self.logger.error(f"設定快取失敗: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        刪除快取數據
        
        Args:
            key: 快取鍵值
            
        Returns:
            bool: 是否成功刪除
        """
        try:
            cache.delete(key)
            self.logger.info(f"快取已刪除: {key}")
            return True
        except Exception as e:
            self.logger.error(f"刪除快取失敗: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        檢查快取是否存在
        
        Args:
            key: 快取鍵值
            
        Returns:
            bool: 快取是否存在
        """
        try:
            return cache.get(key) is not None
        except Exception as e:
            self.logger.error(f"檢查快取存在失敗: {e}")
            return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量取得快取數據
        
        Args:
            keys: 快取鍵值列表
            
        Returns:
            Dict[str, Any]: 快取數據字典
        """
        try:
            result = cache.get_many(keys)
            self.logger.info(f"批量取得快取: {len(result)}/{len(keys)} 個命中")
            return result
        except Exception as e:
            self.logger.error(f"批量取得快取失敗: {e}")
            return {}
    
    def set_many(self, data: Dict[str, Any], timeout: int = None) -> bool:
        """
        批量設定快取數據
        
        Args:
            data: 快取數據字典
            timeout: 過期時間（秒）
            
        Returns:
            bool: 是否成功設定
        """
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            cache.set_many(data, timeout)
            self.logger.info(f"批量設定快取: {len(data)} 個項目")
            return True
        except Exception as e:
            self.logger.error(f"批量設定快取失敗: {e}")
            return False
    
    def delete_many(self, keys: List[str]) -> bool:
        """
        批量刪除快取數據
        
        Args:
            keys: 快取鍵值列表
            
        Returns:
            bool: 是否成功刪除
        """
        try:
            cache.delete_many(keys)
            self.logger.info(f"批量刪除快取: {len(keys)} 個項目")
            return True
        except Exception as e:
            self.logger.error(f"批量刪除快取失敗: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        按模式清除快取
        
        Args:
            pattern: 快取鍵值模式
            
        Returns:
            int: 清除的快取數量
        """
        try:
            # 注意：Django的cache框架不支援模式匹配
            # 這裡需要根據具體的快取後端實作
            self.logger.warning("模式清除快取功能需要根據快取後端實作")
            return 0
        except Exception as e:
            self.logger.error(f"模式清除快取失敗: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """
        清除所有快取
        
        Returns:
            bool: 是否成功清除
        """
        try:
            cache.clear()
            self.logger.info("所有快取已清除")
            return True
        except Exception as e:
            self.logger.error(f"清除所有快取失敗: {e}")
            return False
    
    def get_cache_info(self, key: str) -> Dict[str, Any]:
        """
        取得快取資訊
        
        Args:
            key: 快取鍵值
            
        Returns:
            Dict[str, Any]: 快取資訊
        """
        try:
            # 注意：Django的cache框架不提供詳細的快取資訊
            # 這裡提供基本的資訊
            exists = self.exists(key)
            info = {
                'key': key,
                'exists': exists,
                'checked_at': datetime.now().isoformat()
            }
            
            if exists:
                info['value_type'] = type(self.get(key)).__name__
            
            return info
        except Exception as e:
            self.logger.error(f"取得快取資訊失敗: {e}")
            return {'error': str(e)}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        取得快取統計資訊
        
        Returns:
            Dict[str, Any]: 快取統計資訊
        """
        try:
            # 注意：Django的cache框架不提供統計資訊
            # 這裡提供基本的統計
            stats = {
                'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
                'default_timeout': self.default_timeout,
                'cache_prefix': self.cache_prefix,
                'checked_at': datetime.now().isoformat()
            }
            
            return stats
        except Exception as e:
            self.logger.error(f"取得快取統計失敗: {e}")
            return {'error': str(e)}
    
    def generate_hash_key(self, data: Any) -> str:
        """
        生成數據的雜湊鍵值
        
        Args:
            data: 要雜湊的數據
            
        Returns:
            str: 雜湊鍵值
        """
        try:
            if isinstance(data, str):
                data_str = data
            else:
                data_str = json.dumps(data, sort_keys=True, default=str)
            
            hash_object = hashlib.md5(data_str.encode())
            return hash_object.hexdigest()
        except Exception as e:
            self.logger.error(f"生成雜湊鍵值失敗: {e}")
            return str(hash(data))
    
    def cache_function_result(self, func: callable, *args, 
                            timeout: int = None, 
                            key_prefix: str = None,
                            **kwargs) -> Any:
        """
        快取函數執行結果
        
        Args:
            func: 要執行的函數
            *args: 函數參數
            timeout: 過期時間（秒）
            key_prefix: 鍵值前綴
            **kwargs: 函數關鍵字參數
            
        Returns:
            Any: 函數執行結果
        """
        try:
            # 生成快取鍵值
            if key_prefix is None:
                key_prefix = func.__name__
            
            key_data = {
                'prefix': key_prefix,
                'args': args,
                'kwargs': kwargs
            }
            
            cache_key = self.get_cache_key(**key_data)
            
            # 嘗試從快取取得結果
            cached_result = self.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 執行函數
            result = func(*args, **kwargs)
            
            # 快取結果
            self.set(cache_key, result, timeout)
            
            return result
            
        except Exception as e:
            self.logger.error(f"快取函數結果失敗: {e}")
            # 如果快取失敗，直接執行函數
            return func(*args, **kwargs)
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        按模式使快取失效
        
        Args:
            pattern: 快取鍵值模式
            
        Returns:
            int: 失效的快取數量
        """
        try:
            # 這裡需要根據具體的快取後端實作
            # 例如使用Redis的SCAN命令
            self.logger.warning("模式失效快取功能需要根據快取後端實作")
            return 0
        except Exception as e:
            self.logger.error(f"模式失效快取失敗: {e}")
            return 0
    
    def set_with_tags(self, key: str, value: Any, tags: List[str], 
                     timeout: int = None) -> bool:
        """
        設定帶標籤的快取數據
        
        Args:
            key: 快取鍵值
            value: 要快取的數據
            tags: 標籤列表
            timeout: 過期時間（秒）
            
        Returns:
            bool: 是否成功設定
        """
        try:
            # 儲存數據和標籤
            cache_data = {
                'value': value,
                'tags': tags,
                'created_at': datetime.now().isoformat()
            }
            
            return self.set(key, cache_data, timeout)
            
        except Exception as e:
            self.logger.error(f"設定帶標籤快取失敗: {e}")
            return False
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        按標籤使快取失效
        
        Args:
            tags: 標籤列表
            
        Returns:
            int: 失效的快取數量
        """
        try:
            # 這裡需要實作標籤查詢邏輯
            # 可能需要額外的索引結構
            self.logger.warning("標籤失效快取功能需要額外的索引結構")
            return 0
        except Exception as e:
            self.logger.error(f"標籤失效快取失敗: {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """
        清理過期快取
        
        Returns:
            int: 清理的快取數量
        """
        try:
            # Django的cache框架會自動清理過期快取
            # 這裡可以實作額外的清理邏輯
            self.logger.info("快取自動清理已啟用")
            return 0
        except Exception as e:
            self.logger.error(f"清理過期快取失敗: {e}")
            return 0
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        取得快取記憶體使用情況
        
        Returns:
            Dict[str, Any]: 記憶體使用資訊
        """
        try:
            # 這裡需要根據具體的快取後端實作
            # 例如使用Redis的INFO命令
            self.logger.warning("記憶體使用查詢功能需要根據快取後端實作")
            return {
                'backend': 'unknown',
                'memory_usage': 'unknown',
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"取得記憶體使用失敗: {e}")
            return {'error': str(e)} 