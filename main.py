"""
MIMARISI:
  main_refactored.py
  ├─ SentimentAnalyzerInterface
  │  └─ DistilBERTSentimentAnalyzer.analyze(text) → float
  ├─ CategoryClassifierInterface
  │  └─ ZeroShotCategoryClassifier.classify(text) → str
  ├─ NewsSourceInterface
  │  └─ NewsAPIFetcher.fetch_news(country) → List[Dict]
  ├─ NewsAnalyzer (Business Logic - DI)
  │  └─ analyze_batch(news_list) → List[Dict]
  └─ SQLiteNewsRepository
     ├─ init_database() → bool
     └─ add_news(news_list) → int
"""
import logging
import sys
from typing import List, Dict, Any
import requests

# Yeni mimariden import et
from src.config import get_settings
from src.database import SQLiteNewsRepository
from src.services import NewsAnalyzer
from src.interfaces import SentimentAnalyzerInterface, CategoryClassifierInterface

class DistilBERTSentimentAnalyzer(SentimentAnalyzerInterface):
    """BERT-tabanlı sentiment analizi"""
    
    def __init__(self):
        self.pipeline = None
        self.logger = logging.getLogger(__name__)
        
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
            self.logger.info("✓ BERT Sentiment analyzer yüklendi (GPU: %s)", device >= 0)
        except ImportError as e:
            self.logger.warning("⚠️ Transformers modeli yüklenemedi: %s", e)
            self.logger.warning("   Sentiment analizi -1 olarak ayarlanacaktır")
        except Exception as e:
            self.logger.error("✗ BERT yükleme hatası: %s", e)
            self.logger.warning("   Fallback: Sentiment = 0.0")
    
    def analyze(self, text: str) -> float:
        """
        Text'in duygu skorunu hesapla
        -1: Çok negatif ... +1: Çok pozitif
        """
        if not text or not isinstance(text, str):
            return 0.0
        
        if self.pipeline is None:
            self.logger.debug("Pipeline yüklenmemiş, 0.0 döndürülüyor")
            return 0.0
        
        try:
            # Maksimum uzunluğu kontrol et
            text_truncated = text[:512] if len(text) > 512 else text
            
            result = self.pipeline(text_truncated)[0]
            
            # POSITIVE → 1.0, NEGATIVE → -1.0 
            score = 1.0 if result['label'] == 'POSITIVE' else -1.0
            
            # Confidence ekle
            confidence = result['score']
            return round(score * confidence, 4)
        
        except Exception as e:
            self.logger.warning(f"Sentiment analiz hatası: {e}")
            return 0.0  # Nötr varsayılan


class ZeroShotCategoryClassifier(CategoryClassifierInterface):
    """Zero-shot classification ile kategori sınıflandır"""
    
    def __init__(self, categories: List[str]):
        self.pipeline = None
        self.categories = categories
        self.logger = logging.getLogger(__name__)
        
        try:
            from transformers import pipeline
            
            self.pipeline = pipeline(
                "zero-shot-classification",
                model="valhalla/distilbart-mnli-12-1"
            )
            self.logger.info("✓ Zero-shot classifier yüklendi")
        except ImportError as e:
            self.logger.warning("⚠️ Zero-shot classifier yüklenemedi: %s", e)
        except Exception as e:
            self.logger.error("✗ Classifier yükleme hatası: %s", e)
    
    def classify(self, text: str) -> str:
        """Metni kategorilere göre sınıflandır"""
        if not text or not isinstance(text, str):
            return "Unknown"
        
        if self.pipeline is None:
            self.logger.debug("Pipeline yüklenmemiş, 'Unknown' döndürülüyor")
            return "Unknown"
        
        try:
            result = self.pipeline(
                text[:512],
                self.categories,
                multi_class=False
            )
            return result['labels'][0] if result.get('labels') else "Unknown"
        except Exception as e:
            self.logger.warning(f"Classification hatası: {e}")
            return "Unknown"


