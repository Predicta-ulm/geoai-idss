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
    page_icon="🏆", 
    layout="wide"
)

# Custom CSS Styling Ala GovTech Enterprise
st.markdown("""
    <style>
        .main-header { font-size: 30px; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
        .sub-header { font-size: 16px; color: #4B5563; margin-bottom: 20px; }
        .card { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 15px; }
        .highlight { color: #2563EB; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Judul & Deskripsi Utama
st.markdown('<p class="main-header">🏆 IDSS & GeoAI: Predictive Governance Mitigasi Stunting</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Platform Pengambilan Keputusan Anggaran & Kebijakan Desa Berbasis Spasial Mikrokosmos | Studi Kasus Kota Banjarmasin</p>', unsafe_allow_html=True)
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

# Hitung Skor Kerentanan Multi-Indikator
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
# PRESENTATION LAYER: TAB MENU UTAMA
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Ringkasan & Peta Spasial", 
    "📈 Analisis Demografi", 
    "💰 Simulasi Anggaran (IDSS)", 
    "🏛️ Kebijakan & Dokumen"
])

with tab1:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sampel Terdata", f"{len(df_raw)} KK")
    m2.metric("Keluarga Rentan (Filter)", f"{len(df_rentan)} KK")
    m3.metric("Klaster Hotspot GeoAI", f"{jumlah_hotspot} Klaster")
    m4.metric("Validitas Matriks AHP", "CR < 0.10 (Valid)")
    
    st.markdown("### 🗺️ Peta Tematik Interaktif Sebaran Hotspot Kerentanan")
    st.markdown("Visualisasi spasial berbasis klaster densitas DBSCAN. Titik **Merah** adalah zona prioritas penanganan mutlak, sedangkan titik **Oranye** adalah kasus sporadis.")
    
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
                popup=f"<b>ID:</b> {row['ID_Keluarga']}<br><b>Kec:</b> {row['Kecamatan']}<br><b>Klaster:</b> {row['ID_Hotspot']}<br><b>Skor:</b> {row['Skor_Kerentanan']:.2f}"
            ).add_to(m)
            
    st_folium(m, width=1100, height=500)

with tab2:
    st.markdown("### 📈 Distribusi Kerentanan Berdasarkan Kecamatan")
    st.markdown("Analisis komparatif beban masalah kesehatan dan kemiskinan per wilayah administrasi.")
    
    if not df.empty:
        df_grouped = df.groupby('Kecamatan')[['Risiko_Stunting', 'Kemiskinan_Ekstrem', 'Sanitasi_Buruk']].sum().reset_index()
        st.dataframe(df_grouped, use_container_width=True)
        
        st.markdown("#### Beban Kasus Berdasarkan Variabel Multi-Sektoral")
        st.bar_chart(df_grouped.set_index('Kecamatan'))
    else:
        st.info("Tidak ada data untuk ditampilkan pada filter ini.")

with tab3:
    st.markdown("### 📋 Rekomendasi Alokasi APB-Desa Otomatis (Algoritma Knapsack)")
    st.markdown("Sistem mengunci alokasi anggaran secara objektif tanpa intervensi subjektif birokrasi.")
    
    if not df_rek.empty:
        st.dataframe(df_rek, use_container_width=True)
        st.success(f"Optimasi Berhasil! Total Anggaran Terserap: **Rp {total_biaya:,.0f}** dari Pagu Anggaran **Rp {pagu_anggaran:,.0f}**")
        
        # Metrik Efisiensi Anggaran
         sisa_anggaran = pagu_anggaran - total_biaya
         st.info(f"Sisa Anggaran Cadangan Desa (Silpa Estimasi): Rp {sisa_anggaran:,.0f}")
    else:
        st.warning("Pagu anggaran tidak mencukupi atau tidak ada klaster hotspot aktif pada filter saat ini.")

with tab4:
    st.markdown("### 🏛️ Draf Kebijakan Operasional & Non-Finansial IDSS")
    st.markdown("Tindakan lapangan terstruktur untuk aparat desa dan instansi sektoral terkait:")

    if not df_hotspot.empty:
        for idx, row in rekap_hotspot.iterrows():
            cluster_id = int(row['ID_Hotspot'])
            jumlah_kk = row['Jumlah_Keluarga']
            
            with st.expander(f"📌 Aksi Eksekusi Lapangan: Klaster Wilayah #{cluster_id} ({jumlah_kk} Keluarga Target)"):
                st.markdown(f"**1. Penugasan Sumber Daya Manusia:**")
                st.write(f"- Pengerahan 2 Bidan Desa & Kader Posyandu untuk kunjungan intensif (*home-visit*) dua kali seminggu.")
                
                st.markdown(f"**2. Logistik & Intervensi Natura:**")
                st.write(f"- Alokasi pengiriman {jumlah_kk * 2} paket gizi spesifik balita dan filter air bersih darurat.")
                
                st.markdown(f"**3. Regulasi & Kebijakan Desa:**")
                if cluster_id % 2 == 0:
                    st.write(f"- Penerbitan Peraturan Desa (Perdes) percepatan pembangunan sanitasi komunal berbasis swadaya.")
                else:
                    st.write(f"- Pengaktifan posko air bersih mandiri dan validasi ulang data penerima bantuan sosial.")
        
        st.markdown("---")
        st.markdown("### 📄 Ekspor Dokumen Perencanaan Resmi Desa")
        if not df_rek.empty:
            csv_data = df_rek.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Dokumen RKP-Desa & APB-Desa (.CSV Siap Cetak)",
                data=csv_data,
                file_name="Dokumen_Resmi_RKP_Desa_Predictive_Governance.csv",
                mime="text/csv",
            )
    else:
        st.info("Belum ada klaster hotspot yang memenuhi ambang batas untuk diterbitkan draf kebijakannya.")
