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
    page_icon="🛡️", 
    layout="wide"
)

# Custom CSS untuk mempercantik tampilan ala Dashboard Pemerintahan Modern
st.markdown("""
    <style>
        .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
        .sub-header { font-size: 16px; color: #4B5563; }
        .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB; }
    </style>
""", unsafe_allow_html=True)

# Judul Utama & Deskripsi
st.markdown('<p class="main-header">🛡️ IDSS & GeoAI: Predictive Governance Mitigasi Stunting</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Platform Pengambilan Keputusan Anggaran & Kebijakan Desa Berbasis Spasial | Studi Kasus Kota Banjarmasin</p>', unsafe_allow_html=True)
st.markdown("---")

# 1. Load Data dari GitHub
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/Predicta-ulm/geoai-idss/refs/heads/main/data_dummy_banjarmasin.csv"
    return pd.read_csv(url)

try:
    df = load_data()
except:
    st.error("Gagal memuat data. Pastikan link GitHub CSV sudah benar di kode.")
    st.stop()

# ==========================================
# KATALOG PROGRAM & KONTROL SIDEBAR
# ==========================================
program_katalog = [
    {"Nama_Program": "Pembangunan Sanitasi Komunal", "Biaya": 35000000, "Dampak": 0.8},
    {"Nama_Program": "Penyediaan Sumur Bor/Air Bersih", "Biaya": 25000000, "Dampak": 0.7},
    {"Nama_Program": "Paket Gizi Spesifik Stunting (1 Tahun)", "Biaya": 15000000, "Dampak": 0.9}
]

st.sidebar.header("⚙️ Panel Kontrol IDSS")
pagu_anggaran = st.sidebar.number_input("Pagu Anggaran APB-Desa (Rp)", value=150000000, step=10000000, format="%d")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Skenario Kebijakan")
skenario_pilihan = st.sidebar.selectbox(
    "Fokus Prioritas Intervensi",
    ["Skenario Seimbang (Optimal)", "Fokus Infrastruktur Sanitasi & Air", "Fokus Penanganan Gizi Spesifik"]
)

if skenario_pilihan == "Fokus Infrastruktur Sanitasi & Air":
    program_katalog[0]["Dampak"] = 0.95
    program_katalog[2]["Dampak"] = 0.60
elif skenario_pilihan == "Fokus Penanganan Gizi Spesifik":
    program_katalog[0]["Dampak"] = 0.50
    program_katalog[2]["Dampak"] = 0.95

# Filter Kecamatan di Sidebar
daftar_kecamatan = ["Semua Kecamatan"] + list(df['Kecamatan'].unique())
pilih_kecamatan = st.sidebar.selectbox("Filter Wilayah Kecamatan", daftar_kecamatan)

if pilih_kecamatan != "Semua Kecamatan":
    df = df[df['Kecamatan'] == pilih_kecamatan]

# 2. Proses AHP (Logic Layer)
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

# 3. Proses GeoAI DBSCAN (Spatial Layer)
ambang_batas = df['Skor_Kerentanan'].mean()
df_rentan = df[df['Skor_Kerentanan'] > ambang_batas].copy()

if not df_rentan.empty:
    koordinat_rad = np.radians(df_rentan[['Latitude', 'Longitude']].values)
    dbscan = DBSCAN(eps=0.5/6371., min_samples=3, algorithm='ball_tree', metric='haversine')
    df_rentan['ID_Hotspot'] = dbscan.fit_predict(koordinat_rad)
    df_hotspot = df_rentan[df_rentan['ID_Hotspot'] >= 0]
    jumlah_hotspot = len(df_hotspot['ID_Hotspot'].unique())
else:
    df_hotspot = pd.DataFrame()
    jumlah_hotspot = 0

# ==========================================
# PEMBAGIAN TAB UTAMA (UI MODERN)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Ringkasan & Peta Spasial", "💰 Simulasi Anggaran (IDSS)", "🏛️ Kebijakan & Ekspor Dokumen"])

