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

# Konfigürasyonu valida et (ancak zorunlu değil)
try:
    keys_valid = config.validate_keys()
    if not keys_valid:
        print("⚠️ Uyarı: API anahtarları eksik veya geçersiz.")
        print("ℹ️ Program demo mod'unda çalışacaktır (sadece yerel veritabanı).")
except Exception as e:
    print(f"❌ Konfigürasyon doğrulama hatası: {e}")
    print("ℹ️ Program demo mod'unda çalışacaktır.")

# Logging
logger = backend_logger

# --- ML MODELLERI YÜKLEME ---
logger.info(" AI Modelleri yükleniyor...")
print(" Yapay Zeka Modelleri Yükleniyor (PyTorch)...")

sentiment_pipe = None
classifier = None

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
    print("✓ AI modelleri yüklendi")
except Exception as e:
    logger.error(f" AI modelleri yüklenirken hata: {e}")
    print(f"⚠️ AI modelleri yüklenemedi: {e}")
    print("ℹ️ Program AI olmadan çalışacaktır.")

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
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.DatabaseError as e:
            self.logger.error(f"Veritabanı bağlantı hatası: {e}")
            print(f"❌ Veritabanı hatası: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Beklenmeyen veritabanı hatası: {e}")
            print(f"❌ Beklenmeyen veritabanı hatası: {e}")
            raise
    
    def init_db(self):
        """Veritabanı tablosunu oluştur"""
        try:
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
                print("✓ Veritabanı tabloları oluşturuldu")
            except sqlite3.OperationalError as e:
                self.logger.error(f"Tablo oluşturma hatası: {e}")
                print(f"⚠️ Tablo oluşturma sorunu: {e}")
                conn.rollback()
            except Exception as e:
                self.logger.error(f"Veritabanı oluşturma hatası: {e}")
                print(f"❌ Veritabanı oluşturma hatası: {e}")
                conn.rollback()
            finally:
                conn.close()
        except Exception as e:
            self.logger.error(f"Veritabanı başlatma hatası: {e}")
            print(f"❌ Veritabanı başlatılamadı: {e}")
    
    def insert_news(self, news_data: List[Dict]) -> int:
        """Haberleri veritabanına ekle"""
        if not news_data:
            return 0
            
        try:
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
                            news.get('ulke', 'Unknown'),
                            news.get('tarih', ''),
                            news.get('baslik', ''),
                            news.get('skor', 0.0),
                            news.get('url', ''),
                            news.get('kategori', 'Unknown'),
                            news.get('kaynak', 'NewsAPI'),
                            news.get('risk_seviyesi', 'Normal')
                        ))
                        inserted_count += 1
                    except sqlite3.IntegrityError:
                        # Duplicate news, skip
                        continue
                    except Exception as e:
                        self.logger.warning(f"Haber ekleme skipped: {e}")
                        continue
                
                conn.commit()
                if inserted_count > 0:
                    self.logger.info(f" {inserted_count} yeni haber kaydedildi")
                return inserted_count
            except sqlite3.DatabaseError as e:
                self.logger.error(f"Haber ekleme DB hatası: {e}")
                conn.rollback()
                return 0
            except Exception as e:
                self.logger.error(f"Haber ekleme hatası: {e}")
                conn.rollback()
                return 0
            finally:
                conn.close()
        except Exception as e:
            self.logger.error(f"Veritabanı bağlantı başarısız: {e}")
            print(f"❌ Veritabanı erişim hatası: {e}")
            return 0


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
            if not baslik or not isinstance(baslik, str):
                return 0.0, "Unknown", " HATA"
            
            # Sentiment analizi
            if sentiment_pipe is not None:
                try:
                    sent_res = sentiment_pipe(baslik[:512])[0]  # Max 512 char
                    puan = sent_res['score'] if sent_res['label'] == 'POSITIVE' else -sent_res['score']
                    puan = round(puan, 4)
                except Exception as e:
                    self.logger.warning(f"Sentiment analiz başarısız: {e}")
                    puan = 0.0
            else:
                # AI modeli yoksa varsayılan değer
                puan = 0.0
            
            # Kategori sınıflandırması
            if classifier is not None:
                try:
                    class_res = classifier(baslik[:512], config.NEWS_CATEGORIES)
                    kategori = class_res['labels'][0]
                except Exception as e:
                    self.logger.warning(f"Kategori sınıflandırma başarısız: {e}")
                    kategori = "Unknown"
            else:
                kategori = "Unknown"
            
            # Risk seviyesi
            risk = self.calculate_risk_level(puan)
            
            return puan, kategori, risk
        except Exception as e:
            self.logger.error(f"Haber analiz hatası: {e}")
            return 0.0, "Error", " HATA"
    
    def process_articles(self, articles: List[Dict], country_code: str) -> List[Dict]:
        """Haberler listesini işle ve analiz et"""
        processed_news = []
        
        if not articles:
            return processed_news
        
        for article in articles:
            try:
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
                        'baslik': baslik[:500],  # Truncate long titles
                        'skor': puan,
                        'url': link[:2000],  # Truncate long URLs
                        'kategori': kategori,
                        'kaynak': kaynak[:100],
                        'risk_seviyesi': risk,
                        'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    self.logger.warning(f"Makale işleme hatası: {e}")
                    # Haber işlenemese bile çalışmaya devam et
                    continue
            except Exception as e:
                self.logger.warning(f"Makale parçalama hatası: {e}")
                continue
        
        return processed_news


