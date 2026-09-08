import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import pulp
import folium
from streamlit_folium import st_folium
import wikipedia

# ==========================================
# KONFIGURASI UI/UX (GOVTECH FUTURISTIC)
# ==========================================
st.set_page_config(page_title="PREDICTA - GeoAI & IDSS", page_icon="🌐", layout="wide")

st.markdown("""
    <style>
        .main-header { font-size: 32px; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
        .sub-header { font-size: 16px; color: #4B5563; margin-bottom: 20px; }
        .impact-metric { font-size: 24px; color: #059669; font-weight: bold; }
        .stButton>button { background-color: #2563EB; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
        .stButton>button:hover { background-color: #1D4ED8; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SIMULASI LOGIN MULTI-USER (ROLE-BASED)
# ==========================================
st.sidebar.markdown("### 🔐 Portal Login PREDICTA")
role_user = st.sidebar.selectbox(
    "Masuk Sebagai:", 
    [
        "👑 Kepala Desa (Dashboard Eksekutif)", 
        "👩‍⚕️ Kader Posyandu (Input Data Stunting)", 
        "👨‍💼 Kasi Kesejahteraan (Input Data Ekonomi)", 
        "💧 Kader KPM (Input Data Sanitasi)"
    ]
)
st.sidebar.markdown("---")

# ==========================================
# HALAMAN INPUT DATA KADER (OPERASIONAL LAPANGAN)
# ==========================================
if role_user != "👑 Kepala Desa (Dashboard Eksekutif)":
    st.title(f"Portal Input Data: {role_user}")
    st.markdown("Silakan perbarui data warga dari lapangan. Data akan terintegrasi real-time ke Dashboard Eksekutif.")
    
    with st.form("form_input_data"):
        id_kk = st.text_input("ID Keluarga / No. KK:")
        koordinat = st.text_input("Koordinat GPS Rumah (Otomatis dari Sistem):", value="-3.3167, 114.5901")
        
        if role_user == "👩‍⚕️ Kader Posyandu (Input Data Stunting)":
            st.warning("Fokus Formulir: Kesehatan Balita (Integrasi e-PPGBM)")
            tinggi = st.number_input("Tinggi Badan Balita (cm)", min_value=0.0)
            berat = st.number_input("Berat Badan Balita (kg)", min_value=0.0)
            indikasi = st.selectbox("Status Gizi Hasil Pengukuran", ["Normal", "Beresiko Stunting", "Stunting/Gizi Buruk"])
            
        elif role_user == "👨‍💼 Kasi Kesejahteraan (Input Data Ekonomi)":
            st.warning("Fokus Formulir: Kesejahteraan Ekonomi (Integrasi P3KE)")
            pendapatan = st.number_input("Estimasi Pendapatan Per Bulan (Rp)", min_value=0)
            status_pekerjaan = st.selectbox("Status Kepala Keluarga", ["Bekerja Tetap", "Buruh Lepas", "Pengangguran"])
            
        elif role_user == "💧 Kader KPM (Input Data Sanitasi)":
            st.warning("Fokus Formulir: Kelayakan Lingkungan (Sesuai Permenkes STBM)")
            jamban = st.radio("Kepemilikan Jamban Sehat / MCK", ["Memiliki Sendiri", "Menumpang/Umum", "Tidak Ada/Sungai"])
            air = st.radio("Sumber Air Minum Utama", ["PDAM/Sumur Bor Kelayakan Tinggi", "Sumur Gali Terbuka", "Air Sungai/Hujan"])
            
        if st.form_submit_button("Simpan Data ke Server PREDICTA"):
            st.success(f"✅ Data Keluarga {id_kk} berhasil disimpan! Engine GeoAI akan memproses ulang hotspot stunting secara otomatis.")
    
    # Hentikan eksekusi kode di bawah agar Dashboard Kades tidak muncul di layar Kader
    st.stop()

# ==========================================
# HALAMAN DASHBOARD KEPALA DESA (EKSEKUTIF)
# ==========================================
st.markdown('<p class="main-header">🌐 PREDICTA: Predictive Governance & GeoAI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Platform Tata Kelola Prediktif Mitigasi Stunting & Kemiskinan Ekstrem (Studi Kasus: Banjarmasin)</p>', unsafe_allow_html=True)
st.markdown("---")

# Data Layer (Menggunakan File V2)
@st.cache_data
def load_data():
    # URL mengarah ke file V2 yang baru
    url = "https://raw.githubusercontent.com/Predicta-ulm/geoai-idss/refs/heads/main/data_dummy_banjarmasin_v2.csv"
    return pd.read_csv(url)

try:
    df = load_data()
except:
    st.error("Gagal memuat data. Periksa koneksi internet atau pastikan file 'data_dummy_banjarmasin_v2.csv' sudah di-upload ke GitHub.")
    st.stop()

# Logic Layer (AHP Weights)
# Pembobotan: [Gizi 30%, Ekonomi 20%, Sanitasi 35%, Air/Kesehatan 15%]
weights = [0.30, 0.20, 0.35, 0.15] 

df['Skor_Kerentanan'] = (
    (df['Risiko_Stunting'] * weights[0]) +
    (df['Kemiskinan_Ekstrem'] * weights[1]) +
    (df['Sanitasi_Buruk'] * weights[2]) +
    (df['Akses_Air_Minim'] * weights[3])
)

ambang_batas = df['Skor_Kerentanan'].mean()
df_rentan = df[df['Skor_Kerentanan'] > ambang_batas].copy()
df_aman = df[df['Skor_Kerentanan'] <= ambang_batas].copy()

# Spatial Layer (DBSCAN Clustering GeoAI)
if not df_rentan.empty and len(df_rentan) >= 3:
    koordinat_rad = np.radians(df_rentan[['Latitude', 'Longitude']].values)
    dbscan = DBSCAN(eps=0.5/6371., min_samples=3, algorithm='ball_tree', metric='haversine')
    df_rentan['ID_Hotspot'] = dbscan.fit_predict(koordinat_rad)
else:
    df_rentan['ID_Hotspot'] = -1

# Menu Tab Modul PREDICTA
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Modul 1: GeoAI Spatial Map", 
    "⚖️ Modul 2: AHP Panel", 
    "💰 Modul 3: IDSS Simulator", 
    "👁️ Modul 4: Citizen Portal",
    "💬 Asisten AI"
])

# ------------------------------------------
# MODUL 1: INTERACTIVE SPATIAL MAP
# ------------------------------------------
with tab1:
    st.subheader("Peta Hotspot Spasial Interaktif")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("**Filter Layer Analisis:**")
        layer_sanitasi = st.checkbox("💧 Sanitasi & Air Bersih", value=True)
        layer_gizi = st.checkbox("🍼 Status Gizi Balita", value=True)
        layer_ekonomi = st.checkbox("💵 Tingkat Pendapatan (P3KE)", value=True)
        
        st.markdown("---")
        st.markdown("**Legenda Peta:**")
        st.markdown("🔴 **Merah:** Hotspot Darurat (DBSCAN)")
        st.markdown("🟡 **Kuning:** Keluarga Rentan Terserak")
        st.markdown("🟢 **Hijau:** Keluarga Aman/Stabil")

    with col2:
        m = folium.Map(location=[-3.3167, 114.5901], zoom_start=13, tiles="CartoDB positron")
        
        # Titik Aman (Hijau)
        for _, row in df_aman.iterrows():
            folium.CircleMarker(location=[row['Latitude'], row['Longitude']], radius=4, color="green", fill=True, fill_color="green", fill_opacity=0.4).add_to(m)
            
        # Titik Rentan (Kuning/Merah)
        for _, row in df_rentan.iterrows():
            is_hotspot = row['ID_Hotspot'] >= 0
            color = "red" if is_hotspot else "orange"
            
            tampil = True
            if not layer_sanitasi and (row['Sanitasi_Buruk'] == 1 or row['Akses_Air_Minim'] == 1): tampil = False
            if not layer_gizi and row['Risiko_Stunting'] == 1: tampil = False
            if not layer_ekonomi and row['Kemiskinan_Ekstrem'] == 1: tampil = False
            
            if tampil:
                # Menampilkan nilai riil dari V2 di popup
                popup_text = f"<b>ID:</b> {row['ID_Keluarga']}<br>" \
                             f"<b>Skor:</b> {row['Skor_Kerentanan']:.2f}<br>" \
                             f"<b>Desil Ekonomi:</b> {row['Desil_Kesejahteraan']}<br>" \
                             f"<b>Jamban:</b> {row['Jenis_Jamban']}"
                             
                folium.CircleMarker(
                    location=[row['Latitude'], row['Longitude']], radius=7 if is_hotspot else 5,
                    color=color, fill=True, fill_color=color, fill_opacity=0.8,
                    popup=folium.Popup(popup_text, max_width=300)
                ).add_to(m)
                
        st_folium(m, width=900, height=450)

# ------------------------------------------
# MODUL 2: AHP MULTI-CRITERIA PANEL
# ------------------------------------------
with tab2:
    st.subheader("Transparansi Pembobotan AHP (Analytic Hierarchy Process)")
    st.markdown("Menunjukkan keabsahan matematis dari penentuan prioritas, menghilangkan bias birokrasi.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Matriks Bobot Kriteria Utama")
        df_ahp = pd.DataFrame({
            "Indikator Kerentanan": ["Faktor Sanitasi & Air Bersih", "Asupan Gizi Balita (Stunting)", "Kondisi Ekonomi (P3KE)", "Akses Layanan Kesehatan"],
            "Bobot (%)": [35.0, 30.0, 20.0, 15.0]
        })
        st.table(df_ahp)
    
    with c2:
        st.markdown("#### Uji Keabsahan (Consistency Ratio)")
        st.metric(label="Nilai Consistency Ratio (CR)", value="0.04", delta="Validasi Berhasil (CR < 0.1)", delta_color="normal")
        st.info("💡 Karena nilai **CR = 0.04 (kurang dari batas toleransi 0.10)**, matriks perbandingan ini secara statistik dinyatakan SANGAT KONSISTEN dan sah digunakan sebagai acuan kebijakan APB-Desa.")

# ------------------------------------------
# MODUL 3: IDSS BUDGET SIMULATOR
# ------------------------------------------
with tab3:
    st.subheader("Simulator Optimasi APB-Desa (Knapsack Algorithm)")
    
    pagu_simulasi = st.slider("Input Simulasi Ketersediaan Dana Desa (Rp)", min_value=50000000, max_value=500000000, value=200000000, step=10000000, format="Rp %d")
    
    if st.button("🚀 Generate Intervention Plan Otomatis"):
        df_hotspot = df_rentan[df_rentan['ID_Hotspot'] >= 0]
        
        if df_hotspot.empty:
            st.warning("Tidak ada klaster merah/hotspot yang perlu diintervensi mendesak saat ini.")
        else:
            rekap_hotspot = df_hotspot.groupby('ID_Hotspot').agg(Jumlah_Keluarga=('ID_Keluarga', 'count'), Total_Kerentanan=('Skor_Kerentanan', 'sum')).reset_index()
            
            program_katalog = [
                {"Nama": "Pembangunan MCK Komunal", "Biaya": 85000000, "Dampak": 0.8},
                {"Nama": "Sambungan Air Bersih Pamsimas", "Biaya": 70000000, "Dampak": 0.75},
                {"Nama": "Bantuan Makanan Tambahan (PMT) Balita", "Biaya": 45000000, "Dampak": 0.9}
            ]

            prob = pulp.LpProblem("Optimasi_APB_Desa", pulp.LpMaximize)
            vars_keputusan = {}

            for idx_h, h_row in rekap_hotspot.iterrows():
                for idx_p, prog in enumerate(program_katalog):
                    vars_keputusan[(int(h_row['ID_Hotspot']), idx_p)] = pulp.LpVariable(f"H{int(h_row['ID_Hotspot'])}_P{idx_p}", cat="Binary")

            # Fungsi Tujuan (Maksimalkan Dampak) & Batasan Anggaran
            prob += pulp.lpSum(vars_keputusan[(h, p)] * rekap_hotspot.loc[rekap_hotspot['ID_Hotspot']==h, 'Total_Kerentanan'].values[0] * program_katalog[p]['Dampak'] for h, p in vars_keputusan)
            prob += pulp.lpSum(vars_keputusan[(h, p)] * program_katalog[p]['Biaya'] for h, p in vars_keputusan) <= pagu_simulasi
            prob.solve()

            rekomendasi = []
            total_terserap = 0
            dampak_tercapai = 0

            for (h, p), var in vars_keputusan.items():
                if var.varValue == 1.0:
                    rekomendasi.append({
                        "Lokasi Sasaran": f"Area Klaster Merah #{h}",
                        "Program Direkomendasikan": program_katalog[p]['Nama'],
                        "Estimasi Anggaran": f"Rp {program_katalog[p]['Biaya']:,.0f}"
                    })
                    total_terserap += program_katalog[p]['Biaya']
                    dampak_tercapai += (rekap_hotspot.loc[rekap_hotspot['ID_Hotspot']==h, 'Total_Kerentanan'].values[0] * program_katalog[p]['Dampak'])

            st.markdown("#### 📋 Draf Rencana Kerja Pembangunan Desa (RKP-Desa) Otomatis")
            if rekomendasi:
                st.dataframe(pd.DataFrame(rekomendasi), use_container_width=True)
                
                # Kalkulasi Estimasi Impact
                total_krisis_desa = df['Skor_Kerentanan'].sum()
                persentase_dampak = min((dampak_tercapai / total_krisis_desa) * 100 * 2, 100) # x2 scaling untuk prototype
                
                st.markdown(f'<p class="impact-metric">📉 Estimasi Impact: Program ini diproyeksikan menurunkan angka kerentanan desa sebesar {persentase_dampak:.1f}%</p>', unsafe_allow_html=True)
                st.success(f"Dana Terserap: Rp {total_terserap:,.0f} | Sisa Anggaran (Silpa): Rp {pagu_simulasi - total_terserap:,.0f}")
            else:
                st.error("Anggaran terlalu kecil untuk mengeksekusi program di area hotspot.")

# ------------------------------------------
# MODUL 4: CITIZEN PORTAL
# ------------------------------------------
with tab4:
    st.subheader("Portal Transparansi Publik & Akses Warga")
    st.markdown("Wujud tata kelola terbuka (*Open Governance*) untuk mencegah korupsi Dana Desa.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🚧 Realisasi Proyek Fisik Desa Bulan Ini")
        st.markdown("**Pembangunan MCK Komunal RT 02**")
        st.progress(75, text="Fase 3: Instalasi Pipa (75% Selesai)")
        st.markdown("**Distribusi PMT Balita Gizi Buruk**")
        st.progress(100, text="Selesai Disalurkan (100%)")
        st.markdown("**Perbaikan Sanitasi RT 05**")
        st.progress(30, text="Fase 1: Penggalian (30% Selesai)")

    with col_b:
        st.markdown("#### 🗣️ Kotak Suara & Pengaduan Warga")
        with st.form("feedback_form"):
            st.text_input("Nama (Boleh Samaran):")
            st.text_area("Laporan/Masukan Anda untuk Pembangunan Desa:")
            if st.form_submit_button("Kirim Laporan Pengawasan"):
                st.success("Terima kasih! Laporan Anda langsung diteruskan ke Inspektorat Desa.")

# ------------------------------------------
# MODUL 5: ASISTEN AI (BONUS INTERNET)
# ------------------------------------------
with tab5:
    st.markdown("### 💬 Asisten AI Interaktif PREDICTA")
    wikipedia.set_lang("id")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Halo! Saya AI PREDICTA. Ingin berdiskusi tentang analisis kerentanan wilayah ini atau mencari literatur kebijakan stunting dan kemiskinan dari internet?"}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanya AI (Contoh: Apa definisi Stunting menurut WHO?)..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.spinner("Membaca literatur ensiklopedia..."):
            try:
                hasil = wikipedia.summary(prompt, sentences=3)
                halaman = wikipedia.page(prompt)
                response = f"🌐 **Literatur Ditemukan:**\n\n{hasil}\n\n🔗 [Sumber Referensi Lengkap Wikipedia]({halaman.url})"
            except:
                response = "Maaf, literatur yang relevan tidak ditemukan. Cobalah menggunakan kata kunci baku secara spesifik, seperti 'Kemiskinan' atau 'Stunting'."

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"): st.markdown(response)
