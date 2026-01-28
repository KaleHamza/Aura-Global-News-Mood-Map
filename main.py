"""
Aura Global Intelligence - Backend (News Analysis Engine)
Haber toplama, analiz ve depolama sistemi
"""
import os
import requests
import sqlite3
from datetime import datetime
import time
from transformers import pipeline
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import logging

# Custom modules
from config import config
from logger import backend_logger

# Konfigürasyonu valida et
if not config.validate_keys():
    raise ValueError(" Gerekli API keyleri eksik! .env dosyasını kontrol edin.")

# Logging
logger = backend_logger

# --- ML MODELLERI YÜKLEME ---
logger.info(" AI Modelleri yükleniyor...")
print(" Yapay Zeka Modelleri Yükleniyor (PyTorch)...")

try:
    sentiment_pipe = pipeline(
        "sentiment-analysis", 
        model=config.SENTIMENT_MODEL,
        framework="pt"
    )
    
    classifier = pipeline(
        "zero-shot-classification", 
        model=config.CLASSIFIER_MODEL,
        framework="pt"
    )
    logger.info(" AI modelleri başarıyla yüklendi")
except Exception as e:
    logger.error(f" AI modelleri yüklenirken hata: {e}")
    raise

# --- VERITABANI AYARLARI ---
class Database:
    """SQLite Veritabanı Yönetimi"""
    
    def __init__(self, db_path: str = config.DATABASE_URL.replace("sqlite:///", "")):
        self.db_path = db_path
        self.logger = logger
    
    def connect(self):
        """Veritabanına bağlan"""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except Exception as e:
            self.logger.error(f"Veritabanı bağlantı hatası: {e}")
            raise
    
    def init_db(self):
        """Veritabanı tablosunu oluştur"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS haberler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ulke TEXT NOT NULL,
                    tarih TEXT NOT NULL,
                    baslik TEXT NOT NULL,
                    skor REAL NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    kategori TEXT,
                    kaynak TEXT,
                    risk_seviyesi TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(baslik, url)
                )
            ''')
            
            # Index'ler
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ulke ON haberler(ulke)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_skor ON haberler(skor)')
            
            conn.commit()
            self.logger.info(" Veritabanı tablosu hazır")
        except Exception as e:
            self.logger.error(f"Veritabanı oluşturma hatası: {e}")
            raise
        finally:
            conn.close()
    
    def insert_news(self, news_data: List[Dict]) -> int:
        """Haberleri veritabanına ekle"""
        conn = self.connect()
        cursor = conn.cursor()
        inserted_count = 0
        
        try:
            for news in news_data:
                try:
                    cursor.execute('''
                        INSERT INTO haberler 
                        (ulke, tarih, baslik, skor, url, kategori, kaynak, risk_seviyesi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        news['ulke'],
                        news['tarih'],
                        news['baslik'],
                        news['skor'],
                        news['url'],
                        news.get('kategori', 'Unknown'),
                        news.get('kaynak', 'NewsAPI'),
                        news.get('risk_seviyesi', 'Normal')
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # Duplicate news, skip
                    continue
            
            conn.commit()
            self.logger.info(f" {inserted_count} yeni haber kaydedildi")
            return inserted_count
        except Exception as e:
            self.logger.error(f"Haber ekleme hatası: {e}")
            raise
        finally:
            conn.close()


# --- ANALİZ MODÜLÜ ---
class NewsAnalyzer:
    """Haber analiz motoru"""
    
    def __init__(self):
        self.logger = logger
        self.db = Database()
    
    def calculate_risk_level(self, sentiment_score: float) -> str:
        """Duygu skorundan risk seviyesi hesapla"""
        if sentiment_score <= config.CRITICAL_THRESHOLD:
            return " KRİTİK"
        elif sentiment_score <= config.WARNING_THRESHOLD:
            return " UYARI"
        elif sentiment_score >= config.POSITIVE_THRESHOLD:
            return " POZİTİF"
        else:
            return " NORMAL"
    
    def analyze_article(self, baslik: str) -> Tuple[float, str, str]:
        """
        Haber başlığını analiz et
        Returns: (sentiment_score, kategori, risk_level)
        """
        try:
            # Sentiment analizi
            sent_res = sentiment_pipe(baslik)[0]
            puan = sent_res['score'] if sent_res['label'] == 'POSITIVE' else -sent_res['score']
            puan = round(puan, 4)
            
            # Kategori sınıflandırması
            class_res = classifier(baslik, config.NEWS_CATEGORIES)
            kategori = class_res['labels'][0]
            
            # Risk seviyesi
            risk = self.calculate_risk_level(puan)
            
            return puan, kategori, risk
        except Exception as e:
            self.logger.error(f"Haber analiz hatası: {e}")
            raise
    
    def process_articles(self, articles: List[Dict], country_code: str) -> List[Dict]:
        """Haberler listesini işle ve analiz et"""
        processed_news = []
        
        for article in articles:
            baslik = article.get('title')
            link = article.get('url')
            kaynak = article.get('source', {}).get('name', 'Unknown')
            
            # Geçersiz haberleri filtrele
            if not baslik or not link or "[Removed]" in baslik:
                continue
            
            try:
                puan, kategori, risk = self.analyze_article(baslik)
                
                processed_news.append({
                    'ulke': country_code,
                    'baslik': baslik,
                    'skor': puan,
                    'url': link,
                    'kategori': kategori,
                    'kaynak': kaynak,
                    'risk_seviyesi': risk,
                    'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                self.logger.warning(f"Makale işleme hatası: {e}")
                continue
        
        return processed_news


# --- HABERLERİ ÇEKME MODÜLÜ ---
class NewsCollector:
    """NewsAPI'den haber çekme"""
    
    def __init__(self):
        self.api_key = config.NEWS_API_KEY
        self.logger = logger
        self.timeout = config.REQUEST_TIMEOUT
    
    def fetch_news(self, country: str, country_name: str) -> List[Dict]:
        """Belirli bir ülke için haberleri çek"""
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f'technology AND {country_name}',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 15,
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            articles = response.json().get('articles', [])
            self.logger.info(f" {country.upper()}: {len(articles)} haber çekildi")
            return articles
        except requests.exceptions.RequestException as e:
            self.logger.error(f" {country.upper()} API hatası: {e}")
            return []
    
    def fetch_all_countries(self) -> Dict[str, List[Dict]]:
        """Paralel olarak tüm ülkeler için haberleri çek"""
        all_news = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.fetch_news, code, name): code 
                for code, name in config.COUNTRIES.items()
            }
            
            for future in as_completed(futures):
                country = futures[future]
                try:
                    articles = future.result()
                    all_news[country] = articles
                except Exception as e:
                    self.logger.error(f"Haber çekme hatası ({country}): {e}")
                    all_news[country] = []
        
        return all_news


