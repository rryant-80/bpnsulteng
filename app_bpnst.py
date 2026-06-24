import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Konfigurasi Halaman Streamlit ke Wide Mode
st.set_page_config(layout="wide", page_title="Dashboard Keagrariaan BPN", page_icon="🏢")

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

# Fungsi pemformat angka lokal (Titik ribuan, Koma desimal)
def format_lokal(nilai, pakai_desimal=True):
    if pakai_desimal:
        teks = f"{nilai:,.2f}"
        return teks.replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{int(nilai):,}".replace(",", ".")

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

try:
    df_wilayah = load_data(SPREADSHEET_ID, "1848496896")
    df_pegawai = load_data(SPREADSHEET_ID, "1168898330")
except Exception as e:
    st.error(f"Gagal memuat data dari Google Sheets: {e}")
    st.stop()

# Pembersihan data teks baku
for col in ['kabupaten_kota', 'kecamatan', 'desa_kelurahan']:
    if col in df_wilayah.columns:
        df_wilayah[col] = df_wilayah[col].astype(str).str.strip()

for col in ['kabupaten_kota', 'nama', 'jabatan', 'kategori_asn']:
    if col in df_pegawai.columns:
        df_pegawai[col] = df_pegawai[col].astype(str).str.strip()

# =========================================================================
# CLEANING & KONVERSI NUMERIK (MEMBERSIHKAN TITIK RIBUAN SECARA MURNI)
# =========================================================================
num_cols_wil = ['luas_adm', 'luas_apl', 'jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 'pra_btel', 'jumlah_su', 'jumlah_suvalid', 'pra_suel']
for col in num_cols_wil:
    if col in df_wilayah.columns:
        # Menghapus titik pemisah ribuan bawaan string regional lokal Indonesia agar dibaca utuh oleh pandas
        df_wilayah[col] = df_wilayah[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
        df_wilayah[col] = pd.to_numeric(df_wilayah[col], errors='coerce').fillna(0)

# KONVERSI SATUAN LUAS: m2 ke Hektar (Ha)
df_wilayah['luas_adm'] = df_wilayah['luas_adm'] / 10000
df_wilayah['luas_apl'] = df_wilayah['luas_apl'] / 10000

num_cols_peg = ['target_dipa', 'realisasi_dipa']
for col in num_cols_peg:
    if col in df_pegawai.columns:
        df_pegawai[col] = df_pegawai[col].astype(str).str.replace('Rp', '', regex=False).str.replace('.', '', regex=False).str.replace(' ', '', regex=False)
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
df_peg_filtered = df_pegawai.copy()
if selected_kab != "Sulawesi Tengah":
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains(selected_kab, case=False, na=False)]
else:
    df_peg_filtered = df_peg_filtered[df_peg_filtered['kabupaten_kota'].str.contains("Kanwil|Provinsi|Sulteng", case=False, na=False)]

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
# BARIS ATAS: METRICS & BAR CHART HORISONTAL DIPA MAKRO
# ------------------------------------------
row_metrics = st.columns([1.8, 1.8, 1.8, 1.8, 1.8, 3.2])

with row_metrics[0]:
    jumlah_sdm = df_peg_filtered['nama'].nunique()
    breakdown_asn = df_peg_filtered.groupby('kategori_asn')['nama'].count().to_dict()
    sub_asn_text = ", ".join([f"{k}: {v}" for k, v in breakdown_asn.items()]) if breakdown_asn else "PNS: 0, PPNPN: 0"
    st.markdown(f'<div class="custom-card"><div class="card-title">👥 Jumlah SDM</div><div class="card-value">{format_lokal(jumlah_sdm, False)}</div><div class="card-subtext">{sub_asn_text}</div></div>', unsafe_allow_html=True)

with row_metrics[1]:
    tot_apl = df_wil_filtered['luas_apl'].sum()
    tot_adm = df_wil_filtered['luas_adm'].sum()
    pct_apl = (tot_apl / tot_adm * 100) if tot_adm > 0 else 0
    st.markdown(f'<div class="custom-card"><div class="card-title">🗺️ Luas APL</div><div class="card-value">{format_lokal(tot_apl, True)} Ha</div><div class="card-subtext">{format_lokal(pct_apl, True)}% dari Luas ADM ({format_lokal(tot_adm, True)} Ha)</div></div>', unsafe_allow_html=True)

with row_metrics[2]:
    if selected_kab == "Sulawesi Tengah":
        val_kec = df_wilayah['kecamatan'].nunique()
        lbl_kec = "Total Kecamatan Se-Sulteng"
    else:
        val_kec = df_wil_filtered['kecamatan'].nunique()
        lbl_kec = f"Kecamatan di {selected_kab}"
    st.markdown(f'<div class="custom-card"><div class="card-title">🧩 Kecamatan</div><div class="card-value">{format_lokal(val_kec, False)}</div><div class="card-subtext">{lbl_kec}</div></div>', unsafe_allow_html=True)

with row_metrics[3]:
    if selected_kab == "Sulawesi Tengah":
        val_desa = df_wilayah['desa_kelurahan'].nunique()
        sub_desa_text = "Total Desa/Kel Se-Sulteng"
    else:
        val_desa = df_wil_filtered['desa_kelurahan'].nunique()
        sub_desa_text = "Total Desa & Kelurahan"
    st.markdown(f'<div class="custom-card"><div class="card-title">🏡 Desa / Kelurahan</div><div class="card-value">{format_lokal(val_desa, False)}</div><div class="card-subtext">{sub_desa_text}</div></div>', unsafe_allow_html=True)

with row_metrics[4]:
    # NILAI CARD JUMLAH KW456 (Murni dari jumlahan baris terdata tanpa faktor pengali)
    if selected_kab == "Sulawesi Tengah":
        val_kw = int(df_wilayah['jumlah_kw456'].sum())
        lbl_kw = "Total KW456 Se-Sulteng"
    else:
        val_kw = int(df_wil_filtered['jumlah_kw456'].sum())
        lbl_kw = f"Total KW456 di {selected_kab}"
    st.markdown(f'<div class="custom-card"><div class="card-title">📂 Jumlah KW456</div><div class="card-value">{format_lokal(val_kw, False)}</div><div class="card-subtext">{lbl_kw}</div></div>', unsafe_allow_html=True)

with row_metrics[5]:
    total_target = df_peg_filtered['target_dipa'].sum()
    total_realisasi = df_peg_filtered['realisasi_dipa'].sum()
    sisa_dipa = max(0, total_target - total_realisasi)
    pct_macro = (total_realisasi / total_target * 100) if total_target > 0 else 0
    
    if total_target > 0:
        fig_macro_bar = go.Figure()
        fig_macro_bar.add_trace(go.Bar(
            y=['DIPA'], x=[total_realisasi], name='Realisasi DIPA',
            orientation='h', marker_color='#2ecc71',
            text=f"{format_lokal(pct_macro, True)}%", textposition='inside', textfont=dict(color='white', weight='bold')
        ))
        fig_macro_bar.add_trace(go.Bar(
            y=['DIPA'], x=[sisa_dipa], name='Sisa Target',
            orientation='h', marker_color='#e2e8f0'
        ))
        fig_macro_bar.update_layout(
            barmode='stack', height=65, showlegend=False,
            margin=dict(t=0, b=0, l=5, r=5),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
        )
        st.plotly_chart(fig_macro_bar, use_container_width=True)
        
        st.markdown(f"""
        <div style='font-size: 11px; color: #475569; line-height: 1.4; margin-top: -2px; padding-left: 5px;'>
            <div>Target Pagu: <b>Rp {format_lokal(total_target, False)}</b></div>
            <div>Realisasi DIPA: <span style='color:#27ae60; font-weight:bold;'>Rp {format_lokal(total_realisasi, False)}</span></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Data DIPA Wilayah Kosong")

st.markdown("<hr>", unsafe_allow_html=True)


# ==========================================
# LAYOUT UTAMA: KIRI (PROFIL) vs KANAN (GRAFIK BESAR)
# ==========================================
col_left, col_right = st.columns([4, 8])

with col_left:
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
    if selected_kab == "Sulawesi Tengah":
        df_chart = df_wilayah.groupby('kabupaten_kota').sum().reset_index()
        x_axis_column = 'kabupaten_kota'
    elif selected_kec == "Semua Kecamatan":
        df_chart = df_wil_filtered.groupby('kecamatan').sum().reset_index()
        x_axis_column = 'kecamatan'
    else:
        df_chart = df_wil_filtered.groupby('desa_kelurahan').sum().reset_index()
        x_axis_column = 'desa_kelurahan'

    # GRAFIK PERSIL
    st.markdown("### 🗺️ Grafik Pemetaan & Validasi Persil per-Wilayah")
    if not df_chart.empty:
        fig_batang1 = go.Figure()
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_persil'], name='Jumlah Persil', marker_color='#1d4ed8'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_su'], name='Jumlah SU', marker_color='#3b82f6'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_suvalid'], name='SU Valid', marker_color='#10b981'))
        fig_batang1.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_suel'], name='Pra SUEL', marker_color='#f59e0b'))
        fig_batang1.update_layout(barmode='group', xaxis_title="Daftar Wilayah", yaxis_title="Volume", legend_orientation="h", legend=dict(x=0, y=1.12), margin=dict(t=40, b=30), height=430)
        st.plotly_chart(fig_batang1, use_container_width=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # GRAFIK BUKU TANAH
    st.markdown("### 📖 Grafik Validasi Buku Tanah per-Wilayah")
    if not df_chart.empty:
        fig_batang2 = go.Figure()
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['jumlah_bt'], name='Jumlah BT', marker_color='#6d28d9'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['bt_valid'], name='BT Valid', marker_color='#059669'))
        fig_batang2.add_trace(go.Bar(x=df_chart[x_axis_column], y=df_chart['pra_btel'], name='Pra BTEL', marker_color='#d97706'))
        fig_batang2.update_layout(barmode='group', xaxis_title="Daftar Wilayah", yaxis_title="Volume", legend_orientation="h", legend=dict(x=0, y=1.12), margin=dict(t=40, b=30), height=430)
        st.plotly_chart(fig_batang2, use_container_width=True)
