"""
main.py - SOLID Prensipleriyle Refactored Örnek
Bu dosya, IMPROVEMENT_GUIDE.md ve REFACTORING_EXAMPLES.py'deki prensipleri uygular
"""
import logging
import sys
from typing import List, Dict, Any

# Yeni mimariden import et
from src.config import get_settings
from src.database import SQLiteNewsRepository
from src.services import NewsAnalyzer
from src.interfaces import SentimentAnalyzerInterface, CategoryClassifierInterface
from src.utils import CacheManager


# ============================================================================
# TRANSFORMER IMPLEMENTASYONLARI (Interface'leri gerçekleştir)
# ============================================================================

class DistilBERTSentimentAnalyzer(SentimentAnalyzerInterface):
    """BERT-tabanlı sentiment analizi"""
    
    def __init__(self):
        try:
            from transformers import pipeline
            import torch
            
            # GPU varsa kullan
            device = 0 if torch.cuda.is_available() else -1
            
            self.pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=device
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("✓ BERT Sentiment analyzer yüklendi")
        except ImportError as e:
            raise ImportError("Transformers kütüphanesi gerekli: pip install transformers")
    
    def analyze(self, text: str) -> float:
        """
        Text'in duygu skorunu hesapla
        -1: Çok negatif ... +1: Çok pozitif
        """
        try:
            # Maksimum uzunluğu kontrol et
            text_truncated = text[:512] if len(text) > 512 else text
            
            result = self.pipeline(text_truncated)[0]
            
            # POSITIVE → 1.0, NEGATIVE → -1.0 
            score = 1.0 if result['label'] == 'POSITIVE' else -1.0
            
            # Confidence ekle
            confidence = result['score']
            return score * confidence
        
        except Exception as e:
            self.logger.error(f"Sentiment analiz hatası: {e}")
            return 0.0  # Nötr varsayılan


class ZeroShotCategoryClassifier(CategoryClassifierInterface):
    """Zero-shot classification ile kategori sınıflandır"""
    
    def __init__(self, categories: List[str]):
        try:
            from transformers import pipeline
            
            self.pipeline = pipeline(
                "zero-shot-classification",
                model="valhalla/distilbart-mnli-12-1"
            )
            self.categories = categories
            self.logger = logging.getLogger(__name__)
            self.logger.info("✓ Zero-shot classifier yüklendi")
        except ImportError:
            raise ImportError("Transformers kütüphanesi gerekli")
    
    def classify(self, text: str) -> str:
        """Metni kategorilere göre sınıflandır"""
        try:
            result = self.pipeline(
                text[:512],
                self.categories,
                multi_class=False
            )
            return result['labels'][0]
        except Exception as e:
            self.logger.error(f"Classification hatası: {e}")
            return "Unknown"


class NewsAPIFetcher:
    """NewsAPI'den haber çek"""
    
    def __init__(self, api_key: str):
        import requests
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.logger = logging.getLogger(__name__)
    
    def fetch_news(self, country: str, query: str = "technology") -> List[Dict[str, Any]]:
        """Belirtilen ülke için haberleri çek"""
        try:
            import requests
            
            # ISO country codes mapping
            country_mapping = {
                'us': 'us', 'kr': 'kr', 'fr': 'fr',
                'es': 'es', 'it': 'it', 'gr': 'gr'
            }
            
            country_code = country_mapping.get(country, country)
            
            params = {
                'country': country_code,
                'q': query,
                'apiKey': self.api_key,
                'pageSize': 30,
                'sortBy': 'publishedAt'
            }
            
            response = requests.get(f"{self.base_url}/everything", params=params, timeout=30)
            response.raise_for_status()
            
            articles = response.json().get('articles', [])
            
            # Normalize format
            normalized = []
            for article in articles:
                normalized.append({
                    'ulke': country,
                    'baslik': article.get('title', ''),
                    'url': article.get('url', ''),
                    'kaynak': article.get('source', {}).get('name', 'NewsAPI'),
                    'tarih': article.get('publishedAt', '').split('T')[0]
                })
            
            self.logger.info(f"✓ {len(normalized)} haber çekildi ({country})")
            return normalized
        
        except Exception as e:
            self.logger.error(f"✗ NewsAPI hatası ({country}): {e}")
            return []


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Ana işlem: Fetch → Analyze → Store"""
    
    # 1. SETUP
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Konfigürasyonu valida et
    if not settings.validate_all():
        logger.error("⚠️ Gerekli API keyleri eksik! .env dosyasını kontrol edin")
        return False
    
    logger.info(f"🚀 {settings.security.environment.upper()} modunda başlatılıyor")
    
    # 2. DATABASE INITIALIZE
    repository = SQLiteNewsRepository(
        db_path=settings.database.db_path,
        logger=logger
    )
    
    if not repository.init_database():
        logger.error("✗ Veritabanı başlatılamadı")
        return False
    
    # 3. MODELS LOAD
    logger.info("📚 AI modelleri yükleniyor...")
    try:
        sentiment_analyzer = DistilBERTSentimentAnalyzer()
        category_classifier = ZeroShotCategoryClassifier(
            settings.news.categories
        )
    except ImportError as e:
        logger.error(f"✗ Model yükleme hatası: {e}")
        return False
    
    # 4. ANALYZER SETUP
    analyzer = NewsAnalyzer(
        sentiment_analyzer=sentiment_analyzer,
        category_classifier=category_classifier,
        logger=logger
    )
    
    # 5. NEWS FETCHING
    logger.info("🌐 Haberler çekiliyor...")
    
    news_fetcher = NewsAPIFetcher(settings.api.news_api_key)
    all_raw_news: List[Dict[str, Any]] = []
    
    for country in settings.countries.codes.keys():
        raw_news = news_fetcher.fetch_news(country)
        all_raw_news.extend(raw_news)
    
    if not all_raw_news:
        logger.warning("⚠️ Haber bulunamadı")
        return False
    
    logger.info(f"✓ Toplam {len(all_raw_news)} haber çekildi")
    
    # 6. ANALYSIS
    logger.info("🔍 Haberler analiz ediliyor...")
    analyzed_news = analyzer.analyze_batch(all_raw_news)
    
    # 7. STORAGE
    logger.info("💾 Haberler kaydediliyor...")
    inserted_count = repository.add_news(analyzed_news)
    
    # 8. STATISTICS
    logger.info("\n📊 İSTATİSTİKLER:")
    logger.info(f"  Toplam analiz edilen: {len(analyzed_news)}")
    logger.info(f"  Başarıyla kaydedilen: {inserted_count}")
    
    # Ülke istatistikleri
    logger.info("\n🌍 ÜLKE DURUM RAPORU:")
    for country in settings.countries.codes.keys():
        stats = analyzer.get_country_sentiment(analyzed_news, country)
        country_name = settings.countries.codes.get(country, country)
        logger.info(
            f"  {country_name:15} | "
            f"Avg Score: {stats['avg_score']:+.2f} | "
            f"Risk: {stats['risk_level']} | "
            f"Haber: {stats['total_news']}"
        )
    
    logger.info("\n✅ İşlem tamamlandı!")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Kullanıcı tarafından durduruldu")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Kritik hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
