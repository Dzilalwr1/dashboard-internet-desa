"""
Modul insight untuk Dashboard Internet Desa.

Aturan wajib: SEMUA kalimat insight di sini dihasilkan dari hasil
perhitungan `utils/analysis.py` -- tidak ada nama kabupaten, ISP, angka,
atau kesimpulan yang ditulis manual (hardcoded). Ketika dataset yang
diunggah berubah, kalimat insight otomatis mengikuti hasil hitung yang
baru.

Pola setiap fungsi: data -> panggil fungsi analysis -> ambil nilai
ekstrem/relevan -> susun kalimat.
"""

from utils import analysis as an


def insight_kondisi_terbanyak(df):
    """
    Contoh pola: data -> groupby Hasil Evaluasi -> hitung proporsi ->
    ambil kategori dengan proporsi tertinggi -> generate kalimat.
    """
    dist = an.distribusi_hasil_evaluasi(df)
    if dist.empty:
        return None

    baris_teratas = dist.iloc[0]
    return (
        f"Dari seluruh lokasi yang tercatat, kondisi **{baris_teratas['Hasil Evaluasi']}** "
        f"adalah yang paling banyak ditemukan, mencakup {baris_teratas['Persentase']:.1f}% "
        f"dari total {int(dist['Jumlah'].sum()):,} lokasi."
    )


def insight_kabupaten_bermasalah_tertinggi(df):
    """
    Pola: data -> groupby Kabupaten -> hitung proporsi lokasi
    bermasalah -> ranking -> ambil yang tertinggi -> generate kalimat.
    """
    tabel = an.proporsi_bermasalah_per_grup(df, "Kabupaten")
    if tabel.empty:
        return None

    teratas = tabel.iloc[0]
    return (
        f"Kabupaten dengan proporsi lokasi berkategori perlu perhatian "
        f"(Tidak Optimal/Kurang Optimal/Tidak Terdeteksi/Tidak Aktif/Belum Terpasang) "
        f"tertinggi adalah **{teratas['Kabupaten']}**, yaitu {teratas['Persentase Bermasalah']:.1f}% "
        f"dari {int(teratas['Jumlah_Lokasi'])} lokasi di kabupaten tersebut."
    )


def insight_isp_bermasalah_tertinggi(df):
    """Pola sama seperti di atas, dikelompokkan berdasarkan ISP."""
    tabel = an.proporsi_bermasalah_per_grup(df, "ISP")
    if tabel.empty:
        return None

    teratas = tabel.iloc[0]
    return (
        f"ISP dengan proporsi lokasi perlu perhatian tertinggi adalah **{teratas['ISP']}** "
        f"({teratas['Persentase Bermasalah']:.1f}% dari {int(teratas['Jumlah_Lokasi'])} lokasi yang dilayani)."
    )


