"""
Modul analisis untuk Dashboard Internet Desa.

Semua fungsi di sini bersifat murni: menerima DataFrame yang sudah
dibersihkan (hasil `data_processing.clean_data`) dan mengembalikan
DataFrame/nilai hasil analisis. Tidak ada logika UI (Streamlit) di sini,
sehingga dapat diuji dan digunakan ulang secara independen.

Konsep unit analisis:
- RECORD  = satu baris (satu lokasi pada satu periode/bulan tertentu).
- LOKASI  = satu kombinasi Kabupaten + Kecamatan + Desa (`Location ID`),
  yang dapat muncul di banyak periode (baris) sekaligus.

Temuan penting dari eksplorasi dataset (lihat catatan pengembangan):
`Hasil Evaluasi`, `ISP`, `Produk`, `Status`, dan koordinat bersifat
STATIS per lokasi -- nilainya sama di semua periode untuk lokasi yang
sama. Satu-satunya kolom yang benar-benar berubah dari bulan ke bulan
adalah `Penggunaan`. Karena itu:
- Analisis deskriptif & komparatif berbasis `Hasil Evaluasi` dihitung
  per LOKASI (snapshot), bukan per baris, agar tidak menghitung lokasi
  yang sama 8 kali.
- Analisis temporal difokuskan pada tren `Penggunaan` per bulan,
  karena itulah dimensi yang benar-benar longitudinal di dataset ini.
"""

import numpy as np
import pandas as pd

from utils.data_processing import get_location_snapshot
from utils.constants import (
    URUTAN_HASIL_EVALUASI,
    WARNA_HASIL_EVALUASI,
    KATEGORI_DESA_BERMASALAH,
    PENGGUNAAN_BERMASALAH,
)

def urutkan_hasil_evaluasi(df, kolom="Hasil Evaluasi"):
    """
    Mengurutkan kategori Hasil Evaluasi menggunakan urutan bisnis
    yang telah ditentukan, bukan urutan alfabetis.
    """
    if df.empty or kolom not in df.columns:
        return df

    hasil = df.copy()

    hasil[kolom] = hasil[kolom].astype("string").str.upper().str.strip()

    hasil["_Urutan Evaluasi"] = pd.Categorical(
        hasil[kolom],
        categories=URUTAN_HASIL_EVALUASI,
        ordered=True,
    )

    return (
        hasil
        .sort_values("_Urutan Evaluasi")
        .drop(columns="_Urutan Evaluasi")
        .reset_index(drop=True)
    )

# ANALISIS DESKRIPTIF
def get_kpi_summary(df):
    """
    KPI ringkas dihitung dari data yang sudah difilter.

    Total Lokasi dihitung dari Location ID unik (bukan jumlah baris),
    agar satu lokasi yang muncul di beberapa periode tidak dihitung
    berulang kali.

    Total Record dihitung dari jumlah OBSERVASI BULANAN yang benar-benar
    tercatat (Penggunaan tidak kosong) -- bukan jumlah baris hasil melt
    mentah. Ini penting karena sumber data (Data Master) tidak memiliki
    panel lengkap: lokasi yang belum pernah aktif bisa saja tidak
    memiliki satu pun catatan Penggunaan bulanan, sehingga baris
    "placeholder" hasil melt untuk bulan yang memang tidak disurvei
    tidak dihitung sebagai record.
    """
    return {
        "total_record": int(df["Penggunaan"].notna().sum()),
        "total_lokasi": df["Location ID"].nunique(),
        "total_kabupaten": df["Kabupaten"].nunique(),
        "total_isp": df["ISP"].dropna().nunique(),
    }

def distribusi_hasil_evaluasi(df, per_lokasi=True):
    """
    Distribusi kategori Hasil Evaluasi.

    Per lokasi menggunakan satu snapshot per Location ID agar
    lokasi yang muncul di banyak bulan tidak dihitung berulang.
    """
    base = get_location_snapshot(df) if per_lokasi else df

    hasil = (
        base["Hasil Evaluasi"]
        .dropna()
        .astype("string")
        .str.upper()
        .str.strip()
        .value_counts()
        .rename_axis("Hasil Evaluasi")
        .reset_index(name="Jumlah")
    )

    hasil["Persentase"] = (
        hasil["Jumlah"] / hasil["Jumlah"].sum() * 100
    ).round(2)

    return urutkan_hasil_evaluasi(hasil)

