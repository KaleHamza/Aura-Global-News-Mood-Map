"""
Analyzer Service - SOLID Prensipleri Uygulanmış
SRP: Sadece analiz yapar, DB'ye yazmaz
DIP: Interface'lere bağlı, concrete class'lara değil
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..interfaces import (
    SentimentAnalyzerInterface,
    CategoryClassifierInterface,
    LoggerInterface
)
from ..config import get_settings


class NewsAnalyzer:
    """
    Haber analiz motoru - Temiz mimarinin örneği
    Sorumluluğu: Text analizi ve risk hesabı
    """
    
    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzerInterface,
        category_classifier: CategoryClassifierInterface,
        logger: Optional[logging.Logger] = None
    ):
        """
        Dependency Injection - Tüm bağımlılıklar dışarıdan gelir
        """
        self.sentiment = sentiment_analyzer
        self.classifier = category_classifier
        self.logger = logger or logging.getLogger(__name__)
        self.settings = get_settings()
    
    def analyze_news(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        Haberi analiz et (DB'ye yazmaz)
        
        Args:
            news: {
                'baslik': str,
                'url': str,
                'source': str,
                'country': str,
                'published_at': str
            }
        
        Returns:
            Analiz edilmiş haber + skor ve kategori
        """
        if not news or 'baslik' not in news:
            self.logger.warning("Geçersiz haber verisi")
            return news
        
        try:
            # Sentiment analizi
            sentiment_score = self.sentiment.analyze(news['baslik'])
            
            # Kategori sınıflandırması
            category = self.classifier.classify(news['baslik'])
            
            # Risk seviyesi hesapla
            risk_level = self.settings.risk_thresholds.get_risk_level(sentiment_score)
            
            # Analiz sonuçlarını ekle
            analyzed = {
                **news,
                'skor': sentiment_score,
                'kategori': category,
                'risk_seviyesi': risk_level,
                'analyzed_at': datetime.now().isoformat()
            }
            
            self.logger.debug(f"Analiz: {news['baslik'][:50]}... → Skor: {sentiment_score:.2f}")
            return analyzed
            
        except Exception as e:
            self.logger.error(f"Analiz hatası: {str(e)}", exc_info=True)
            # Haber verisi, hatalar rağmen döndür
            return {
                **news,
                'skor': 0.0,
                'kategori': 'Error',
                'risk_seviyesi': '⚠️ HATA',
                'error': str(e)
            }
    
    def analyze_batch(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Toplu analiz"""
        results = []
        for news in news_list:
            results.append(self.analyze_news(news))
        
        successful = len([r for r in results if 'error' not in r])
        self.logger.info(f"Toplu analiz: {successful}/{len(results)} başarılı")
        
        return results
    
    def get_country_sentiment(self, analyzed_news: List[Dict[str, Any]], country: str) -> Dict[str, Any]:
        """Ülkenin genel duygu durumunu analiz et"""
        country_news = [n for n in analyzed_news if n.get('ulke') == country]
        
        if not country_news:
            return {
                'country': country,
                'avg_score': 0.0,
                'total_news': 0,
                'risk_level': '🔍 VERİ YOK'
            }
        
        scores = [n.get('skor', 0) for n in country_news]
        avg_score = sum(scores) / len(scores)
        
        return {
            'country': country,
            'avg_score': avg_score,
            'total_news': len(country_news),
            'risk_level': self.settings.risk_thresholds.get_risk_level(avg_score),
            'min_score': min(scores),
            'max_score': max(scores)
        }
