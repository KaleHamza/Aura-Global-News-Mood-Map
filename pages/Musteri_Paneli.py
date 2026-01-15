import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Müşteri Görünümü", layout="wide")

# --- VERİ YÜKLEME ---
def verileri_yukle():
    try:
        # Veritabanı bir üst klasörde olduğu için yolu ../ ile vermiyoruz, 
        # Streamlit kök dizinden çalışır, o yüzden direkt ismi yazıyoruz.
        conn = sqlite3.connect("haber_analizi.db")
        df = pd.read_sql_query("SELECT * FROM haberler", conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

df = verileri_yukle()

# --- AI AYARLARI (Senin Key'in) ---
API_KEY = "Your_API_Key_Here"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash') 
except:
    pass

def ceo_raporu_yaz(haberler_listesi):
    if not haberler_listesi: return "Veri yok."
    metin = "\n- ".join(haberler_listesi[:20])
    prompt = f"""
    Sen üst düzey bir strateji danışmanısın. Aşağıdaki teknoloji haberlerini analiz et.
    Müşterin olan CEO için teknik terim kullanmadan, doğrudan iş dünyasına etkilerini içeren 
    3 maddelik bir 'Risk ve Fırsat Bülteni' hazırla. Türkçe olsun.
    
    Haberler:
    {metin}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI Servisi şu an yanıt veremiyor."

def risk_kadrani_ciz(skor):
    normalized_score = (skor + 1) * 50
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = normalized_score,
        title = {'text': "KÜRESEL GÜVEN ENDEKSİ"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 40], 'color': "#ff4b4b"},
                {'range': [40, 60], 'color': "#faca2b"},
                {'range': [60, 100], 'color': "#09ab3b"}
            ],
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- ARAYÜZ ---
st.title("💼 Aura Executive: Stratejik Karar Ekranı")
st.markdown("---")

if not df.empty:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Piyasa Nabzı")
        global_ortalama = df['skor'].mean()
        st.plotly_chart(risk_kadrani_ciz(global_ortalama), use_container_width=True)
        if global_ortalama < -0.2:
            st.error("⚠️ PİYASA RİSKLİ")
        elif global_ortalama > 0.2:
            st.success("✅ PİYASA GÜVENLİ")
        else:
            st.warning("⚖️ PİYASA DENGELİ")

    with col2:
        st.subheader("🤖 AI Yönetici Özeti")
        if st.button("📝 Raporu Oluştur"):
            with st.spinner("Analiz ediliyor..."):
                son_basliklar = df.sort_values(by='tarih', ascending=False)['baslik'].tolist()
                rapor = ceo_raporu_yaz(son_basliklar)
                st.info(rapor)
        else:
            st.write("Güncel strateji raporu için butona tıklayın.")

    st.markdown("---")
    st.subheader("🌍 Ülke Bazlı Risk Durumu")
    cols = st.columns(6)
    bayraklar = {'us':'🇺🇸', 'kr':'🇰🇷', 'fr':'🇫🇷', 'es':'🇪🇸', 'it':'🇮🇹', 'gr':'🇬🇷'}
    
    for idx, ulke in enumerate(df['ulke'].unique()):
        skor = df[df['ulke'] == ulke]['skor'].mean()
        renk = "🟢" if skor > 0.2 else ("🔴" if skor < -0.2 else "🟡")
        with cols[idx % 6]:
            st.markdown(f"### {bayraklar.get(ulke, ulke)}")
            st.write(f"{renk} Skor: %{int((skor+1)*50)}")

else:
    st.warning("Veri bekleniyor...")