def distribusi_penggunaan(df):
    """
    Distribusi kategori Penggunaan pada data yang difilter (per baris,
    karena Penggunaan memang bervariasi per periode -- lihat docstring
    modul).
    """
    base = df.dropna(subset=["Penggunaan"])

    hasil = (
        base["Penggunaan"]
        .value_counts(dropna=False)
        .rename_axis("Penggunaan")
        .reset_index(name="Jumlah")
    )
    hasil["Persentase"] = (
        hasil["Jumlah"] / hasil["Jumlah"].sum() * 100
    ).round(2)

    return hasil

# ANALISIS KOMPARATIF (Kabupaten & ISP)
def komposisi_evaluasi_per_grup(df, kolom_grup):
    """
    Komposisi persentase Hasil Evaluasi per grup.
    Satu lokasi hanya dihitung satu kali.
    """
    snap = get_location_snapshot(df)
    snap = snap.dropna(subset=[kolom_grup]).copy()

    snap["Hasil Evaluasi"] = (
        snap["Hasil Evaluasi"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    tabel = (
        snap.groupby(kolom_grup)["Hasil Evaluasi"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .rename("Persentase")
        .reset_index()
    )

    tabel = urutkan_hasil_evaluasi(tabel)

    jumlah_lokasi = (
        snap.groupby(kolom_grup)["Location ID"]
        .nunique()
        .rename("Jumlah Lokasi")
        .reset_index()
    )

    return tabel, jumlah_lokasi

def komposisi_evaluasi_per_kabupaten(df):
    """Komposisi (%) Hasil Evaluasi untuk setiap Kabupaten."""
    return komposisi_evaluasi_per_grup(df, "Kabupaten")

def komposisi_evaluasi_per_isp(df):
    """Komposisi (%) Hasil Evaluasi untuk setiap ISP."""
    return komposisi_evaluasi_per_grup(df, "ISP")

def proporsi_bermasalah_per_grup(df, kolom_grup):
    """
    Menghitung proporsi DESA BERMASALAH per Kabupaten/ISP.

    Desa Bermasalah HANYA:
    - TIDAK AKTIF
    - BELUM TERPASANG

    Setiap lokasi dihitung satu kali berdasarkan Location ID.
    """
    snap = get_location_snapshot(df).dropna(subset=[kolom_grup]).copy()

    snap["Hasil Evaluasi"] = (
        snap["Hasil Evaluasi"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    snap["Desa Bermasalah"] = snap["Hasil Evaluasi"].isin(
        KATEGORI_DESA_BERMASALAH
    )

    hasil = (
        snap.groupby(kolom_grup)
        .agg(
            Jumlah_Lokasi=("Location ID", "nunique"),
            Jumlah_Bermasalah=("Desa Bermasalah", "sum"),
        )
        .reset_index()
    )

    hasil["Persentase Bermasalah"] = (
        hasil["Jumlah_Bermasalah"]
        / hasil["Jumlah_Lokasi"]
        * 100
    ).round(2)

    return hasil.sort_values(
        "Persentase Bermasalah",
        ascending=False,
    ).reset_index(drop=True)

# ANALISIS TEMPORAL (berbasis Penggunaan, lihat docstring modul)
def jumlah_observasi_per_periode(df):
    """
    Jumlah lokasi yang benar-benar memiliki catatan Penggunaan pada
    setiap periode, diurutkan kronologis. Dipakai untuk transparansi:
    sumber data (Data Master) tidak memiliki panel lengkap, sehingga
    sebagian periode (terutama bulan-bulan terbaru yang belum lama
    disurvei) bisa saja hanya memiliki sedikit sekali observasi --
    statistik pada periode seperti itu tidak boleh dibaca sebagai
    representasi kondisi keseluruhan.
    """
    base = df.dropna(subset=["Penggunaan"])
    hasil = (
        base.groupby(["Periode Urutan", "Periode Label"])
        .size()
        .rename("Jumlah Lokasi Tercatat")
        .reset_index()
        .sort_values("Periode Urutan")
    )
    return hasil

def tren_penggunaan_bulanan(df):
    """
    Distribusi proporsi kategori Penggunaan pada setiap periode,
    diurutkan kronologis (Periode Urutan), bukan alfabetis.

    Mengembalikan tabel long-format: Periode Label, Periode Urutan,
    Penggunaan, Jumlah, Persentase -- siap dipakai untuk stacked
    area/bar chart di app.py.
    """
    base = df.dropna(subset=["Penggunaan"])

    tabel = (
        base.groupby(["Periode Urutan", "Periode Label"])["Penggunaan"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .rename("Persentase")
        .reset_index()
    )

    jumlah = (
        base.groupby(["Periode Urutan", "Penggunaan"])
        .size()
        .rename("Jumlah")
        .reset_index()
    )

    tabel = tabel.merge(jumlah, on=["Periode Urutan", "Penggunaan"], how="left")

    return tabel.sort_values(["Periode Urutan", "Penggunaan"])

def tren_evaluasi_terkini_per_periode_tersedia(df):
    """
    Menampilkan jumlah lokasi per kategori Hasil Evaluasi untuk setiap
    periode yang ADA di data ter-filter.

    Catatan penting: pada dataset ini Hasil Evaluasi bersifat statis
    per lokasi (tidak berubah antar bulan), sehingga hasil fungsi ini
    akan identik/flat di semua periode -- bukan bug, melainkan
    karakteristik data. Fungsi ini tetap disediakan agar transparan
    ketika ditampilkan (dengan catatan/insight yang menjelaskan hal
    ini), tetapi tren yang sesungguhnya bermakna ada pada
    `tren_penggunaan_bulanan`.
    """
    tabel = (
        df.groupby(["Periode Urutan", "Periode Label"])["Hasil Evaluasi"]
        .value_counts()
        .rename("Jumlah")
        .reset_index()
    )
    return tabel.sort_values(["Periode Urutan", "Hasil Evaluasi"])

# ANALISIS SPASIAL
def data_peta(df):
    """
    Satu baris per lokasi dengan koordinat valid, siap dipakai untuk
    peta. Lokasi dengan koordinat tidak valid (lihat
    `data_processing.clean_data`) dikeluarkan dari peta, TAPI tetap
    ada di data lain (tidak dihapus dari dataset).
    """
    snap = get_location_snapshot(df)
    return snap[snap["Koordinat Valid"] == True].copy()  # noqa: E712

# ANALISIS LOKASI PRIORITAS
def lokasi_prioritas(df):
    """
    Menghasilkan ranking lokasi prioritas monitoring.

    Desa Bermasalah HANYA:
    - TIDAK AKTIF
    - BELUM TERPASANG

    Kategori KURANG OPTIMAL dan TIDAK OPTIMAL tetap tersedia sebagai
    informasi evaluasi, tetapi tidak dihitung sebagai Desa Bermasalah.
    """
    kerja = df.copy()

    kerja["Hasil Evaluasi"] = (
        kerja["Hasil Evaluasi"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    kerja["Penggunaan"] = (
        kerja["Penggunaan"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    kerja["Penggunaan Bermasalah"] = kerja["Penggunaan"].isin(
        PENGGUNAAN_BERMASALAH
    )

    kerja["Penggunaan Tercatat"] = kerja["Penggunaan"].notna()

    agregat = (
        kerja.groupby("Location ID")
        .agg(
            Kabupaten=("Kabupaten", "first"),
            Kecamatan=("Kecamatan", "first"),
            Desa=("Desa", "first"),
            ISP=("ISP", "first"),
            Kondisi_Evaluasi_Terkini=("Hasil Evaluasi", "first"),
            Total_Periode_Tercatat=("Penggunaan Tercatat", "sum"),
            Jumlah_Periode_Penggunaan_Bermasalah=(
                "Penggunaan Bermasalah",
                "sum",
            ),
        )
        .reset_index()
    )

    penyebut = (
        agregat["Total_Periode_Tercatat"]
        .astype(float)
        .replace(0, np.nan)
    )

    agregat["Persentase Periode Bermasalah"] = (
        agregat["Jumlah_Periode_Penggunaan_Bermasalah"]
        / penyebut
        * 100
    ).round(2)

    # DEFINISI BARU DESA BERMASALAH
    agregat["Desa Bermasalah"] = agregat[
        "Kondisi_Evaluasi_Terkini"
    ].isin(KATEGORI_DESA_BERMASALAH)

    # Tetap pertahankan nama lama agar fitur/filter dashboard
    # tidak rusak.
    agregat["Evaluasi Bermasalah"] = agregat["Desa Bermasalah"]

    agregat = agregat.sort_values(
        by=[
            "Desa Bermasalah",
            "Persentase Periode Bermasalah",
        ],
        ascending=[False, False],
        na_position="last",
    )

    return agregat.reset_index(drop=True)