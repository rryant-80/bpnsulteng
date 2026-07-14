import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Konfigurasi Halaman Streamlit ke Wide Mode
st.set_page_config(layout="wide", page_title="Dashboard BPN Sulteng", page_icon="🏢")

# Custom CSS untuk layout kotak profil pejabat dan kartu metrik
st.markdown("""
<style>
    .profile-box {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
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
        margin-bottom: 4px;
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
        font-size: 18px;
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

# Fungsi pemformat angka lokal (Titik ribuan, Koma desimal untuk Luas Ha)
def format_lokal(nilai, pakai_desimal=True):
    if pakai_desimal:
        teks = f"{nilai:,.2f}"
        return teks.replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{int(nilai):,}".replace(",", ".")

# Pemetaan Singkatan Wilayah untuk Sumbu X Grafik di Sidebar
MAP_SINGKATAN = {
    "banggai kepulauan": "BK",
    "banggai laut": "BL",
    "banggai": "BG",
    "buol": "BU",
    "donggala": "DG",
    "morowali utara": "MU",
    "morowali": "MW",
    "palu": "PL",
    "parigi moutong": "PM",
    "poso": "PS",
    "sigi": "SG",
    "tojo una-una": "TU",
    "kanwil sulawesi tengah": "ST",
    "tolitoli": "TL"
}

def singgkat_nama_wilayah(nama):
    nama_clean = str(nama).strip().lower()
    for kunci, singkatan in MAP_SINGKATAN.items():
        if kunci in nama_clean:
            return singkatan
    return str(nama).title()

# 2. Memuat Data dari Google Sheets via Secrets
@st.cache_data(ttl=600)
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url, thousands='.')

try:
    SPREADSHEET_ID = st.secrets["spreadsheet"]["id"]
except KeyError:
    st.error("Spreadsheet ID belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

try:
    df_wilayah = load_data(SPREADSHEET_ID, "1848496896")
    df_pegawai = load_data(SPREADSHEET_ID, "1168898330")
    df_prosedur = load_data(SPREADSHEET_ID, "1447858691") # MEMUAT SHEET BARU
except Exception as e:
    st.error(f"Gagal memuat data dari Google Sheets: {e}")
    st.stop()

# Pembersihan data teks baku
for df in [df_wilayah, df_pegawai, df_prosedur]:
    for col in ['kabupaten_kota', 'kecamatan', 'desa_kelurahan', 'nama', 'jabatan', 'kategori_asn', 'nama_prosedur', 'posisi_berkas']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

# KONVERSI DATA NUMERIK GID WILAYAH
num_cols_wil = [
    'luas_adm', 'luas_apl', 'jumlah_persil', 'luas_persil', 'luas_persil_valid', 
    'jumlah_kw456', 'luas_kw456', 'jumlah_bt', 'bt_valid', 'luas_persil_deliniasi', 
    'pra_sertel', 'pra_btel', 'jumlah_su', 'jumlah_suvalid', 'pra_suel'
]
for col in num_cols_wil:
    if col in df_wilayah.columns:
        if df_wilayah[col].dtype == 'object':
            df_wilayah[col] = df_wilayah[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
        elif df_wilayah[col].dtype == 'float64':
            df_wilayah[col] = df_wilayah[col].fillna(0)
        df_wilayah[col] = pd.to_numeric(df_wilayah[col], errors='coerce').fillna(0)

# KONVERSI SATUAN LUAS: m2 ke Hektar (Ha)
df_wilayah['luas_adm'] = df_wilayah['luas_adm'] / 10000
df_wilayah['luas_apl'] = df_wilayah['luas_apl'] / 10000

# Pembersihan data DIPA Pegawai
num_cols_peg = ['target_dipa', 'realisasi_dipa']
for col in num_cols_peg:
    if col in df_pegawai.columns:
        if df_pegawai[col].dtype == 'object':
            df_pegawai[col] = df_pegawai[col].astype(str).str.replace('Rp', '', regex=False).str.replace('.', '', regex=False).str.replace(' ', '', regex=False)
        df_pegawai[col] = pd.to_numeric(df_pegawai[col], errors='coerce').fillna(0)

# KONVERSI DATA NUMERIK GID PROSEDUR BARU
if 'biaya' in df_prosedur.columns:
    if df_prosedur['biaya'].dtype == 'object':
        df_prosedur['biaya'] = df_prosedur['biaya'].astype(str).str.replace('Rp', '', regex=False).str.replace('.', '', regex=False)
    df_prosedur['biaya'] = pd.to_numeric(df_prosedur['biaya'], errors='coerce').fillna(0)

# ==========================================
# 3. SIDEBAR (FILTER & GRAFIK MAKRO INDEPENDEN)
# ==========================================
st.sidebar.title("FILTER WILAYAH")

# REVISI FILTER: Menambahkan "Semua Kabupaten/Kota" di baris paling atas menu filter
list_kab = ["Semua Kabupaten/Kota", "Sulawesi Tengah"] + sorted(list(df_wilayah['kabupaten_kota'].dropna().unique())) if not df_wilayah.empty else ["Semua Kabupaten/Kota"]
selected_kab = st.sidebar.selectbox("Kabupaten / Kota", list_kab)

if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"]:
    list_kec = ["Semua Kecamatan"]
else:
    list_kec = ["Semua Kecamatan"] + sorted(list(df_wilayah[df_wilayah['kabupaten_kota'] == selected_kab]['kecamatan'].dropna().unique()))

selected_kec = st.sidebar.selectbox("Kecamatan", list_kec)

st.sidebar.markdown("---")

# --- GRAFIK SIDEBAR 1: TINGKAT REALISASI GLOBAL ---
st.sidebar.subheader("📊 % Realisasi Anggaran")
if not df_pegawai.empty:
    df_side_calc = df_pegawai.groupby('kabupaten_kota')[['target_dipa', 'realisasi_dipa']].sum().reset_index()
    df_side_calc['persen_realisasi'] = (df_side_calc['realisasi_dipa'] / df_side_calc['target_dipa'] * 100).fillna(0)
    df_side_calc['wilayah_singkat'] = df_side_calc['kabupaten_kota'].apply(singgkat_nama_wilayah)
    df_side_calc = df_side_calc.sort_values(by='persen_realisasi', ascending=False)
    
    try:
        fig_sidebar = go.Figure()
        hover_nama_lengkap = list(df_side_calc['kabupaten_kota'])
        hover_text_rupiah = [f"Rp {format_lokal(val, False)}" for val in df_side_calc['realisasi_dipa']]
        custom_hover_data = list(zip(hover_nama_lengkap, hover_text_rupiah))
        
        fig_sidebar.add_trace(go.Bar(
            x=df_side_calc['wilayah_singkat'],
            y=df_side_calc['persen_realisasi'],
            marker_color='#2ecc71',
            text=df_side_calc['persen_realisasi'].apply(lambda x: f"{format_lokal(x, True)}%"),
            textposition='outside',
            textfont=dict(size=8, weight='bold'),
            customdata=custom_hover_data,
            hovertemplate="<b>Wilayah:</b> %{customdata[0]}<br><b>Persen Realisasi:</b> %{y:.2f}%<br><b>Total Realisasi:</b> %{customdata[1]}<extra></extra>"
        ))
        fig_sidebar.update_layout(
            margin=dict(t=25, b=15, l=5, r=5), height=240,
            xaxis=dict(title=None, tickfont=dict(size=9, weight='bold'), type='category', dtick=1),
            yaxis=dict(title=None, tickfont=dict(size=9), maxallowed=60, range=[0, 100]),
            showlegend=False
        )
        st.sidebar.plotly_chart(fig_sidebar, use_container_width=True)
    except Exception as e:
        st.sidebar.bar_chart(df_side_calc, x='wilayah_singkat', y='persen_realisasi', color='#2ecc71', height=200, use_container_width=True)


st.sidebar.markdown("---")

# --- GRAFIK SIDEBAR 2: GRAFIK VOLUME BERKAS PROSEDUR ---
st.sidebar.subheader("📂 PPDM 2015-2026")
status_toggle = st.sidebar.toggle("Tampilkan Tahun 2026 Saja", value=False)

df_pros_side = df_prosedur.copy()

if 'thn_berkas' in df_pros_side.columns:
    df_pros_side['thn_berkas'] = pd.to_numeric(df_pros_side['thn_berkas'], errors='coerce').fillna(0)
    if status_toggle:
        df_pros_side = df_pros_side[df_pros_side['thn_berkas'] == 2026]        
    else:
        df_pros_side = df_pros_side[(df_pros_side['thn_berkas'] >= 2015) & (df_pros_side['thn_berkas'] <= 2025)]        

if selected_kab not in ["Semua Kabupaten/Kota", "Sulawesi Tengah"]:
    df_pros_side = df_pros_side[df_pros_side['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]

if not df_pros_side.empty:
    if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"]:
        df_pros_calc = df_pros_side.groupby('kabupaten_kota').agg(
            jumlah_berkas=('nmr_berkas', 'count'),
            total_biaya=('biaya', 'sum')
        ).reset_index()
        # REVISI: Menerapkan map singkatan wilayah saat berada pada tampilan makro
        df_pros_calc['wilayah_x'] = df_pros_calc['kabupaten_kota'].apply(singgkat_nama_wilayah)
        custom_nama_lengkap = list(df_pros_calc['kabupaten_kota'])
    else:
        df_pros_calc = df_pros_side.groupby('posisi_berkas').agg(
            jumlah_berkas=('nmr_berkas', 'count'),
            total_biaya=('biaya', 'sum')
        ).reset_index()
        df_pros_calc['wilayah_x'] = df_pros_calc['posisi_berkas']
        custom_nama_lengkap = list(df_pros_calc['posisi_berkas'])
    
    df_pros_calc = df_pros_calc.sort_values(by='jumlah_berkas', ascending=False)
    hover_biaya_side = [f"Rp {format_lokal(val, False)}" for val in df_pros_calc['total_biaya']]
    custom_hover_pros = list(zip(custom_nama_lengkap, hover_biaya_side))
    
    try:
        fig_pros_sidebar = go.Figure()
        fig_pros_sidebar.add_trace(go.Bar(
            x=df_pros_calc['wilayah_x'],
            y=df_pros_calc['jumlah_berkas'],
            marker_color='#2c3e50',
            text=df_pros_calc['jumlah_berkas'].astype(str),
            textposition='outside',
            textfont=dict(size=8, weight='bold'),
            customdata=custom_hover_pros,
            hovertemplate=(
                "<b>Posisi/Nama:</b> %{customdata[0]}<br>"
                "<b>Jumlah Berkas:</b> %{y} berkas<br>"
                "<b>Total Biaya:</b> %{customdata[1]}"
                "<extra></extra>"
            )
        ))
        fig_pros_sidebar.update_layout(
            margin=dict(t=25, b=25, l=5, r=5), height=260, showlegend=False,
            xaxis=dict(title=None, tickfont=dict(size=8, weight='bold'), type='category', dtick=1),
            yaxis=dict(title=None, tickfont=dict(size=9))
        )
        st.sidebar.plotly_chart(fig_pros_sidebar, use_container_width=True)
    except Exception as e:
        st.sidebar.bar_chart(df_pros_calc, x='wilayah_x', y='jumlah_berkas', color='#2c3e50', height=220, use_container_width=True)
else:
    st.sidebar.caption("⚠️ Tidak ada tunggakan PDDM.")

st.sidebar.markdown("---")

# --- GRAFIK SIDEBAR 3: GRAFIK MALAH INDEPENDEN % KW456 ---
st.sidebar.subheader("📉 % KW456 (K4)")
if not df_wilayah.empty:
    # Agregasi data dasar murni tanpa terpengaruh filter apa pun
    df_kw_calc = df_wilayah.groupby('kabupaten_kota').agg(
        total_kw=('jumlah_kw456', 'sum'),
        total_bt=('jumlah_bt', 'sum'),
        total_luas_kw=('luas_kw456', 'sum')
    ).reset_index()
    
    df_kw_calc['persen_kw'] = (df_kw_calc['total_kw'] / df_kw_calc['total_bt'] * 100).fillna(0)
    df_kw_calc['wilayah_singkat'] = df_kw_calc['kabupaten_kota'].apply(singgkat_nama_wilayah)
    
    # PERBAIKAN: Mengubah urutan dimulai dari persentase terendah ke tertinggi
    df_kw_calc = df_kw_calc.sort_values(by='persen_kw', ascending=True)
    
    try:
        fig_kw_side = go.Figure()
        custom_hover_kw = list(zip(
            list(df_kw_calc['kabupaten_kota']),
            [format_lokal(v, False) for v in df_kw_calc['total_kw']],
            [format_lokal(v / 10000, True) for v in df_kw_calc['total_luas_kw']], # Konversi m2 ke Ha untuk Luas KW
            [format_lokal(v, False) for v in df_kw_calc['total_bt']]
        ))
        
        fig_kw_side.add_trace(go.Bar(
            x=df_kw_calc['wilayah_singkat'],
            y=df_kw_calc['persen_kw'],
            marker_color='#2980b9',
            text=df_kw_calc['persen_kw'].apply(lambda x: f"{format_lokal(x, True)}%"),
            textposition='outside',
            textfont=dict(size=8, weight='bold'),
            customdata=custom_hover_kw,
            hovertemplate=(
                "<b>Kabupaten/Kota:</b> %{customdata[0]}<br>"
                "<b>Jumlah KW456:</b> %{customdata[1]}<br>"
                "<b>Luas KW456:</b> %{customdata[2]} Ha<br>"
                "<b>Jumlah BT:</b> %{customdata[3]}<br>"
                "<extra></extra>"
            )
        ))
        fig_kw_side.update_layout(
            margin=dict(t=25, b=25, l=5, r=5), height=260, showlegend=False,
            xaxis=dict(title=None, tickfont=dict(size=8, weight='bold'), type='category', dtick=1),
            yaxis=dict(title=None, tickfont=dict(size=9))
        )
        st.sidebar.plotly_chart(fig_kw_side, use_container_width=True)
    except Exception as e:
        st.sidebar.bar_chart(df_kw_calc, x='wilayah_singkat', y='persen_kw', color='#2980b9', height=220, use_container_width=True)

st.sidebar.markdown("---")

# --- GRAFIK SIDEBAR 4: GRAFIK MAKRO INDEPENDEN % PRASERTEL ---
st.sidebar.subheader("📉 % Prasertel")
if not df_wilayah.empty:
    df_pt_calc = df_wilayah.groupby('kabupaten_kota').agg(
        total_sertel=('pra_sertel', 'sum'),
        total_bt_valid=('bt_valid', 'sum'),
        total_btel=('pra_btel', 'sum'),
        total_suel=('pra_suel', 'sum')
    ).reset_index()
    
    df_pt_calc['persen_sertel'] = (df_pt_calc['total_sertel'] / df_pt_calc['total_bt_valid'] * 100).fillna(0)
    df_pt_calc['wilayah_singkat'] = df_pt_calc['kabupaten_kota'].apply(singgkat_nama_wilayah)
    df_pt_calc = df_pt_calc.sort_values(by='persen_sertel', ascending=False)
    
    try:
        fig_pt_side = go.Figure()
        custom_hover_pt = list(zip(
            list(df_pt_calc['kabupaten_kota']),
            [format_lokal(v, False) for v in df_pt_calc['total_bt_valid']],
            [format_lokal(v, False) for v in df_pt_calc['total_sertel']],
            [format_lokal(v, False) for v in df_pt_calc['total_btel']],
            [format_lokal(v, False) for v in df_pt_calc['total_suel']]
        ))
        
        fig_pt_side.add_trace(go.Bar(
            x=df_pt_calc['wilayah_singkat'],
            y=df_pt_calc['persen_sertel'],
            marker_color='#e67e22',
            text=df_pt_calc['persen_sertel'].apply(lambda x: f"{format_lokal(x, True)}%"),
            textposition='outside',
            textfont=dict(size=8, weight='bold'),
            customdata=custom_hover_pt,
            hovertemplate=(
                "<b>Kabupaten/Kota:</b> %{customdata[0]}<br>"
                "<b>BT Valid:</b> %{customdata[1]}<br>"
                "<b>Pra Sertel:</b> %{customdata[2]}<br>"
                "<b>Pra Btel:</b> %{customdata[3]}<br>"
                "<b>Pra Suel:</b> %{customdata[4]}<br>"
                "<extra></extra>"
            )
        ))
        fig_pt_side.update_layout(
            margin=dict(t=25, b=25, l=5, r=5), height=260, showlegend=False,
            xaxis=dict(title=None, tickfont=dict(size=8, weight='bold'), type='category', dtick=1),
            yaxis=dict(title=None, tickfont=dict(size=9))
        )
        st.sidebar.plotly_chart(fig_pt_side, use_container_width=True)
    except Exception as e:
        st.sidebar.bar_chart(df_pt_calc, x='wilayah_singkat', y='persen_sertel', color='#e67e22', height=220, use_container_width=True)

# ==========================================
# PRE-PROCESSING DATA FILTER SEBELUM LAYOUT (PERBAIKAN LOGIKA TOTAL)
# ==========================================
df_peg_filtered = df_pegawai.copy()
df_wil_filtered = df_wilayah.copy()
df_pros_filtered = df_prosedur.copy()

if selected_kab not in ["Semua Kabupaten/Kota", "Sulawesi Tengah"]:
    # Jika memilih salah satu kabupaten spesifik
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]
    df_wil_filtered = df_wil_filtered[df_wil_filtered['kabupaten_kota'] == selected_kab]
    df_pros_filtered = df_pros_filtered[df_pros_filtered['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]
    
    if selected_kec != "Semua Kecamatan":
        df_wil_filtered = df_wil_filtered[df_wil_filtered['kecamatan'] == selected_kec]
else:
    # PERBAIKAN: Jika "Semua Kabupaten/Kota" atau "Sulawesi Tengah", JANGAN difilter ke Kanwil saja.
    # Biarkan df_peg_filtered, df_wil_filtered, dan df_pros_filtered memuat SELURUH baris data database.
    pass


# ==========================================
# 4. MAIN CONTENT MAIN LAYOUT
# ==========================================
st.title(f"🏢 Dashboard Kinerja BPN — {selected_kab}")
if selected_kec != "Semua Kecamatan":
    st.subheader(f"Kecamatan: {selected_kec}")
st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------
# BARIS ATAS: METRICS & BAR CHART HORISONTAL DIPA MAKRO (AKURAT DATABASE)
# ------------------------------------------
row_metrics = st.columns([1.8, 1.8, 1.8, 1.8, 1.8, 3.2])

with row_metrics[0]:
    # Menghitung total unik SDM dari data yang sudah difilter
    jumlah_sdm = df_peg_filtered['nama'].nunique()
    breakdown_asn = df_peg_filtered.groupby('kategori_asn')['nama'].count().to_dict()
    sub_asn_text = ", ".join([f"{k}: {v}" for k, v in breakdown_asn.items()]) if breakdown_asn else "PNS: 0, PPNPN: 0"
    st.markdown(f'<div class="custom-card"><div class="card-title">👥 Jumlah SDM</div><div class="card-value">{format_lokal(jumlah_sdm, False)}</div><div class="card-subtext">{sub_asn_text}</div></div>', unsafe_allow_html=True)

with row_metrics[1]:
    tot_apl = df_wil_filtered['luas_apl'].sum()
    tot_adm = df_wil_filtered['luas_adm'].sum()
    pct_apl = (tot_apl / tot_adm * 100) if tot_adm > 0 else 0
    st.markdown(f'<div class="custom-card"><div class="card-title">🗺️ Luas APL (Ha)</div><div class="card-value">{format_lokal(tot_apl, True)}</div><div class="card-subtext">{format_lokal(pct_apl, True)}% dari Luas ADM ({format_lokal(tot_adm, True)} Ha)</div></div>', unsafe_allow_html=True)

with row_metrics[2]:
    val_kec = df_wil_filtered['kecamatan'].nunique()
    lbl_kec = "Total Kecamatan Se-Sulteng" if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"] else f"Kecamatan di {selected_kab}"
    st.markdown(f'<div class="custom-card"><div class="card-title">🧩 Kecamatan</div><div class="card-value">{format_lokal(val_kec, False)}</div><div class="card-subtext">{lbl_kec}</div></div>', unsafe_allow_html=True)

with row_metrics[3]:
    val_desa = df_wil_filtered['desa_kelurahan'].nunique()
    sub_desa_text = "Total Desa/Kel Se-Sulteng" if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"] else "Total Desa & Kelurahan"
    st.markdown(f'<div class="custom-card"><div class="card-title">🏡 Desa / Kelurahan</div><div class="card-value">{format_lokal(val_desa, False)}</div><div class="card-subtext">{sub_desa_text}</div></div>', unsafe_allow_html=True)

with row_metrics[4]:
    val_kw = int(df_wil_filtered['jumlah_kw456'].sum())
    lbl_kw = "Total KW456 Se-Sulteng" if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"] else f"Total KW456 di {selected_kab}"
    st.markdown(f'<div class="custom-card"><div class="card-title">📂 Jumlah KW456</div><div class="card-value">{format_lokal(val_kw, False)}</div><div class="card-subtext">{lbl_kw}</div></div>', unsafe_allow_html=True)

with row_metrics[5]:
    total_target = df_peg_filtered['target_dipa'].sum()
    total_realisasi = df_peg_filtered['realisasi_dipa'].sum()
    sisa_dipa = max(0, total_target - total_realisasi)
    
    # PERBAIKAN PERSENTASE REALISASI:
    # Jika mode "Semua Kabupaten/Kota" / "Sulawesi Tengah", tampilkan Rerata Persentase Kinerja
    if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"] and not df_pegawai.empty:
        # Menghitung rerata persentase dari performa riil masing-masing kab_kota di database
        df_realisasi_kab = df_pegawai.groupby('kabupaten_kota')[['target_dipa', 'realisasi_dipa']].sum().reset_index()
        df_realisasi_kab['persen'] = (df_realisasi_kab['realisasi_dipa'] / df_realisasi_kab['target_dipa'] * 100).fillna(0)
        pct_display = df_realisasi_kab['persen'].mean()
    else:
        # Jika single kabupaten terpilih, gunakan persentase langsung daerah tersebut
        pct_display = (total_realisasi / total_target * 100) if total_target > 0 else 0
        
    if total_target > 0:
        fig_macro_bar = go.Figure()
        fig_macro_bar.add_trace(go.Bar(
            y=['DIPA'], x=[total_realisasi], name='Realisasi DIPA',
            orientation='h', marker_color='#2ecc71',
            text=f"{format_lokal(pct_display, True)}%", textposition='inside', 
            textfont=dict(color='white', weight='bold')
        ))
        fig_macro_bar.add_trace(go.Bar(
            y=['DIPA'], x=[sisa_dipa], name='Sisa Target',
            orientation='h', marker_color='#e2e8f0'
        ))
        fig_macro_bar.update_layout(
            barmode='stack', height=65, showlegend=False, margin=dict(t=0, b=0, l=5, r=5),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
        )
        st.plotly_chart(fig_macro_bar, use_container_width=True)
        
        st.markdown(f"""
        <div style='font-size: 11px; color: #475569; line-height: 1.4; margin-top: -2px; padding-left: 5px;'>
            <div>TARGET PAGU: <b>Rp {format_lokal(total_target, False)}</b></div>
            <div>REALISASI: <span style='color:#27ae60; font-weight:bold;'>Rp {format_lokal(total_realisasi, False)}</span></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Data DIPA Wilayah Kosong")

st.markdown("<hr>", unsafe_allow_html=True)


# ==========================================
# LAYOUT UTAMA: KIRI (PROFIL PEJABAT) vs KANAN (GRAFIK BESAR)
# ==========================================
col_left, col_right = st.columns([4, 8])

with col_left:
    col_url2, col_url1 = st.columns(2)
    
    with col_url2:
        df_bendahara = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Bendahara", case=False, na=False)]
        img_bendahara = df_bendahara.iloc[0]['url'] if not df_bendahara.empty and pd.notna(df_bendahara.iloc[0]['url']) else "https://via.placeholder.com/150"
        st.image(img_bendahara, use_container_width=True)
        
    with col_url1:
        df_kakan = df_peg_filtered[df_peg_filtered['jabatan'].str.contains("Kepala Kantor|Kakan|Kakanwil", case=False, na=False)]
        img_kakan = df_kakan.iloc[0]['url'] if not df_kakan.empty and pd.notna(df_kakan.iloc[0]['url']) else "https://via.placeholder.com/150"
        st.image(img_kakan, use_container_width=True)
        
    st.markdown("<br><p style='font-weight:bold; font-size:15px; border-bottom:2px solid #cbd5e1; padding-bottom:4px;'>Profil Pejabat Struktural & Kinerja</p>", unsafe_allow_html=True)
    
    def render_dashboard_profile(jabatan_keyword):
        row = df_peg_filtered[df_peg_filtered['jabatan'].str.contains(jabatan_keyword, case=False, na=False)]
        if not row.empty:
            row = row.iloc[0]
            target = row['target_dipa']
            realisasi = row['realisasi_dipa']
            pct = (realisasi / target * 100) if target > 0 else 0
            img_url = row['url'] if pd.notna(row['url']) and str(row['url']).startswith("http") else "https://via.placeholder.com/150"
            
            progress_bar_container = f'<div style="background-color:#e2e8f0; border-radius:4px; height:10px; width:100%; margin:6px 0 4px 0; overflow:hidden;"><div style="background-color:#2ecc71; width:{min(pct, 100.0)}%; height:100%; border-radius:4px;"></div></div>'
            
            html_content = (
                '<div class="profile-box">'
                    '<div style="display:flex; align-items:flex-start;">'
                        f'<div style="width:25%;"><img src="{img_url}" style="width:100%; border-radius:6px; border:1px solid #e2e8f0; display:block;"></div>'
                        f'<div style="width:75%; padding-left:14px;">'
                            f'<div class="profile-name">{row["nama"]}</div>'
                            f'<div class="profile-title">{row["jabatan"]}</div>'
                            f'<div class="profile-target">Target: Rp {format_lokal(target, False)}</div>'
                            f'{progress_bar_container}'
                            f'<div style="font-size:11px; color:#475569; text-align:right; font-weight:500;">Realisasi: <span style="color:#2ecc71; font-weight:700;">{format_lokal(pct, True)}%</span> (Rp {format_lokal(realisasi, False)})</div>'
                        '</div>'
                    '</div>'
                '</div>'
            )
            st.markdown(html_content, unsafe_allow_html=True)
        else:
            st.caption(f"⚠️ Jabatan '{jabatan_keyword}' tidak ditemukan di wilayah ini.")

    order_struktural = ["Tata Usaha", "Survei dan Pemetaan", "Penetapan Hak", "Penataan", "Pengadaan Tanah", "Sengketa"]
    for java in order_struktural:
        render_dashboard_profile(java)

with col_right:
    # Penentuan poros sumbu absis grafik pertanahan besar di sebelah kanan
    if selected_kab in ["Semua Kabupaten/Kota", "Sulawesi Tengah"]:
        df_chart = df_wilayah.groupby('kabupaten_kota').sum().reset_index()
        x_axis_column = 'kabupaten_kota'
    elif selected_kec == "Semua Kecamatan":
        df_chart = df_wil_filtered.groupby('kecamatan').sum().reset_index()
        x_axis_column = 'kecamatan'
    else:
        df_chart = df_wil_filtered.groupby('desa_kelurahan').sum().reset_index()
        x_axis_column = 'desa_kelurahan'

    # GRAFIK 1: PERSIL
    st.markdown("### 🗺️ Grafik Pemetaan & Validasi Persil")
    if not df_chart.empty:
        fig_batang1 = go.Figure()
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_persil'], name='Jumlah Persil', marker_color='#1d4ed8'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_su'], name='Jumlah SU', marker_color='#3b82f6'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_suvalid'], name='SU Valid', marker_color='#10b981'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_suel'], name='Pra SUEL', marker_color='#f59e0b'))
        fig_batang1.update_layout(barmode='group', xaxis_title="Daftar Wilayah", yaxis_title="Volume", legend_orientation="h", legend=dict(x=0, y=1.12), margin=dict(t=40, b=30), height=410)
        st.plotly_chart(fig_batang1, use_container_width=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # GRAFIK 2: BUKU TANAH & PRASERTEL
    st.markdown("### 📖 Grafik Validasi Buku Tanah & Prasertel")
    if not df_chart.empty:
        fig_batang2 = go.Figure()
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_bt'], name='Jumlah BT', marker_color='#6d28d9'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['bt_valid'], name='BT Valid', marker_color='#059669'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_btel'], name='Pra BTEL', marker_color='#d97706'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_sertel'], name='Pra SERTEL', marker_color='#e74c3c'))
        fig_batang2.update_layout(barmode='group', xaxis_title="Daftar Wilayah", yaxis_title="Volume", legend_orientation="h", legend=dict(x=0, y=1.12), margin=dict(t=40, b=30), height=410)
        st.plotly_chart(fig_batang2, use_container_width=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)
