"""
Dashboard Analisis Internet Desa.

Antarmuka Streamlit tipis di atas modul `utils`. File ini hanya
menangani layout halaman dan interaksi pengguna; seluruh logika
pembacaan data, pembersihan, perhitungan analisis, dan pembuatan
insight berada di `utils/data_processing.py`, `utils/analysis.py`,
dan `utils/insights.py`.
"""

import io

import pandas as pd
import plotly.express as px
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, to_hex

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from utils import analysis as an
from utils import insights as ins
from utils.constants import (
    WARNA_HASIL_EVALUASI,
    URUTAN_HASIL_EVALUASI,
    WARNA_PENGGUNAAN,
    URUTAN_PENGGUNAAN,
    URUTAN_PRIORITAS,
    )
from utils.data_processing import (
    load_excel,
    validate_columns,
    clean_data,
)
from utils.pdf_export import buat_pdf, buat_pdf_insight

PAGE_TITLE = "Dashboard Analisis Internet Desa"
LABEL_TANPA_ISP = "(Belum ada ISP / Belum Terpasang)"
PETA_ZOOM_LEVEL = 6
PETA_TINGGI_PIKSEL = 600
TAHUN_DEFAULT = 2026

# Pusat default peta = Kalimantan Timur (kawasan lokasi data).
PETA_PUSAT_KALTIM = {"lat": 0.5, "lon": 116.5}


def konfigurasi_halaman() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)
    st.write(
        "Analisis, monitoring, dan insight kondisi layanan Internet Desa "
        "berdasarkan data Excel yang diunggah."
    )


def ambil_file_upload():
    st.sidebar.header("Data")

    uploaded_file = st.sidebar.file_uploader(
        "Upload file Excel (harus memiliki sheet 'Data Master')",
        type=["xlsx", "xls"],
    )

    return uploaded_file


def muat_dan_validasi_data(uploaded_file) -> pd.DataFrame | None:
    try:
        df_mentah = load_excel(uploaded_file)
    except Exception as error:
        st.error(f"Gagal membaca file Excel: {error}")
        return None

    try:
        validate_columns(df_mentah)
    except ValueError as error:
        st.error("Format file tidak sesuai kontrak data aplikasi.")
        st.error(str(error))
        return None

    try:
        df_bersih = clean_data(df_mentah, tahun=TAHUN_DEFAULT)
    except ValueError as error:
        st.error(f"Data tidak dapat diproses: {error}")
        return None

    st.sidebar.success(
        f"Data berhasil dimuat: "
        f"{df_bersih['Location ID'].nunique():,} lokasi"
    )

    return df_bersih

