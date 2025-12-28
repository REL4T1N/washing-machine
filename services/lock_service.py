import time
from typing import Dict

from config.config import LOCK_TIMEOUT

class LockService:
    """Сервис для управления блокировками"""
    
    _locks: Dict[str, float] = {}
    
    @classmethod
    def acquire_lock(cls, key: str) -> bool:
        """Пытается получить блокировку"""
        current_time = time.time()
        
        # Очищаем устаревшие блокировки
        expired_keys = [k for k, v in LOCK_TIMEOUT if current_time - v > LOCK_TIMEOUT]
        
        for key_to_remove in expired_keys:
            cls._locks.pop(key_to_remove, None)
        
        # Проверяем, заблокировано ли
        if key in cls._locks:
            lock_age = current_time - cls._locks[key]
            if lock_age < LOCK_TIMEOUT:
                return False
        
        # Устанавливаем блокировку
        cls._locks[key] = current_time
        return True
    
    @classmethod
    def release_lock(cls, key: str):
        """Освобождает блокировку"""
        cls._locks.pop(key, None)
    
    @classmethod
    def is_locked(cls, key: str) -> bool:
        """Проверяет, заблокирован ли ключ"""
        if key not in cls._locks:
            return False
        
        current_time = time.time()
        lock_age = current_time - cls._locks[key]
        
        if lock_age > LOCK_TIMEOUT:
            cls._locks.pop(key, None)
            return False
        
        return True