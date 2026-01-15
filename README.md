#  Aura Global Intelligence

Yapay Zeka Destekli Küresel Teknoloji Duygu Analizi ve Risk Takip Paneli

---
##  Özellikler

###  Temel Özellikler

- **Gerçek Zamanlı Haber Takibi**: NewsAPI üzerinden 6 ülkeden otomatik haber topla
- **AI Sentiment Analizi**: BERT modeli ile duygu analizi (POSITIVE/NEGATIVE/NEUTRAL)
- **Kategorilendirme**: Zero-shot classification ile otomatik haber kategorizasyonu
- **Risk Puanlama**: Gelişmiş risk scoring sistemi (0-100 puan)
- **Anomali Tespit**: İstatistiksel anomali detection (Z-score)
- **Trend Prediction**: 7/30 günlük trend analizi ve prediksiyon

###  Dashboard Özellikleri

 ** Harita** | Dünya haritası üzerinde ülkelerin duygu analizi 
 ** Ortalama** | Ülke bazında duygusal analiz ve kategori dağılımı 
 ** Trend** | Zaman serisinde duygu değişimi grafiği 
 ** Bulut** | Haber başlıklarından kelime bulutu (word cloud) 
 ** Versus** | Ülke karşılaştırması (vs) 
 ** Şirketler** | Apple, Nvidia, Tesla vs. şirket takibi 

###  Güvenlik Özellikleri

-  API anahtarları `.env` dosyasında güvenli depolama
-  Streamlit password protection (production mode)
-  Comprehensive logging sistemi
-  Secure database transactions

###  Performance Özellikleri

-  Paralel haber çekme (ThreadPoolExecutor)
-  In-memory caching sistemi
-  Database indexing
-  Rotating file logs

---

##  Kurulum

### 1. Repository'yi Clone Et

```bash
git clone https://github.com/KaleHamza/Aura-Global-News-Mood-Map.git
cd Aura-Global-News-Mood-Map
```

### 2. Virtual Environment Oluştur

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Kur

```bash
pip install -r requirements.txt
```

### 4. Ortam Değişkenlerini Ayarla

```bash
# .env.example'i .env olarak kopyala
cp .env.example .env

# .env dosyasını düzenle ve API anahtarlarını ekle
```

---

##  Yapılandırma

### .env Dosyası Örneği

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key_here
NEWS_API_KEY=your_newsapi_key_here
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Güvenlik
STREAMLIT_PASSWORD=yourpasswordhere
SECRET_KEY=your_secret_key_here

# Ortam
ENVIRONMENT=production  # development, staging, production

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Cache
CACHE_ENABLED=true
CACHE_TIMEOUT=300
```

### Ortam Değişkenlerini Alma

#### Google Gemini API Key

1. [Google Cloud Console](https://console.cloud.google.com) ziyaret et
2. Yeni proje oluştur
3. Generative AI API'yi etkinleştir
4. API key oluştur

#### NewsAPI Key

1. [NewsAPI.org](https://newsapi.org) ziyaret et
2. Ücretsiz hesap oluştur
3. API key'i al

#### Telegram Bot Token

1. Telegram'da `@BotFather` ile konuşma başlat
2. `/newbot` komutu kullan
3. Token'ı al

---

##  Kullanım

### 1. Backend'i Başlat (Haber Analiz Motoru)

```bash
python main.py
```

**Çıktı:**
```
 Aura Global Intelligence Başlatıldı
 Analiz Başlatıldı: 14:30:22
 US: 15 yeni haber (Sınıflandırıldı)
 KR: 12 yeni haber
...
 Sonraki tarama: 600s sonra (10 dakika)
```

### 2. Frontend'i Başlat (Dashboard)

Yeni terminal penceresinde:

```bash
streamlit run app.py
```

**Çıktı:**
```
Collecting usage statistics...
  You can turn off usage stats by setting telemetry.enabled = false

  Welcome to Streamlit! 

  URL: http://localhost:8501