def render_filter_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menampilkan kontrol filter di sidebar dan mengembalikan DataFrame
    yang sudah difilter sesuai pilihan pengguna.

    Baris dengan ISP kosong (lokasi belum terpasang) ditangani secara
    eksplisit lewat opsi `LABEL_TANPA_ISP`, agar tidak diam-diam
    terbuang saat pengguna memilih "semua ISP".
    """
    st.sidebar.header("Filter")

    periode_options = (
        df[["Periode Urutan", "Periode Label"]]
        .drop_duplicates()
        .sort_values("Periode Urutan")
    )
    label_ke_urutan = dict(
        zip(periode_options["Periode Label"], periode_options["Periode Urutan"])
    )

    periode_terpilih = st.sidebar.multiselect(
        "Periode (Bulan Tahun)",
        options=periode_options["Periode Label"].tolist(),
        default=periode_options["Periode Label"].tolist(),
    )

    kabupaten_options = sorted(df["Kabupaten"].dropna().unique())
    kabupaten_terpilih = st.sidebar.multiselect(
        "Kabupaten", options=kabupaten_options, default=kabupaten_options
    )

    isp_options_asli = sorted(df["ISP"].dropna().unique())
    ada_isp_kosong = df["ISP"].isna().any()
    isp_options = isp_options_asli + ([LABEL_TANPA_ISP] if ada_isp_kosong else [])
    isp_terpilih = st.sidebar.multiselect(
        "ISP", options=isp_options, default=isp_options
    )

    urutan_terpilih = [label_ke_urutan[label] for label in periode_terpilih]

    mask_isp = df["ISP"].isin(isp_terpilih)
    if LABEL_TANPA_ISP in isp_terpilih:
        mask_isp = mask_isp | df["ISP"].isna()

    return df[
        df["Periode Urutan"].isin(urutan_terpilih)
        & df["Kabupaten"].isin(kabupaten_terpilih)
        & mask_isp
    ], periode_options["Periode Label"].tolist()

@st.cache_data(show_spinner="Membuat laporan PDF (dengan grafik)...")
def _buat_pdf_cache(df_terfilter: pd.DataFrame) -> bytes:
    """
    Wrapper ter-cache di sekitar `buat_pdf`.

    PDF sekarang menyertakan grafik (bukan hanya tabel), sehingga proses
    pembuatannya lebih berat. Tanpa cache, PDF ini akan dibangun ulang
    dari nol setiap kali halaman Streamlit rerun -- misalnya setiap kali
    pengguna mengganti tab atau membuka expander -- padahal isinya tidak
    berubah selama filter/data yang sama. `st.cache_data` menyimpan hasil
    berdasarkan isi `df_terfilter`, jadi PDF hanya dibangun ulang saat
    filter atau data benar-benar berubah.
    """
    return buat_pdf(df_terfilter)


def render_tombol_unduh_pdf(df_terfilter: pd.DataFrame) -> None:
    """Tombol untuk mengunduh seluruh hasil analisis dalam bentuk PDF."""
    st.sidebar.header("Ekspor Laporan")
    try:
        pdf_bytes = _buat_pdf_cache(df_terfilter)
        st.sidebar.download_button(
            "Unduh Laporan PDF",
            data=pdf_bytes,
            file_name="laporan_internet_desa.pdf",
            mime="application/pdf",
        )
    except Exception as error:
        st.sidebar.warning(f"PDF tidak dapat dibuat: {error}")

def terapkan_warna_evaluasi(fig):
    """
    Memastikan warna kategori Hasil Evaluasi konsisten.
    """
    fig.update_layout(
        legend_title_text="Hasil Evaluasi",
    )

    for trace in fig.data:
        nama = str(trace.name).upper().strip()

        if nama in WARNA_HASIL_EVALUASI:
            trace.marker.color = WARNA_HASIL_EVALUASI[nama]

    return fig

def buat_bar_chart_persentase(
    data: pd.DataFrame,
    x: str,
    y: str,
    warna: str | None = None,
):
    """
    Bar chart persentase.

    Untuk kolom "Hasil Evaluasi" dan "Penggunaan", warna mengikuti
    palet tetap (WARNA_HASIL_EVALUASI / WARNA_PENGGUNAAN) yang disusun
    berdasarkan URUTAN kategorinya (mis. Penggunaan: dari 0GB hingga
    >1000GB), BUKAN berdasarkan besar-kecilnya persentase bar tersebut.
    Ini penting karena bar dengan persentase terbesar belum tentu
    kategori "terbaik" -- kategori 0GB tetap harus tampil merah
    (kondisi buruk) walau kebetulan jumlah lokasinya sedikit/banyak.
    Warna ini juga konsisten dengan grafik tren Penggunaan pada tab
    Analisis Temporal, yang memakai palet yang sama.

    Untuk kolom lain (mis. proporsi bermasalah per Kabupaten/ISP),
    warna tetap berdasarkan nilai (tinggi = hijau, rendah = merah),
    karena di situ memang tidak ada urutan kategori intrinsik.
    """

    fig = px.bar(
        data,
        x=x,
        y=y,
        text=y,
    )

    if x == "Hasil Evaluasi":
        warna_bars = [
            WARNA_HASIL_EVALUASI.get(str(kategori).upper().strip(), "#808080")
            for kategori in data[x]
        ]
    elif x == "Penggunaan":
        warna_bars = [
            WARNA_PENGGUNAAN.get(str(kategori).strip(), "#808080")
            for kategori in data[x]
        ]
    else:
        nilai = pd.to_numeric(data[y], errors="coerce")

        nilai_min = nilai.min()
        nilai_max = nilai.max()

        if nilai_max == nilai_min:
            norm = Normalize(vmin=0, vmax=1)
            posisi = [0.5] * len(nilai)
        else:
            norm = Normalize(
                vmin=nilai_min,
                vmax=nilai_max,
            )
            posisi = [
                norm(v)
                for v in nilai
            ]

        cmap = matplotlib.colormaps["RdYlGn"]

        warna_bars = [
            to_hex(cmap(p))
            for p in posisi
        ]

    fig.update_traces(
        marker_color=warna_bars,
        texttemplate="%{text:.1f}%",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        uniformtext_minsize=9,
        uniformtext_mode="hide",
        margin=dict(t=50),
    )

    return fig

@st.cache_data(show_spinner="Membuat PDF insight...")
def _buat_pdf_insight_cache(df_terfilter: pd.DataFrame) -> bytes:
    """Wrapper ter-cache di sekitar `buat_pdf_insight` (lihat alasan
    caching pada `_buat_pdf_cache`)."""
    return buat_pdf_insight(df_terfilter)


def render_tab_overview(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Ringkasan Umum")

    kpi = an.get_kpi_summary(df_terfilter)
    kolom = st.columns(5)
    lokasi_prioritas = an.lokasi_prioritas(df_terfilter)
    jumlah_desa_bermasalah = int(
    lokasi_prioritas["Desa Bermasalah"].sum()
    )

    kolom[0].metric(
    "Total Record",
    f"{kpi['total_record']:,}"
    )

    kolom[1].metric(
        "Total Lokasi",
        f"{kpi['total_lokasi']:,}"
    )

    kolom[2].metric(
        "Total Kabupaten",
        f"{kpi['total_kabupaten']:,}"
    )

    kolom[3].metric(
        "Total ISP",
        f"{kpi['total_isp']:,}"
    )

    kolom[4].metric(
        "Desa Bermasalah",
        f"{jumlah_desa_bermasalah:,}"
    )

    st.caption(
        "Total Lokasi dihitung dari kombinasi unik Kabupaten, Kecamatan, dan Desa, "
        "bukan jumlah baris -- satu lokasi dapat muncul di beberapa periode."
    )

    kolom_kiri, kolom_kanan = st.columns(2)

    with kolom_kiri:
        st.markdown("**Distribusi Hasil Evaluasi (per lokasi)**")
        dist_evaluasi = an.distribusi_hasil_evaluasi(df_terfilter)
        fig_evaluasi = buat_bar_chart_persentase(
            dist_evaluasi, x="Hasil Evaluasi", y="Persentase", warna="Hasil Evaluasi"
        )
        fig_evaluasi.update_layout(
            xaxis={
                "categoryorder": "array",
                "categoryarray": URUTAN_HASIL_EVALUASI,
            },
        )
        st.plotly_chart(fig_evaluasi, use_container_width=True)

    with kolom_kanan:
        st.markdown("**Distribusi Penggunaan (seluruh baris terfilter)**")
        jumlah_tercatat = int(df_terfilter["Penggunaan"].notna().sum())
        jumlah_lokasi_terfilter = df_terfilter["Location ID"].nunique()
        st.caption(
            f"Dihitung dari {jumlah_tercatat} observasi bulanan yang benar-benar "
            f"tercatat, dari {jumlah_lokasi_terfilter} lokasi pada filter saat ini. "
            "Sumber data tidak memiliki panel lengkap -- pada filter periode yang "
            "sempit, jumlah observasi bisa jauh lebih kecil dari jumlah lokasi, "
            "sehingga persentase di bawah ini bisa tidak representatif."
        )
        dist_penggunaan = an.distribusi_penggunaan(df_terfilter)

        fig = buat_bar_chart_persentase(
            dist_penggunaan,
            x="Penggunaan",
            y="Persentase"
        )

        fig.update_layout(
        xaxis_tickangle=-30,
        xaxis={
            "categoryorder": "array",
            "categoryarray": URUTAN_PENGGUNAAN,
            },
        )

        st.plotly_chart(fig, use_container_width=True)

    kolom_judul_insight, kolom_tombol_insight = st.columns([4, 1])
    with kolom_judul_insight:
        st.markdown("**Insight Utama**")

    daftar_insight = ins.generate_all_insights(df_terfilter)

    with kolom_tombol_insight:
        try:
            pdf_insight_bytes = _buat_pdf_insight_cache(df_terfilter)
            st.download_button(
                "Ekspor PDF",
                data=pdf_insight_bytes,
                file_name="insight_internet_desa.pdf",
                mime="application/pdf",
                key="unduh_pdf_insight",
            )
        except Exception as error:
            st.warning(f"PDF insight tidak dapat dibuat: {error}")

    if not daftar_insight:
        st.write("Belum ada insight yang dapat dihitung dari data terfilter saat ini.")
        return
    for teks in daftar_insight:
        st.info(teks)


def render_tab_perbandingan_grup(df_terfilter: pd.DataFrame, kolom_grup: str) -> None:
    """
    Tab perbandingan yang polanya sama untuk Kabupaten maupun ISP:
    stacked bar komposisi evaluasi, bar proporsi bermasalah, dan
    tabel jumlah lokasi. Dipakai ulang oleh kedua tab agar tidak ada
    duplikasi antara tab Wilayah dan tab ISP.
    """
    st.subheader(f"Perbandingan Kondisi Antar {kolom_grup}")
    st.caption(
        "Perbandingan menggunakan persentase, bukan jumlah baris mentah, "
        f"agar {kolom_grup.lower()} dengan jumlah lokasi lebih banyak tidak "
        "otomatis terlihat lebih buruk."
    )

    tabel_komposisi, jumlah_lokasi = an.komposisi_evaluasi_per_grup(
        df_terfilter, kolom_grup
    )
    fig_komposisi = px.bar(
    tabel_komposisi,
    x=kolom_grup,
    y="Persentase",
    color="Hasil Evaluasi",
    barmode="stack",
    text="Persentase",
    category_orders={
        "Hasil Evaluasi": an.URUTAN_HASIL_EVALUASI
    },
    color_discrete_map=WARNA_HASIL_EVALUASI,
    )

    fig_komposisi.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="inside",
        insidetextanchor="middle",
        cliponaxis=False,
    )

    fig_komposisi.update_layout(
        yaxis_title="Persentase (%)",
        margin=dict(t=40),
    )

    fig_komposisi = terapkan_warna_evaluasi(fig_komposisi)

    fig_komposisi.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(fig_komposisi, use_container_width=True)

    st.markdown(
    f"**Proporsi Desa Bermasalah per {kolom_grup}**")
    proporsi_bermasalah = an.proporsi_bermasalah_per_grup(df_terfilter, kolom_grup)
    fig_proporsi = buat_bar_chart_persentase(
    proporsi_bermasalah,
    x=kolom_grup,
    y="Persentase Bermasalah",)

    fig_proporsi.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(fig_proporsi, use_container_width=True)

    with st.expander(f"Lihat tabel jumlah lokasi per {kolom_grup}"):
        st.dataframe(jumlah_lokasi, use_container_width=True)


def render_tab_temporal(df_terfilter: pd.DataFrame, urutan_periode_label: list[str]) -> None:
    st.subheader("Tren Penggunaan Bulanan")
    st.warning(
        "Catatan metodologi: kolom Hasil Evaluasi pada dataset ini bersifat "
        "statis per lokasi (nilainya sama di semua periode/bulan). Karena itu, "
        "tren waktu yang bermakna pada dataset ini dihitung dari kolom "
        "Penggunaan, yang memang berubah dari bulan ke bulan."
    )

    observasi_per_periode = an.jumlah_observasi_per_periode(df_terfilter)
    st.markdown("**Jumlah Lokasi Tercatat per Periode**")
    st.caption(
        "Sumber data tidak memiliki panel lengkap -- sebagian periode (biasanya "
        "bulan yang paling baru) baru tersurvei di sebagian kecil lokasi. Grafik "
        "persentase di bawah bisa menyesatkan pada periode dengan jumlah lokasi "
        "tercatat yang masih sedikit."
    )
    fig_observasi = px.bar(
        observasi_per_periode,
        x="Periode Label",
        y="Jumlah Lokasi Tercatat",
        text="Jumlah Lokasi Tercatat",
        category_orders={
        "Periode Label": urutan_periode_label,
        "Penggunaan": URUTAN_PENGGUNAAN,
        },
    )

    # Warna berdasarkan tinggi/rendahnya jumlah lokasi
    nilai = pd.to_numeric(
        observasi_per_periode["Jumlah Lokasi Tercatat"],
        errors="coerce",
    )

    nilai_min = nilai.min()
    nilai_max = nilai.max()

    if nilai_max == nilai_min:
        posisi = [0.5] * len(nilai)
    else:
        posisi = [
            (v - nilai_min) / (nilai_max - nilai_min)
            for v in nilai
        ]

    cmap = matplotlib.colormaps["RdYlGn"]

    warna_bars = [
        to_hex(cmap(p))
        for p in posisi
    ]

    fig_observasi.update_traces(
        marker_color=warna_bars,
        texttemplate="%{text:,}",
        textposition="outside",
        cliponaxis=False,
    )

    fig_observasi.update_layout(
        margin=dict(t=50),
    )
    st.plotly_chart(fig_observasi, use_container_width=True)

    tren_penggunaan = an.tren_penggunaan_bulanan(df_terfilter)
    fig_tren = px.area(
        tren_penggunaan,
        x="Periode Label",
        y="Persentase",
        color="Penggunaan",
        color_discrete_map=WARNA_PENGGUNAAN,
        category_orders={"Periode Label": urutan_periode_label},
    )
    st.plotly_chart(fig_tren, use_container_width=True)

    with st.expander("Lihat distribusi Hasil Evaluasi per periode (referensi, bersifat statis)"):
        tren_evaluasi = an.tren_evaluasi_terkini_per_periode_tersedia(df_terfilter)
        fig_evaluasi = px.bar(
            tren_evaluasi,
            x="Periode Label",
            y="Jumlah",
            color="Hasil Evaluasi",
            barmode="stack",
            text="Jumlah",
            category_orders={
                "Periode Label": urutan_periode_label,
                "Hasil Evaluasi": an.URUTAN_HASIL_EVALUASI,
            },
            color_discrete_map=WARNA_HASIL_EVALUASI,
        )

        fig_evaluasi.update_traces(
            texttemplate="%{text:,}",
            textposition="inside",
        )

        fig_evaluasi.update_layout(
            margin=dict(t=40),
        )

        fig_evaluasi = terapkan_warna_evaluasi(fig_evaluasi)
        st.plotly_chart(fig_evaluasi, use_container_width=True)


def render_tab_spasial(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Peta Persebaran Lokasi Internet Desa")

    data_peta = an.data_peta(df_terfilter)
    jumlah_dikecualikan = df_terfilter["Location ID"].nunique() - len(data_peta)
    if jumlah_dikecualikan > 0:
        st.caption(
            f"{jumlah_dikecualikan} lokasi tidak ditampilkan di peta karena koordinat "
            "tidak valid/tidak wajar (data tetap tersedia di tab Detail Data)."
        )

    if data_peta.empty:
        st.info("Tidak ada lokasi dengan koordinat valid pada filter saat ini.")
        return

    data_peta = data_peta.sort_values(
        ["Kabupaten", "Kecamatan", "Desa"],
        key=lambda s: s.astype("string").str.lower(),
    ).reset_index(drop=True)

    data_peta["Label Peta"] = (
        data_peta["Desa"].astype("string")
        + " — "
        + data_peta["Kecamatan"].astype("string")
        + ", "
        + data_peta["Kabupaten"].astype("string")
    )

    pilihan = st.selectbox(
        "Pilih lokasi untuk dipusatkan pada peta",
        data_peta["Label Peta"],
        index=None,
        placeholder="Tampilkan semua lokasi (zoom default)...",
    )

    target = data_peta[data_peta["Label Peta"] == pilihan] if pilihan else pd.DataFrame()
    if not target.empty:
        pusat = {
            "lat": float(target.iloc[0]["Latitude"]),
            "lon": float(target.iloc[0]["Longitude"]),
        }
        zoom_peta = 13
    else:
        pusat = PETA_PUSAT_KALTIM
        zoom_peta = PETA_ZOOM_LEVEL

    try:
        fig_peta = px.scatter_map(
            data_peta,
            lat="Latitude",
            lon="Longitude",
            color="Hasil Evaluasi",
            hover_name="Desa",
            hover_data={
                "Kecamatan": True,
                "Kabupaten": True,
                "ISP": True,
                "Produk": True,
                "Penggunaan": True,
                "Hasil Evaluasi": True,
                "Latitude": False,
                "Longitude": False,
            },
            center=pusat,
            zoom=zoom_peta,
            height=PETA_TINGGI_PIKSEL,
            category_orders={
                "Hasil Evaluasi": an.URUTAN_HASIL_EVALUASI
            },
            color_discrete_map=WARNA_HASIL_EVALUASI,
        )
        
        fig_peta.update_layout(
            map_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend_title_text="Hasil Evaluasi",
        )
        
    except AttributeError:
        fig_peta = px.scatter_mapbox(
            data_peta,
            lat="Latitude",
            lon="Longitude",
            color="Hasil Evaluasi",
            hover_name="Desa",
            hover_data={
                "Kecamatan": True,
                "Kabupaten": True,
                "ISP": True,
                "Produk": True,
                "Penggunaan": True,
                "Hasil Evaluasi": True,
                "Latitude": False,
                "Longitude": False,
            },
            center=pusat,
            zoom=zoom_peta,
            height=PETA_TINGGI_PIKSEL,
            category_orders={
                "Hasil Evaluasi": an.URUTAN_HASIL_EVALUASI
            },
            color_discrete_map=WARNA_HASIL_EVALUASI,
        )
        
        fig_peta.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend_title_text="Hasil Evaluasi",
        )

    fig_peta = terapkan_warna_evaluasi(fig_peta)
    st.plotly_chart(fig_peta, use_container_width=True)


def render_tab_lokasi_prioritas(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Lokasi Prioritas Monitoring")
    st.caption(
        "Desa Bermasalah hanya terdiri dari kategori "
        "Tidak Aktif dan Belum Terpasang. "
        "Kategori Kurang Optimal dan Tidak Optimal tetap "
        "ditampilkan sebagai hasil evaluasi, tetapi tidak "
        "dimasukkan ke perhitungan Desa Bermasalah."
    )

    lokasi_prioritas = an.lokasi_prioritas(df_terfilter)
    hanya_bermasalah = st.checkbox(
        "Tampilkan hanya Desa Bermasalah",
        value=True,
    )
    
    data_tampil = (
        lokasi_prioritas[lokasi_prioritas["Desa Bermasalah"]]
        if hanya_bermasalah
        else lokasi_prioritas
    )

    st.dataframe(
        data_tampil.rename(
            columns={
                "Kondisi_Evaluasi_Terkini": "Kondisi Evaluasi Terkini",
                "Total_Periode_Tercatat": "Total Periode Tercatat",
                "Jumlah_Periode_Penggunaan_Bermasalah": "Jumlah Periode Penggunaan Bermasalah",
                "Desa Bermasalah": "Desa Bermasalah",
            }
        ),
        use_container_width=True,
        height=450,
    )


def render_tab_detail_data(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Detail Data Terfilter")
    st.dataframe(df_terfilter, use_container_width=True, height=500)

    data_csv = df_terfilter.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Unduh data terfilter (CSV)",
        data=data_csv,
        file_name="internet_desa_terfilter.csv",
        mime="text/csv",
    )

def main() -> None:
    konfigurasi_halaman()

    uploaded_file = ambil_file_upload()
    if uploaded_file is None:
        st.info("Silakan upload file Excel untuk memulai analisis.")
        return

    df = muat_dan_validasi_data(uploaded_file)
    if df is None:
        return

    df_terfilter, urutan_periode_label = render_filter_sidebar(df)
    if df_terfilter.empty:
        st.warning("Tidak ada data pada kombinasi filter yang dipilih.")
        return

    render_tombol_unduh_pdf(df_terfilter)

    tab_overview, tab_wilayah, tab_isp, tab_temporal, tab_spasial, tab_prioritas, tab_detail = st.tabs(
        [
            "Overview",
            "Analisis Wilayah",
            "Analisis ISP",
            "Analisis Temporal",
            "Analisis Spasial",
            "Lokasi Prioritas",
            "Detail Data",
        ]
    )

    with tab_overview:
        render_tab_overview(df_terfilter)
    with tab_wilayah:
        render_tab_perbandingan_grup(df_terfilter, "Kabupaten")
    with tab_isp:
        render_tab_perbandingan_grup(df_terfilter, "ISP")
    with tab_temporal:
        render_tab_temporal(df_terfilter, urutan_periode_label)
    with tab_spasial:
        render_tab_spasial(df_terfilter)
    with tab_prioritas:
        render_tab_lokasi_prioritas(df_terfilter)
    with tab_detail:
        render_tab_detail_data(df_terfilter)

if __name__ == "__main__":
    main()