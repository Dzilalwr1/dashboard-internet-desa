"""Fungsi pembentukan insight untuk dashboard Internet Desa."""

import pandas as pd

from utils import analysis as an

def insight_kondisi_terbanyak(df: pd.DataFrame) -> str:
    """Mencari kategori hasil evaluasi yang paling banyak."""
    dist = an.distribusi_hasil_evaluasi(df)

    if dist.empty:
        return "Belum ada data hasil evaluasi."

    row = dist.loc[dist["Jumlah"].idxmax()]

    return (
        f"Kondisi terbanyak adalah {row['Hasil Evaluasi']} "
        f"dengan {row['Jumlah']:,} lokasi ({row['Persentase']:.1f}%)."
    )

def insight_kabupaten_bermasalah_tertinggi(df: pd.DataFrame) -> str:
    """Mencari kabupaten dengan proporsi desa bermasalah tertinggi."""
    dist = an.proporsi_bermasalah_per_grup(df, "Kabupaten")

    if dist.empty:
        return "Belum ada data kabupaten."

    row = dist.loc[dist["Persentase Bermasalah"].idxmax()]

    return (
        f"Kabupaten dengan proporsi desa bermasalah tertinggi adalah "
        f"{row['Kabupaten']} dengan {row['Persentase Bermasalah']:.1f}% "
        f"({row['Jumlah_Bermasalah']:,} dari {row['Jumlah_Lokasi']:,} lokasi)."
    )

def insight_isp_bermasalah_tertinggi(df: pd.DataFrame) -> str:
    """Mencari ISP dengan proporsi desa bermasalah tertinggi."""
    dist = an.proporsi_bermasalah_per_grup(df, "ISP")

    if dist.empty:
        return "Belum ada data ISP."

    row = dist.loc[dist["Persentase Bermasalah"].idxmax()]

    return (
        f"ISP dengan proporsi desa bermasalah tertinggi adalah "
        f"{row['ISP']} dengan {row['Persentase Bermasalah']:.1f}% "
        f"({row['Jumlah_Bermasalah']:,} dari {row['Jumlah_Lokasi']:,} lokasi)."
    )

def insight_periode_terbaru_penggunaan(df: pd.DataFrame) -> str:
    """Mencari periode terbaru yang memiliki data penggunaan yang representatif."""
    tren = an.tren_penggunaan_bulanan(df)

    if tren.empty:
        return "Belum ada data penggunaan bulanan."

    total_lokasi = df["Location ID"].nunique()

    if total_lokasi == 0:
        return "Belum ada data lokasi."

    # Jumlah observasi per periode berasal dari fungsi khususnya,
    # sehingga tidak bergantung pada kolom agregat distribusi kategori.
    jumlah_observasi = an.jumlah_observasi_per_periode(df)
    batas_minimum = total_lokasi * 0.30
    periode_valid = jumlah_observasi[
        jumlah_observasi["Jumlah Lokasi Tercatat"] >= batas_minimum
    ]

    if periode_valid.empty:
        return "Belum ada periode dengan data penggunaan yang cukup."

    periode_terbaru = periode_valid.iloc[-1]
    periode_urutan = periode_terbaru["Periode Urutan"]
    periode = periode_terbaru["Periode Label"]
    data_periode = df[df["Periode Urutan"] == periode_urutan]
    dist = an.distribusi_penggunaan(data_periode)

    if dist.empty:
        return f"Periode terbaru dengan data cukup adalah {periode}."

    row = dist.loc[dist["Jumlah"].idxmax()]

    return (
        f"Periode terbaru dengan data yang cukup adalah {periode}, "
        f"dengan {periode_terbaru['Jumlah Lokasi Tercatat']:,} observasi. "
        f"Kategori penggunaan terbanyak adalah {row['Penggunaan']} "
        f"sebanyak {row['Jumlah']:,} ({row['Persentase']:.1f}%)."
    )

def insight_lokasi_prioritas(df: pd.DataFrame) -> str:
    """Meringkas jumlah lokasi yang masuk daftar prioritas."""
    prioritas = an.lokasi_prioritas(df)

    if prioritas.empty:
        return "Belum ada lokasi yang dapat dianalisis sebagai prioritas."

    total = len(prioritas)
    desa_bermasalah = prioritas["Desa Bermasalah"].sum()
    usage_bermasalah = (
        prioritas["Jumlah_Periode_Penggunaan_Bermasalah"] > 0
    ).sum()

    return (
        f"Terdapat {total:,} lokasi dalam daftar prioritas. "
        f"{desa_bermasalah:,} lokasi termasuk Desa Bermasalah "
        f"(TIDAK AKTIF atau BELUM TERPASANG), sedangkan "
        f"{usage_bermasalah:,} lokasi memiliki penggunaan bermasalah "
        f"pada setidaknya satu periode."
    )

def insight_kualitas_data(df: pd.DataFrame) -> str:
    """Meringkas kualitas koordinat dan kelengkapan data."""
    if df.empty:
        return "Data belum tersedia."

    total_lokasi = df["Location ID"].nunique()

    if total_lokasi == 0:
        return "Belum ada lokasi yang dapat dianalisis."

    snapshot = an.get_location_snapshot(df)

    if snapshot.empty:
        return "Belum ada data lokasi yang dapat dianalisis."

    koordinat_valid = snapshot["Koordinat Valid"].sum()
    persentase_koordinat = koordinat_valid / total_lokasi * 100

    return (
        f"Sebanyak {koordinat_valid:,} dari {total_lokasi:,} lokasi "
        f"({persentase_koordinat:.1f}%) memiliki koordinat yang valid "
        f"untuk kebutuhan pemetaan."
    )

def generate_all_insights(df: pd.DataFrame) -> list[str]:
    """Menghasilkan seluruh insight utama dashboard."""
    return [
        insight_kondisi_terbanyak(df),
        insight_kabupaten_bermasalah_tertinggi(df),
        insight_isp_bermasalah_tertinggi(df),
        insight_periode_terbaru_penggunaan(df),
        insight_lokasi_prioritas(df),
        insight_kualitas_data(df),
    ]