# 🌐 Dashboard Analisis Internet Desa

Dashboard berbasis web untuk melakukan **pengolahan, analisis, visualisasi, dan monitoring data Internet Desa** secara interaktif.

Proyek ini dikembangkan sebagai **proyek akhir Praktik Kerja Lapangan (PKL)** dengan konsep:

> **Input: File Excel → Proses & Analisis Data → Output: Dashboard Analisis Berbasis Web**

Dashboard dirancang agar data dapat diperbarui secara berkala. Pengguna cukup mengunggah file Excel terbaru dengan struktur data yang sesuai, kemudian sistem akan memproses dan memperbarui hasil analisis secara otomatis.

---

## 📌 Ringkasan Proyek

Data Internet Desa dapat mengalami pembaruan setiap bulan. Jika data hanya dianalisis secara manual, proses pembaruan grafik, ringkasan, dan identifikasi kondisi wilayah harus dilakukan berulang kali.

Proyek ini bertujuan membuat sebuah dashboard yang dapat:

1. menerima file Excel sebagai input;
2. memvalidasi struktur data;
3. melakukan preprocessing/cleaning;
4. menyediakan filter interaktif;
5. menghasilkan analisis statistik deskriptif;
6. membandingkan kondisi antarwilayah dan ISP;
7. menganalisis perubahan kondisi dari waktu ke waktu;
8. menampilkan persebaran lokasi secara spasial;
9. menghasilkan insight berdasarkan data terbaru.

---

## 🎯 Tujuan

### Tujuan Umum

Mengembangkan dashboard analisis berbasis web untuk membantu proses monitoring dan analisis data Internet Desa.

### Tujuan Khusus

* Mempermudah proses input data Internet Desa melalui file Excel.
* Mengurangi proses pengolahan data secara manual.
* Menyajikan informasi dalam bentuk visualisasi interaktif.
* Membantu melihat kondisi Internet Desa berdasarkan wilayah, ISP, penggunaan, dan periode.
* Membantu mengidentifikasi lokasi yang memerlukan perhatian.
* Memungkinkan dashboard digunakan kembali ketika dataset diperbarui.

---

## 📥 Input

Input utama aplikasi adalah file:

**Excel (`.xlsx` / `.xls`)**

Dataset utama dibaca dari sheet:

```text
data_dashboard
```

Struktur data yang digunakan mencakup:

| Kolom             | Keterangan                     |
| ----------------- | ------------------------------ |
| Tahun             | Tahun pengamatan               |
| Bulan             | Periode pengamatan             |
| Kabupaten         | Kabupaten lokasi layanan       |
| Kecamatan         | Kecamatan lokasi layanan       |
| Desa              | Desa lokasi layanan            |
| Koordinat Lintang | Latitude lokasi                |
| Koordinat Bujur   | Longitude lokasi               |
| ISP               | Penyedia layanan               |
| Produk            | Produk/layanan internet        |
| Status            | Status layanan                 |
| Penggunaan        | Kategori penggunaan internet   |
| Hasil Evaluasi    | Hasil evaluasi kondisi layanan |

> **Catatan:** Struktur kolom merupakan kontrak input aplikasi. Jika format dataset berubah, bagian validasi dan preprocessing perlu disesuaikan.

---

## 📊 Karakteristik Dataset

Dataset contoh yang digunakan dalam pengembangan prototype memiliki:

* **6.728 record**
* **841 lokasi layanan**
* **8 periode bulanan**
* Periode contoh: **Juni 2025 – Januari 2026**

Data bersifat **longitudinal**, karena satu lokasi dapat memiliki beberapa record untuk periode yang berbeda.

Contoh:

```text
1 Lokasi
   ├── Juni 2025
   ├── Juli 2025
   ├── Agustus 2025
   ├── September 2025
   ├── Oktober 2025
   ├── November 2025
   ├── Desember 2025
   └── Januari 2026
```

Identitas lokasi menggunakan:

```text
Kabupaten + Kecamatan + Desa
```

Hal ini dilakukan agar desa dengan nama yang sama di wilayah berbeda tidak dianggap sebagai lokasi yang sama.

---

# 🔄 Alur Sistem

```text
┌───────────────────┐
│     File Excel    │
│   Dataset terbaru │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│    Upload File    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Validasi Struktur │
│       Data        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Data Preprocessing│
│    & Cleaning     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│    Filter Data    │
│ Tahun/Bulan/      │
│ Kabupaten/ISP     │
└─────────┬─────────┘
          │
          ▼
┌────────────────────────────┐
│          ANALISIS          │
│                            │
│ • Deskriptif               │
│ • Komparatif               │
│ • Temporal                 │
│ • Spasial                  │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│        VISUALISASI         │
│                            │
│ • KPI                      │
│ • Grafik                   │
│ • Tren                     │
│ • Peta                     │
│ • Tabel                    │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│      INSIGHT OTOMATIS      │
└────────────────────────────┘
```

---

# 🔬 Metode Analisis