with tab1:
    # Metrik Utama
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Keluarga Terdata", f"{len(df)} KK")
    m2.metric("Keluarga Kategori Rentan", f"{len(df_rentan)} KK")
    m3.metric("Hotspot Rawan Ditemukan", f"{jumlah_hotspot} Klaster")
    
    st.markdown("### 🗺️ Peta Tematik Interaktif Sebaran Hotspot Banjarmasin")
    st.markdown("Titik **Merah** menandakan klaster kepadatan tinggi (*Hotspot*), sedangkan titik **Oranye** adalah keluarga rentan yang terpencar.")
    
    m = folium.Map(location=[-3.3167, 114.5901], zoom_start=13, tiles="CartoDB positron")
    
    if not df_rentan.empty:
        for idx, row in df_rentan.iterrows():
            color = "red" if row['ID_Hotspot'] >= 0 else "orange"
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=f"ID: {row['ID_Keluarga']}<br>Kec: {row['Kecamatan']}<br>Klaster: {row['ID_Hotspot']}<br>Skor: {row['Skor_Kerentanan']:.2f}"
            ).add_to(m)
            
    st_folium(m, width=1100, height=450)

with tab2:
    st.markdown("### 📋 Rekomendasi Alokasi APB-Desa Berbasis Optimasi Knapsack")
    st.markdown("Sistem secara matematis mengalokasikan anggaran untuk memaksimalkan dampak penurunan stunting berdasarkan tingkat keparahan klaster.")
    
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

        rekomendasi = []
        total_biaya = 0

        for (h, p), var in variabel_keputusan.items():
            if var.varValue == 1.0:
                nama_prog = program_katalog[p]['Nama_Program']
                biaya_prog = program_katalog[p]['Biaya']
                total_biaya += biaya_prog
                rekomendasi.append({
                    "Klaster Target": f"Klaster Wilayah #{h}",
                    "Program Rekomendasi": nama_prog,
                    "Estimasi Anggaran": f"Rp {biaya_prog:,.0f}"
                })

        if rekomendasi:
            df_rek = pd.DataFrame(rekomendasi)
            st.dataframe(df_rek, use_container_width=True)
            st.success(f"Optimasi Selesai! Total Anggaran Terserap: **Rp {total_biaya:,.0f}** dari Pagu **Rp {pagu_anggaran:,.0f}**")
        else:
            st.warning("Pagu anggaran terlalu kecil untuk menjalankan program intervensi.")
    else:
        st.info("Tidak ada data klaster yang memenuhi syarat untuk optimasi anggaran.")

with tab3:
    st.markdown("### 🏛️ Kebijakan Operasional & Non-Finansial IDSS")
    st.markdown("Tindakan lapangan terstruktur yang dirumuskan secara otomatis oleh sistem bagi aparat desa:")

    if not df_hotspot.empty:
        for idx, row in rekap_hotspot.iterrows():
            cluster_id = int(row['ID_Hotspot'])
            jumlah_kk = row['Jumlah_Keluarga']
            
            with st.expander(f"📌 Aksi Rekomendasi untuk Klaster Wilayah #{cluster_id} ({jumlah_kk} Keluarga Rentan)"):
                st.markdown(f"**1. Penugasan Personel Lapangan:**")
                st.write(f"- Menugaskan 2 orang Kader Posyandu & 1 Bidan Desa untuk *home visit* mingguan.")
                
                st.markdown(f"**2. Distribusi Logistik & Bantuan Natura:**")
                st.write(f"- Prioritaskan distribusi {jumlah_kk * 2} paket gizi spesifik stunting dan filter air bersih.")
                
                st.markdown(f"**3. Rekomendasi Regulasi Desa (Perdes):**")
                if cluster_id % 2 == 0:
                    st.write(f"- Mendorong penerbitan Perdes percepatan pembangunan sanitasi komunal.")
                else:
                    st.write(f"- Mendorong pengaktifan pos pelayanan air bersih dan pengawasan bansos.")
        
        st.markdown("---")
        st.markdown("### 📄 Ekspor Dokumen Resmi Perencanaan Desa")
        if 'df_rek' in locals() and not df_rek.empty:
            csv_data = df_rek.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Draf RKP-Desa & APB-Desa (.CSV)",
                data=csv_data,
                file_name="Draf_RKP_Desa_Predictive_Governance.csv",
                mime="text/csv",
            )
    else:
        st.info("Belum ada klaster hotspot untuk diekskalasi.")
