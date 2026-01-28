"""
Utilities Modülü - Tekrarlı kodu DRY prensibiyle çıkart
"""
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import time


class CacheManager:
    """In-memory cache sistemi - TTL desteği"""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: Cache geçerlilik süresi (saniye)
        """
        self._cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if datetime.now() < expiry:
            return value
        else:
            del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Cache'e değer ekle"""
        expiry = datetime.now() + timedelta(seconds=ttl or self.ttl)
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Cache'i temizle"""
        self._cache.clear()
    
    def cached(self, ttl: Optional[int] = None):
        """Decorator: Fonksiyon sonucunu cache'le"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Cache key'i oluştur
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # Cache'de var mı kontrol et
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Cache'de yok, hesapla
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator


class ErrorHandler:
    """Ortak error handling - DRY prensibiyle hataları yönet"""
    
    @staticmethod
    def handle_api_error(func: Callable, logger: logging.Logger):
        """API çağrılarında hata yönetimi"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ConnectionError as e:
                logger.error(f"Bağlantı hatası: {str(e)}")
                raise
            except TimeoutError as e:
                logger.error(f"Zaman aşımı: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"API hatası: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    
    @staticmethod
    def retry(max_retries: int = 3, delay: float = 1.0):
        """Retry decorator - API çağrılarını yeniden dene"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                
            return wrapper
        return decorator


class DataValidator:
    """Veri doğrulama - Garbage in, garbage out sorunu çöz"""
    
    @staticmethod
    def validate_news_data(news: Dict[str, Any]) -> bool:
        """Haber verisi doğrulama"""
        required_fields = ['baslik', 'url', 'ulke']
        return all(field in news and news[field] for field in required_fields)
    
    @staticmethod
    def validate_sentiment_score(score: float) -> bool:
        """Sentiment skoru doğrulama (-1 ile +1 arası)"""
        return -1 <= score <= 1
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Metni temizle"""
        return text.strip().lower() if isinstance(text, str) else ""


# Global cache instance
global_cache = CacheManager(ttl_seconds=300)
