import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import google.generativeai as genai
import hashlib

# --- 1. SAYFA AYARLARI (Sadece bir kez ve en üstte olmalı) ---
st.set_page_config(page_title="Aura Global Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- GÜVENLIK: PASSWORD PROTECTION ---
def check_password():
    """Streamlit'te password koruması"""
    from config import config
    
    if config.ENVIRONMENT == "production" and config.STREAMLIT_PASSWORD:
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        
        if not st.session_state.authenticated:
            st.warning(" Bu dashboard şifre ile korunmaktadır")
            password = st.text_input("Şifreyi girin:", type="password")
            
            if password:
                if hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(config.STREAMLIT_PASSWORD.encode()).hexdigest():
                    st.session_state.authenticated = True
                    st.success(" Başarılı giriş!")
                    st.rerun()
                else:
                    st.error(" Şifre yanlış!")
                    return False
            return False
    
    return True

if not check_password():
    st.stop()

# --- 2. VERİ YÜKLEME FONKSİYONU ---
def verileri_yukle():
    try:
        conn = sqlite3.connect("haber_analizi.db")
        # Sadece kategori sütunu DOLU olan verileri çekmekte fayda olabilir
        df = pd.read_sql_query("SELECT * FROM haberler ORDER BY tarih DESC", conn)
        conn.close()
        return df
    except FileNotFoundError:
        st.warning("⚠️ Veritabanı dosyası bulunamadı. Lütfen main.py'yi çalıştırın.")
        return pd.DataFrame()
    except sqlite3.DatabaseError as e:
        st.error(f"❌ Veritabanı okuma hatası: {e}") 
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Beklenmeyen hata: {e}")
        return pd.DataFrame()
# Veriyi en başta yüklüyoruz ki sidebar ve diğer yerlerde kullanabilelim
df = verileri_yukle()

# --- 3. CONFIGURATION & SECURITY ---
from config import config
from logger import frontend_logger

logger = frontend_logger

# API Key'i config'den yükle
google_api_key = config.GOOGLE_API_KEY
model = None

if not google_api_key or google_api_key == "your_google_api_key_here":
    st.warning(" GOOGLE_API_KEY .env dosyasında tanımlanmamış! AI özet özelliği devre dışıdır.")
    logger.warning("Google API Key eksik")
else:
    try:
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        logger.info("Google Gemini API başarıyla yapılandırıldı")
    except Exception as e:
        st.error(f"❌ AI Başlatılamadı: {e}")
        logger.error(f"Gemini yapılandırma hatası: {e}")
        model = None

def ai_ozet_al(haberler_listesi):
    """Yapay Zeka ile haber özeti al"""
    if not haberler_listesi:
        return "Analiz edilecek veri bulunamadı."
    
    if model is None:
        return "⚠️ AI modeli yüklenmedi. Lütfen GOOGLE_API_KEY'i kontrol edin."
    
    try:
        metin = "\n- ".join(haberler_listesi[:15])
        prompt = f"Aşağıdaki teknoloji haberlerini analiz et ve dünya gündemini 3 kısa Türkçe cümleyle özetle:\n{metin}"
        
        response = model.generate_content(prompt, timeout=30)
        return response.text
    except Exception as e:
        return f"⚠️ AI Yanıt Hatası: {str(e)}"

# --- 4. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=100)
    st.title("Aura v2.5")
    st.markdown("---")
    st.write(" **Takip Edilen Ülkeler:**")
    st.info("USA, S.Korea, France, Spain, Italy, Greece")
    st.markdown("---")
    if st.button(" Verileri Şimdi Yenile"):
        st.rerun()
    
    if not df.empty:
        df['tarih'] = pd.to_datetime(df['tarih'])
        st.write(" Son Tarama: " + df['tarih'].max().strftime('%H:%M:%S'))

# --- 6. ANA BAŞLIK ---
st.title("🛡️ Aura: Global Tech Intelligence")
st.caption("Yapay Zeka Destekli Küresel Teknoloji Duygu Analizi ve Risk Takip Paneli")

if not df.empty:
    # --- AI Özet Butonu ---
    if st.button("✨ Yapay Zeka ile Gündemi Özetle"):
        if model is None:
            st.error("❌ AI modeli yüklenmedi. GOOGLE_API_KEY'i kontrol edin.")
        else:
            with st.spinner("Gemini 2.5 analiz ediyor..."):
                try:
                    son_basliklar = df.sort_values(by='tarih', ascending=False)['baslik'].tolist()
                    ozet = ai_ozet_al(son_basliklar)
                    st.info(f" **AI Analizi:** {ozet}")
                except Exception as e:
                    st.error(f"❌ AI analizi başarısız: {e}")

    # --- Üst Bilgi Kartları ---
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Toplam Haber", len(df))
    with col2:
        en_pozitif = df.groupby('ulke')['skor'].mean().idxmax()
        st.metric("En Pozitif Ülke", en_pozitif.upper())
    with col3: st.metric("Ülke Sayısı", df['ulke'].nunique())
    with col4: st.metric("Son Güncelleme", df['tarih'].max().strftime('%H:%M'))

    # --- Sekmeler ---
    tabs = st.tabs(["🌍 Harita", "📊 Ortalama", "📈 Trend", "☁️ Bulut", "⚔️ Versus", "🏢 Şirketler", "🔬 Analitik"])
    
    with tabs[0]: # Harita
        iso_map = {'us':'USA','kr':'KOR','gr':'GRC','it':'ITA','fr':'FRA','es':'ESP'}
        map_data = df.groupby('ulke')['skor'].mean().reset_index()
        map_data['iso'] = map_data['ulke'].map(iso_map)
        fig_map = px.choropleth(map_data, locations="iso", color="skor", color_continuous_scale='RdYlGn', range_color=[-1, 1])
        st.plotly_chart(fig_map, use_container_width=True)

    with tabs[1]: # Ortalama
        try:
            st.plotly_chart(px.bar(df.groupby('ulke')['skor'].mean().reset_index(), x='ulke', y='skor', color='skor', color_continuous_scale='RdYlGn'), use_container_width=True)
        except Exception as e:
            st.error(f"Grafik oluşturma hatası: {e}")
        
        st.divider()
        st.subheader("🎯 Teknoloji Dikey Analizi")
        try:
            if 'kategori' in df.columns:
                kat_df = df.groupby('kategori').agg({'skor': 'mean', 'baslik': 'count'}).reset_index()
                kat_df.columns = ['Kategori', 'Ortalama Duygu', 'Haber Sayısı']
                
                fig_kat = px.scatter(kat_df, x='Ortalama Duygu', y='Haber Sayısı', 
                                    size='Haber Sayısı', color='Ortalama Duygu',
                                    hover_name='Kategori', color_continuous_scale='RdYlGn',
                                    range_x=[-1, 1], title="Hangi Teknoloji Bugün Daha Riskli?")
                st.plotly_chart(fig_kat, use_container_width=True)
            else:
                st.info("ℹ️ Kategori verisi henüz işlenmedi")
        except Exception as e:
            st.error(f"Kategori analizi hatası: {e}")

    with tabs[2]: # Trend (Güncellenmiş Teknik Görünüm)
        st.subheader("📈 Zaman İçinde Duygu Değişimi")
        try:
            # Veriyi tarihe göre gruplayıp ortalamasını alıyoruz
            trend_data = df.groupby([df['tarih'].dt.date, 'ulke'])['skor'].mean().reset_index()
            fig_trend = px.line(trend_data, x='tarih', y='skor', color='ulke', markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
        except Exception as e:
            st.error(f"Trend grafiği oluşturma hatası: {e}")

    with tabs[3]: # Kelime Bulutu
        st.subheader("☁️ Kelime Bulutu")
        try:
            ulke = st.selectbox("Ülke seçin:", sorted(df['ulke'].unique()))
            metin = " ".join(df[df['ulke'] == ulke]['baslik'].astype(str).tolist())
            if len(metin) > 10:
                wc = WordCloud(width=800, height=400, background_color='white', colormap='coolwarm').generate(metin)
                fig, ax = plt.subplots()
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
            else:
                st.info("ℹ️ Bu ülke için yeterli veri yok")
        except Exception as e:
            st.error(f"Kelime bulutu oluşturma hatası: {e}")

    with tabs[4]: # Versus
        st.subheader("⚔️ Ülke Karşılaştırması")
        try:
            u1, u2 = st.columns(2)
            sel1 = u1.selectbox("1. Ülke", sorted(df['ulke'].unique()), index=0)
            sel2 = u2.selectbox("2. Ülke", sorted(df['ulke'].unique()), index=1 if len(df['ulke'].unique()) > 1 else 0)
            
            vs_data = df[df['ulke'].isin([sel1, sel2])]
            if not vs_data.empty:
                st.plotly_chart(px.line(vs_data, x='tarih', y='skor', color='ulke'), use_container_width=True)
            else:
                st.info("ℹ️ Karşılaştırma için yeterli veri yok")
        except Exception as e:
            st.error(f"Karşılaştırma hatası: {e}")

    with tabs[5]: # ŞİRKET TAKİBİ
        st.subheader("🏢 Şirket Takibi")
        try:
            sirketler = ["Apple", "Nvidia", "Samsung", "Tesla", "Microsoft", "Google", "Amazon", "OpenAI"]
            s_data = []
            for s in sirketler:
                match = df[df['baslik'].str.contains(s, case=False, na=False)]
                if not match.empty:
                    s_data.append({"Şirket": s, "Duygu Skoru": match['skor'].mean(), "Haber Sayısı": len(match)})
            
            if s_data:
                sdf = pd.DataFrame(s_data)
                st.info(f"✓ Bugün toplam {len(sdf)} dev teknoloji şirketi global gündemde yer alıyor.")
                
                c_s1, c_s2 = st.columns([2, 1])
                with c_s1:
                    # Daha estetik bir grafik
                    fig_s = px.bar(sdf, x='Duygu Skoru', y='Şirket', orientation='h', 
                                   color='Duygu Skoru', color_continuous_scale='RdYlGn', 
                                   range_color=[-1,1], text_auto='.2f')
                    fig_s.update_layout(showlegend=False)
                    st.plotly_chart(fig_s, use_container_width=True)
                with c_s2:
                    # Haber sayısına göre sıralanmış tablo
                    st.write("📊 **Haber Yoğunluğu**")
                    st.dataframe(sdf.sort_values(by="Haber Sayısı", ascending=False), hide_index=True)
            else:
                st.info("ℹ️ Henüz takip edilen şirketlerle ilgili bir haber düşmedi.")
        except Exception as e:
            st.error(f"Şirket takip hatası: {e}")

    with tabs[6]: # ADVANCED ANALYTICS
        st.subheader("🔬 Gelişmiş Analitik")
        
        try:
            try:
                from utils import risk_engine, anomaly_detector, trend_predictor
                utils_available = True
            except ImportError:
                st.warning("⚠️ Advanced analytics modülleri yüklenmedi. Utils modülü kontrol edin.")
                utils_available = False
            
            if utils_available:
                try:
                    # Risk Scoring
                    st.write("### 📊 Risk Puanlama (0-100)")
                    df_risk = risk_engine.calculate_risk_score(df)
                    
                    risk_by_country = df_risk.groupby('ulke')['risk_score'].mean().reset_index()
                    fig_risk = px.bar(risk_by_country, x='ulke', y='risk_score', 
                                    color='risk_score', color_continuous_scale='Reds',
                                    range_color=[0, 100], title="Ülke Bazında Risk Skoru")
                    st.plotly_chart(fig_risk, use_container_width=True)
                except Exception as e:
                    st.error(f"Risk puanlama hatası: {e}")
                
                try:
                    # Risk kategorileri
                    st.write("### 🎯 Risk Kategorilendirilmesi")
                    risk_dist = df_risk['risk_category'].value_counts()
                    fig_risk_cat = px.pie(values=risk_dist.values, names=risk_dist.index,
                                          title="Haberlerin Risk Kategori Dağılımı",
                                          color_discrete_map={
                                              'Çok Düşük': '#00ff00',
                                              'Düşük': '#90ee90',
                                              'Orta': '#ffff00',
                                              'Yüksek': '#ff6347',
                                              'Kritik': '#ff0000'
                                          })
                    st.plotly_chart(fig_risk_cat, use_container_width=True)
                except Exception as e:
                    st.error(f"Risk kategorisi hatası: {e}")
                
                try:
                    # Anomaly Detection
                    st.write("### 🚨 Anomali Tespit")
                    df_anomaly = anomaly_detector.detect_spikes(df, column='skor')
                    anomaly_count = df_anomaly['is_anomaly'].sum()
                    st.metric("Tespit Edilen Anomali", anomaly_count)
                    
                    if anomaly_count > 0:
                        anomaly_news = df_anomaly[df_anomaly['is_anomaly']][['tarih', 'baslik', 'skor', 'anomaly_score']]
                        st.dataframe(anomaly_news, use_container_width=True)
                except Exception as e:
                    st.error(f"Anomali tespit hatası: {e}")
                
                try:
                    # Trend Prediction
                    st.write("### 📈 Trend Prediksiyon (7 Gün)")
                    selected_country = st.selectbox("Ülke seçin:", df['ulke'].unique(), key="trend_select")
                    
                    trend_result = trend_predictor.predict_sentiment_trend(df, selected_country, days_ahead=7)
                    
                    if trend_result['status'] == 'success':
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Güncel Duygu", f"{trend_result['current_sentiment']:.2f}")
                        with col2:
                            st.metric("7-Günlük Ort.", f"{trend_result['7day_average']:.2f}")
                        with col3:
                            st.metric("30-Günlük Ort.", f"{trend_result['30day_average']:.2f}")
                        with col4:
                            st.metric("Volatilite", f"{trend_result['volatility']:.2f}")
                        
                        st.write(f"**Trend Yönü:** {trend_result['trend']}")
                    else:
                        st.info(trend_result.get('message', 'Trend verisi hesaplanamadı'))
                except Exception as e:
                    st.error(f"Trend prediksiyon hatası: {e}")
        
        except Exception as e:
            st.error(f"❌ Analitik hatası: {e}")

    # --- Detay Tablosu ---
    st.divider()
    st.subheader("📋 Detaylı İnceleme")
    try:
        if not df.empty:
            secilen = st.selectbox("Detaylı incele:", sorted(df['ulke'].unique()))
            detail_df = df[df['ulke'] == secilen].sort_values(by='tarih', ascending=False)[['tarih', 'baslik', 'skor', 'kategori', 'url']]
            st.dataframe(detail_df, use_container_width=True)
        else:
            st.info("ℹ️ Detaylı veri yok")
    except Exception as e:
        st.error(f"Detay tablosu hatası: {e}")

else:
    st.warning("⚠️ Veri bekleniyor... Lütfen main.py'yi çalıştırın.")