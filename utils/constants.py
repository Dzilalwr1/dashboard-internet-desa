# Urutan kategori Hasil Evaluasi
URUTAN_HASIL_EVALUASI = [
    "SANGAT OPTIMAL",
    "OPTIMAL",
    "KURANG OPTIMAL",
    "TIDAK OPTIMAL",
    "TIDAK AKTIF",
    "BELUM TERPASANG",
]

# Urutan prioritas lokasi: kondisi terburuk → terbaik
URUTAN_PRIORITAS = {
    "BELUM TERPASANG": 0,
    "TIDAK AKTIF": 1,
    "TIDAK OPTIMAL": 2,
    "KURANG OPTIMAL": 3,
    "OPTIMAL": 4,
    "SANGAT OPTIMAL": 5,
}

# Warna Hasil Evaluasi
WARNA_HASIL_EVALUASI = {
    "SANGAT OPTIMAL": "#006E00",   # hijau tua
    "OPTIMAL": "#00FF6E",          # hijau
    "KURANG OPTIMAL": "#FFD700",   # kuning
    "TIDAK OPTIMAL": "#FF8C00",    # oranye
    "TIDAK AKTIF": "#AD0000",      # merah tua
    "BELUM TERPASANG": "#808080",  # abu-abu
}

# Definisi RESMI untuk istilah "Desa Bermasalah" di dashboard.
KATEGORI_DESA_BERMASALAH = {
    "TIDAK AKTIF",
    "BELUM TERPASANG",
}

# Kategori Penggunaan Bermasalah
PENGGUNAAN_BERMASALAH = {
    "BELUM TERPASANG",
    "TIDAK TERDETEKSI",
    "TIDAK AKTIF",
}

# Warna Periode Penggunaan
WARNA_PENGGUNAAN = {
    "0GB": "#7B0000",
    "<= 1GB": "#FF3232",
    "<= 10GB": "#FF3232",
    "<= 50GB": "#F98425",
    "<= 100GB": "#F98425",
    "<= 150GB": "#C0C000",
    "<= 200GB": "#C0C000",
    "<= 500GB": "#2BB800",
    "<= 1000GB": "#006E1A",
    ">1000GB": "#003A7D",
    "BELUM TERPASANG": "#723B00",
    "TIDAK TERDETEKSI": "#383839",
}