## 1. Analisis Deskriptif

Digunakan untuk memberikan gambaran umum mengenai dataset.

Contoh:

* jumlah record;
* jumlah lokasi;
* jumlah kabupaten;
* jumlah ISP;
* distribusi hasil evaluasi;
* distribusi penggunaan internet.

### Output

KPI dan grafik distribusi.

---

## 2. Analisis Komparatif

Digunakan untuk membandingkan kondisi antar kelompok.

### Berdasarkan Kabupaten

Mengetahui komposisi hasil evaluasi pada masing-masing kabupaten.

### Berdasarkan ISP

Mengetahui kondisi layanan berdasarkan ISP.

Perbandingan menggunakan **persentase** ketika membandingkan wilayah atau ISP agar kelompok dengan jumlah record lebih besar tidak otomatis terlihat lebih buruk hanya karena jumlah datanya lebih banyak.

---

## 3. Analisis Temporal

Data memiliki dimensi waktu sehingga kondisi dapat dianalisis dari bulan ke bulan.

Contoh:

```text
Juni 2025
     ↓
Juli 2025
     ↓
Agustus 2025
     ↓
...
     ↓
Januari 2026
```

Analisis digunakan untuk melihat:

* perubahan distribusi hasil evaluasi;
* tren kondisi layanan;
* peningkatan atau penurunan kondisi;
* periode yang membutuhkan perhatian.

---

## 4. Analisis Spasial

Karena dataset memiliki koordinat lintang dan bujur, data dapat divisualisasikan pada peta.

Analisis spasial membantu:

* melihat persebaran lokasi Internet Desa;
* menemukan lokasi berdasarkan hasil evaluasi;
* memfokuskan pencarian pada wilayah tertentu;
* melihat persebaran titik yang membutuhkan perhatian.

---

## 5. Analisis Lokasi Prioritas

Analisis lanjutan dapat digunakan untuk mengidentifikasi lokasi yang berulang kali mengalami kondisi bermasalah.

Kategori yang dapat menjadi perhatian:

* `TIDAK OPTIMAL`
* `KURANG OPTIMAL`
* `TIDAK TERDETEKSI`
* `TIDAK AKTIF`
* `BELUM TERPASANG`

Contoh:

```text
Lokasi A
Juni       → Tidak Optimal
Juli       → Tidak Optimal
Agustus    → Kurang Optimal
September  → Tidak Optimal
```

Lokasi seperti ini dapat masuk dalam daftar **lokasi prioritas monitoring**.

---

# 📈 Rancangan Dashboard

## 1. Data Input

Pengguna dapat mengunggah file Excel melalui sidebar.

```text
📂 Upload File Excel
```

Sistem kemudian membaca sheet `data_dashboard`.

---

## 2. Filter

Filter utama:

* Tahun
* Bulan
* Kabupaten
* ISP

Filter digunakan agar pengguna dapat melakukan eksplorasi data secara interaktif.

---

## 3. KPI

Informasi ringkas:

```text
Total Record
Total Lokasi
Total Kabupaten
Total ISP
```

---

## 4. Kondisi Internet Desa

Menampilkan distribusi:

* Sangat Optimal
* Optimal
* Kurang Optimal
* Tidak Optimal
* Tidak Terdeteksi
* Tidak Aktif
* Belum Terpasang

Visualisasi dapat berupa bar chart dan pie/donut chart.

---

## 5. Perbandingan Kabupaten

Menampilkan komposisi hasil evaluasi pada setiap kabupaten.

Tujuan:

> Mengetahui perbedaan kondisi Internet Desa antarwilayah.

---

## 6. Perbandingan ISP

Menampilkan komposisi hasil evaluasi berdasarkan ISP.

Tujuan:

> Melihat distribusi dan kondisi layanan pada masing-masing penyedia.

---

## 7. Tren Bulanan

Menampilkan perubahan kondisi Internet Desa dari periode ke periode.

Tujuan:

> Memantau perkembangan kondisi layanan dari waktu ke waktu.

---

## 8. Penggunaan Internet

Menampilkan distribusi kategori penggunaan.

Tujuan:

> Memberikan gambaran pola penggunaan layanan Internet Desa.

---

## 9. Peta Persebaran

Menampilkan lokasi berdasarkan koordinat.

Informasi ketika titik dipilih dapat mencakup:

* Desa
* Kecamatan
* Kabupaten
* ISP
* Produk
* Penggunaan
* Hasil Evaluasi

---

## 10. Insight Otomatis

Sistem dapat menghasilkan ringkasan berdasarkan hasil analisis.

Contoh:

> Pada periode terbaru, kategori evaluasi terbanyak adalah **KURANG OPTIMAL**.

atau:

> Kabupaten dengan proporsi **TIDAK OPTIMAL** tertinggi pada periode terbaru adalah **Kabupaten X**.

Insight harus dihitung dari dataset yang sedang digunakan, bukan ditulis secara manual.

---

# 🔁 Mekanisme Pembaruan Data

