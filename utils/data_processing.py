"""
Modul pemrosesan data untuk Dashboard Internet Desa.

Sumber data: sheet "Data Master" (format lebar -- satu baris per lokasi,
kolom terpisah untuk tiap bulan). Modul ini bertanggung jawab mengubah
format lebar tersebut menjadi format panjang (satu baris per
lokasi-per-periode) dengan skema kolom kanonik yang konsisten, supaya
`utils/analysis.py` dan `utils/insights.py` tidak perlu tahu format
mentah file Excel.

Keterbatasan sumber data yang perlu diketahui (didokumentasikan di sini
supaya tidak diam-diam ditebak/disembunyikan -- lihat TAHAP 10):

1. Sheet "Data Master" TIDAK memiliki kolom Tahun -- hanya nama bulan.
   Karena itu, Tahun harus disediakan oleh pengguna saat upload
   (lihat parameter `tahun` pada `clean_data`), bukan diasumsikan diam-diam
   oleh kode.
2. Tidak semua bulan terisi untuk semua lokasi (misalnya lokasi yang
   TIDAK AKTIF sejak awal bisa saja tidak punya catatan Penggunaan sama
   sekali). Baris tetap dipertahankan (bukan dihapus) supaya lokasi
   tersebut tetap terhitung di KPI Total Lokasi dan analisis spasial/
   komparatif, walau tidak funya observasi bulanan.
"""

import pandas as pd

# Baris header sebenarnya berada di baris kedua sheet Excel (baris
# pertama kosong/merged), sehingga `header=1` diperlukan saat membaca.
SHEET_NAME = "Data Master"
HEADER_ROW = 1

# Kolom mentah (raw) yang WAJIB ada pada sheet Data Master.
REQUIRED_RAW_COLUMNS = [
    "NAMA KABUPATEN",
    "NAMA KECAMATAN",
    "NAMA DESA",
    "KOORDINAT LINTANG",
    "KOORDINAT BUJUR",
    "ISP",
    "PRODUK",
    "STATUS",
    "HASIL EVALUASI",
]

# Pemetaan nama kolom mentah (raw, dari Excel) ke nama kolom kanonik
# yang dipakai di seluruh aplikasi (analysis.py, insights.py, app.py).
RENAME_MAP = {
    "NAMA KABUPATEN": "Kabupaten",
    "NAMA KECAMATAN": "Kecamatan",
    "NAMA DESA": "Desa",
    "TITIK PEMASANGAN": "Titik Pemasangan",
    "KOORDINAT LINTANG": "Koordinat Lintang",
    "KOORDINAT BUJUR": "Koordinat Bujur",
    "ISP": "ISP",
    "PRODUK": "Produk",
    "Bandwitdh / Kuota": "Paket Kontrak",
    "STATUS": "Status",
    "HASIL EVALUASI": "Hasil Evaluasi",
    "LISTRIK": "Sumber Listrik",
    "JUMLAH PENDUDUK (JIWA)": "Jumlah Penduduk",
    "SMA/SMK": "SMA SMK Terdekat",
    "BIAYA BULANAN": "Biaya Bulanan",
    "LINK": "Link Website Desa",
}

# Urutan bulan tidak alfabetis, mengikuti kalender. Nomor bulan dipakai
# untuk membangun kunci pengurutan kronologis (Tahun * 12 + Bulan No),
# sehingga Januari tahun berikutnya tetap terurut setelah Desember,
# bukan tersortir alfabetis. Kolom bulan yang benar-benar dipakai
# dideteksi secara DINAMIS dari kolom yang ada pada file yang diunggah
# (lihat `_deteksi_kolom_bulan`), bukan didaftar hardcode di sini,
# supaya dashboard tetap reusable ketika kolom bulan baru ditambahkan
# pada update data berikutnya.
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

# Rentang koordinat yang masuk akal untuk wilayah Kalimantan Timur /
# Kalimantan Utara. Dipakai hanya untuk MENANDAI kewajaran koordinat,
# bukan untuk mengubah/menghapus nilai asli.
LAT_MIN, LAT_MAX = -5.0, 5.0
LON_MIN, LON_MAX = 110.0, 120.0


def load_excel(uploaded_file, sheet_name=SHEET_NAME):
    """
    Membaca sheet Data Master dari file Excel.

    Header sebenarnya ada di baris kedua sheet (baris pertama kosong),
    sehingga dibaca dengan `header=HEADER_ROW`. Melempar error yang
    jelas jika sheet tidak ditemukan.
    """
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        raise ValueError(f"File Excel tidak dapat dibuka: {e}")

    if sheet_name not in xls.sheet_names:
        raise ValueError(
            f"Sheet '{sheet_name}' tidak ditemukan pada file ini. "
            f"Sheet yang tersedia: {', '.join(xls.sheet_names)}"
        )

    df = pd.read_excel(xls, sheet_name=sheet_name, header=HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]

    return df


def _deteksi_kolom_bulan(df):
    """
    Mendeteksi kolom mana saja pada file yang merupakan kolom bulan,
    berdasarkan kecocokan nama kolom dengan BULAN_NO_MAP -- bukan
    daftar tetap Januari..September, supaya kolom bulan baru pada
    file yang diperbarui otomatis ikut terbaca.
    """
    return [col for col in df.columns if col.strip().upper() in BULAN_NO_MAP]


def validate_columns(df):
    """
    Mengembalikan daftar kolom wajib yang belum ditemukan pada file.
    List kosong berarti struktur file valid.
    """
    kolom_hilang = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]

    if not _deteksi_kolom_bulan(df):
        kolom_hilang.append("(minimal satu kolom nama bulan, contoh: JANUARI)")

    return kolom_hilang


