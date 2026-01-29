"""
Veritabanı İş Mantığı Katmanı (Repository Pattern)
SOLID: SRP - Sadece veritabanı işlemleri
"""
import sqlite3
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import contextlib


class DatabaseException(Exception):
    """Veritabanı işlemleri için custom exception"""
    pass


class NewsSchema:
    """Haber tablosu şeması - DRY prensibi"""
    CREATE_TABLE_SQL = '''
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
    '''
    
    CREATE_INDEXES_SQL = [
        'CREATE INDEX IF NOT EXISTS idx_ulke ON haberler(ulke)',
        'CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih)',
        'CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)',
        'CREATE INDEX IF NOT EXISTS idx_skor ON haberler(skor)',
    ]
    
    INSERT_NEWS_SQL = '''
        INSERT INTO haberler 
        (ulke, tarih, baslik, skor, url, kategori, kaynak, risk_seviyesi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    SELECT_ALL_SQL = "SELECT * FROM haberler"
    SELECT_BY_COUNTRY_SQL = "SELECT * FROM haberler WHERE ulke = ? ORDER BY tarih DESC"
    SELECT_BY_CATEGORY_SQL = "SELECT * FROM haberler WHERE kategori = ? ORDER BY tarih DESC"
    SELECT_RECENT_SQL = "SELECT * FROM haberler ORDER BY tarih DESC LIMIT ?"


class DatabaseConnection:
    """Context Manager ile veritabanı bağlantısı - DRY prensibi"""
    
    def __init__(self, db_path: str, timeout: int = 30):
        self.db_path = db_path
        self.timeout = timeout
        self.conn: Optional[sqlite3.Connection] = None
    
    def __enter__(self) -> sqlite3.Connection:
        """Context açılırken bağlantı oluştur"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            self.conn.row_factory = sqlite3.Row  # Dict-like access
            return self.conn
        except sqlite3.Error as e:
            raise DatabaseException(f"Veritabanı bağlantı hatası: {e}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context kapanırken bağlantı kapat"""
        if self.conn:
            self.conn.close()
        return False


class IRepository(ABC):
    """Repository Interface - Liskov Substitution Principle"""
    
    @abstractmethod
    def add_news(self, news_list: List[Dict[str, Any]]) -> int:
        """Haber ekle ve eklenen sayı döndür"""
        pass
    
    @abstractmethod
    def get_all_news(self) -> List[Dict[str, Any]]:
        """Tüm haberleri al"""
        pass
    
    @abstractmethod
    def get_news_by_country(self, country: str) -> List[Dict[str, Any]]:
        """Ülkeye göre haberleri al"""
        pass
    
    @abstractmethod
    def get_news_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Kategoriye göre haberleri al"""
        pass
    
    @abstractmethod
    def get_recent_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Son haberler"""
        pass
    
    @abstractmethod
    def init_database(self) -> bool:
        """Veritabanını başlat"""
        pass


class SQLiteNewsRepository(IRepository):
    """SQLite implementasyonu - Open/Closed Principle"""
    
    def __init__(self, db_path: str, logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
    
    def init_database(self) -> bool:
        """Veritabanı tablosunu oluştur"""
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tablo oluştur
                cursor.execute(NewsSchema.CREATE_TABLE_SQL)
                
                # İndeks oluştur
                for index_sql in NewsSchema.CREATE_INDEXES_SQL:
                    cursor.execute(index_sql)
                
                conn.commit()
                self.logger.info("✓ Veritabanı tablosu hazır")
                return True
        except DatabaseException as e:
            self.logger.error(f"✗ Veritabanı oluşturma hatası: {e}")
            return False
    
    def add_news(self, news_list: List[Dict[str, Any]]) -> int:
        """Haberleri toplu ekle"""
        if not news_list:
            return 0
        
        inserted_count = 0
        duplicate_count = 0
        
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                
                for news in news_list:
                    try:
                        cursor.execute(
                            NewsSchema.INSERT_NEWS_SQL,
                            (
                                news.get('ulke'),
                                news.get('tarih'),
                                news.get('baslik'),
                                news.get('skor', 0.0),
                                news.get('url'),
                                news.get('kategori', 'Unknown'),
                                news.get('kaynak', 'NewsAPI'),
                                news.get('risk_seviyesi', 'Normal')
                            )
                        )
                        inserted_count += 1
                    except sqlite3.IntegrityError:
                        duplicate_count += 1
                        continue
                
                conn.commit()
                self.logger.info(
                    f"✓ {inserted_count} haber eklendi, {duplicate_count} duplikat atlandı"
                )
                return inserted_count
        
        except DatabaseException as e:
            self.logger.error(f"✗ Haber ekleme hatası: {e}")
            raise
    
    def get_all_news(self) -> List[Dict[str, Any]]:
        """Tüm haberleri getir"""
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(NewsSchema.SELECT_ALL_SQL)
                return [dict(row) for row in cursor.fetchall()]
        except DatabaseException as e:
            self.logger.error(f"✗ Haber okuma hatası: {e}")
            return []
    
    def get_news_by_country(self, country: str) -> List[Dict[str, Any]]:
        """Ülkeye göre haberleri getir"""
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(NewsSchema.SELECT_BY_COUNTRY_SQL, (country,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"✗ Ülkeye göre haber okuma hatası: {e}")
            return []
        except Exception as e:
            self.logger.error(f"✗ Beklenmeyen hata: {e}")
            return []
    
    def get_news_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Kategoriye göre haberleri getir"""
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(NewsSchema.SELECT_BY_CATEGORY_SQL, (category,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"✗ Kategoriye göre haber okuma hatası: {e}")
            return []
        except Exception as e:
            self.logger.error(f"✗ Beklenmeyen hata: {e}")
            return []
    
    def get_recent_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Son haberleri getir"""
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(NewsSchema.SELECT_RECENT_SQL, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except DatabaseException as e:
            self.logger.error(f"✗ Son haber okuma hatası: {e}")
            return []
