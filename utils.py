"""
Aura Utilities Module
Cache, anomaly detection, trend prediction
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
import sqlite3
import pandas as pd
import numpy as np
from logger import logger

class SimpleCache:
    """Basit in-memory cache sistemi"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        if key in self.cache:
            timestamp, value = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                logger.debug(f" Cache hit: {key}")
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Cache'e değer ekle"""
        self.cache[key] = (datetime.now(), value)
        logger.debug(f" Cache set: {key}")
    
    def clear(self):
        """Cache'i temizle"""
        self.cache.clear()


class AnomalyDetector:
    """Anomali tespit sistemi"""
    
    @staticmethod
    def detect_spikes(df: pd.DataFrame, column: str = 'skor', threshold: float = 2.0) -> pd.DataFrame:
        """
        Veri anomalilerini tespit et (Z-score)
        """
        if df.empty or column not in df.columns:
            return df
        
        df_copy = df.copy()
        mean = df_copy[column].mean()
        std = df_copy[column].std()
        
        if std == 0:
            df_copy['is_anomaly'] = False
            return df_copy
        
        z_scores = np.abs((df_copy[column] - mean) / std)
        df_copy['is_anomaly'] = z_scores > threshold
        df_copy['anomaly_score'] = z_scores
        
        return df_copy
    
    @staticmethod
    def detect_trend_change(df: pd.DataFrame, column: str = 'skor', window: int = 7) -> pd.DataFrame:
        """Trend değişikliklerini tespit et"""
        if df.empty or len(df) < window:
            return df
        
        df_copy = df.copy()
        df_copy['rolling_mean'] = df_copy[column].rolling(window=window, center=True).mean()
        df_copy['trend_change'] = abs(df_copy[column] - df_copy['rolling_mean']) > df_copy[column].std()
        
        return df_copy


class TrendPredictor:
    """Trend prediction (basit moving average)"""
    
    @staticmethod
    def predict_sentiment_trend(df: pd.DataFrame, country: str, days_ahead: int = 7) -> dict:
        """
        Basit moving average ile trend tahmin
        """
        try:
            country_data = df[df['ulke'] == country].sort_values('tarih')
            
            if len(country_data) < 5:
                return {"status": "insufficient_data", "message": "Yeterli veri yok"}
            
            # Son 30 günü al
            country_data['tarih'] = pd.to_datetime(country_data['tarih'])
            recent = country_data[country_data['tarih'] >= country_data['tarih'].max() - timedelta(days=30)]
            
            if recent.empty:
                return {"status": "no_recent_data"}
            
            # Moving average
            ma_7 = recent['skor'].rolling(window=7).mean()
            ma_30 = recent['skor'].rolling(window=30).mean()
            
            trend = " Yükseliş" if ma_7.iloc[-1] > ma_30.iloc[-1] else " Düşüş"
            
            return {
                "status": "success",
                "country": country,
                "current_sentiment": float(recent['skor'].iloc[-1]),
                "7day_average": float(ma_7.iloc[-1]),
                "30day_average": float(ma_30.iloc[-1]),
                "trend": trend,
                "volatility": float(recent['skor'].std())
            }
        except Exception as e:
            logger.error(f"Trend prediction hatası: {e}")
            return {"status": "error", "message": str(e)}


class RiskScoringEngine:
    """Gelişmiş risk puanlama sistemi"""
    
    RISK_WEIGHTS = {
        'sentiment_score': 0.4,
        'frequency': 0.3,
        'volatility': 0.2,
        'critical_keywords': 0.1
    }
    
    CRITICAL_KEYWORDS = [
        'breach', 'hack', 'exploit', 'vulnerability', 'crash', 'fail',
        'risk', 'threat', 'danger', 'critical', 'emergency', 'urgent',
        'crisis', 'disaster', 'attack', 'malware', 'ransomware'
    ]
    
    @classmethod
    def calculate_risk_score(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Kapsamlı risk skoru hesapla
        Returns: 0-100 risk skoru
        """
        df_copy = df.copy()
        
        # 1. Sentiment komponent
        sentiment_component = ((df_copy['skor'] + 1) / 2 * 100) * cls.RISK_WEIGHTS['sentiment_score']
        
        # 2. Frekans komponent (ülke başına haber sayısı)
        country_freq = df_copy.groupby('ulke').size() / len(df_copy) * 100
        df_copy['frequency_score'] = df_copy['ulke'].map(country_freq) * cls.RISK_WEIGHTS['frequency']
        
        # 3. Volatilite komponent
        df_copy['volatility_score'] = df_copy.groupby('ulke')['skor'].transform('std') * 100 * cls.RISK_WEIGHTS['volatility']
        
        # 4. Kritik kelime komponent
        has_critical = df_copy['baslik'].str.lower().str.contains('|'.join(cls.CRITICAL_KEYWORDS), na=False)
        df_copy['critical_keyword_score'] = has_critical.astype(int) * 100 * cls.RISK_WEIGHTS['critical_keywords']
        
        # Toplam risk skoru
        df_copy['risk_score'] = (
            sentiment_component +
            df_copy['frequency_score'] +
            df_copy['volatility_score'] +
            df_copy['critical_keyword_score']
        ).clip(0, 100)
        
        # Risk kategorisi
        df_copy['risk_category'] = pd.cut(
            df_copy['risk_score'],
            bins=[0, 20, 40, 60, 80, 100],
            labels=['Çok Düşük', 'Düşük', 'Orta', 'Yüksek', 'Kritik']
        )
        
        return df_copy


# Global cache instance
cache = SimpleCache()
anomaly_detector = AnomalyDetector()
trend_predictor = TrendPredictor()
risk_engine = RiskScoringEngine()
