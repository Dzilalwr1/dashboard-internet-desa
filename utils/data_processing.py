"""Fungsi pemrosesan dan pembersihan data Internet Desa."""

import re

import pandas as pd

SHEET_NAME = "Data Master"
HEADER_ROW = 1

REQUIRED_RAW_COLUMNS = [
    "NAMA KABUPATEN",
    "NAMA KECAMATAN",
    "NAMA DESA",
    "KOORDINAT BUJUR",
    "KOORDINAT LINTANG",
    "ISP",
    "PRODUK",
    "STATUS",
    "HASIL EVALUASI",
]

RENAME_MAP = {
    "NAMA KABUPATEN": "Kabupaten",
    "NAMA KECAMATAN": "Kecamatan",
    "NAMA DESA": "Desa",
    "KOORDINAT BUJUR": "Longitude",
    "KOORDINAT LINTANG": "Latitude",
    "ISP": "ISP",
    "PRODUK": "Produk",
    "STATUS": "Status",
    "HASIL EVALUASI": "Hasil Evaluasi",
}

BULAN_NO_MAP = {
    "JANUARI": 1,
    "FEBRUARI": 2,
    "MARET": 3,
    "APRIL": 4,
    "MEI": 5,
    "JUNI": 6,
    "JULI": 7,
    "AGUSTUS": 8,
    "SEPTEMBER": 9,
    "OKTOBER": 10,
    "NOVEMBER": 11,
    "DESEMBER": 12,
}

NORMALISASI_PENGGUNAAN = {
    "0 GB": "0GB",
    "0GB": "0GB",
    "<=1GB": "<= 1GB",
    "<= 1 GB": "<= 1GB",
    "<=10GB": "<= 10GB",
    "<= 10 GB": "<= 10GB",
    "<=50GB": "<= 50GB",
    "<= 50 GB": "<= 50GB",
    "<=100GB": "<= 100GB",
    "<= 100 GB": "<= 100GB",
    "<=150GB": "<= 150GB",
    "<= 150 GB": "<= 150GB",
    "<=200GB": "<= 200GB",
    "<= 200 GB": "<= 200GB",
    "<=500GB": "<= 500GB",
    "<= 500 GB": "<= 500GB",
    "<=1000GB": "<= 1000GB",
    "<= 1000 GB": "<= 1000GB",
    ">1000GB": ">1000GB",
    "> 1000GB": ">1000GB",
    "> 1000 GB": ">1000GB",
    "BELUM TERPASANG": "BELUM TERPASANG",
    "TIDAK TERDETEKSI": "TIDAK TERDETEKSI",
}

def load_excel(file):
    """Membaca sheet Data Master dari file Excel."""
    return pd.read_excel(
        file,
        sheet_name=SHEET_NAME,
        header=HEADER_ROW,
    )

def validate_columns(df):
    """Memastikan kolom wajib tersedia."""
    missing = [column for column in REQUIRED_RAW_COLUMNS if column not in df.columns]

    if missing:
        raise ValueError(
            "Kolom wajib tidak ditemukan: "
            + ", ".join(missing)
        )

    return True

def _clean_coordinate_series(series):
    """Membersihkan kolom koordinat dan mengubahnya menjadi numerik."""
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )

    return pd.to_numeric(cleaned, errors="coerce")

def _normalize_usage(value):
    """Menormalkan kategori penggunaan internet."""
    if pd.isna(value):
        return pd.NA

    value = str(value).strip().upper()
    value = re.sub(r"\s+", " ", value)

    if value in NORMALISASI_PENGGUNAAN:
        return NORMALISASI_PENGGUNAAN[value]

    value_no_space = value.replace(" ", "")

    if value_no_space in NORMALISASI_PENGGUNAAN:
        return NORMALISASI_PENGGUNAAN[value_no_space]

    return value

def clean_data(df, tahun):
    """Membersihkan data dan mengubah format bulanan menjadi long format."""
    data = df.copy()

    data = data.dropna(subset=["NAMA KABUPATEN"])

    for column in data.select_dtypes(include=["object", "string"]).columns:
        data[column] = data[column].astype("string").str.strip()

    bulan_columns = [
        column
        for column in data.columns
        if str(column).strip().upper() in BULAN_NO_MAP
    ]

    if not bulan_columns:
        raise ValueError("Kolom bulan tidak ditemukan pada Data Master.")

    data = data.rename(columns=RENAME_MAP)

    bulan_columns = [
        column
        for column in data.columns
        if str(column).strip().upper() in BULAN_NO_MAP
    ]

    id_columns = [
        column
        for column in data.columns
        if column not in bulan_columns
    ]

    data = data.melt(
        id_vars=id_columns,
        value_vars=bulan_columns,
        var_name="Periode",
        value_name="Penggunaan",
    )

    data["Penggunaan"] = data["Penggunaan"].apply(_normalize_usage)

    data["Longitude"] = _clean_coordinate_series(data["Longitude"])
    data["Latitude"] = _clean_coordinate_series(data["Latitude"])

    data["Koordinat Valid"] = (
        data["Latitude"].between(-90, 90, inclusive="both")
        & data["Longitude"].between(-180, 180, inclusive="both")
    )

    data["Location ID"] = (
        data["Kabupaten"].fillna("").astype(str).str.strip()
        + " | "
        + data["Kecamatan"].fillna("").astype(str).str.strip()
        + " | "
        + data["Desa"].fillna("").astype(str).str.strip()
    )

    data["Periode"] = (
        data["Periode"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    data["Bulan"] = data["Periode"].map(BULAN_NO_MAP)
    data["Tahun"] = tahun

    data["Periode Urutan"] = (
        data["Tahun"] * 100
        + data["Bulan"].fillna(0)
    )

    data["Periode Label"] = (
        data["Periode"].str.title()
        + " "
        + data["Tahun"].astype(str)
    )

    return data

def get_location_snapshot(df):
    """Mengambil kondisi terbaru untuk setiap lokasi."""
    if df.empty:
        return df.copy()

    data = df.sort_values(
        ["Location ID", "Periode Urutan"]
    ).copy()

    return data.drop_duplicates(
        subset=["Location ID"],
        keep="last",
    ).reset_index(drop=True)