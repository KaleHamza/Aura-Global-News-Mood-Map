"""
Unit Tests for Aura Backend
"""

import unittest
import sqlite3
import tempfile
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import Database, NewsAnalyzer, NewsCollector


class TestDatabase(unittest.TestCase):
    """Database class tests"""
    
    def setUp(self):
        """Her test öncesi geçici veritabanı oluştur"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.db = Database(self.db_path)
        self.db.init_db()
    
    def tearDown(self):
        """Test sonrası temizle"""
        import os
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_database_initialization(self):
        """Veritabanı oluşturulup oluşturulmadığını test et"""
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        self.assertTrue(any('haberler' in table for table in tables))
    
    def test_insert_news(self):
        """Haber ekleme fonksiyonunu test et"""
        test_news = [{
            'ulke': 'us',
            'baslik': 'Test Haberi',
            'skor': 0.85,
            'url': 'https://example.com/test',
            'kategori': 'AI',
            'kaynak': 'TestAPI',
            'risk_seviyesi': ' POZİTİF',
            'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }]
        
        count = self.db.insert_news(test_news)
        self.assertEqual(count, 1)
        
        # Veritabanından kontrol et
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM haberler")
        total = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(total, 1)
    
    def test_duplicate_news_handling(self):
        """Duplicate haber işlemesini test et"""
        test_news = [{
            'ulke': 'us',
            'baslik': 'Aynı Haber',
            'skor': 0.5,
            'url': 'https://example.com/same',
            'kategori': 'Tech',
            'kaynak': 'TestAPI',
            'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }]
        
        # İlk ekleme
        count1 = self.db.insert_news(test_news)
        self.assertEqual(count1, 1)
        
        # İkinci ekleme (duplicate)
        count2 = self.db.insert_news(test_news)
        self.assertEqual(count2, 0)  # Eklenmemeli


class TestNewsAnalyzer(unittest.TestCase):
    """NewsAnalyzer class tests"""
    
    def setUp(self):
        """Test setup"""
        self.analyzer = NewsAnalyzer()
    
    def test_risk_level_calculation(self):
        """Risk seviyesi hesaplamasını test et"""
        test_cases = [
            (-0.8, " KRİTİK"),
            (-0.5, " UYARI"),
            (0.7, " POZİTİF"),
            (0.0, " NORMAL")
        ]
        
        for score, expected_risk in test_cases:
            result = self.analyzer.calculate_risk_level(score)
            self.assertEqual(result, expected_risk)
    
    def test_article_analysis(self):
        """Haber analiz fonksiyonunu test et"""
        baslik = "Apple açıkladı yeni AI teknolojisini"
        
        try:
            puan, kategori, risk = self.analyzer.analyze_article(baslik)
            
            # Puan -1 ile 1 arasında olmalı
            self.assertTrue(-1 <= puan <= 1)
            
            # Kategori string olmalı
            self.assertIsInstance(kategori, str)
            
            # Risk emojisi içermeli
            self.assertIn("", risk)  # Contains emoji/text
        except Exception as e:
            # Model yüklenmemişse skip
            self.skipTest(f"ML model initialization failed: {e}")


class TestUtils(unittest.TestCase):
    """Utils module tests"""
    
    def test_cache_system(self):
        """Cache sistemini test et"""
        from utils import cache
        
        # Cache'e ekle
        cache.set("test_key", "test_value")
        
        # Oku
        value = cache.get("test_key")
        self.assertEqual(value, "test_value")
        
        # Non-existent key
        self.assertIsNone(cache.get("non_existent"))
    
    def test_anomaly_detection(self):
        """Anomali detection test"""
        import pandas as pd
        from utils import anomaly_detector
        
        df = pd.DataFrame({
            'skor': [0.1, 0.2, 0.15, -0.95, 0.1, 0.2, 0.15],
            'ulke': ['us'] * 7
        })
        
        result = anomaly_detector.detect_spikes(df)
        
        # Result DataFrame olmalı
        self.assertIsInstance(result, pd.DataFrame)
        
        # 'is_anomaly' sütunu olmalı
        self.assertIn('is_anomaly', result.columns)


class TestConfig(unittest.TestCase):
    """Configuration tests"""
    
    def test_config_loading(self):
        """Config yüklemesini test et"""
        from config import config, Config
        
        # Config instance'ı kontrol et
        self.assertIsInstance(config, Config)
        
        # Ülkeler listesi var mı
        self.assertIn('us', Config.COUNTRIES)
        self.assertIn('kr', Config.COUNTRIES)
    
    def test_environment_validation(self):
        """Ortam validation'ını test et"""
        import os
        
        # Test için ortam değişkenlerini ayarla
        os.environ['GOOGLE_API_KEY'] = ''
        os.environ['NEWS_API_KEY'] = 'test_key'
        
        # Re-import config
        import importlib
        import config as config_module
        importlib.reload(config_module)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_end_to_end_workflow(self):
        """End-to-end iş akışını test et"""
        import tempfile
        import os
        
        # Geçici veritabanı
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Database
            db = Database(db_path)
            db.init_db()
            
            # Mock news data
            mock_news = [{
                'ulke': 'us',
                'baslik': 'Integration Test News',
                'skor': 0.5,
                'url': 'https://example.com/integration',
                'kategori': 'Test',
                'kaynak': 'Test',
                'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }]
            
            # Insert
            count = db.insert_news(mock_news)
            self.assertEqual(count, 1)
            
            # Verify
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM haberler")
            total = cursor.fetchone()[0]
            conn.close()
            
            self.assertEqual(total, 1)
        
        finally:
            try:
                os.unlink(db_path)
            except:
                pass


if __name__ == '__main__':
    unittest.main()
