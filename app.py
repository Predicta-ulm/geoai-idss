import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import pulp

# Konfigurasi Halaman Web
st.set_page_config(page_title="IDSS Stunting & Kemiskinan Banjarmasin", layout="wide")

st.title("🌐 IDSS & GeoAI: Predictive Governance Mitigasi Stunting")
st.markdown("**Studi Kasus Kota Banjarmasin | Platform Pengambilan Keputusan Anggaran Desa Berbasis Data Spasial**")
st.markdown("---")

# 1. Load Data dari GitHub (Pastikan file CSV sudah ada di repo GitHub Anda)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/Predicta-ulm/geoai-idss/refs/heads/main/data_dummy_banjarmasin.csv"
    return pd.read_csv(url)

try:
    df = load_data()
except:
    st.error("Gagal memuat data. Pastikan link GitHub CSV sudah benar di kode.")
    st.stop()

# Sidebar untuk Pengaturan Pengguna
st.sidebar.header("⚙️ Kontrol Kebijakan IDSS")
pagu_anggaran = st.sidebar.number_input("Pagu Anggaran APB-Desa (Rp)", value=150000000, step=10000000)

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

koordinat_rad = np.radians(df_rentan[['Latitude', 'Longitude']].values)
dbscan = DBSCAN(eps=0.5/6371., min_samples=3, algorithm='ball_tree', metric='haversine')
df_rentan['ID_Hotspot'] = dbscan.fit_predict(koordinat_rad)
df_hotspot = df_rentan[df_rentan['ID_Hotspot'] >= 0]

jumlah_hotspot = len(df_hotspot['ID_Hotspot'].unique())

# Tampilan Metrik Utama di Web
col1, col2, col3 = st.columns(3)
col1.metric("Total Keluarga Terdata", f"{len(df)} KK")
col2.metric("Keluarga Kategori Rentan", f"{len(df_rentan)} KK")
col3.metric("Hotspot Rawan Ditemukan", f"{jumlah_hotspot} Klaster")

st.markdown("### 🗺️ Peta Sebaran Klaster Hotspot Kerentanan")
st.map(df_hotspot[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'}))

# 4. Proses Optimasi Knapsack (Decision Layer)
rekap_hotspot = df_hotspot.groupby('ID_Hotspot').agg(
    Jumlah_Keluarga=('ID_Keluarga', 'count'),
    Total_Kerentanan=('Skor_Kerentanan', 'sum')
).reset_index()

program_katalog = [
    {"Nama_Program": "Pembangunan Sanitasi Komunal", "Biaya": 35000000, "Dampak": 0.8},
    {"Nama_Program": "Penyediaan Sumur Bor/Air Bersih", "Biaya": 25000000, "Dampak": 0.7},
    {"Nama_Program": "Paket Gizi Spesifik Stunting (1 Tahun)", "Biaya": 15000000, "Dampak": 0.9}
]

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

# Tampilkan Hasil Rekomendasi di Web
st.markdown("### 📋 Draf Rekomendasi Alokasi APB-Desa Otomatis")
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
    st.table(df_rek)
    st.success(f"Optimasi Selesai! Total Anggaran Terserap: **Rp {total_biaya:,.0f}** dari Pagu **Rp {pagu_anggaran:,.0f}**")
else:
    st.warning("Pagu anggaran terlalu kecil untuk menjalankan program intervensi pada klaster yang ada.")
