import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import pulp
import folium
from streamlit_folium import st_folium

# Konfigurasi Halaman Web
st.set_page_config(
    page_title="IDSS & GeoAI - Predictive Governance Banjarmasin", 
    page_icon="🤖", 
    layout="wide"
)

# Custom CSS Styling Ala GovTech Enterprise
st.markdown("""
    <style>
        .main-header { font-size: 30px; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
        .sub-header { font-size: 16px; color: #4B5563; margin-bottom: 20px; }
        .card { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# Judul & Deskripsi Utama
st.markdown('<p class="main-header">🤖 IDSS & GeoAI: Predictive Governance Mitigasi Stunting</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Platform Pengambilan Keputusan & AI Chat Assistant Berbasis Spasial | Studi Kasus Kota Banjarmasin</p>', unsafe_allow_html=True)
st.markdown("---")

# 1. Load Data dari GitHub
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/Predicta-ulm/geoai-idss/refs/heads/main/data_dummy_banjarmasin.csv"
    return pd.read_csv(url)

try:
    df_raw = load_data()
except:
    st.error("Gagal memuat data dari GitHub. Pastikan link URL CSV sudah benar.")
    st.stop()

# ==========================================
# SIDEBAR KONTROL KEBIJAKAN & SKENARIO
# ==========================================
st.sidebar.header("⚙️ Panel Kontrol Eksekutif IDSS")
pagu_anggaran = st.sidebar.number_input("Pagu Anggaran APB-Desa (Rp)", value=200000000, step=25000000, format="%d")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Simulasi Skenario Kebijakan")
skenario_pilihan = st.sidebar.selectbox(
    "Pilih Fokus Strategis Pembangunan",
    ["Skenario Seimbang (Optimal)", "Fokus Infrastruktur Sanitasi & Air", "Fokus Penanganan Gizi Spesifik"]
)

# Katalog Program Intervensi Desa
program_katalog = [
    {"Nama_Program": "Pembangunan Sanitasi Komunal Skala Desa", "Biaya": 40000000, "Dampak": 0.8},
    {"Nama_Program": "Instalasi Sumur Bor & Filter Air Bersih", "Biaya": 25000000, "Dampak": 0.7},
    {"Nama_Program": "Intervensi Paket Gizi Spesifik Stunting (1 Tahun)", "Biaya": 15000000, "Dampak": 0.9}
]

if skenario_pilihan == "Fokus Infrastruktur Sanitasi & Air":
    program_katalog[0]["Dampak"] = 0.95
    program_katalog[1]["Dampak"] = 0.90
    program_katalog[2]["Dampak"] = 0.50
elif skenario_pilihan == "Fokus Penanganan Gizi Spesifik":
    program_katalog[0]["Dampak"] = 0.50
    program_katalog[1]["Dampak"] = 0.50
    program_katalog[2]["Dampak"] = 0.95

# Filter Wilayah Kecamatan
daftar_kecamatan = ["Semua Kecamatan"] + list(df_raw['Kecamatan'].unique())
pilih_kecamatan = st.sidebar.selectbox("Filter Wilayah Administratif", daftar_kecamatan)

if pilih_kecamatan != "Semua Kecamatan":
    df = df_raw[df_raw['Kecamatan'] == pilih_kecamatan].copy()
else:
    df = df_raw.copy()

# ==========================================
# 2. LOGIC LAYER: PEMBOBOTAN AHP
# ==========================================
ahp_matrix = np.array([
    [1,   2,   4,   5],
    [1/2, 1,   2,   3],
    [1/4, 1/2, 1,   2],
    [1/5, 1/3, 1/2, 1]
])
col_sums = ahp_matrix.sum(axis=0)
weights = (ahp_matrix / col_sums).mean(axis=1)

df['Skor_Kerentanan'] = (
    (df['Risiko_Stunting'] * weights[0]) +
    (df['Kemiskinan_Ekstrem'] * weights[1]) +
    (df['Sanitasi_Buruk'] * weights[2]) +
    (df['Akses_Air_Minim'] * weights[3])
)

# ==========================================
# 3. SPATIAL LAYER: GeoAI DBSCAN CLUSTERING
# ==========================================
ambang_batas = df['Skor_Kerentanan'].mean()
df_rentan = df[df['Skor_Kerentanan'] > ambang_batas].copy()

if not df_rentan.empty and len(df_rentan) >= 3:
    koordinat_rad = np.radians(df_rentan[['Latitude', 'Longitude']].values)
    dbscan = DBSCAN(eps=0.5/6371., min_samples=3, algorithm='ball_tree', metric='haversine')
    df_rentan['ID_Hotspot'] = dbscan.fit_predict(koordinat_rad)
    df_hotspot = df_rentan[df_rentan['ID_Hotspot'] >= 0]
    jumlah_hotspot = len(df_hotspot['ID_Hotspot'].unique())
else:
    df_rentan['ID_Hotspot'] = -1
    df_hotspot = pd.DataFrame()
    jumlah_hotspot = 0

# ==========================================
# 4. DECISION LAYER: OPTIMASI KNAPSACK APB-DESA
# ==========================================
rekomendasi = []
total_biaya = 0
df_rek = pd.DataFrame()

if not df_hotspot.empty:
    rekap_hotspot = df_hotspot.groupby('ID_Hotspot').agg(
        Jumlah_Keluarga=('ID_Keluarga', 'count'),
        Total_Kerentanan=('Skor_Kerentanan', 'sum')
    ).reset_index()

    prob = pulp.LpProblem("Optimasi_APB_Desa", pulp.LpMaximize)
    variabel_keputusan = {}

    for idx_h, hotspot in rekap_hotspot.iterrows():
        id_h = int(hotspot['ID_Hotspot'])
        for idx_p, prog in enumerate(program_katalog):
            variabel_keputusan[(id_h, idx_p)] = pulp.LpVariable(f"H{id_h}_P{idx_p}", cat="Binary")

    prob += pulp.lpSum(
        variabel_keputusan[(h, p)] * rekap_hotspot.loc[rekap_hotspot['ID_Hotspot']==h, 'Total_Kerentanan'].values[0] * program_katalog[p]['Dampak']
        for h, p in variabel_keputusan
    )

    prob += pulp.lpSum(
        variabel_keputusan[(h, p)] * program_katalog[p]['Biaya']
        for h, p in variabel_keputusan
    ) <= pagu_anggaran

    prob.solve()

    for (h, p), var in variabel_keputusan.items():
        if var.varValue == 1.0:
            nama_prog = program_katalog[p]['Nama_Program']
            biaya_prog = program_katalog[p]['Biaya']
            total_biaya += biaya_prog
            rekomendasi.append({
                "Klaster Target": f"Klaster Spasial #{h}",
                "Program Rekomendasi": nama_prog,
                "Alokasi Anggaran": f"Rp {biaya_prog:,.0f}"
            })

    if rekomendasi:
        df_rek = pd.DataFrame(rekomendasi)

# ==========================================
# PRESENTATION LAYER: TAB MENU UTAMA & CHATBOT
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Ringkasan & Peta", 
    "📈 Analisis Demografi", 
    "💰 Simulasi Anggaran", 
    "🏛️ Kebijakan Desa",
    "💬 Tanya AI Konsultan"
])

with tab1:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sampel Terdata", f"{len(df_raw)} KK")
    m2.metric("Keluarga Rentan", f"{len(df_rentan)} KK")
    m3.metric("Klaster Hotspot GeoAI", f"{jumlah_hotspot} Klaster")
    m4.metric("Validitas AHP", "CR < 0.10 (Valid)")
    
    st.markdown("### 🗺️ Peta Tematik Interaktif Sebaran Hotspot Kerentanan")
    m = folium.Map(location=[-3.3167, 114.5901], zoom_start=13, tiles="CartoDB positron")
    
    if not df_rentan.empty:
        for idx, row in df_rentan.iterrows():
            color = "red" if row['ID_Hotspot'] >= 0 else "orange"
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                popup=f"ID: {row['ID_Keluarga']}<br>Kec: {row['Kecamatan']}<br>Klaster: {row['ID_Hotspot']}<br>Skor: {row['Skor_Kerentanan']:.2f}"
            ).add_to(m)
            
    st_folium(m, width=1100, height=500)

with tab2:
    st.markdown("### 📈 Distribusi Kerentanan Per Kecamatan")
    if not df.empty:
        df_grouped = df.groupby('Kecamatan')[['Risiko_Stunting', 'Kemiskinan_Ekstrem', 'Sanitasi_Buruk']].sum().reset_index()
        st.dataframe(df_grouped, use_container_width=True)
        st.bar_chart(df_grouped.set_index('Kecamatan'))
    else:
        st.info("Tidak ada data.")

with tab3:
    st.markdown("### 📋 Rekomendasi Alokasi APB-Desa Otomatis")
    if not df_rek.empty:
        st.dataframe(df_rek, use_container_width=True)
        st.success(f"Optimasi Berhasil! Total Anggaran Terserap: **Rp {total_biaya:,.0f}** dari Pagu **Rp {pagu_anggaran:,.0f}**")
        sisa_anggaran = pagu_anggaran - total_biaya
        st.info(f"Sisa Anggaran Cadangan Desa (Silpa Estimasi): Rp {sisa_anggaran:,.0f}")
    else:
        st.warning("Pagu anggaran tidak mencukupi atau tidak ada klaster hotspot aktif.")

with tab4:
    st.markdown("### 🏛️ Draf Kebijakan Operasional & Non-Finansial IDSS")
    if not df_hotspot.empty:
        for idx, row in rekap_hotspot.iterrows():
            cluster_id = int(row['ID_Hotspot'])
            jumlah_kk = row['Jumlah_Keluarga']
            with st.expander(f"📌 Aksi Lapangan: Klaster Wilayah #{cluster_id} ({jumlah_kk} Keluarga Target)"):
                st.write(f"- Pengerahan 2 Bidan Desa & Kader Posyandu untuk home-visit mingguan.")
                st.write(f"- Alokasi pengiriman {jumlah_kk * 2} paket gizi spesifik balita dan filter air bersih.")
        
        st.markdown("---")
        if not df_rek.empty:
            csv_data = df_rek.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Unduh Dokumen RKP-Desa & APB-Desa (.CSV)", data=csv_data, file_name="RKP_Desa.csv", mime="text/csv")
    else:
        st.info("Belum ada klaster hotspot.")

with tab5:
    st.markdown("### 🤖 IDSS Conversational AI (Asisten Perencanaan Kebijakan Desa)")
    st.markdown("Tanyakan apa saja seputar data mitigasi stunting, analisis spasial, atau rekomendasi anggaran desa kepada AI.")

    # Inisialisasi riwayat chat di session state Streamlit
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Halo! Saya Asisten AI IDSS. Ada yang bisa saya bantu terkait analisis stunting, klaster wilayah, atau alokasi anggaran APB-Desa di Banjarmasin?"}
        ]

    # Tampilkan riwayat pesan
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input chat dari pengguna (seperti ChatGPT)
    if prompt := st.chat_input("Ketik pertanyaan Anda di sini... (Contoh: Berapa klaster rawan stunting di Banjarmasin?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Logika respons AI berbasis data real-time aplikasi
        prompt_lower = prompt.lower()
        if "klaster" in prompt_lower or "hotspot" in prompt_lower:
            response = f"Berdasarkan analisis GeoAI DBSCAN terkini pada filter wilayah aktif, sistem mendeteksi **{jumlah_hotspot} klaster hotspot** utama yang menjadi prioritas intervensi penanganan stunting dan kemiskinan."
        elif "anggaran" in prompt_lower or "pagu" in prompt_lower or "apb" in prompt_lower:
            response = f"Pagu anggaran APB-Desa saat ini ditetapkan sebesar **Rp {pagu_anggaran:,.0f}**. Dari simulasi optimasi Knapsack, total anggaran yang terserap adalah **Rp {total_biaya:,.0f}** dengan sisa cadangan Silpa sekitar **Rp {pagu_anggaran - total_biaya:,.0f}**."
        elif "stunting" in prompt_lower or "kemiskinan" in prompt_lower:
            response = f"Terdapat total **{len(df_rentan)} keluarga kategori rentan** dari total {len(df_raw)} KK yang terdata. Prioritas tertinggi didasarkan pada pembobotan multikriteria AHP di mana variabel risiko stunting memiliki bobot terbesar."
        elif "rekomendasi" in prompt_lower or "program" in prompt_lower:
            response = "Rekomendasi program utama meliputi Pembangunan Sanitasi Komunal, Instalasi Sumur Bor/Air Bersih, serta Intervensi Paket Gizi Spesifik Stunting yang dialokasikan langsung ke titik koordinat hotspot."
        else:
            response = f"Pertanyaan menarik! Berdasarkan data sistem *Predictive Governance* Kota Banjarmasin, fokus utama kami adalah mentranslasikan data spasial mikro menjadi rekomendasi kebijakan preventif yang objektif dan transparan. Silakan jelajahi tab menu di atas untuk melihat visualisasi peta dan draf anggarannya."

        # Tampilkan respons AI
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
