import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="KRFinans Terminali", page_icon="📈", layout="wide")

# --- SOL MENÜ (KONTROL PANELİ) ---
st.sidebar.header("🚀 KRFinans Ana Menü")
mod_secimi = st.sidebar.radio("Çalışma Modu", ["Tekli Hisse Analizi", "Piyasa Tarayıcı"])

st.sidebar.markdown("---")

# --- HİSSE TARAYICI FONKSİYONU ---
def hisse_analiz_et(sembol):
    try:
        h = yf.Ticker(sembol)
        df = h.history(period="60d", interval="1d") # Analiz için yeterli veri
        if df.empty: return None
        
        # Göstergeler
        df['SMA22'] = df['Close'].rolling(window=22).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['BB_Orta'] = df['Close'].rolling(window=20).mean()
        df['BB_Alt'] = df['BB_Orta'] - (2 * df['Close'].rolling(window=20).std())
        
        delta = df['Close'].diff()
        kazanc = delta.where(delta > 0, 0)
        kayip = -delta.where(delta < 0, 0)
        rs = kazanc.ewm(alpha=1/14, adjust=False).mean() / kayip.ewm(alpha=1/14, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Sinyaller
        son = df.iloc[-1]
        onceki = df.iloc[-2]
        
        sinyal = "Nötr"
        # KR-Dip Avcısı Kontrolü
        vol_sma = df['Volume'].rolling(window=20).mean().iloc[-1]
        if (son['Low'] <= son['BB_Alt']) and (son['Volume'] > vol_sma * 1.5) and (son['RSI'] < 40):
            sinyal = "💎 KR-DİP FIRSATI"
        elif son['SMA22'] > son['SMA50'] and onceki['SMA22'] <= onceki['SMA50']:
            sinyal = "✅ AL (Golden Cross)"
        elif son['RSI'] < 30:
            sinyal = "🟢 AŞIRI UCUZ"
        elif son['RSI'] > 70:
            sinyal = "🔴 AŞIRI ŞİŞKİN"
            
        return {
            "Hisse": sembol.replace(".IS", ""),
            "Fiyat": round(son['Close'], 2),
            "Günlük Değişim %": round(((son['Close'] / onceki['Close']) - 1) * 100, 2),
            "RSI": round(son['RSI'], 1),
            "Durum": sinyal
        }
    except:
        return None

# --- MOD 1: TEKLİ ANALİZ ---
if mod_secimi == "Tekli Hisse Analizi":
    st.sidebar.markdown("**Hisse Kodunu Yazın:**")
    girilen_kod = st.sidebar.text_input("Örn: THYAO, TUPRS, ASELS", value="ASELS")

    girilen_kod = girilen_kod.upper().strip()
    if not girilen_kod.endswith(".IS"):
        hisse_sembolu = f"{girilen_kod}.IS"
    else:
        hisse_sembolu = girilen_kod

    st.sidebar.subheader("⏱️ Zaman ve Mum Ayarları")

    interval_secimi = st.sidebar.selectbox("Mum Aralığı (Periyot)", ["15 Dakika", "30 Dakika", "1 Saat", "4 Saat", "1 Gün", "1 Hafta", "1 Ay"], index=4)
    interval_sozlugu = {"15 Dakika": "15m", "30 Dakika": "30m", "1 Saat": "1h", "4 Saat": "4h", "1 Gün": "1d", "1 Hafta": "1wk", "1 Ay": "1mo"}
    secilen_interval = interval_sozlugu[interval_secimi]

    # yfinance kısıtlamalarına göre çökmemesi için Dinamik Menü
    if secilen_interval in ["15m", "30m"]:
        periyot_secenekleri = ["1 Gün", "5 Gün", "1 Ay", "60 Gün"]
        periyot_sozlugu = {"1 Gün": "1d", "5 Gün": "5d", "1 Ay": "1mo", "60 Gün": "60d"}
        index_val = 1
    elif secilen_interval in ["1h", "4h"]:
        periyot_secenekleri = ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "730 Gün"]
        periyot_sozlugu = {"1 Ay": "1mo", "3 Ay": "3mo", "6 Ay": "6mo", "1 Yıl": "1y", "730 Gün": "730d"}
        index_val = 1
    else:
        periyot_secenekleri = ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "2 Yıl", "5 Yıl", "Maksimum"]
        periyot_sozlugu = {"1 Ay": "1mo", "3 Ay": "3mo", "6 Ay": "6mo", "1 Yıl": "1y", "2 Yıl": "2y", "5 Yıl": "5y", "Maksimum": "max"}
        index_val = 3

    periyot_secimi = st.sidebar.selectbox("Grafik Süresi (Geriye Dönük)", periyot_secenekleri, index=index_val)
    secilen_periyot = periyot_sozlugu[periyot_secimi]

    st.sidebar.markdown("---")

    st.sidebar.subheader("👁️ Görünüm Ayarları")
    goster_ho = st.sidebar.checkbox("Hareketli Ortalamalar (HO)", value=True)
    goster_sinyal = st.sidebar.checkbox("Al/Sat Okları", value=False)
    goster_bollinger = st.sidebar.checkbox("Bollinger Zırhı", value=True)
    goster_formasyon = st.sidebar.checkbox("Boğa/Ayı Emojileri", value=False)
    goster_kr_ozel = st.sidebar.checkbox("💎 KR-Dip Avcısı Sinyali", value=True)
    goster_fibo = st.sidebar.checkbox("Fibonacci Seviyeleri", value=False)
    goster_rsi = st.sidebar.checkbox("RSI Alt Grafiği", value=True)
    goster_macd = st.sidebar.checkbox("MACD Alt Grafiği", value=True)

    with st.sidebar.expander("🧮 Detaylı Algoritma Ayarları"):
        st.info("Not: Kısa/Uzun Vade ayarları seçtiğiniz 'Mum Aralığına' göre çalışır.")
        kisa_vade = st.number_input("Kısa Vade HO", min_value=1, max_value=200, value=22, step=1)
        uzun_vade = st.number_input("Uzun Vade HO", min_value=2, max_value=500, value=50, step=1)
        rsi_periyot = st.number_input("RSI Periyodu", min_value=1, max_value=100, value=14, step=1)
        bb_periyot = st.number_input("BB Periyodu", min_value=5, max_value=100, value=20, step=1)
        bb_std = st.number_input("BB Std. Sapma", min_value=1.0, max_value=5.0, value=2.0, step=0.1)
        macd_hizli = st.number_input("MACD Hızlı", min_value=1, max_value=50, value=12, step=1)
        macd_yavas = st.number_input("MACD Yavaş", min_value=1, max_value=100, value=26, step=1)
        macd_sinyal = st.number_input("MACD Sinyal", min_value=1, max_value=50, value=9, step=1)

    # --- ANA EKRAN VE VERİ ÇEKİMİ ---
    st.title("KRFinans Yatırım Terminali 🚀")

    @st.cache_data 
    def veri_getir(sembol, periyot, aralik):
        hisse = yf.Ticker(sembol)
        
        # 4 SAATLİK MUM MÜHENDİSLİĞİ
        if aralik == "4h":
            df = hisse.history(period=periyot, interval="1h")
            if not df.empty:
                df = df.resample('4h').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
        else:
            df = hisse.history(period=periyot, interval=aralik)
            
        try:
            bilgi = hisse.info
        except:
            bilgi = {}
        return df, bilgi

    with st.spinner(f"{girilen_kod} verileri çekiliyor..."):
        veri, sirket_bilgisi = veri_getir(hisse_sembolu, secilen_periyot, secilen_interval)

    if veri.empty:
        st.error(f"❌ '{girilen_kod}' kodlu hisse bulunamadı veya bu zaman aralığı için veri yok.")
    else:
        # --- TEMEL ANALİZ KARTLARI ---
        st.markdown("### 📊 Temel Analiz Özeti")
        col1, col2, col3, col4 = st.columns(4)
        
        son_fiyat = veri['Close'].iloc[-1]
        fk_orani = sirket_bilgisi.get('trailingPE', 'Yok')
        pd_degeri = sirket_bilgisi.get('marketCap', 0)
        temettu_verimi = sirket_bilgisi.get('dividendYield', 0)
        
        pd_milyar = f"{pd_degeri / 1e9:.2f} Milyar ₺" if pd_degeri else "Bilinmiyor"
        temettu_yuzde = f"%{temettu_verimi * 100:.2f}" if temettu_verimi else "Yok"
        fk_formatli = f"{fk_orani:.2f}" if isinstance(fk_orani, float) else fk_orani

        col1.metric("Anlık Fiyat", f"{son_fiyat:.2f} ₺")
        col2.metric("F/K Oranı", fk_formatli)
        col3.metric("Piyasa Değeri", pd_milyar)
        col4.metric("Temettü Verimi", temettu_yuzde)
        
        st.markdown("---")

        # --- MATEMATİK VE ALGORİTMALAR ---
        sma_kisa_kolon = f"SMA_{kisa_vade}"
        sma_uzun_kolon = f"SMA_{uzun_vade}"
        veri[sma_kisa_kolon] = veri['Close'].rolling(window=kisa_vade).mean()
        veri[sma_uzun_kolon] = veri['Close'].rolling(window=uzun_vade).mean()

        veri['Sinyal'] = 0 
        veri.loc[(veri[sma_kisa_kolon] > veri[sma_uzun_kolon]) & (veri[sma_kisa_kolon].shift(1) <= veri[sma_uzun_kolon].shift(1)), 'Sinyal'] = 1
        veri.loc[(veri[sma_kisa_kolon] < veri[sma_uzun_kolon]) & (veri[sma_kisa_kolon].shift(1) >= veri[sma_uzun_kolon].shift(1)), 'Sinyal'] = -1

        veri['Yutan_Boga'] = (veri['Close'].shift(1) < veri['Open'].shift(1)) & (veri['Close'] > veri['Open']) & (veri['Open'] <= veri['Close'].shift(1)) & (veri['Close'] >= veri['Open'].shift(1))
        veri['Yutan_Ayi'] = (veri['Close'].shift(1) > veri['Open'].shift(1)) & (veri['Close'] < veri['Open']) & (veri['Open'] >= veri['Close'].shift(1)) & (veri['Close'] <= veri['Open'].shift(1))

        veri['BB_Orta'] = veri['Close'].rolling(window=bb_periyot).mean()
        veri['BB_Std'] = veri['Close'].rolling(window=bb_periyot).std()
        veri['BB_Ust'] = veri['BB_Orta'] + (bb_std * veri['BB_Std'])
        veri['BB_Alt'] = veri['BB_Orta'] - (bb_std * veri['BB_Std'])

        delta = veri['Close'].diff()
        kazanc = (delta.where(delta > 0, 0)).fillna(0)
        kayip = (-delta.where(delta < 0, 0)).fillna(0)
        rs = kazanc.ewm(alpha=1/rsi_periyot, adjust=False).mean() / kayip.ewm(alpha=1/rsi_periyot, adjust=False).mean()
        veri['RSI'] = 100 - (100 / (1 + rs))

        veri['EMA_Hizli'] = veri['Close'].ewm(span=macd_hizli, adjust=False).mean()
        veri['EMA_Yavas'] = veri['Close'].ewm(span=macd_yavas, adjust=False).mean()
        veri['MACD'] = veri['EMA_Hizli'] - veri['EMA_Yavas']
        veri['MACD_Sinyal'] = veri['MACD'].ewm(span=macd_sinyal, adjust=False).mean()
        veri['MACD_Hist'] = veri['MACD'] - veri['MACD_Sinyal']
        macd_renkleri = ['green' if val >= 0 else 'red' for val in veri['MACD_Hist']]

        # --- KR-ÖZEL SİNYALİ (HACİMLİ DİP AVCISI) ---
        veri['Vol_SMA_20'] = veri['Volume'].rolling(window=20).mean()
        sart_hacim = veri['Volume'] > (veri['Vol_SMA_20'] * 1.5)
        sart_bollinger = veri['Low'] <= veri['BB_Alt']
        sart_rsi = veri['RSI'] < 40
        veri['KR_Ozel_Sinyal'] = sart_hacim & sart_bollinger & sart_rsi

        # --- DİNAMİK GRAFİK MİMARİSİ ---
        satir_sayisi = 1
        if goster_rsi: satir_sayisi += 1
        if goster_macd: satir_sayisi += 1

        if satir_sayisi == 3:
            row_heights = [0.60, 0.20, 0.20]; rsi_row = 2; macd_row = 3; grafik_boyu = 950
        elif satir_sayisi == 2:
            row_heights = [0.75, 0.25]; rsi_row = 2 if goster_rsi else None; macd_row = 2 if goster_macd else None; grafik_boyu = 750
        else:
            row_heights = [1.0]; rsi_row = None; macd_row = None; grafik_boyu = 600

        st.subheader(f"{girilen_kod} - Teknik Grafik ({interval_secimi}lik Mumlar)")
        
        fig = make_subplots(rows=satir_sayisi, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=row_heights)

        fig.add_trace(go.Candlestick(x=veri.index, open=veri['Open'], high=veri['High'], low=veri['Low'], close=veri['Close'], increasing_line_color='green', decreasing_line_color='red', name="Fiyat"), row=1, col=1)

        if goster_bollinger:
            fig.add_trace(go.Scatter(x=veri.index, y=veri['BB_Ust'], mode='lines', line=dict(color='gray', width=1, dash='dot'), name="BB Üst"), row=1, col=1)
            fig.add_trace(go.Scatter(x=veri.index, y=veri['BB_Alt'], mode='lines', line=dict(color='gray', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128, 128, 128, 0.1)', name="BB Alt"), row=1, col=1)

        if goster_ho:
            fig.add_trace(go.Scatter(x=veri.index, y=veri[sma_kisa_kolon], mode='lines', line=dict(color='blue', width=1.5), name=f"{kisa_vade} Mum HO"), row=1, col=1)
            fig.add_trace(go.Scatter(x=veri.index, y=veri[sma_uzun_kolon], mode='lines', line=dict(color='orange', width=2), name=f"{uzun_vade} Mum HO"), row=1, col=1)

        if goster_sinyal:
            al_noktalari = veri[veri['Sinyal'] == 1]
            sat_noktalari = veri[veri['Sinyal'] == -1]
            if not al_noktalari.empty: fig.add_trace(go.Scatter(x=al_noktalari.index, y=al_noktalari['Low'] * 0.95, mode='markers', marker=dict(symbol='triangle-up', color='green', size=16, line=dict(width=1, color='black')), name='HO Al'), row=1, col=1)
            if not sat_noktalari.empty: fig.add_trace(go.Scatter(x=sat_noktalari.index, y=sat_noktalari['High'] * 1.05, mode='markers', marker=dict(symbol='triangle-down', color='red', size=16, line=dict(width=1, color='black')), name='HO Sat'), row=1, col=1)

        if goster_formasyon:
            boga_noktalari = veri[veri['Yutan_Boga']]
            ayi_noktalari = veri[veri['Yutan_Ayi']]
            if not boga_noktalari.empty: fig.add_trace(go.Scatter(x=boga_noktalari.index, y=boga_noktalari['Low'] * 0.92, mode='text', text="🐂", textposition="bottom center", name="Yutan Boğa", textfont=dict(size=20)), row=1, col=1)
            if not ayi_noktalari.empty: fig.add_trace(go.Scatter(x=ayi_noktalari.index, y=ayi_noktalari['High'] * 1.08, mode='text', text="🐻", textposition="top center", name="Yutan Ayı", textfont=dict(size=20)), row=1, col=1)

        if goster_kr_ozel:
            kr_noktalari = veri[veri['KR_Ozel_Sinyal']]
            if not kr_noktalari.empty:
                fig.add_trace(go.Scatter(x=kr_noktalari.index, y=kr_noktalari['Low'] * 0.88, mode='text', text="💎", textposition="bottom center", name="KR-Dip Avcısı", textfont=dict(size=24)), row=1, col=1)

        if goster_fibo:
            max_fiyat = veri['High'].max()
            min_fiyat = veri['Low'].min()
            fark = max_fiyat - min_fiyat
            fibo_seviyeler = [(0.0, max_fiyat, "0.0%", "red"), (0.236, max_fiyat - fark * 0.236, "23.6%", "orange"), (0.382, max_fiyat - fark * 0.382, "38.2%", "yellow"), (0.5, max_fiyat - fark * 0.5, "50.0%", "green"), (0.618, max_fiyat - fark * 0.618, "61.8%", "blue"), (1.0, min_fiyat, "100.0%", "gray")]
            for oran, seviye, etiket, renk in fibo_seviyeler:
                fig.add_hline(y=seviye, line_dash="dash", line_color=renk, line_width=1, annotation_text=etiket, annotation_position="right", row=1, col=1)

        if goster_rsi:
            fig.add_trace(go.Scatter(x=veri.index, y=veri['RSI'], mode='lines', line=dict(color='purple', width=1.5), name=f"RSI ({rsi_periyot})"), row=rsi_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=rsi_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=rsi_row, col=1)

        if goster_macd:
            fig.add_trace(go.Bar(x=veri.index, y=veri['MACD_Hist'], marker_color=macd_renkleri, name="MACD Hist"), row=macd_row, col=1)
            fig.add_trace(go.Scatter(x=veri.index, y=veri['MACD'], mode='lines', line=dict(color='blue', width=1.5), name="MACD"), row=macd_row, col=1)
            fig.add_trace(go.Scatter(x=veri.index, y=veri['MACD_Sinyal'], mode='lines', line=dict(color='orange', width=1.5), name="Sinyal"), row=macd_row, col=1)

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        fig.update_layout(
            height=grafik_boyu, margin=dict(l=0, r=0, t=30, b=0), hovermode='x unified', dragmode='pan',
            newshape=dict(line_color='yellow', line_width=2), xaxis_rangeslider_visible=False
        )

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape']})

        # --- 🤖 OTOMATİK ALGORİTMA YORUMCUSU ---
        st.markdown("---")
        st.subheader("🤖 Algoritmik Yorumcu (Otomatik Analiz)")
        
        son_kapanis = veri['Close'].iloc[-1]
        son_rsi = veri['RSI'].iloc[-1]
        son_macd = veri['MACD'].iloc[-1]
        son_sinyal = veri['MACD_Sinyal'].iloc[-1]
        
        son_tarih = veri.index[-1]
        tarih_metni = son_tarih.strftime('%d-%m-%Y %H:%M') if secilen_interval in ['15m', '30m', '1h', '4h'] else son_tarih.strftime('%d-%m-%Y')
        
        yorum_metni = f"**{girilen_kod}** hissesinin son işlem anına ({tarih_metni}) ait sistemin okuduğu teknik görünüm:\n\n"
        
        if veri[sma_kisa_kolon].iloc[-1] > veri[sma_uzun_kolon].iloc[-1]:
            yorum_metni += f"* 📈 **Trend Yönü:** {kisa_vade} mumluk kısa vadeli ortalama, {uzun_vade} mumluk uzun vadeli ortalamanın **üzerinde**. Trend yönü yukarı.\n"
        else:
            yorum_metni += f"* 📉 **Trend Yönü:** {kisa_vade} mumluk kısa vadeli ortalama, {uzun_vade} mumluk uzun vadeli ortalamanın **altında**. Trend yönü aşağı.\n"

        if son_rsi >= 70:
            yorum_metni += f"* ⚠️ **Fiyat Şişkinliği (RSI):** Gösterge {son_rsi:.1f} seviyesinde! Hisse şu anki zaman diliminde aşırı değerlenmiş (şişmiş). Kar satışlarına dikkat.\n"
        elif son_rsi <= 30:
            yorum_metni += f"* 🟢 **Fiyat Ucuzluğu (RSI):** Gösterge {son_rsi:.1f} seviyesinde! Hisse bu periyotta aşırı satılmış ve ucuzlamış. Tepki alımı gelebilir.\n"
        else:
            yorum_metni += f"* ⚖️ **Fiyat Dengesi (RSI):** Gösterge {son_rsi:.1f} seviyesinde. Fiyat dengeli bir bölgede, uç noktalarda değil.\n"

        if son_macd > son_sinyal:
            yorum_metni += f"* 🚀 **Piyasa İştahı (MACD):** MACD çizgisi sinyal çizgisini yukarı kesmiş durumda. Alım iştahı ve momentum güçlü.\n"
        else:
            yorum_metni += f"* 🐢 **Piyasa İştahı (MACD):** MACD çizgisi sinyal çizgisinin altında. Yükseliş gücü zayıf görünüyor.\n"

        if veri['KR_Ozel_Sinyal'].iloc[-1]:
            yorum_metni += f"* 💎 **KR-DİP AVCISI:** Sistem şu an hacimli bir dip dönüş formasyonu yakaladı! Bu periyotta güçlü bir 'Trend Dönüş' sinyali.\n"
        elif veri['Yutan_Boga'].iloc[-1]:
            yorum_metni += f"* 🐂 **MUM FORMASYONU:** Son mum 'Yutan Boğa' mumu. Alıcıların gücü eline aldığını gösterir.\n"
        elif veri['Yutan_Ayi'].iloc[-1]:
            yorum_metni += f"* 🐻 **MUM FORMASYONU:** Son mum 'Yutan Ayı' mumu. Satıcıların baskın gelmeye başladığını gösterir.\n"
            
        st.info(yorum_metni)

        st.sidebar.markdown("---")
        csv_verisi = veri.to_csv().encode('utf-8')
        st.sidebar.download_button(label="📥 Tüm Verileri Excel Olarak İndir", data=csv_verisi, file_name=f"{girilen_kod}_KRFinans_{secilen_interval}.csv", mime='text/csv')

# --- MOD 2: PİYASA TARAYICI ---
else:
    st.title("🔍 KRFinans - Akıllı Piyasa Tarayıcı")
    
    # Kullanıcıya tarama havuzunu seçtiriyoruz
    tarama_kapsami = st.selectbox("Tarama Havuzu Seçin:", ["BİST 30 (Hızlı Tarama)", "BİST 50", "BİST 100 (Kapsamlı Tarama)"])
    st.write(f"{tarama_kapsami} hisseleri taranıyor ve KR-Algoritmalarına göre listeleniyor...")
    
    # BİST HİSSE LİSTELERİ
    liste_bist30 = ['AKBNK.IS', 'ARCLK.IS', 'ASELS.IS', 'BIMAS.IS', 'EKGYO.IS', 'ENKAI.IS', 'EREGL.IS', 'FROTO.IS', 'GARAN.IS', 'GUBRF.IS', 'HALKB.IS', 'HEKTS.IS', 'ISCTR.IS', 'KCHOL.IS', 'KOZAA.IS', 'KOZAL.IS', 'KRDMD.IS', 'PETKM.IS', 'PGSUS.IS', 'SAHOL.IS', 'SASA.IS', 'SISE.IS', 'TAVHL.IS', 'TCELL.IS', 'THYAO.IS', 'TKFEN.IS', 'TTKOM.IS', 'TUPRS.IS', 'VAKBN.IS', 'YKBNK.IS']
    
    liste_bist50 = liste_bist30 + ['ALARK.IS', 'CCOLA.IS', 'DOAS.IS', 'ENJSA.IS', 'GESAN.IS', 'ISMEN.IS', 'KONTR.IS', 'MGROS.IS', 'ODAS.IS', 'OYAKC.IS', 'SOKM.IS', 'TOASO.IS', 'TSKB.IS', 'TTRAK.IS', 'VESBE.IS', 'YGGYO.IS', 'ZOREN.IS', 'AEFES.IS', 'ASTOR.IS', 'EUPWR.IS']
    
    liste_bist100 = liste_bist50 + ['AGHOL.IS', 'AHGAZ.IS', 'AKFGY.IS', 'AKSA.IS', 'AKSEN.IS', 'ALBRK.IS', 'ALFAS.IS', 'AYDEM.IS', 'BAGFS.IS', 'BERA.IS', 'BRSAN.IS', 'CANTE.IS', 'CIMSA.IS', 'CWENE.IS', 'DOHOL.IS', 'ECILC.IS', 'EGEEN.IS', 'ENERY.IS', 'EUREN.IS', 'FENER.IS', 'GENIL.IS', 'GLYHO.IS', 'GWIND.IS', 'HLGYO.IS', 'IMASM.IS', 'IPEKE.IS', 'ISGYO.IS', 'KARSN.IS', 'KAYSE.IS', 'KMPUR.IS', 'KORDS.IS', 'KZBGY.IS', 'MAVI.IS', 'MIATK.IS', 'OTKAR.IS', 'PENTA.IS', 'QUAGR.IS', 'SARKY.IS', 'SKBNK.IS', 'SMRTG.IS', 'TUKAS.IS', 'ULKER.IS', 'VAKKO.IS', 'YEOTK.IS', 'ZGOLD.IS']

    # Seçime göre listeyi belirliyoruz
    if "30" in tarama_kapsami:
        taranacak_liste = liste_bist30
    elif "50" in tarama_kapsami:
        taranacak_liste = liste_bist50
    else:
        taranacak_liste = liste_bist100

    if st.button("Taramayı Başlat"):
        sonuclar = []
        progress_bar = st.progress(0)
        durum_metni = st.empty()
        
        import time # Ban yememek için bekleme modülü
        
        for i, hisse in enumerate(taranacak_liste):
            durum_metni.text(f"Taranıyor: {hisse} ({i+1}/{len(taranacak_liste)})")
            res = hisse_analiz_et(hisse)
            if res:
                sonuclar.append(res)
            
            # Eğer 30'dan fazla hisse taranıyorsa, Yahoo bizi banlamasın diye her hissede çok kısa (0.2 saniye) bekliyoruz
            if len(taranacak_liste) > 30:
                time.sleep(0.2)
                
            progress_bar.progress((i + 1) / len(taranacak_liste))
        
        durum_metni.text("Tarama Bitti!")
        df_sonuc = pd.DataFrame(sonuclar)
        
        # Renklendirme ve Görselleştirme
        def renk_ata(val):
            if isinstance(val, str):
                if "💎" in val: color = '#3fb5ff' # Elmas mavisi
                elif "✅" in val or "🟢" in val: color = '#2ecc71' # Yeşil
                elif "🔴" in val: color = '#e74c3c' # Kırmızı
                else: color = 'white'
                return f'color: {color}; font-weight: bold'
            return ''

        try:
            styled_df = df_sonuc.style.map(renk_ata, subset=['Durum'])
        except AttributeError:
            styled_df = df_sonuc.style.applymap(renk_ata, subset=['Durum'])

        st.dataframe(styled_df, use_container_width=True)
        
        # Özet İstatistikler
        col1, col2 = st.columns(2)
        firsatlar = df_sonuc[df_sonuc['Durum'].str.contains("💎|✅|🟢")]
        col1.success(f"🔍 Tarama Tamamlandı! BİST{len(taranacak_liste)} havuzunda {len(firsatlar)} hissede alım/fırsat sinyali bulundu.")
        
        if not firsatlar.empty:
            st.subheader("🔥 Öne Çıkan Fırsat Listesi")
            st.table(firsatlar)
    
    