class NewsAPIFetcher:
    """NewsAPI'den haber çek"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.logger = logging.getLogger(__name__)
        self.has_valid_key = bool(api_key and api_key != "your_newsapi_key_here")
    
    def fetch_news(self, country: str, query: str = "technology") -> List[Dict[str, Any]]:
        """Belirtilen ülke için haberleri çek"""
        if not self.has_valid_key:
            self.logger.warning("⚠️ NEWS_API_KEY eksik veya geçersiz (%s)", country)
            return []
        
        try:
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
            
            response = requests.get(
                f"{self.base_url}/everything", 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            
            articles = response.json().get('articles', [])
            
            # Normalize format
            normalized = []
            for article in articles:
                if article.get('title') and article.get('url'):
                    normalized.append({
                        'ulke': country,
                        'baslik': article.get('title', '')[:500],
                        'url': article.get('url', '')[:2000],
                        'kaynak': article.get('source', {}).get('name', 'NewsAPI')[:100],
                        'tarih': article.get('publishedAt', '').split('T')[0]
                    })
            
            self.logger.info(f"✓ {len(normalized)} haber çekildi ({country.upper()})")
            return normalized
        
        except requests.exceptions.Timeout:
            self.logger.error(f"✗ {country.upper()} API timeout")
            return []
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"✗ {country.upper()} ağ hatası: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"✗ {country.upper()} HTTP {e.response.status_code}")
            return []
        except Exception as e:
            self.logger.error(f"✗ {country.upper()} haber çekme hatası: {e}")
            return []


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Ana işlem: Fetch → Analyze → Store"""
    
    # 1. SETUP
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        settings = get_settings()
        logger.info("✓ Konfigürasyon yüklendi")
        
        # Validate essential settings
        if not hasattr(settings, 'database') or not hasattr(settings.database, 'db_path'):
            logger.error("✗ Veritabanı ayarları bulunamadı")
            return False
        if not hasattr(settings, 'api'):
            logger.error("✗ API ayarları bulunamadı")
            return False
        if not hasattr(settings, 'news') or not hasattr(settings.news, 'categories'):
            logger.error("✗ Haber kategorileri ayarlanmadı")
            return False
            
    except Exception as e:
        logger.error(f"✗ Konfigürasyon yükleme hatası: {e}")
        return False
    
    # 2. DATABASE INITIALIZE
    try:
        repository = SQLiteNewsRepository(
            db_path=settings.database.db_path,
            logger=logger
        )
        
        if not repository.init_database():
            logger.error("✗ Veritabanı başlatılamadı")
            return False
        logger.info("✓ Veritabanı hazırlandı")
    except Exception as e:
        logger.error(f"✗ Veritabanı hatası: {e}")
        return False
    
    # 3. MODELS LOAD
    logger.info("📚 AI modelleri yükleniyor...")
    try:
        sentiment_analyzer = DistilBERTSentimentAnalyzer()
        category_classifier = ZeroShotCategoryClassifier(
            settings.news.categories
        )
        logger.info("✓ AI modelleri hazırlandı")
    except Exception as e:
        logger.error(f"✗ Model yükleme hatası: {e}")
        logger.warning("   Program modelsiz (fallback mod) çalışacaktır")
    
    # 4. ANALYZER SETUP
    try:
        analyzer = NewsAnalyzer(
            sentiment_analyzer=sentiment_analyzer,
            category_classifier=category_classifier,
            logger=logger
        )
    except Exception as e:
        logger.error(f"✗ Analyzer başlatma hatası: {e}")
        return False
    
    # 5. NEWS FETCHING
    logger.info("🌐 Haberler çekiliyor...")
    
    try:
        # Validate settings.countries exists before accessing
        if not hasattr(settings, 'countries') or not hasattr(settings.countries, 'codes'):
            logger.error("✗ Ülke ayarları bulunamadı")
            return False
        
        news_fetcher = NewsAPIFetcher(settings.api.news_api_key)
        all_raw_news: List[Dict[str, Any]] = []
        
        for country in settings.countries.codes.keys():
            try:
                raw_news = news_fetcher.fetch_news(country)
                all_raw_news.extend(raw_news)
            except Exception as e:
                logger.warning(f"⚠️ {country.upper()} haber çekme hatası: {e}")
                continue
    except Exception as e:
        logger.error(f"✗ Haber çekme işlemi hatası: {e}")
        all_raw_news = []
    
    if not all_raw_news:
        logger.warning("⚠️ Haber bulunamadı - demo modunda çalışılacak")
        return False
    
    logger.info(f"✓ Toplam {len(all_raw_news)} haber çekildi")
    
    # 6. ANALYSIS
    logger.info("🔍 Haberler analiz ediliyor...")
    try:
        analyzed_news = analyzer.analyze_batch(all_raw_news)
        logger.info(f"✓ {len(analyzed_news)} haber analiz edildi")
    except Exception as e:
        logger.error(f"✗ Analiz hatası: {e}")
        analyzed_news = []
    
    if not analyzed_news:
        logger.warning("⚠️ Analiz yapılacak haber yok")
        return False
    
    # 7. STORAGE
    logger.info("💾 Haberler kaydediliyor...")
    try:
        inserted_count = repository.add_news(analyzed_news)
        logger.info(f"✓ {inserted_count} haber kaydedildi")
    except Exception as e:
        logger.error(f"✗ Haber kaydetme hatası: {e}")
        inserted_count = 0
    
    if inserted_count == 0:
        logger.warning("⚠️ Hiçbir haber kaydedilmedi")
        return False
    
    # 8. STATISTICS
    logger.info("\n" + "="*60)
    logger.info("📊 İSTATİSTİKLER")
    logger.info("="*60)
    logger.info(f"  Toplam çekilen:     {len(all_raw_news):>5}")
    logger.info(f"  Analiz edilen:      {len(analyzed_news):>5}")
    logger.info(f"  Başarıyla kaydedilen: {inserted_count:>5}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ İşlem tamamlandı başarıyla!")
    logger.info("="*60)
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