```

### 3. Dashboard'a Erişim

Tarayıcıda açın

---

##  Mimarı

### Sistem Bileşenleri

```
NewsAPI -> Analysis Engine -> SQLite -> Risk Scoring Engine


### Dosya Yapısı

```
Aura-Global-News-Mood-Map/
├── app.py                  # Streamlit Frontend
├── main.py                 # Backend - Haber Analiz Motoru
├── config.py              # Konfigürasyon yönetimi
├── logger.py              # Logging sistemi
├── utils.py               # Utilities (cache, anomali, trend)
├── requirements.txt       # Python bağımlılıkları
├── Dockerfile             # Docker image
├── docker-compose.yml     # Docker compose (prod)
├── .env.example           # Ortam değişkenleri örneği
├── .gitignore             # Git ignore dosyası
├── README.md              # Bu dosya
├── logs/                  # Log dosyaları (otomatik oluşturulur)
├── tests/                 # Unit tests     
├── pages/                 # Unit tests  
|   ├── Musteri_Paneli.py  # Musteriye analizin tek raporda oluşturulduğu sayfa 
└── docs/                  # Dokümantasyon
    ├── Project_report.md
```

---


#### Database Class

```python
from main import Database

db = Database()
db.init_db()  # Tablo oluştur
db.insert_news([{
    'ulke': 'us',
    'baslik': 'Apple açıkladı...',
    'skor': 0.85,
    'url': 'https://...',
    'kategori': 'Hardware & Chips',
    'kaynak': 'NewsAPI'
}])
```

### Docker ile Deployment

#### 1. Docker Build

```bash
docker build -t aura:latest .
```

#### 2. Environment File Oluştur

```bash
cat > .env.prod <<EOF
GOOGLE_API_KEY=your_key
NEWS_API_KEY=your_key
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
STREAMLIT_PASSWORD=strongpassword
ENVIRONMENT=production
EOF
```

#### 3. Docker Compose Çalıştır

```bash
docker-compose -f docker-compose.yml up -d
```

#### 4. Servisleri Kontrol Et

```bash
docker-compose ps
docker-compose logs -f
```

### Production Checklist

- [ ] API keyleri `.env` dosyasına taşındı
- [ ] STREAMLIT_PASSWORD güçlü şifre olarak ayarlandı
- [ ] ENVIRONMENT=production ayarlandı
- [ ] Logs directory'si var ve yazılabilir
- [ ] Database backup sistemi kuruldu
- [ ] Monitoring aktif
- [ ] HTTPS yapılandırıldı (Reverse proxy ile)
- [ ] Rate limiting aktif

---
##  Sorun Giderme




### Risk Scoring Formul

$$\text{Risk Score} = 0.4 \times \text{Sentiment} + 0.3 \times \text{Frequency} + 0.2 \times \text{Volatility} + 0.1 \times \text{Critical Words}$$

### Anomaly Detection (Z-Score)

$$Z = \frac{X - \mu}{\sigma}$$

Eğer $|Z| > 2.0$ ise anomali tespit edilir.

---


##  Lisans

Bu proje MIT Lisansı altında dağıtılmaktadır.

---

##  İletişim

- **GitHub Issues**: [Sorun bildir](https://github.com/KaleHamza/issues)
- **Email**: hamza1kale@gmail.com
---

##  Roadmap

### v3.0 PLANLANAN

- [ ] Multilingual sentiment (TR, AR, ZH)
- [ ] PostgreSQL support
- [ ] Redis caching
- [ ] GraphQL API
- [ ] Mobile app
- [ ] Real-time WebSocket updates

### v2.5 Mevcut OLANLAR

-  Risk scoring sistemi
-  Anomaly detection
-  Trend prediction
-  Docker support
-  Logging sistem
-  Config management

---

## Kaynaklar

- [Streamlit Docs](https://docs.streamlit.io)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [NewsAPI Documentation](https://newsapi.org)
- [Google Generative AI](https://ai.google.dev)

---

**Son Güncelleme**: Ocak 2026 
**Versiyon**: 2.5.0
