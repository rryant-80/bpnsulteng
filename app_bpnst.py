import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Konfigurasi Halaman Streamlit ke Wide Mode
st.set_page_config(layout="wide", page_title="Dashboard Keagrariaan BPN", page_icon="🏢")

# Custom CSS untuk layout profil pejabat dan kartu metrik
st.markdown("""
<style>
    .profile-box {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 4px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .profile-name {
        font-weight: bold;
        font-size: 14px;
        color: #1e293b;
    }
    .profile-title {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .profile-target {
        font-size: 11px;
        color: #059669;
    }
    .custom-card {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 6px;
    }
    .card-title {
        font-size: 11px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .card-value {
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        margin: 2px 0;
    }
    .card-subtext {
        font-size: 10px;
        color: #94a3b8;
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

# Memuat kedua dataset
try:
    df_wilayah = load_data(SPREADSHEET_ID, "1848496896")
    df_pegawai = load_data(SPREADSHEET_ID, "1168898330")
except Exception as e:
    st.error(f"Gagal memuat data dari Google Sheets: {e}")
    st.stop()

# Pembersihan whitespace pada data teks
for col in ['kabupaten_kota', 'kecamatan', 'desa_kelurahan']:
    if col in df_wilayah.columns:
        df_wilayah[col] = df_wilayah[col].astype(str).str.strip()

for col in ['kabupaten_kota', 'nama', 'jabatan', 'kategori_asn']:
    if col in df_pegawai.columns:
        df_pegawai[col] = df_pegawai[col].astype(str).str.strip()

# Konversi tipe data numerik dan bersihkan karakter non-numerik (seperti titik/koma pemisah ribuan dari string)
num_cols_wil = ['luas_adm', 'luas_apl', 'jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 'pra_btel', 'jumlah_su', 'jumlah_suvalid', 'pra_suel']
for col in num_cols_wil:
    if col in df_wilayah.columns:
        df_wilayah[col] = pd.to_numeric(df_wilayah[col].astype(str).str.replace('.', '').str.replace(',', ''), errors='coerce').fillna(0)

num_cols_peg = ['target_dipa', 'realisasi_dipa']
for col in num_cols_peg:
    if col in df_pegawai.columns:
        # Menangani pembersihan jika data angka di spreadsheet dibaca sebagai string berformat rupiah
        df_pegawai[col] = df_pegawai[col].astype(str).str.replace('Rp', '').str.replace('.', '').str.replace(',', '').str.replace(' ', '')
        df_pegawai[col] = pd.to_numeric(df_pegawai[col], errors='coerce').fillna(0)


# ==========================================
# 3. SIDEBAR (HANYA BERISI MENU FILTER)
# ==========================================
st.sidebar.title("Filter Wilayah")

list_kab = ["Sulawesi Tengah"] + sorted(list(df_wilayah['kabupaten_kota'].dropna().unique())) if not df_wilayah.empty else ["Sulawesi Tengah"]
selected_kab = st.sidebar.selectbox("Kabupaten / Kota", list_kab)

if selected_kab == "Sulawesi Tengah":
    list_kec = ["Semua Kecamatan"]
else:
    list_kec = ["Semua Kecamatan"] + sorted(list(df_wilayah[df_wilayah['kabupaten_kota'] == selected_kab]['kecamatan'].dropna().unique()))

selected_kec = st.sidebar.selectbox("Kecamatan", list_kec)


# ==========================================
# PRE-PROCESSING DATA FILTER SEBELUM LAYOUT
# ==========================================
# Perbaikan Utama: Menggunakan .str.contains() agar "Palu" bisa COCOK dengan "Kantor Pertanahan Kota Palu"
df_peg_filtered = df_pegawai.copy()
if selected_kab != "Sulawesi Tengah":
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]
else:
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains("Kanwil|Provinsi|Sulteng", case=False, na=False)]

# Penyiapan filter data wilayah utama
df_wil_filtered = df_wilayah.copy()
if selected_kab != "Sulawesi Tengah":
    df_wil_filtered = df_wil_filtered[df_wil_filtered['kabupaten_kota'] == selected_kab]
    if selected_kec != "Semua Kecamatan":
        df_wil_filtered = df_wil_filtered[df_wil_filtered['kecamatan'] == selected_kec]


# ==========================================
# 4. MAIN CONTENT MAIN LAYOUT
# ==========================================
st.title(f"🏢 Dashboard Kinerja & Agraria — {selected_kab}")
if selected_kec != "Semua Kecamatan":
    st.subheader(f"Kecamatan: {selected_kec}")
st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------
# BARIS ATAS: METRICS & PIE CHART MACRO DIPA
# ------------------------------------------
row_metrics = st.columns([2, 2, 2, 2, 2, 2.5])

with row_metrics[0]:
    jumlah_sdm = df_peg_filtered['nama'].nunique()
    breakdown_asn = df_peg_filtered.groupby('kategori_asn')['nama'].count().to_dict()
    sub_asn_text = ", ".join([f"{k}: {v}" for k, v in breakdown_asn.items()]) if breakdown_asn else "PNS: 0, PPNPN: 0"
    st.markdown(f'<div class="custom-card"><div class="card-title">👥 Jumlah SDM</div><div class="card-value">{jumlah_sdm}</div><div class="card-subtext">{sub_asn_text}</div></div>', unsafe_allow_html=True)

with row_metrics[1]:
    tot_apl = df_wil_filtered['luas_apl'].sum()
    tot_adm = df_wil_filtered['luas_adm'].sum()
    pct_apl = (tot_apl / tot_adm * 100) if tot_adm > 0 else 0
    st.markdown(f'<div class="custom-card"><div class="card-title">🗺️ Luas APL</div><div class="card-value">{tot_apl:,.1f} Ha</div><div class="card-subtext">{pct_apl:.2f}% dari Luas ADM</div></div>', unsafe_allow_html=True)

with row_metrics[2]:
    if selected_kab == "Sulawesi Tengah":
        val_kec = df_wilayah['kabupaten_kota'].nunique()
        lbl_kec = "Total Kabupaten/Kota"
    else:
        val_kec = df_wil_filtered['kecamatan'].nunique()
        lbl_kec = f"Kecamatan di {selected_kab}"
    st.markdown(f'<div class="custom-card"><div class="card-title">🧩 Kecamatan</div><div class="card-value">{val_kec}</div><div class="card-subtext">{lbl_kec}</div></div>', unsafe_allow_html=True)

with row_metrics[3]:
    if selected_kab == "Sulawesi Tengah":
        val_desa = df_wilayah['kabupaten_kota'].nunique()
        sub_desa_text = "Seluruh Kabupaten/Kota"
    else:
        val_desa = df_wil_filtered['desa_kelurahan'].nunique()
        sub_desa_text = "Total Desa & Kelurahan"
    st.markdown(f'<div class="custom-card"><div class="card-title">🏡 Desa / Kelurahan</div><div class="card-value">{val_desa}</div><div class="card-subtext">{sub_desa_text}</div></div>', unsafe_allow_html=True)

with row_metrics[4]:
    if selected_kab == "Sulawesi Tengah":
        val_kw = df_wilayah['kabupaten_kota'].nunique()
        lbl_kw = "Kabupaten/Kota Terdata"
    else:
        val_kw = int(df_wil_filtered['jumlah_kw456'].sum())
        lbl_kw = "Total Berkas KW456"
    st.markdown(f'<div class="custom-card"><div class="card-title">📂 Jumlah KW456</div><div class="card-value">{val_kw}</div><div class="card-subtext">{lbl_kw}</div></div>', unsafe_allow_html=True)

with row_metrics[5]:
    total_target = df_peg_filtered['target_dipa'].sum()
    total_realisasi = df_peg_filtered['realisasi_dipa'].sum()
    sisa_dipa = max(0, total_target - total_realisasi)
    
    if total_target > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Realisasi DIPA', 'Sisa Target'],
            values=[total_realisasi, sisa_dipa],
            hole=.35,
            textinfo='percent',
            marker=dict(colors=['#2563eb', '#ef4444'])
        )])
        fig_pie.update_layout(
            margin=dict(t=5, b=5, l=5, r=5), 
            height=75, 
            showlegend=True,
            legend=dict(font=dict(size=9), yanchor="center", y=0.5, xanchor="left", x=1.1)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.caption("Data DIPA Wilayah Kosong")

st.markdown("<hr>", unsafe_allow_html=True)


# ------------------------------------------
# LAYOUT UTAMA: KIRI (PROFIL & IMAGES) vs KANAN (2 GRAFIK BESAR)
# ------------------------------------------
col_left, col_right = st.columns([4, 8])

with col_left:
    # --- SUB-ROW FOTO URL 2 DAN URL 1 ---
    col_url2, col_url1 = st.columns(2)
    
    with col_url2:
        df_bendahara = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Bendahara", case=False, na=False)]
        img_bendahara = df_bendahara.iloc[0]['url'] if not df_bendahara.empty and pd.notna(df_bendahara.iloc[0]['url']) else "https://via.placeholder.com/150"
        st.markdown("<p style='text-align:center; font-weight:600; margin-bottom:2px; font-size:12px;'>URL 2 (Bendahara)</p>", unsafe_allow_html=True)
        st.image(img_bendahara, use_container_width=True)
        
    with col_url1:
        df_kakan = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Kepala Kantor|Kakan|Kakanwil", case=False, na=False)]
        img_kakan = df_kakan.iloc[0]['url'] if not df_kakan.empty and pd.notna(df_kakan.iloc[0]['url']) else "https://via.placeholder.com/150"
        st.markdown("<p style='text-align:center; font-weight:600; margin-bottom:2px; font-size:12px;'>URL 1 (Kepala Kantor)</p>", unsafe_allow_html=True)
        st.image(img_kakan, use_container_width=True)
        
    st.markdown("<br><p style='font-weight:bold; font-size:15px; border-bottom:2px solid #cbd5e1; padding-bottom:4px;'>Profil Pejabat Struktural</p>", unsafe_allow_html=True)
    
    # --- FUNGSI MENCETAK PROFIL STRUKTURAL ---
    def render_dashboard_profile(jabatan_keyword):
        # Menggunakan regex atau substring agar pencarian jabatan fleksibel
        row = df_peg_filtered[df_peg_filtered['jabatan'].str.contains(jabatan_keyword, case=False, na=False)]
        if not row.empty:
            row = row.iloc[0]
            target = row['target_dipa']
            realisasi = row['realisasi_dipa']
            pct = (realisasi / target * 100) if target > 0 else 0
            img_url = row['url'] if pd.notna(row['url']) and str(row['url']).startswith("http") else "https://via.placeholder.com/150"
            
            st.markdown(f"""
            <div class="profile-box">
                <table style="width:100%; border:none; background:transparent;">
                    <tr style="border:none; background:transparent;">
                        <td style="width:25%; border:none; vertical-align:top; background:transparent;">
                            <img src="{img_url}" style="width:100%; border-radius:6px; border:1px solid #e2e8f0;">
                        </td>
                        <td style="width:75%; border:none; padding-left:12px; vertical-align:top; background:transparent;">
                            <div class="profile-name">{row['nama']}</div>
                            <div class="profile-title">{row['jabatan']}</div>
                            <div class="profile-target">Target: Rp {target:,.0f}</div>
                        </td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            # Grafik Batang Representatif Kinerja DIPA Jabatan Terkait
            st.progress(min(float(pct/100), 1.0))
            st.markdown(f"<p style='font-size:11px; margin-top:-8px; margin-bottom:12px; color:#475569; text-align:right;'>Realisasi: <b>{pct:.2f}%</b> (Rp {realisasi:,.0f})</p>", unsafe_allow_html=True)
        else:
            st.caption(f"⚠️ Jabatan '{jabatan_keyword}' tidak ditemukan di wilayah ini.")

    # 6 Urutan Struktural (Menggunakan potongan kata kunci kunci yang aman dari variasi pengetikan)
    order_struktural = [
        "Tata Usaha",
        "Survei dan Pemetaan",
        "Penetapan Hak",
        "Penataan",
        "Pengadaan Tanah",
        "Sengketa"
    ]
    
    for jabatan in order_struktural:
        render_dashboard_profile(jabatan)

with col_right:
    # Pengelompokkan sumbu X berdasarkan filter wilayah yang aktif terpilih
    if selected_kab == "Sulawesi Tengah":
        df_chart = df_wilayah.groupby('kabupaten_kota').sum().reset_index()
        x_axis_column = 'kabupaten_kota'
    elif selected_kec == "Semua Kecamatan":
        df_chart = df_wil_filtered.groupby('kecamatan').sum().reset_index()
        x_axis_column = 'kecamatan'
    else:
        df_chart = df_wil_filtered.groupby('desa_kelurahan').sum().reset_index()
        x_axis_column = 'desa_kelurahan'

    # --- GRAFIK UTAMA 1 BESAR ---
    st.markdown("### 🗺️ Grafik Pemetaan & Validasi Persil per-Wilayah")
    if not df_chart.empty:
        fig_batang1 = go.Figure()
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_persil'], name='Jumlah Persil', marker_color='#1d4ed8'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_su'], name='Jumlah SU', marker_color='#3b82f6'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_suvalid'], name='SU Valid', marker_color='#10b981'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_suel'], name='Pra SUEL', marker_color='#f59e0b'))
        
        fig_batang1.update_layout(
            barmode='group',
            xaxis_title="Daftar Wilayah",
            yaxis_title="Volume",
            legend_orientation="h",
            legend=dict(x=0, y=1.12),
            margin=dict(t=40, b=30),
            height=430
        )
        st.plotly_chart(fig_batang1, use_container_width=True)
    else:
        st.info("Data wilayah tidak tersedia.")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- GRAFIK UTAMA 2 BESAR ---
    st.markdown("### 📖 Grafik Validasi Buku Tanah per-Wilayah")
    if not df_chart.empty:
        fig_batang2 = go.Figure()
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_bt'], name='Jumlah BT', marker_color='#6d28d9'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['bt_valid'], name='BT Valid', marker_color='#059669'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_btel'], name='Pra BTEL', marker_color='#d97706'))
        
        fig_batang2.update_layout(
            barmode='group',
            xaxis_title="Daftar Wilayah",
            yaxis_title="Volume",
            legend_orientation="h",
            legend=dict(x=0, y=1.12),
            margin=dict(t=40, b=30),
            height=430
        )
        st.plotly_chart(fig_batang2, use_container_width=True)
