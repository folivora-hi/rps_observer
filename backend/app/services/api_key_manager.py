"""
API 金鑰管理器

功能：
- 管理多個 API 金鑰
- 實現負載均衡
- 處理 API 金鑰錯誤和限流
- 提供金鑰輪換機制
"""

import random
import time
from typing import List, Optional, Dict, Any
from threading import Lock
from ..core.config import settings
import os


class APIKeyManager:
    """API 金鑰管理器，支援多個金鑰的負載均衡和錯誤處理"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.keys: List[str] = []
        self.key_status: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self._load_keys()
    
    def _load_keys(self):
        """載入 API 金鑰"""
        if self.provider == "openai":
            self.keys = settings.OPENAI_API_KEYS.copy()
        elif self.provider == "deepseek-official":
            if settings.DEEPSEEK_API_KEY:
                self.keys = [settings.DEEPSEEK_API_KEY]
        elif self.provider == "openrouter":
            if os.getenv("OPENROUTER_API_KEY"):
                self.keys = [os.getenv("OPENROUTER_API_KEY")]
        
        # 初始化金鑰狀態
        for key in self.keys:
            self.key_status[key] = {
                'last_used': 0,
                'error_count': 0,
                'last_error': None,
                'rate_limit_reset': 0,
                'is_available': True
            }
    
    def get_available_key(self) -> Optional[str]:
        """獲取可用的 API 金鑰"""
        with self.lock:
            available_keys = []
            current_time = time.time()
            
            for key in self.keys:
                status = self.key_status[key]
                
                # 檢查金鑰是否可用
                if not status['is_available']:
                    continue
                
                # 檢查是否在限流冷卻期
                if current_time < status['rate_limit_reset']:
                    continue
                
                # 檢查錯誤次數
                if status['error_count'] >= 3:
                    # 重置錯誤計數（給金鑰一個重試機會）
                    status['error_count'] = 0
                    status['last_error'] = None
                
                available_keys.append(key)
            
            if not available_keys:
                return None
            
            # 選擇最久未使用的金鑰（簡單的負載均衡）
            selected_key = min(available_keys, 
                             key=lambda k: self.key_status[k]['last_used'])
            
            # 更新使用時間
            self.key_status[selected_key]['last_used'] = current_time
            
            return selected_key
    
    def mark_key_error(self, key: str, error: Exception, reset_time: int = 60):
        """標記金鑰錯誤"""
        with self.lock:
            if key in self.key_status:
                status = self.key_status[key]
                status['error_count'] += 1
                status['last_error'] = str(error)
                status['rate_limit_reset'] = time.time() + reset_time
                
                # 如果錯誤次數過多，暫時禁用金鑰
                if status['error_count'] >= 5:
                    status['is_available'] = False
                    status['rate_limit_reset'] = time.time() + 300  # 5分鐘冷卻
    
    def mark_key_success(self, key: str):
        """標記金鑰成功使用"""
        with self.lock:
            if key in self.key_status:
                status = self.key_status[key]
                status['error_count'] = 0
                status['last_error'] = None
                status['is_available'] = True
    
    def get_key_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有金鑰狀態"""
        with self.lock:
            return self.key_status.copy()
    
    def reset_all_keys(self):
        """重置所有金鑰狀態"""
        with self.lock:
            for key in self.keys:
                self.key_status[key] = {
                    'last_used': 0,
                    'error_count': 0,
                    'last_error': None,
                    'rate_limit_reset': 0,
                    'is_available': True
                }


# 全局 API 金鑰管理器實例
_openai_key_manager = None
_deepseek_key_manager = None
_openrouter_key_manager = None


def get_key_manager(provider: str) -> Optional[APIKeyManager]:
    """獲取指定提供者的 API 金鑰管理器"""
    global _openai_key_manager, _deepseek_key_manager, _openrouter_key_manager
    
    if provider == "openai":
        if _openai_key_manager is None:
            _openai_key_manager = APIKeyManager("openai")
        return _openai_key_manager
    elif provider == "deepseek-official":
        if _deepseek_key_manager is None:
            _deepseek_key_manager = APIKeyManager("deepseek-official")
        return _deepseek_key_manager
    elif provider == "openrouter":
        if _openrouter_key_manager is None:
            _openrouter_key_manager = APIKeyManager("openrouter")
        return _openrouter_key_manager
    
    return None


def get_available_api_key(provider: str) -> Optional[str]:
    """獲取可用的 API 金鑰"""
    manager = get_key_manager(provider)
    if manager:
        return manager.get_available_key()
    return None


def mark_api_key_error(provider: str, key: str, error: Exception, reset_time: int = 60):
    """標記 API 金鑰錯誤"""
    manager = get_key_manager(provider)
    if manager:
        manager.mark_key_error(key, error, reset_time)


def mark_api_key_success(provider: str, key: str):
    """標記 API 金鑰成功使用"""
    manager = get_key_manager(provider)
    if manager:
        manager.mark_key_success(key)
