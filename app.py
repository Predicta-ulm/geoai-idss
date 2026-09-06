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
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Skenario Kebijakan Simulasi")
skenario_pilihan = st.sidebar.selectbox(
    "Pilih Fokus Prioritas Intervensi",
    ["Fokus Infrastruktur Sanitasi & Air", "Fokus Penanganan Gizi Spesifik", "Skenario Seimbang (Optimal)"]
)

# Menyesuaikan bobot program berdasarkan skenario pilihan juri
if skenario_pilihan == "Fokus Infrastruktur Sanitasi & Air":
    program_katalog[0]["Dampak"] = 0.95
    program_katalog[2]["Dampak"] = 0.60
elif skenario_pilihan == "Fokus Penanganan Gizi Spesifik":
    program_katalog[0]["Dampak"] = 0.50
    program_katalog[2]["Dampak"] = 0.95
else:
    program_katalog[0]["Dampak"] = 0.8
    program_katalog[2]["Dampak"] = 0.9

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
import folium
from streamlit_folium import st_folium

st.markdown("### 🗺️ Peta Tematik Interaktif Sebaran Klaster Hotspot")

# Inisialisasi peta berpusat di Kota Banjarmasin
m = folium.Map(location=[-3.3167, 114.5901], zoom_start=13, tiles="CartoDB positron")

# Plot titik keluarga rentan dengan warna berdasarkan klaster
for idx, row in df_rentan.iterrows():
    color = "red" if row['ID_Hotspot'] >= 0 else "orange"
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=5,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=f"ID: {row['ID_Keluarga']}<br>Klaster: {row['ID_Hotspot']}<br>Skor: {row['Skor_Kerentanan']:.2f}"
    ).add_to(m)

# Render peta di Streamlit
st_folium(m, width=1000, height=450)

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
st.markdown("### 📋 Rekomendasi Alokasi APB-Desa Otomatis")
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
st.markdown("---")
st.markdown("### 🏛️ Draf Kebijakan Operasional & Non-Finansial IDSS")
st.markdown("Sistem secara otomatis merumuskan tindakan lapangan berbasis klaster hotspot kerentanan tertinggi:")

# Looping otomatis berdasarkan klaster yang terdeteksi oleh DBSCAN
if not df_hotspot.empty:
    for idx, row in rekap_hotspot.iterrows():
        cluster_id = int(row['ID_Hotspot'])
        jumlah_kk = row['Jumlah_Keluarga']
        
        with st.expander(f"📌 Aksi Rekomendasi untuk Klaster Wilayah #{cluster_id} ({jumlah_kk} Keluarga Rentan)"):
            st.markdown(f"**1. Penugasan Personel Lapangan:**")
            st.write(f"- Menugaskan 2 orang Kader Posyandu & 1 Bidan Desa dari Puskesmas terdekat untuk melakukan *home visit* intensif mingguan ke Klaster #{cluster_id}.")
            
            st.markdown(f"**2. Distribusi Logistik & Bantuan Natura:**")
            st.write(f"- Prioritaskan distribusi {jumlah_kk * 2} kotak susu formula pencegah stunting dan paket filter air bersih darurat ke titik koordinat klaster ini.")
            
            st.markdown(f"**3. Rekomendasi Regulasi Desa (Perdes):**")
            if cluster_id % 2 == 0:
                st.write(f"- Mendorong Kepala Desa menerbitkan Perdes tentang percepatan pembangunan sanitasi komunal berbasis gotong royong di wilayah Klaster #{cluster_id}.")
            else:
                st.write(f"- Mendorong pengaktifan pos pelayanan air bersih desa dan pengawasan ketat distribusi Raskin/Bantuan Pangan Non-Tunai.")
else:
    st.info("Belum ada klaster hotspot yang memenuhi syarat minimum untuk eskalasi kebijakan non-finansial.")

