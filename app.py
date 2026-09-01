"""
Dashboard Analisis Internet Desa.

Antarmuka Streamlit tipis di atas modul `utils`. File ini hanya
menangani layout halaman dan interaksi pengguna; seluruh logika
pembacaan data, pembersihan, perhitungan analisis, dan pembuatan
insight berada di `utils/data_processing.py`, `utils/analysis.py`,
dan `utils/insights.py`.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import analysis as an
from utils import insights as ins
from utils.data_processing import clean_data, load_excel, validate_columns

PAGE_TITLE = "Dashboard Analisis Internet Desa"
LABEL_TANPA_ISP = "(Belum ada ISP / Belum Terpasang)"
PETA_ZOOM_LEVEL = 6
PETA_TINGGI_PIKSEL = 600
TAHUN_DEFAULT = 2026


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

    tahun = st.sidebar.number_input(
        "Tahun data pada file ini",
        min_value=2000,
        max_value=2100,
        value=TAHUN_DEFAULT,
        step=1,
        help=(
            "Sheet Data Master hanya berisi nama bulan tanpa tahun, "
            "sehingga tahun perlu ditentukan secara manual saat upload."
        ),
    )

    return uploaded_file, int(tahun)


def muat_dan_validasi_data(uploaded_file, tahun: int) -> pd.DataFrame | None:
    """
    Memuat, memvalidasi struktur kolom, dan membersihkan data.

    Mengembalikan None jika terjadi kegagalan pada salah satu tahap;
    pesan error yang sesuai sudah ditampilkan ke pengguna sebelum
    fungsi ini mengembalikan None.
    """
    try:
        df_mentah = load_excel(uploaded_file)
    except Exception as error:
        st.error(f"Gagal membaca file Excel: {error}")
        return None

    kolom_hilang = validate_columns(df_mentah)
    if kolom_hilang:
        st.error("Format file tidak sesuai kontrak data aplikasi.")
        st.write("Kolom yang belum ditemukan:")
        st.write(kolom_hilang)
        return None

    try:
        df_bersih = clean_data(df_mentah, tahun=tahun)
    except ValueError as error:
        st.error(f"Data tidak dapat diproses: {error}")
        return None

    st.sidebar.success(f"Data berhasil dimuat: {df_bersih['Location ID'].nunique():,} lokasi")
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


def buat_bar_chart_persentase(data: pd.DataFrame, x: str, y: str, warna: str | None = None):
    """
    Bar chart dengan label persentase di atas setiap batang.
    Dipakai berulang di beberapa tab sehingga dipusatkan di sini
    untuk menghindari duplikasi konfigurasi Plotly.
    """
    fig = px.bar(data, x=x, y=y, text=y, color=warna)
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    return fig


def render_tab_overview(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Ringkasan Umum")

    kpi = an.get_kpi_summary(df_terfilter)
    kolom = st.columns(4)
    kolom[0].metric("Total Record", f"{kpi['total_record']:,}")
    kolom[1].metric("Total Lokasi", f"{kpi['total_lokasi']:,}")
    kolom[2].metric("Total Kabupaten", f"{kpi['total_kabupaten']:,}")
    kolom[3].metric("Total ISP", f"{kpi['total_isp']:,}")

    st.caption(
        "Total Lokasi dihitung dari kombinasi unik Kabupaten, Kecamatan, dan Desa, "
        "bukan jumlah baris -- satu lokasi dapat muncul di beberapa periode."
    )

    kolom_kiri, kolom_kanan = st.columns(2)

    with kolom_kiri:
        st.markdown("**Distribusi Hasil Evaluasi (per lokasi)**")
        dist_evaluasi = an.distribusi_hasil_evaluasi(df_terfilter)
        st.plotly_chart(
            buat_bar_chart_persentase(
                dist_evaluasi, x="Hasil Evaluasi", y="Persentase", warna="Hasil Evaluasi"
            ),
            use_container_width=True,
        )

    with kolom_kanan:
        st.markdown("**Distribusi Penggunaan (seluruh baris terfilter)**")
        dist_penggunaan = an.distribusi_penggunaan(df_terfilter)
        fig = buat_bar_chart_persentase(dist_penggunaan, x="Penggunaan", y="Persentase")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Insight Utama**")
    daftar_insight = ins.generate_all_insights(df_terfilter)
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
    )
    fig_komposisi.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(fig_komposisi, use_container_width=True)

    st.markdown(f"**Proporsi Lokasi Perlu Perhatian per {kolom_grup}**")
    proporsi_bermasalah = an.proporsi_bermasalah_per_grup(df_terfilter, kolom_grup)
    fig_proporsi = buat_bar_chart_persentase(
        proporsi_bermasalah, x=kolom_grup, y="Persentase Bermasalah"
    )
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
        category_orders={"Periode Label": urutan_periode_label},
    )
    st.plotly_chart(fig_observasi, use_container_width=True)

    tren_penggunaan = an.tren_penggunaan_bulanan(df_terfilter)
    fig_tren = px.area(
        tren_penggunaan,
        x="Periode Label",
        y="Persentase",
        color="Penggunaan",
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
            category_orders={"Periode Label": urutan_periode_label},
        )
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

    fig_peta = px.scatter_mapbox(
        data_peta,
        lat="Koordinat Lintang",
        lon="Koordinat Bujur",
        color="Hasil Evaluasi",
        hover_name="Desa",
        hover_data={
            "Kecamatan": True,
            "Kabupaten": True,
            "ISP": True,
            "Produk": True,
            "Penggunaan": True,
            "Hasil Evaluasi": True,
            "Koordinat Lintang": False,
            "Koordinat Bujur": False,
        },
        zoom=PETA_ZOOM_LEVEL,
        height=PETA_TINGGI_PIKSEL,
    )
    fig_peta.update_layout(
        mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    st.plotly_chart(fig_peta, use_container_width=True)


def render_tab_lokasi_prioritas(df_terfilter: pd.DataFrame) -> None:
    st.subheader("Lokasi Prioritas Monitoring")
    st.caption(
        "Metrik: kondisi evaluasi terkini, jumlah dan persentase periode dengan "
        "kategori Penggunaan bermasalah (Belum Terpasang/Tidak Terdeteksi/Tidak Aktif). "
        "Diurutkan: lokasi dengan evaluasi bermasalah dan persentase periode "
        "bermasalah tertinggi ditampilkan lebih dulu."
    )

    lokasi_prioritas = an.lokasi_prioritas(df_terfilter)
    hanya_bermasalah = st.checkbox(
        "Tampilkan hanya lokasi dengan Evaluasi Bermasalah", value=True
    )
    data_tampil = (
        lokasi_prioritas[lokasi_prioritas["Evaluasi Bermasalah"]]
        if hanya_bermasalah
        else lokasi_prioritas
    )

    st.dataframe(
        data_tampil.rename(
            columns={
                "Kondisi_Evaluasi_Terkini": "Kondisi Evaluasi Terkini",
                "Total_Periode_Tercatat": "Total Periode Tercatat",
                "Jumlah_Periode_Penggunaan_Bermasalah": "Jumlah Periode Penggunaan Bermasalah",
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

    uploaded_file, tahun = ambil_file_upload()
    if uploaded_file is None:
        st.info("Silakan upload file Excel untuk memulai analisis.")
        return

    df = muat_dan_validasi_data(uploaded_file, tahun)
    if df is None:
        return

    df_terfilter, urutan_periode_label = render_filter_sidebar(df)
    if df_terfilter.empty:
        st.warning("Tidak ada data pada kombinasi filter yang dipilih.")
        return

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
