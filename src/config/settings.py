"""
Merkezi Konfigürasyon Yönetimi
SOLID Prensibi: Tüm ayarlar bir yerde, hiç magic string yok
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv


# .env dosyasını yükle
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


@dataclass
class DatabaseConfig:
    """Veritabanı Konfigürasyonu"""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///haber_analizi.db"))
    timeout: int = int(os.getenv("DATABASE_TIMEOUT", "30"))
    
    @property
    def db_path(self) -> str:
        """SQLite dosya yolu"""
        return self.url.replace("sqlite:///", "")


@dataclass
class APIConfig:
    """API Anahtarları ve Limitleri"""
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    news_api_key: str = field(default_factory=lambda: os.getenv("NEWS_API_KEY", ""))
    
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    rate_limit: int = int(os.getenv("NEWSAPI_RATE_LIMIT", "1000"))
    
    def validate(self) -> bool:
        """Gerekli API keyleri kontrol et"""
        required = ["google_api_key", "news_api_key"]
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            print(f"⚠️ Eksik API keyleri: {', '.join(missing)}")
            return False
        return True


@dataclass
class MLModelsConfig:
    """Makine Öğrenmesi Modelleri"""
    sentiment_model: str = field(
        default_factory=lambda: os.getenv(
            "SENTIMENT_MODEL", 
            "distilbert-base-uncased-finetuned-sst-2-english"
        )
    )
    classifier_model: str = field(
        default_factory=lambda: os.getenv(
            "CLASSIFIER_MODEL",
            "valhalla/distilbart-mnli-12-1"
        )
    )
    summarizer_model: str = field(
        default_factory=lambda: os.getenv(
            "SUMMARIZER_MODEL",
            "facebook/bart-large-cnn"
        )
    )


@dataclass
class RiskThresholdsConfig:
    """Risk Seviyeleri Eşikleri"""
    critical: float = -0.7
    warning: float = -0.4
    normal: float = 0.0
    positive: float = 0.5
    
    def get_risk_level(self, score: float) -> str:
        """Skora göre risk seviyesi döndür"""
        if score <= self.critical:
            return "🔴 KRİTİK"
        elif score <= self.warning:
            return "🟠 UYARI"
        elif score < self.normal:
            return "🟡 NORMAL"
        elif score < self.positive:
            return "🟢 POZİTİF"
        else:
            return "🟢 ÇOK POZİTİF"


@dataclass
class CacheConfig:
    """Cache Ayarları"""
    enabled: bool = field(
        default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true"
    )
    timeout_seconds: int = int(os.getenv("CACHE_TIMEOUT", "300"))


@dataclass
class LoggingConfig:
    """Logging Konfigürasyonu"""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    dir_path: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "logs")))
    
    def __post_init__(self):
        """Log klasörünü oluştur"""
        self.dir_path.mkdir(exist_ok=True)
    
    @property
    def backend_log_path(self) -> Path:
        return self.dir_path / "backend.log"
    
    @property
    def frontend_log_path(self) -> Path:
        return self.dir_path / "frontend.log"


@dataclass
class CountriesConfig:
    """İzlenen Ülkeler"""
    codes: Dict[str, str] = field(default_factory=lambda: {
        'us': 'United States',
        'kr': 'South Korea',
        'fr': 'France',
        'es': 'Spain',
        'it': 'Italy',
        'gr': 'Greece'
    })
    iso_codes: Dict[str, str] = field(default_factory=lambda: {
        'us': 'USA',
        'kr': 'KOR',
        'gr': 'GRC',
        'it': 'ITA',
        'fr': 'FRA',
        'es': 'ESP'
    })


@dataclass
class NewsConfig:
    """Haber Kategorileri ve Ayarları"""
    categories: List[str] = field(default_factory=lambda: [
        "Artificial Intelligence",
        "Cybersecurity",
        "Hardware & Chips",
        "Crypto & Fintech",
        "Electric Vehicles",
        "Software Development",
        "Cloud Computing",
        "Mobile Technology"
    ])
    default_category: str = "Uncategorized"


@dataclass
class SecurityConfig:
    """Güvenlik Ayarları"""
    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "change-this-in-production")
    )
    streamlit_password: str = field(
        default_factory=lambda: os.getenv("STREAMLIT_PASSWORD", "")
    )
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    debug: bool = field(default=False)
    
    def __post_init__(self):
        self.debug = self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@dataclass
class MonitoringConfig:
    """İzleme (Monitoring) Ayarları"""
    enabled: bool = field(
        default_factory=lambda: os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    )
    port: int = int(os.getenv("MONITORING_PORT", "8000"))


class Settings:
    """Ana Konfigürasyon Sınıfı - Singleton Pattern"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.ml_models = MLModelsConfig()
        self.risk_thresholds = RiskThresholdsConfig()
        self.cache = CacheConfig()
        self.logging = LoggingConfig()
        self.countries = CountriesConfig()
        self.news = NewsConfig()
        self.security = SecurityConfig()
        self.monitoring = MonitoringConfig()
    
    def validate_all(self) -> bool:
        """Tüm konfigürasyonları valida et"""
        return self.api.validate()
    
    def get_config_summary(self) -> Dict:
        """Konfigürasyon özetini döndür"""
        return {
            "environment": self.security.environment,
            "database": self.database.db_path,
            "ml_models": {
                "sentiment": self.ml_models.sentiment_model,
                "classifier": self.ml_models.classifier_model,
            },
            "cache_enabled": self.cache.enabled,
            "monitoring_enabled": self.monitoring.enabled,
        }


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Settings singleton'ı al"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
