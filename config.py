"""
Aura Configuration Module
Tüm ortam değişkenlerini ve ayarları yönetir
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# .env dosyasını yükle
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

class Config:
    """Base Configuration"""
    
    # API Keys
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///haber_analizi.db")
    
    # Streamlit Security
    STREAMLIT_PASSWORD: str = os.getenv("STREAMLIT_PASSWORD", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Cache
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TIMEOUT: int = int(os.getenv("CACHE_TIMEOUT", "300"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)
    
    # API Rate Limits
    NEWSAPI_RATE_LIMIT: int = int(os.getenv("NEWSAPI_RATE_LIMIT", "1000"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # ML Models
    SENTIMENT_MODEL: str = os.getenv("SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")
    CLASSIFIER_MODEL: str = os.getenv("CLASSIFIER_MODEL", "valhalla/distilbart-mnli-12-1")
    
    # Monitoring
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    MONITORING_PORT: int = int(os.getenv("MONITORING_PORT", "8000"))
    
    # Countries
    COUNTRIES = {
        'us': 'United States',
        'kr': 'South Korea',
        'fr': 'France',
        'es': 'Spain',
        'it': 'Italy',
        'gr': 'Greece'
    }
    
    # News Categories
    NEWS_CATEGORIES = [
        "Artificial Intelligence",
        "Cybersecurity",
        "Hardware & Chips",
        "Crypto & Fintech",
        "Electric Vehicles",
        "Software Development",
        "Cloud Computing",
        "Mobile Technology"
    ]
    
    # Risk Thresholds
    CRITICAL_THRESHOLD = -0.7
    WARNING_THRESHOLD = -0.4
    POSITIVE_THRESHOLD = 0.5
    
    @classmethod
    def validate_keys(cls) -> bool:
        """Gerekli API keylerin var olup olmadığını kontrol et"""
        try:
            required_keys = ["GOOGLE_API_KEY", "NEWS_API_KEY"]
            missing = [key for key in required_keys if not getattr(cls, key)]
            
            if missing:
                print(f"⚠️ Eksik API keyleri: {', '.join(missing)}")
                print("ℹ️ Program sınırlı işlevsellikle devam edecektir.")
                return False
            return True
        except Exception as e:
            print(f"❌ Anahtar doğrulama hatası: {e}")
            return False
    
    @classmethod
    def get_google_api_key(cls) -> str:
        """Google API anahtarını güvenli şekilde al"""
        try:
            key = cls.GOOGLE_API_KEY
            if not key or key == "your_google_api_key_here":
                return ""
            return key
        except Exception as e:
            print(f"❌ Google API anahtarı okunurken hata: {e}")
            return ""
    
    @classmethod
    def get_news_api_key(cls) -> str:
        """News API anahtarını güvenli şekilde al"""
        try:
            key = cls.NEWS_API_KEY
            if not key or key == "your_newsapi_key_here":
                return ""
            return key
        except Exception as e:
            print(f"❌ News API anahtarı okunurken hata: {e}")
            return ""


class DevelopmentConfig(Config):
    """Development Configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production Configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing Configuration"""
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"


# Ortama göre config seç
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config() -> Config:
    """Geçerli ortam için config döndür"""
    env = os.getenv("ENVIRONMENT", "development")
    return config_by_name.get(env, DevelopmentConfig)


# Global config instance
config = get_config()