# --- ANA ÇALIŞTIRICI ---
def main_loop():
    """Ana analiz döngüsü"""
    
    logger.info(" Aura Global Intelligence Başlatıldı")
    print(" Aura Global Intelligence Başlatıldı")
    
    # Veritabanı hazırla
    db = Database()
    db.init_db()
    
    # Bileşenleri başlat
    collector = NewsCollector()
    analyzer = NewsAnalyzer()
    
    # Ana döngü
    while True:
        try:
            print(f"\n Analiz Başlatıldı: {datetime.now().strftime('%H:%M:%S')}")
            logger.info("=" * 50)
            
            # Haberleri çek (paralel)
            all_news = collector.fetch_all_countries()
            
            # Analiz ve kaydet
            total_processed = 0
            critical_count = 0
            
            for country_code, articles in all_news.items():
                processed = analyzer.process_articles(articles, country_code)
                
                # Veritabanına kaydet
                if processed:
                    count = db.insert_news(processed)
                    total_processed += count
                    
                    # Kritik haberleri tespit et
                    for news in processed:
                        if "KRİTİK" in news['risk_seviyesi']:
                            critical_count += 1
                            logger.warning(f" KRİTİK HABER: {news['baslik']} (Skor: {news['skor']})")
            
            # Özet log
            logger.info(f" Özet: {total_processed} yeni haber, {critical_count} kritik")
            print(f" İşlem Tamamlandı: {total_processed} yeni haber kaydedildi")

            # Bekleme (20 dakika)
            bekleme = 1200
            print(f" Sonraki tarama: {bekleme}s sonra ({bekleme//60} dakika)")
            time.sleep(bekleme)
            
        except KeyboardInterrupt:
            logger.info(" Program kullanıcı tarafından durduruldu")
            print("\n Program durduruldu")
            break
        except Exception as e:
            logger.error(f" Ana döngü hatası: {e}")
            print(f" Hata: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main_loop()