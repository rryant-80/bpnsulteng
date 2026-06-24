import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(layout="wide", page_title="Dashboard Keagrariaan BPN", page_icon="🏢")

# Custom CSS untuk mempercantik tampilan profil di sidebar kiri dan kartu metrik
st.markdown("""
<style>
    .profile-container {
        border: 1px solid #3498db;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 15px;
        background-color: #f8fafd;
    }
    .profile-name {
        font-weight: bold;
        font-size: 14px;
        color: #2c3e50;
    }
    .profile-title {
        font-size: 12px;
        color: #7f8c8d;
    }
    .profile-target {
        font-size: 11px;
        color: #27ae60;
    }
    .custom-card {
        background-color: #f1f4f9;
        border-left: 5px solid #2980b9;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .card-title {
        font-size: 13px;
        color: #555;
        font-weight: bold;
        text-transform: uppercase;
    }
    .card-value {
        font-size: 22px;
        font-weight: bold;
        color: #2c3e50;
    }
    .card-subtext {
        font-size: 11px;
        color: #7f8c8d;
    }
</style>
""", unsafe_allow_html=True)

# 2. Memuat Data dari Google Sheets via Secrets
@st.cache_data(ttl=600)
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

try:
    SPREADSHEET_ID = st.secrets["spreadsheet"]["id"]
except KeyError:
    st.error("Spreadsheet ID belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

# Memuat data
try:
    df_wilayah = load_data(SPREADSHEET_ID, "1848496896")
    df_pegawai = load_data(SPREADSHEET_ID, "1168898330")
except Exception as e:
    st.error(f"Gagal memuat data dari Google Sheets: {e}")
    st.stop()

# Cleaning data teks dari spasi berlebih
for col in ['kabupaten_kota', 'kecamatan', 'desa_kelurahan']:
    if col in df_wilayah.columns:
        df_wilayah[col] = df_wilayah[col].astype(str).str.strip()

for col in ['kabupaten_kota', 'nama', 'jabatan', 'kategori_asn']:
    if col in df_pegawai.columns:
        df_pegawai[col] = df_pegawai[col].astype(str).str.strip()

# Konversi kolom numerik yang krusial
num_cols_wil = ['luas_adm', 'luas_apl', 'jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 'pra_btel', 'jumlah_su', 'jumlah_suvalid', 'pra_suel']
for col in num_cols_wil:
    if col in df_wilayah.columns:
        df_wilayah[col] = pd.to_numeric(df_wilayah[col], errors='coerce').fillna(0)

num_cols_peg = ['target_dipa', 'realisasi_dipa']
for col in num_cols_peg:
    if col in df_pegawai.columns:
        df_pegawai[col] = pd.to_numeric(df_pegawai[col], errors='coerce').fillna(0)


# ==========================================
# 3. SIDEBAR: FILTER & PROFIL PEGAWAI
# ==========================================
st.sidebar.title("Navigasi & Filter")

# Filter Kabupaten_Kota (Sumber utama dari df_wilayah)
list_kab = ["Sulawesi Tengah"] + sorted(list(df_wilayah['kabupaten_kota'].dropna().unique())) if not df_wilayah.empty else ["Sulawesi Tengah"]
selected_kab = st.sidebar.selectbox("Kabupaten / Kota", list_kab)

# Filter Kecamatan menyesuaikan Kabupaten
if selected_kab == "Sulawesi Tengah":
    list_kec = ["Semua Kecamatan"]
else:
    list_kec = ["Semua Kecamatan"] + sorted(list(df_wilayah[df_wilayah['kabupaten_kota'] == selected_kab]['kecamatan'].dropna().unique()))

selected_kec = st.sidebar.selectbox("Kecamatan", list_kec)

st.sidebar.markdown("---")
st.sidebar.subheader("Profil Pejabat Structural")

# Menyaring data pegawai menggunakan nama kolom 'kabupaten_kota'
df_peg_filtered = df_pegawai.copy()
if selected_kab != "Sulawesi Tengah":
    # Filter pegawai berdasarkan kabupaten_kota yang dipilih
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]
else:
    # Jika Sulawesi Tengah, tampilkan tingkat Provinsi (Kanwil / yang mengandung kata "Kanwil", "Provinsi", atau "Sulteng")
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains("Kanwil|Provinsi|Sulteng", case=False, na=False)]