def _clean_coordinate_series(series):
    """
    Membersihkan artefak penulisan pada kolom koordinat, seperti spasi
    atau tanda koma yang tidak sengaja ikut ter-input di depan/belakang
    angka (contoh: ", 117.27..." atau "-0.246...,").

    Nilai yang setelah dibersihkan tetap tidak bisa diparse sebagai
    angka akan menjadi NaN -- TIDAK ditebak/diperbaiki isinya, karena
    itu berarti mengarang data.
    """
    cleaned = (
        series
        .astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(cleaned, errors="coerce")


def clean_data(df, tahun):
    """
    Membersihkan data Data Master dan mengubahnya dari format lebar
    (satu baris per lokasi, kolom terpisah per bulan) menjadi format
    panjang (satu baris per lokasi-per-periode) dengan skema kolom
    kanonik.

    Parameter
    ---------
    df : DataFrame mentah hasil `load_excel`.
    tahun : int
        Tahun yang berlaku untuk seluruh kolom bulan pada file ini.
        WAJIB disediakan pengguna karena sheet Data Master tidak
        memiliki kolom Tahun -- aplikasi tidak menebak tahun secara
        diam-diam.

    Tidak ada baris lokasi yang dihapus, termasuk lokasi tanpa satu
    pun catatan bulanan (misalnya lokasi yang belum pernah aktif).
    Baris kosong di akhir sheet (footer/separator) dibuang karena
    memang bukan data lokasi.
    """
    df = df.copy()

    # Buang baris kosong (biasanya footer/separator di akhir sheet),
    # dikenali dari kolom kunci Kabupaten yang kosong.
    df = df.dropna(subset=["NAMA KABUPATEN"])

    # Bersihkan whitespace pada seluruh kolom teks sebelum rename/melt.
    kolom_teks = df.select_dtypes(include=["object", "string"]).columns
    for col in kolom_teks:
        df[col] = df[col].astype("string").str.strip()

    kolom_bulan = _deteksi_kolom_bulan(df)
    if not kolom_bulan:
        raise ValueError(
            "Tidak ditemukan satu pun kolom bulan (contoh: JANUARI, FEBRUARI) "
            "pada file ini."
        )

    df = df.rename(columns=RENAME_MAP)

    kolom_statis = [
        canonical for raw, canonical in RENAME_MAP.items()
        if canonical in df.columns and raw not in kolom_bulan
    ]

    df_panjang = df.melt(
        id_vars=kolom_statis,
        value_vars=kolom_bulan,
        var_name="Bulan",
        value_name="Penggunaan",
    )

    df_panjang["Penggunaan"] = df_panjang["Penggunaan"].astype("string").str.strip()

    # Konversi koordinat, membersihkan artefak penulisan terlebih dahulu.
    df_panjang["Koordinat Lintang"] = _clean_coordinate_series(df_panjang["Koordinat Lintang"])
    df_panjang["Koordinat Bujur"] = _clean_coordinate_series(df_panjang["Koordinat Bujur"])

    df_panjang["Koordinat Valid"] = (
        df_panjang["Koordinat Lintang"].between(LAT_MIN, LAT_MAX)
        & df_panjang["Koordinat Bujur"].between(LON_MIN, LON_MAX)
    )

    # Identitas lokasi: Kabupaten + Kecamatan + Desa. Nama Desa saja
    # TIDAK unik (beberapa desa memakai nama yang sama di kabupaten
    # berbeda), sehingga kombinasi ini dipakai sebagai identitas lokasi
    # di seluruh aplikasi.
    df_panjang["Location ID"] = (
        df_panjang["Kabupaten"].astype("string").fillna("")
        + " | "
        + df_panjang["Kecamatan"].astype("string").fillna("")
        + " | "
        + df_panjang["Desa"].astype("string").fillna("")
    )

    # Periode kronologis: Bulan No + kunci urut Tahun*12 + Bulan No.
    bulan_upper = df_panjang["Bulan"].astype("string").str.upper().str.strip()
    df_panjang["Bulan No"] = bulan_upper.map(BULAN_NO_MAP)

    if df_panjang["Bulan No"].isna().any():
        nama_tidak_dikenali = sorted(
            bulan_upper[df_panjang["Bulan No"].isna()].dropna().unique().tolist()
        )
        raise ValueError(
            "Ditemukan nama bulan yang tidak dikenali: "
            f"{nama_tidak_dikenali}. Periksa penulisan nama bulan pada file Excel."
        )

    df_panjang["Tahun"] = tahun
    df_panjang["Bulan No"] = df_panjang["Bulan No"].astype(int)
    df_panjang["Periode Urutan"] = df_panjang["Tahun"] * 12 + df_panjang["Bulan No"]
    df_panjang["Periode Label"] = (
        df_panjang["Bulan"].astype("string").str.capitalize() + " " + df_panjang["Tahun"].astype(str)
    )

    return df_panjang


def get_location_snapshot(df):
    """
    Mengambil satu baris representatif per lokasi (Location ID).

    Kolom-kolom seperti ISP, Produk, Status, Hasil Evaluasi, dan
    koordinat bersifat statis per lokasi (satu nilai per lokasi pada
    sheet Data Master, hanya diduplikasi ke banyak baris akibat proses
    melt bulanan), sehingga aman diambil satu baris saja per lokasi
    untuk kebutuhan seperti KPI jumlah lokasi dan peta persebaran.

    Baris yang diambil adalah baris dengan `Periode Urutan` terbesar
    (periode terbaru) untuk lokasi tersebut.
    """
    df_sorted = df.sort_values("Periode Urutan")
    return df_sorted.drop_duplicates(subset="Location ID", keep="last")
