# Dashboard Analisis Internet Desa

Dashboard berbasis web untuk **pengolahan, analisis, visualisasi, dan monitoring data Internet Desa** secara interaktif.

Dikembangkan sebagai proyek akhir Praktik Kerja Lapangan (PKL) dengan konsep:

> **Input: File Excel → Proses & Analisis Data → Output: Dashboard Analisis Berbasis Web**

---

## Ringkasan Proyek

Data Internet Desa diperbarui setiap bulan. Jika dianalisis secara manual, proses pembaruan grafik, ringkasan, dan identifikasi kondisi wilayah harus dilakukan berulang kali. Dashboard ini memungkinkan:

1. Menerima file Excel sebagai input
2. Memvalidasi struktur data
3. Melakukan preprocessing & cleaning
4. Menyediakan filter interaktif
5. Menghasilkan analisis statistik deskriptif
6. Membandingkan kondisi antarwilayah dan ISP
7. Menganalisis perubahan kondisi dari waktu ke waktu
8. Menampilkan persebaran lokasi secara spasial
9. Menghasilkan insight berdasarkan data terbaru

---

## Fitur Utama

| Fitur | Deskripsi |
| --- | --- |
| Upload Excel | Pengguna cukup upload file Excel terbaru untuk memperbarui data |
| Filter Interaktif | Filter berdasarkan periode, kabupaten, dan ISP |
| KPI Dashboard | Total record, lokasi, kabupaten, ISP, desa bermasalah |
| Analisis Wilayah | Perbandingan komposisi evaluasi antar kabupaten |
| Analisis ISP | Perbandingan kondisi layanan antar penyedia internet |
| Analisis Temporal | Tren penggunaan dan evaluasi dari bulan ke bulan |
| Peta Spasial | Persebaran lokasi Internet Desa berdasarkan koordinat |
| Lokasi Prioritas | Identifikasi desa dengan kondisi bermasalah |
| Insight Otomatis | Ringkasan analisis yang dihitung langsung dari data |
| Ekspor PDF | Unduh laporan analisis dalam format PDF |

---

## Struktur Dataset

Input utama adalah file Excel dengan sheet `data_dashboard` yang memiliki kolom berikut:

| Kolom | Keterangan |
| --- | --- |
| Tahun | Tahun pengamatan |
| Bulan | Periode pengamatan |
| Kabupaten | Kabupaten lokasi layanan |
| Kecamatan | Kecamatan lokasi layanan |
| Desa | Desa lokasi layanan |
| Koordinat Lintang | Latitude lokasi |
| Koordinat Bujur | Longitude lokasi |
| ISP | Penyedia layanan |
| Produk | Produk/layanan internet |
| Status | Status layanan |
| Penggunaan | Kategori penggunaan internet |
| Hasil Evaluasi | Hasil evaluasi kondisi layanan |

Dataset bersifat **longitudinal** -- satu lokasi dapat memiliki beberapa record untuk periode yang berbeda. Identitas lokasi dihitung dari kombinasi `Kabupaten + Kecamatan + Desa`.

### Kategori Hasil Evaluasi

- SANGAT OPTIMAL
- OPTIMAL
- KURANG OPTIMAL
- TIDAK OPTIMAL
- TIDAK TERDETEKSI
- TIDAK AKTIF
- BELUM TERPASANG

---

## Alur Sistem

```
File Excel → Upload → Validasi Struktur → Preprocessing & Cleaning → Filter Data
    → Analisis (Deskriptif, Komparatif, Temporal, Spasial)
    → Visualisasi (KPI, Grafik, Tren, Peta, Tabel)
    → Insight Otomatis
```

---

## Teknologi

| Teknologi | Fungsi |
| --- | --- |
| Python | Bahasa pemrograman |
| Streamlit | Framework dashboard web |
| Pandas | Pengolahan dan analisis data |
| OpenPyXL | Membaca file Excel |
| Plotly | Visualisasi interaktif |
| Matplotlib | Utilitas warna dan colormap |
| ReportLab | Ekspor laporan PDF |

---

## Struktur Proyek

```
dashboard-internet-desa/
├── app.py                    # Aplikasi utama Streamlit
├── requirements.txt          # Daftar dependency
├── data/
│   ├── Internet-Desa-2026.xlsx
│   └── metadata.json
└── utils/
    ├── __init__.py
    ├── constants.py          # Konstanta warna dan urutan kategori
    ├── data_processing.py    # Load, validasi, cleaning data
    ├── analysis.py           # Fungsi-fungsi analisis
    ├── insights.py           # Generasi insight otomatis
    └── pdf_export.py         # Ekspor laporan PDF
```

---

## Cara Menjalankan

### 1. Masuk ke folder project

```bash
cd dashboard-internet-desa
```

### 2. Buat virtual environment

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

### 3. Install dependency

```bash
pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```bash
streamlit run app.py
```

Buka alamat yang diberikan oleh Streamlit pada browser.

---

## Prinsip Pengembangan

- **Data-driven** -- Hasil dashboard harus berasal dari data yang diunggah
- **Reusable** -- Aplikasi tidak bergantung pada satu nama file tertentu
- **Dynamic** -- Perubahan dataset menghasilkan perubahan analisis dan visualisasi
- **Interactive** -- Pengguna dapat memilih filter dan mengeksplorasi data
- **Modular** -- Pengolahan data, analisis, dan insight dipisahkan ke dalam modul

---
