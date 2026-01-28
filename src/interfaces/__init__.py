"""
Services İçin Interface Tanımları
SOLID: Dependency Inversion Principle
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class NewsSourceInterface(ABC):
    """Haber kaynağı interface'i - yeni kaynak eklemek kolay"""
    
    @abstractmethod
    def fetch_news(self, country: str) -> List[Dict[str, Any]]:
        """Belirtilen ülke için haberleri al"""
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """API kimlik bilgilerini doğrula"""
        pass


class SentimentAnalyzerInterface(ABC):
    """Sentiment analiz interface'i"""
    
    @abstractmethod
    def analyze(self, text: str) -> float:
        """
        Metni analiz et ve -1 ile +1 arası skor döndür
        -1: Çok negatif
        0: Nötr
        +1: Çok pozitif
        """
        pass


class CategoryClassifierInterface(ABC):
    """Kategori sınıflandırıcı interface'i"""
    
    @abstractmethod
    def classify(self, text: str) -> str:
        """Metni kategorize et"""
        pass


class TextSummarizerInterface(ABC):
    """Metin özetleme interface'i"""
    
    @abstractmethod
    def summarize(self, texts: List[str], max_length: int = 150) -> str:
        """Metinleri özetle"""
        pass


class LoggerInterface(ABC):
    """Logger interface'i"""
    
    @abstractmethod
    def info(self, message: str): pass
    
    @abstractmethod
    def warning(self, message: str): pass
    
    @abstractmethod
    def error(self, message: str): pass
    
    @abstractmethod
    def debug(self, message: str): pass
