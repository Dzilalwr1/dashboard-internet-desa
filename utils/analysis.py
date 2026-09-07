"""Fungsi analisis data untuk Dashboard Internet Desa."""

import numpy as np
import pandas as pd

from utils.constants import (
    KATEGORI_DESA_BERMASALAH,
    PENGGUNAAN_BERMASALAH,
    URUTAN_HASIL_EVALUASI,
    URUTAN_PENGGUNAAN,
    URUTAN_PRIORITAS,
)
from utils.data_processing import get_location_snapshot

def urutkan_hasil_evaluasi(df, kolom="Hasil Evaluasi"):
    """Mengurutkan kategori hasil evaluasi sesuai urutan bisnis."""
    if df.empty or kolom not in df.columns:
        return df

    hasil = df.copy()

    hasil[kolom] = (
        hasil[kolom]
        .astype("string")
        .str.upper()
        .str.strip()
    )

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
    """Menghitung KPI utama dari data yang sudah difilter."""
    return {
        "total_record": int(df["Penggunaan"].notna().sum()),
        "total_lokasi": df["Location ID"].nunique(),
        "total_kabupaten": df["Kabupaten"].nunique(),
        "total_isp": df["ISP"].dropna().nunique(),
    }

def distribusi_hasil_evaluasi(df, per_lokasi=True):
    """Menghitung distribusi kategori hasil evaluasi."""
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
        hasil["Jumlah"]
        / hasil["Jumlah"].sum()
        * 100
    ).round(2)

    return urutkan_hasil_evaluasi(hasil)

def urutkan_penggunaan(df, kolom="Penggunaan"):
    """Mengurutkan kategori penggunaan sesuai urutan bisnis."""
    hasil = df.copy()

    hasil["_Urutan"] = hasil[kolom].map(
        {value: i for i, value in enumerate(URUTAN_PENGGUNAAN)}
    )

    hasil = hasil.sort_values(
        "_Urutan",
        key=lambda series: [
            value if value is not None else float("inf")
            for value in series
        ],
        na_position="last",
    )

    return (
        hasil
        .drop(columns="_Urutan")
        .reset_index(drop=True)
    )

def distribusi_penggunaan(df):
    """Menghitung distribusi kategori penggunaan internet."""
    base = df.dropna(subset=["Penggunaan"])

    hasil = (
        base["Penggunaan"]
        .value_counts(dropna=False)
        .rename_axis("Penggunaan")
        .reset_index(name="Jumlah")
    )

    hasil["Persentase"] = (
        hasil["Jumlah"]
        / hasil["Jumlah"].sum()
        * 100
    ).round(2)

    return urutkan_penggunaan(hasil)

# ANALISIS KOMPARATIF
def komposisi_evaluasi_per_grup(df, kolom_grup):
    """Menghitung komposisi hasil evaluasi berdasarkan grup."""
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
    """Menghitung komposisi hasil evaluasi per Kabupaten."""
    return komposisi_evaluasi_per_grup(df, "Kabupaten")

def komposisi_evaluasi_per_isp(df):
    """Menghitung komposisi hasil evaluasi per ISP."""
    return komposisi_evaluasi_per_grup(df, "ISP")

def proporsi_bermasalah_per_grup(df, kolom_grup):
    """Menghitung proporsi Desa Bermasalah per grup."""
    snap = get_location_snapshot(df)
    snap = snap.dropna(subset=[kolom_grup]).copy()

    snap["Hasil Evaluasi"] = (
        snap["Hasil Evaluasi"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    # Desa Bermasalah hanya TIDAK AKTIF dan BELUM TERPASANG.
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

    return (
        hasil
        .sort_values(
            "Persentase Bermasalah",
            ascending=False,
        )
        .reset_index(drop=True)
    )

# ANALISIS TEMPORAL
def jumlah_observasi_per_periode(df):
    """Menghitung jumlah observasi penggunaan pada setiap periode."""
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
    """Menghitung distribusi penggunaan internet per periode."""
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

    tabel = tabel.merge(
        jumlah,
        on=["Periode Urutan", "Penggunaan"],
        how="left",
    )

    return tabel.sort_values(
        ["Periode Urutan", "Penggunaan"]
    )


def tren_evaluasi_terkini_per_periode_tersedia(df):
    """Menghitung jumlah kategori evaluasi pada setiap periode."""
    tabel = (
        df.groupby(["Periode Urutan", "Periode Label"])["Hasil Evaluasi"]
        .value_counts()
        .rename("Jumlah")
        .reset_index()
    )

    return tabel.sort_values(
        ["Periode Urutan", "Hasil Evaluasi"]
    )


# ANALISIS SPASIAL

def data_peta(df):
    """Mengambil snapshot lokasi dengan koordinat yang valid."""
    snap = get_location_snapshot(df)

    return snap[snap["Koordinat Valid"]].copy()


# ANALISIS LOKASI PRIORITAS

def lokasi_prioritas(df):
    """Membuat ranking lokasi berdasarkan kondisi dan penggunaan."""
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

    # Evaluasi adalah atribut lokasi; ambil dari snapshot periode terakhir
    # agar "Kondisi Evaluasi Terkini" tidak bergantung pada urutan baris.
    snapshot = get_location_snapshot(kerja)
    evaluasi_terkini = snapshot.set_index("Location ID")["Hasil Evaluasi"]

    agregat = (
        kerja.groupby("Location ID")
        .agg(
            Kabupaten=("Kabupaten", "first"),
            Kecamatan=("Kecamatan", "first"),
            Desa=("Desa", "first"),
            ISP=("ISP", "first"),
            Total_Periode_Tercatat=(
                "Penggunaan Tercatat",
                "sum",
            ),
            Jumlah_Periode_Penggunaan_Bermasalah=(
                "Penggunaan Bermasalah",
                "sum",
            ),
        )
        .reset_index()
    )
    agregat["Kondisi_Evaluasi_Terkini"] = (
        agregat["Location ID"].map(evaluasi_terkini)
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

    # Desa Bermasalah hanya berdasarkan hasil evaluasi.
    agregat["Desa Bermasalah"] = agregat[
        "Kondisi_Evaluasi_Terkini"
    ].isin(KATEGORI_DESA_BERMASALAH)

    agregat["Evaluasi Bermasalah"] = agregat["Desa Bermasalah"]

    agregat["_Urutan Prioritas"] = (
        agregat["Kondisi_Evaluasi_Terkini"]
        .map(URUTAN_PRIORITAS)
    )

    agregat = agregat.sort_values(
        by=[
            "_Urutan Prioritas",
            "Persentase Periode Bermasalah",
        ],
        ascending=[True, False],
        na_position="last",
    )

    return (
        agregat
        .drop(columns="_Urutan Prioritas")
        .reset_index(drop=True)
    )