# Fungsi bantu untuk merender profil pegawai di sidebar sesuai urutan jabatan
def render_profile(jabatan_keyword):
    row = df_peg_filtered[df_peg_filtered['jabatan'].str.contains(jabatan_keyword, case=False, na=False)]
    if not row.empty:
        row = row.iloc[0]
        pct = (row['realisasi_dipa'] / row['target_dipa'] * 100) if row['target_dipa'] > 0 else 0
        img_url = row['url'] if pd.notna(row['url']) and str(row['url']).startswith("http") else "https://via.placeholder.com/150"
        
        st.sidebar.markdown(f"""
        <div class="profile-container">
            <table style="width:100%; border:none; background:transparent;">
                <tr style="border:none; background:transparent;">
                    <td style="width:35%; border:none; vertical-align:top; background:transparent;">
                        <img src="{img_url}" style="width:100%; border-radius:4px; border:1px solid #ddd;">
                    </td>
                    <td style="width:65%; border:none; padding-left:8px; vertical-align:top; background:transparent;">
                        <div class="profile-name">{row['nama']}</div>
                        <div class="profile-title">{row['jabatan']}</div>
                        <div class="profile-target">Target: Rp {row['target_dipa']:,.0f}</div>
                    </td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.progress(min(float(pct/100), 1.0))
        st.sidebar.caption(f"Realisasi DIPA: {pct:.2f}% (Rp {row['realisasi_dipa']:,.0f})")

# Urutan Jabatan sesuai Instruksi dari Atas ke Bawah
order_jabatan = [
    "Tata Usaha",
    "Survei dan Pemetaan",
    "Penetapan Hak dan Pendaftaran",
    "Penata", 
    "Pengadaan Tanah",
    "Sengketa" 
]

for jab in order_jabatan:
    render_profile(jab)


# ==========================================
# 4. MAIN CONTENT: HEADER & ROW ATAS
# ==========================================
st.title(f"📊 Dashboard Kinerja & Agraria - {selected_kab}")
if selected_kec != "Semua Kecamatan":
    st.subheader(f"Kecamatan: {selected_kec}")

# Menyiapkan data wilayah terfilter
df_wil_filtered = df_wilayah.copy()
if selected_kab != "Sulawesi Tengah":
    df_wil_filtered = df_wil_filtered[df_wil_filtered['kabupaten_kota'] == selected_kab]
    if selected_kec != "Semua Kecamatan":
        df_wil_filtered = df_wil_filtered[df_wil_filtered['kecamatan'] == selected_kec]

# Baris Atas: URL, Pie Chart, dan Metrik Cards
row_top = st.columns([1.5, 1.5, 2, 6])

with row_top[0]:
    # URL 2: Jabatan "Bendahara" sesuai filter kabupaten
    df_bendahara = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Bendahara", case=False, na=False)]
    url_2_link = df_bendahara.iloc[0]['url'] if not df_bendahara.empty and pd.notna(df_bendahara.iloc[0]['url']) else "#"
    st.markdown(f'''
    <div style="border:2px solid #e67e22; border-radius:8px; padding:20px; text-align:center; height:120px; background-color:#fffdfa;">
        <h4 style="margin:0; color:#e67e22;">URL 2</h4>
        <p style="margin:5px 0 0 0; font-size:12px; color:#555;">Bendahara</p>
        <a href="{url_2_link}" target="_blank" style="text-decoration:none; font-weight:bold; color:#d35400;">Buka Tautan 🔗</a>
    </div>
    ''', unsafe_allow_html=True)

with row_top[1]:
    # URL 1: Jabatan "Kepala Kantor"
    df_kakan = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Kepala Kantor|Kakan|Kakanwil", case=False, na=False)]
    url_1_link = df_kakan.iloc[0]['url'] if not df_kakan.empty and pd.notna(df_kakan.iloc[0]['url']) else "#"
    st.markdown(f'''
    <div style="border:2px solid #e67e22; border-radius:8px; padding:20px; text-align:center; height:120px; background-color:#fffdfa;">
        <h4 style="margin:0; color:#e67e22;">URL 1</h4>
        <p style="margin:5px 0 0 0; font-size:12px; color:#555;">Kepala Kantor</p>
        <a href="{url_1_link}" target="_blank" style="text-decoration:none; font-weight:bold; color:#d35400;">Buka Tautan 🔗</a>
    </div>
    ''', unsafe_allow_html=True)

with row_top[2]:
    # Grafik Pie Total Realisasi DIPA
    total_target = df_peg_filtered['target_dipa'].sum()
    total_realisasi = df_peg_filtered['realisasi_dipa'].sum()
    sisa_dipa = max(0, total_target - total_realisasi)
    
    if total_target > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Realisasi DIPA', 'Sisa Target'],
            values=[total_realisasi, sisa_dipa],
            hole=.4,
            textinfo='label+percent',
            marker=dict(colors=['#2980b9', '#e74c3c'])
        )])
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=130, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.markdown("<div style='text-align:center; padding-top:40px; color:#999; font-size:12px;'>Pie Chart DIPA (Data Kosong)</div>", unsafe_allow_html=True)

with row_top[3]:
    c_sdm, c_apl, c_kec, c_desa, c_kw = st.columns(5)
    
    with c_sdm:
        jumlah_sdm = df_peg_filtered['nama'].nunique()
        breakdown_asn = df_peg_filtered.groupby('kategori_asn')['nama'].count().to_dict()
        sub_asn_text = ", ".join([f"{k}: {v}" for k, v in breakdown_asn.items()]) if breakdown_asn else "PNS: 0, PPNPN: 0"
        st.markdown(f'<div class="custom-card"><div class="card-title">Jumlah SDM</div><div class="card-value">{jumlah_sdm}</div><div class="card-subtext">{sub_asn_text}</div></div>', unsafe_allow_html=True)
        
    with c_apl:
        tot_apl = df_wil_filtered['luas_apl'].sum()
        tot_adm = df_wil_filtered['luas_adm'].sum()
        pct_apl = (tot_apl / tot_adm * 100) if tot_adm > 0 else 0
        st.markdown(f'<div class="custom-card"><div class="card-title">Luas APL</div><div class="card-value">{tot_apl:,.1f} Ha</div><div class="card-subtext">{pct_apl:.2f}% dari Luas ADM</div></div>', unsafe_allow_html=True)
        
    with c_kec:
        if selected_kab == "Sulawesi Tengah":
            val_kec = df_wilayah['kabupaten_kota'].nunique()
            lbl_kec = "Total Kabupaten/Kota"
        else:
            val_kec = df_wil_filtered['kecamatan'].nunique()
            lbl_kec = f"Kecamatan di {selected_kab}"
        st.markdown(f'<div class="custom-card"><div class="card-title">Kecamatan</div><div class="card-value">{val_kec}</div><div class="card-subtext">{lbl_kec}</div></div>', unsafe_allow_html=True)
        
    with c_desa:
        if selected_kab == "Sulawesi Tengah":
            val_desa = df_wilayah['kabupaten_kota'].nunique()
            sub_desa_text = "Seluruh Kabupaten/Kota"
        else:
            val_desa = df_wil_filtered['desa_kelurahan'].nunique()
            sub_desa_text = "Total Desa & Kelurahan"
        st.markdown(f'<div class="custom-card"><div class="card-title">Desa / Kelurahan</div><div class="card-value">{val_desa}</div><div class="card-subtext">{sub_desa_text}</div></div>', unsafe_allow_html=True)
        
    with c_kw:
        if selected_kab == "Sulawesi Tengah":
            val_kw = df_wilayah['kabupaten_kota'].nunique()
            lbl_kw = "Kabupaten/Kota Terdata"
        else:
            val_kw = int(df_wil_filtered['jumlah_kw456'].sum())
            lbl_kw = "Total Berkas KW456"
        st.markdown(f'<div class="custom-card"><div class="card-title">Jumlah KW456</div><div class="card-value">{val_kw}</div><div class="card-subtext">{lbl_kw}</div></div>', unsafe_allow_html=True)


# ==========================================
# 5. MAIN CONTENT: GRAFIK UTAMA
# ==========================================
if selected_kab == "Sulawesi Tengah":
    df_chart = df_wilayah.groupby('kabupaten_kota').sum().reset_index()
    x_axis_column = 'kabupaten_kota'
elif selected_kec == "Semua Kecamatan":
    df_chart = df_wil_filtered.groupby('kecamatan').sum().reset_index()
    x_axis_column = 'kecamatan'
else:
    df_chart = df_wil_filtered.groupby('desa_kelurahan').sum().reset_index()
    x_axis_column = 'desa_kelurahan'

st.markdown("### 🗺️ Grafik Pemetaan & Validasi Persil per-Wilayah")
if not df_chart.empty:
    fig_batang1 = go.Figure()
    fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_persil'], name='Jumlah Persil', marker_color='#2980b9'))
    fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_su'], name='Jumlah SU', marker_color='#3498db'))
    fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_suvalid'], name='SU Valid', marker_color='#2ecc71'))
    fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_suel'], name='Pra SUEL', marker_color='#e67e22'))
    fig_batang1.update_layout(barmode='group', xaxis_title="Wilayah", yaxis_title="Jumlah", legend_orientation="h", legend=dict(x=0, y=1.1), margin=dict(t=30, b=20), height=350)
    st.plotly_chart(fig_batang1, use_container_width=True)

st.markdown("---")

st.markdown("### 📖 Grafik Validasi Buku Tanah per-Wilayah")
if not df_chart.empty:
    fig_batang2 = go.Figure()
    fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_bt'], name='Jumlah BT', marker_color='#8e44ad'))
    fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['bt_valid'], name='BT Valid', marker_color='#27ae60'))
    fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_btel'], name='Pra BTEL', marker_color='#f39c12'))
    fig_batang2.update_layout(barmode='group', xaxis_title="Wilayah", yaxis_title="Jumlah", legend_orientation="h", legend=dict(x=0, y=1.1), margin=dict(t=30, b=20), height=350)
    st.plotly_chart(fig_batang2, use_container_width=True)