def insight_periode_terbaru_penggunaan(df):
    """
    Pola: data -> ambil periode kronologis terbaru YANG DATANYA CUKUP
    memadai untuk dibaca sebagai gambaran umum -> hitung distribusi
    Penggunaan pada periode itu -> ambil kategori tertinggi -> generate
    kalimat.

    Sumber data tidak memiliki panel lengkap: sebagian periode (biasanya
    bulan yang paling baru) bisa saja baru tersurvei di sebagian kecil
    lokasi. Periode dengan jumlah lokasi tercatat kurang dari
    `AMBANG_MINIMAL_PROPORSI_LOKASI` dari total lokasi dilewati agar
    insight tidak menyimpulkan sesuatu dari sampel yang terlalu kecil.
    Jumlah lokasi yang mendasari insight selalu disebutkan secara
    eksplisit di kalimatnya, supaya pembaca bisa menilai sendiri
    keterwakilannya.
    """
    AMBANG_MINIMAL_PROPORSI_LOKASI = 0.3

    observasi_per_periode = an.jumlah_observasi_per_periode(df)
    if observasi_per_periode.empty:
        return None

    total_lokasi = df["Location ID"].nunique()
    ambang_jumlah = total_lokasi * AMBANG_MINIMAL_PROPORSI_LOKASI

    kandidat = observasi_per_periode[
        observasi_per_periode["Jumlah Lokasi Tercatat"] >= ambang_jumlah
    ]
    if kandidat.empty:
        # Tidak ada periode dengan data cukup representatif -- lebih
        # baik tidak menyimpulkan apa pun daripada menyesatkan.
        return None

    periode_terpilih = kandidat["Periode Urutan"].max()

    tren = an.tren_penggunaan_bulanan(df)
    data_periode = tren[tren["Periode Urutan"] == periode_terpilih]
    label_periode = data_periode["Periode Label"].iloc[0]
    jumlah_lokasi_periode = int(
        observasi_per_periode.loc[
            observasi_per_periode["Periode Urutan"] == periode_terpilih,
            "Jumlah Lokasi Tercatat",
        ].iloc[0]
    )
    teratas = data_periode.sort_values("Persentase", ascending=False).iloc[0]

    return (
        f"Pada periode {label_periode} (berdasarkan {jumlah_lokasi_periode} lokasi yang "
        f"sudah tercatat pada periode tersebut), kategori penggunaan terbanyak adalah "
        f"**{teratas['Penggunaan']}** ({teratas['Persentase']:.1f}% dari lokasi tercatat)."
    )


def insight_lokasi_prioritas(df):
    """
    Pola: data -> hitung metrik lokasi prioritas -> hitung jumlah
    lokasi dengan evaluasi bermasalah DAN persentase periode
    bermasalah tinggi -> generate kalimat ringkasan (bukan menyebut
    nama lokasi satu per satu, karena daftar lengkapnya sudah
    ditampilkan sebagai tabel terpisah di dashboard).
    """
    lp = an.lokasi_prioritas(df)
    if lp.empty:
        return None

    jumlah_bermasalah = int(lp["Evaluasi Bermasalah"].sum())
    total_lokasi = len(lp)
    selalu_bermasalah = int(
        ((lp["Evaluasi Bermasalah"]) & (lp["Persentase Periode Bermasalah"] == 100)).sum()
    )

    return (
        f"Sebanyak {jumlah_bermasalah} dari {total_lokasi} lokasi ({jumlah_bermasalah/total_lokasi*100:.1f}%) "
        f"saat ini berada dalam kondisi evaluasi yang perlu perhatian. Dari jumlah tersebut, "
        f"{selalu_bermasalah} lokasi tercatat mengalami penggunaan bermasalah "
        f"(belum terpasang/tidak terdeteksi/tidak aktif) di SELURUH periode yang tersedia."
    )


def insight_kualitas_data(df):
    """
    Insight transparansi kualitas data, bukan kondisi layanan --
    supaya pengguna sadar keterbatasan data yang sedang dianalisis.
    """
    total_lokasi = df["Location ID"].nunique()
    lokasi_koordinat_bermasalah = (
        df[df["Koordinat Valid"] != True]["Location ID"].nunique()  # noqa: E712
    )

    if lokasi_koordinat_bermasalah == 0:
        return None

    return (
        f"Catatan kualitas data: {lokasi_koordinat_bermasalah} dari {total_lokasi} lokasi "
        f"memiliki koordinat yang tidak valid/tidak wajar sehingga tidak ditampilkan pada peta "
        f"(data lokasi tersebut tetap tersedia pada analisis lain)."
    )


def generate_all_insights(df):
    """
    Mengumpulkan seluruh insight yang berhasil dihitung (melewati
    fungsi-fungsi di atas), melewati yang bernilai None (misalnya
    karena data kosong setelah difilter).
    """
    fungsi_insight = [
        insight_kondisi_terbanyak,
        insight_kabupaten_bermasalah_tertinggi,
        insight_isp_bermasalah_tertinggi,
        insight_periode_terbaru_penggunaan,
        insight_lokasi_prioritas,
        insight_kualitas_data,
    ]

    hasil = []
    for fungsi in fungsi_insight:
        teks = fungsi(df)
        if teks:
            hasil.append(teks)

    return hasil