# --- HABERLERİ ÇEKME MODÜLÜ ---
class NewsCollector:
    """NewsAPI'den haber çekme"""
    
    def __init__(self):
        self.api_key = config.NEWS_API_KEY
        self.logger = logger
        self.timeout = config.REQUEST_TIMEOUT
        self.has_api_key = bool(self.api_key and self.api_key != "your_newsapi_key_here")
    
    def fetch_news(self, country: str, country_name: str) -> List[Dict]:
        """Belirli bir ülke için haberleri çek"""
        if not self.has_api_key:
            self.logger.warning(f"NEWS_API_KEY eksik - {country} için haber çekilen miyor")
            return []
        
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
        except requests.exceptions.Timeout:
            self.logger.error(f" {country.upper()} API timeout: Bağlantı zaman aşımı")
            return []
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f" {country.upper()} ağ hatası: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            self.logger.error(f" {country.upper()} HTTP hatası: {e.response.status_code}")
            return []
        except ValueError as e:
            self.logger.error(f" {country.upper()} JSON parse hatası: {e}")
            return []
        except Exception as e:
            self.logger.error(f" {country.upper()} API hatası: {e}")
            return []
    
    def fetch_all_countries(self) -> Dict[str, List[Dict]]:
        """Paralel olarak tüm ülkeler için haberleri çek"""
        all_news = {}
        
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self.fetch_news, code, name): code 
                    for code, name in config.COUNTRIES.items()
                }
                
                for future in as_completed(futures):
                    country = futures[future]
                    try:
                        articles = future.result(timeout=config.REQUEST_TIMEOUT + 5)
                        all_news[country] = articles
                    except Exception as e:
                        self.logger.error(f"Haber çekme hatası ({country}): {e}")
                        all_news[country] = []
        except Exception as e:
            self.logger.error(f"Paralel haber çekme hatası: {e}")
            # Fallback: Sequential fetch
            for code, name in config.COUNTRIES.items():
                try:
                    all_news[code] = self.fetch_news(code, name)
                except Exception as e:
                    self.logger.warning(f"Sequential fetch failed for {code}: {e}")
                    all_news[code] = []
        
        return all_news


# --- ANA ÇALIŞTIRICI ---
def main_loop():
    """Ana analiz döngüsü"""
    
    logger.info(" Aura Global Intelligence Başlatıldı")
    print(" Aura Global Intelligence Başlatıldı")
    
    # Veritabanı hazırla
    try:
        db = Database()
        db.init_db()
        print("✓ Veritabanı hazırlandı")
    except Exception as e:
        logger.error(f"Veritabanı başlatma hatası: {e}")
        print(f"❌ Veritabanı başlatılamadı: {e}")
        return
    
    # Bileşenleri başlat
    try:
        collector = NewsCollector()
        analyzer = NewsAnalyzer()
        print("✓ Bileşenler başlatıldı")
    except Exception as e:
        logger.error(f"Bileşen başlatma hatası: {e}")
        print(f"❌ Bileşenler başlatılamadı: {e}")
        return
    
    # Ana döngü
    iteration = 0
    while True:
        iteration += 1
        try:
            print(f"\n[Döngü #{iteration}] Analiz Başlatıldı: {datetime.now().strftime('%H:%M:%S')}")
            logger.info("=" * 50)
            
            # Haberleri çek (paralel)
            try:
                all_news = collector.fetch_all_countries()
            except Exception as e:
                logger.error(f"Haber çekme hatası: {e}")
                all_news = {}
            
            # Analiz ve kaydet
            total_processed = 0
            critical_count = 0
            
            try:
                for country_code, articles in all_news.items():
                    try:
                        processed = analyzer.process_articles(articles, country_code)
                        
                        # Veritabanına kaydet
                        if processed:
                            try:
                                count = db.insert_news(processed)
                                total_processed += count
                                
                                # Kritik haberleri tespit et
                                for news in processed:
                                    if "KRİTİK" in news['risk_seviyesi']:
                                        critical_count += 1
                                        logger.warning(f" KRİTİK HABER: {news['baslik'][:60]}... (Skor: {news['skor']})")
                            except Exception as e:
                                logger.error(f"Veritabanı ekleme hatası ({country_code}): {e}")
                                continue
                    except Exception as e:
                        logger.error(f"Ülke işleme hatası ({country_code}): {e}")
                        continue
            except Exception as e:
                logger.error(f"Analiz döngüsü hatası: {e}")
            
            # Özet log
            logger.info(f" Özet: {total_processed} yeni haber, {critical_count} kritik")
            print(f"✓ İşlem Tamamlandı: {total_processed} yeni haber kaydedildi, {critical_count} kritik")

            # Bekleme (20 dakika)
            bekleme = 1200
            print(f"⏳ Sonraki tarama: {bekleme}s sonra ({bekleme//60} dakika)")
            time.sleep(bekleme)
            
        except KeyboardInterrupt:
            logger.info(" Program kullanıcı tarafından durduruldu")
            print("\n✓ Program durduruldu")
            break
        except Exception as e:
            logger.error(f" Ana döngü hatası: {e}")
            print(f"⚠️ Hata: {e}")
            print("ℹ️ 60 saniye sonra yeniden denenecek...")
            try:
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info(" Program kullanıcı tarafından durduruldu")
                print("\n✓ Program durduruldu")
                break


if __name__ == "__main__":
    main_loop()