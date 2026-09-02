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
    Insight Kabupaten dengan proporsi Desa Bermasalah tertinggi.

    Desa Bermasalah hanya:
    TIDAK AKTIF dan BELUM TERPASANG.
    """
    tabel = an.proporsi_bermasalah_per_grup(df, "Kabupaten")

    if tabel.empty:
        return None

    teratas = tabel.iloc[0]

    return (
        f"Kabupaten dengan proporsi **Desa Bermasalah** tertinggi adalah "
        f"**{teratas['Kabupaten']}**, yaitu "
        f"{teratas['Persentase Bermasalah']:.1f}% dari "
        f"{int(teratas['Jumlah_Lokasi']):,} lokasi."
    )


def insight_isp_bermasalah_tertinggi(df):
    """
    Insight ISP dengan proporsi Desa Bermasalah tertinggi.
    """
    tabel = an.proporsi_bermasalah_per_grup(df, "ISP")

    if tabel.empty:
        return None

    teratas = tabel.iloc[0]

    return (
        f"ISP dengan proporsi **Desa Bermasalah** tertinggi adalah "
        f"**{teratas['ISP']}**, yaitu "
        f"{teratas['Persentase Bermasalah']:.1f}% dari "
        f"{int(teratas['Jumlah_Lokasi']):,} lokasi yang dilayani."
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
    Insight lokasi prioritas berdasarkan definisi Desa Bermasalah.
    """
    lp = an.lokasi_prioritas(df)

    if lp.empty:
        return None

    jumlah_bermasalah = int(lp["Desa Bermasalah"].sum())
    total_lokasi = len(lp)

    selalu_bermasalah = int(
        (
            lp["Desa Bermasalah"]
            & (
                lp["Persentase Periode Bermasalah"] == 100
            )
        ).sum()
    )

    persentase = (
        jumlah_bermasalah / total_lokasi * 100
        if total_lokasi
        else 0
    )

    return (
        f"Terdapat **{jumlah_bermasalah:,} Desa Bermasalah** "
        f"dari {total_lokasi:,} lokasi ({persentase:.1f}%). "
        f"Desa Bermasalah hanya mencakup kategori "
        f"**Tidak Aktif** dan **Belum Terpasang**. "
        f"Dari jumlah tersebut, {selalu_bermasalah:,} lokasi "
        f"memiliki penggunaan bermasalah pada seluruh periode "
        f"yang tercatat."
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