Salah satu tujuan utama proyek adalah membuat dashboard yang dapat digunakan ketika data diperbarui.

Contoh dataset awal:

```text
Internet Desa 2026.xlsx

Juni 2025
Juli 2025
...
Januari 2026
```

Dataset berikutnya:

```text
Internet Desa 2026 Update.xlsx

Juni 2025
Juli 2025
...
Januari 2026
Februari 2026
```

Pengguna cukup:

```text
Upload Excel terbaru
        ↓
Dashboard membaca data
        ↓
Analisis dihitung ulang
        ↓
Grafik diperbarui
        ↓
Insight diperbarui
```

Tidak diperlukan perubahan kode selama struktur data tetap sesuai.

---

# 🛠️ Teknologi

| Teknologi     | Fungsi                       |
| ------------- | ---------------------------- |
| Python        | Bahasa pemrograman           |
| Streamlit     | Framework dashboard web      |
| Pandas        | Pengolahan dan analisis data |
| OpenPyXL      | Membaca file Excel           |
| Plotly        | Visualisasi interaktif       |
| PyDeck/Folium | Visualisasi spasial/peta     |

---

# 📁 Struktur Project

```text
internet-desa-dashboard/
│
├── app.py
├── requirements.txt
├── README.md
├── PROJECT.md
│
├── utils/
│   ├── __init__.py
│   ├── data_processing.py
│   ├── analysis.py
│   └── insights.py
│
└── data/
    └── README.md
```

### `app.py`

File utama aplikasi Streamlit.

### `data_processing.py`

Menangani:

* pembacaan Excel;
* validasi;
* cleaning;
* standardisasi;
* pembentukan identitas lokasi;
* pembentukan periode.

### `analysis.py`

Berisi fungsi analisis.

### `insights.py`

Menghasilkan insight berdasarkan hasil analisis.

---

# 🚀 Cara Menjalankan

## 1. Masuk ke folder project

```bash
cd internet-desa-dashboard
```

## 2. Buat virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install dependency

```bash
pip install -r requirements.txt
```

## 4. Jalankan aplikasi

```bash
streamlit run app.py
```

Kemudian buka alamat yang diberikan oleh Streamlit pada browser.

---

# 📌 Prinsip Pengembangan

### 1. Data-driven

Hasil dashboard harus berasal dari data yang diunggah.

### 2. Reusable

Aplikasi tidak bergantung pada satu nama file tertentu.

### 3. Dynamic

Perubahan dataset menghasilkan perubahan analisis dan visualisasi.

### 4. Interactive

Pengguna dapat memilih filter dan mengeksplorasi data.

### 5. Modular

Pengolahan data, analisis, dan insight dipisahkan ke dalam modul.

### 6. Reproducible

Proses analisis dapat dijalankan kembali ketika dataset diperbarui.

---

# 📋 Status Pengembangan

| Komponen                  | Status          |
| ------------------------- | --------------- |
| Upload Excel              | ✅               |
| Validasi data             | ✅               |
| Data cleaning             | ✅               |
| Filter                    | ✅               |
| KPI                       | ✅               |
| Analisis evaluasi         | ✅               |
| Analisis kabupaten        | ✅               |
| Analisis ISP              | ✅               |
| Analisis temporal         | ✅               |
| Analisis penggunaan       | ✅               |
| Peta                      | ✅ Prototype     |
| Insight otomatis          | ✅ Prototype     |
| Analisis lokasi prioritas | 🔄 Pengembangan |
| Penyempurnaan UI/UX       | 🔄 Pengembangan |
| Testing dataset terbaru   | 🔄 Pengembangan |

---

# 🎓 Konteks PKL

Proyek ini dikembangkan sebagai bagian dari **Praktik Kerja Lapangan (PKL)** pada bidang yang berkaitan dengan pengelolaan dan analisis data Internet Desa.

Konsep proyek mengikuti arahan:

> **Input berupa file Excel dan output berupa dashboard analisis berbasis web.**

Fokus utama proyek bukan membangun sistem transaksi atau sistem informasi baru, tetapi **mengubah data yang tersedia menjadi informasi yang lebih mudah dipahami dan digunakan untuk monitoring serta pengambilan keputusan.**

---

# 🔮 Pengembangan Selanjutnya

Fitur yang dapat dikembangkan:

* analisis perubahan kondisi setiap lokasi;
* ranking lokasi prioritas;
* filter berdasarkan kecamatan/desa;
* perbandingan antarperiode;
* peta dengan filter hasil evaluasi;
* export hasil analisis;
* download data hasil filtering;
* sistem scoring kondisi;
* deployment ke server/web;
* autentikasi pengguna;
* integrasi database apabila diperlukan.

---

## 👤 Project

**Project:** Dashboard Analisis Internet Desa
**Jenis:** Proyek Akhir PKL
**Platform:** Web Dashboard
**Input:** Excel
**Output:** Dashboard Analisis Interaktif
**Status:** Prototype Development