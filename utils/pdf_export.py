"""
Ekspor hasil analisis dashboard Internet Desa menjadi PDF.

Modul ini memakai ReportLab untuk menyusun laporan PDF yang memuat
seluruh hasil perhitungan analisis, disajikan sebagai TABEL sekaligus
GRAFIK (mengikuti visualisasi yang tampil pada dashboard). Grafik
dirender lewat Matplotlib (backend "Agg", tanpa perlu tampilan/GUI)
lalu disisipkan sebagai gambar PNG ke dalam PDF -- pendekatan ini tidak
memerlukan dependensi tambahan seperti kaleido/chromium untuk
merender chart Plotly menjadi gambar statis.

Setiap bagian menjawab satu tab pada dashboard:

- Ringkasan Umum (KPI + distribusi + grafik + insight)
- Analisis Wilayah (per Kabupaten): tabel + grafik komposisi & proporsi
- Analisis ISP: tabel + grafik komposisi & proporsi
- Analisis Temporal: tabel + grafik jumlah observasi & tren penggunaan
- Lokasi Prioritas: HANYA kategori Tidak Aktif & Belum Terpasang
  (Desa Bermasalah), lengkap dengan grafik ringkasannya

Bagian "Detail Data" sengaja TIDAK disertakan dalam ekspor PDF karena
isinya adalah data mentah ter-filter baris-per-baris yang lebih sesuai
diunduh sebagai CSV (lihat tombol unduh CSV di tab Detail Data pada
dashboard) daripada dicetak sebagai tabel PDF yang bisa sangat panjang.
"""

import html
import io
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # render tanpa GUI/display, aman untuk server web
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import analysis as an
from utils import insights as ins
from utils.constants import (
    URUTAN_HASIL_EVALUASI,
    URUTAN_PENGGUNAAN,
    WARNA_HASIL_EVALUASI,
    WARNA_PENGGUNAAN,
)

JUDUL = "Laporan Analisis Internet Desa"

_WARNA_JUDUL = colors.HexColor("#1F4E79")
_WARNA_HEADER = colors.HexColor("#1F4E79")
_WARNA_BARIS_ALTE = colors.HexColor("#F2F7FB")


def _fmt_angka(v, ribuan=True):
    """Format angka menjadi teks, menangani NaN/None dengan rapi."""
    if v is None:
        return "-"
    try:
        f = float(v)
        if f != f:  # NaN
            return "-"
        return f"{f:,.2f}" if ribuan else f"{f:.2f}"
    except (TypeError, ValueError):
        return str(v)


def _markdown_ke_reportlab(teks: str) -> str:
    """
    Konversi kalimat insight (memakai markdown ringan `**tebal**`) menjadi
    markup yang dipahami ReportLab Paragraph (`<b>tebal</b>`).

    Karakter XML khusus (&, <, >) di-escape lebih dulu supaya teks asli
    tidak pernah dianggap sebagai tag oleh ReportLab.
    """
    aman = html.escape(teks, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", aman)


def _gaya():
    styles = getSampleStyleSheet()
    s_judul = styles["Title"]
    s_judul.textColor = _WARNA_JUDUL
    s_bab = styles["Heading1"]
    s_bab.textColor = _WARNA_JUDUL
    s_sub = styles["Heading2"]
    s_sub.textColor = _WARNA_JUDUL
    s_isi = styles["BodyText"]
    s_isi.spaceAfter = 6
    s_kecil = ParagraphStyle(
        name="KecilLaporan",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=4,
    )
    return {
        "judul": s_judul,
        "bab": s_bab,
        "sub": s_sub,
        "isi": s_isi,
        "kecil": s_kecil,
    }


# Gaya khusus untuk ISI SEL tabel (bukan judul/paragraf biasa). Nilai sel
# dibungkus sebagai Paragraph memakai gaya ini supaya teks panjang
# (nama desa/kecamatan, dsb.) melipat ke baris berikutnya di dalam sel,
# bukan meluber/bertabrakan dengan kolom di sebelahnya saat lebar kolom
# sempit -- ini penyebab utama tabel terlihat "kepenuhan/press" di PDF.
_STYLE_SEL_TABEL = ParagraphStyle(
    name="SelTabel",
    fontName="Helvetica",
    fontSize=7,
    leading=8.5,
)


def _sel(nilai):
    """Bungkus satu nilai sel sebagai Paragraph agar bisa word-wrap."""
    if nilai is None:
        return "-"
    teks = str(nilai)
    if not teks:
        return "-"
    return Paragraph(html.escape(teks, quote=False), _STYLE_SEL_TABEL)


_STYLE_HEADER_TABEL = ParagraphStyle(
    name="HeaderTabel",
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9,
    textColor=colors.white,
    alignment=1,  # tengah (TA_CENTER)
)


def _sel_header(nilai):
    """Bungkus label header sebagai Paragraph agar label panjang melipat
    ke baris berikutnya di dalam sel header, bukan meluber ke header
    kolom sebelahnya."""
    if nilai is None:
        return ""
    return Paragraph(html.escape(str(nilai), quote=False), _STYLE_HEADER_TABEL)


def _gaya_tabel(data, col_widths=None, repeat=1):
    """Tabel dasar dengan header berwarna dan zebra strip.

    Baris header (baris pertama) selalu dibungkus sebagai Paragraph
    supaya label kolom yang panjang ikut word-wrap, konsisten dengan
    isi tabel yang sudah dibungkus lewat `_sel()`.
    """
    if data:
        header_asli = data[0]
        header_dibungkus = [
            v if isinstance(v, Paragraph) else _sel_header(v) for v in header_asli
        ]
        data = [header_dibungkus] + list(data[1:])

    tbl = LongTable(data, colWidths=col_widths, repeatRows=repeat)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _WARNA_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _WARNA_BARIS_ALTE]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C6D6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tbl


def _tabel_dari_df(df, kolom_label=None, kapital=True):
    """Konversi DataFrame menjadi daftar baris tabel ReportLab.

    Nilai sel dibungkus lewat `_sel()` (Paragraph) supaya teks panjang
    melipat ke baris berikutnya, bukan meluber ke kolom sebelah.
    """
    if df is None or df.empty:
        return [["(tidak ada data)"]]
    kolom = list(df.columns)
    label = kolom_label or {k: k for k in kolom}
    header = [label.get(k, k).replace("_", " ") for k in kolom]
    if kapital:
        header = [str(h).upper() for h in header]
    baris = []
    for _, r in df.iterrows():
        baris.append([_sel(v) if pd.notna(v) else "-" for v in r[kolom]])
    return [header] + baris


_LEBAR_GRAFIK_CM = 17.5  # ~lebar halaman A4 usable dengan margin 1.5 cm kiri-kanan


def _simpan_grafik(fig, lebar_cm=_LEBAR_GRAFIK_CM):
    """
    Render figure Matplotlib menjadi flowable `Image` ReportLab.

    Tinggi gambar dihitung otomatis dari rasio aspek PNG asli (bukan
    lebar/tinggi tetap) supaya grafik tidak gepeng/meregang ketika
    diskalakan ke lebar halaman. Figure ditutup setelah disimpan agar
    tidak menumpuk di memori saat laporan memuat banyak grafik.
    """
    bufer = io.BytesIO()
    fig.savefig(bufer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    bufer.seek(0)
    lebar_px, tinggi_px = PILImage.open(bufer).size
    bufer.seek(0)
    lebar = lebar_cm * cm
    tinggi = lebar * (tinggi_px / lebar_px)
    return Image(bufer, width=lebar, height=tinggi)


def _warna_berdasar_nilai(nilai):
    """Warna RdYlGn per-bar berdasar besar nilainya (tinggi = hijau,
    rendah = merah), meniru `buat_bar_chart_persentase` pada app.py."""
    angka = pd.to_numeric(pd.Series(nilai), errors="coerce")
    vmin, vmax = angka.min(), angka.max()
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        posisi = [0.5] * len(angka)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
        posisi = [norm(v) for v in angka]
    cmap = matplotlib.colormaps["RdYlGn"]
    return [cmap(p) for p in posisi]


def _grafik_bar_persentase(df, kolom_x, kolom_y, urutan=None, label_y="Persentase (%)", persen=True):
    """Bar chart nilai berwarna berdasar besarnya nilai (RdYlGn),
    versi statis dari `buat_bar_chart_persentase` di app.py.

    `persen=False` dipakai untuk grafik berbasis jumlah (bukan %),
    misalnya jumlah lokasi per periode, agar label & sumbu-y tidak
    salah dibubuhi tanda "%".
    """
    if df is None or df.empty:
        return None
    data = df.copy()
    if urutan:
        data[kolom_x] = pd.Categorical(
            data[kolom_x].astype(str), categories=urutan, ordered=True
        )
        data = data.sort_values(kolom_x)
    nilai = pd.to_numeric(data[kolom_y], errors="coerce")
    if kolom_x == "Hasil Evaluasi":
        warna = [
            WARNA_HASIL_EVALUASI.get(str(kategori).upper().strip(), "#808080")
            for kategori in data[kolom_x]
        ]
    else:
        warna = _warna_berdasar_nilai(nilai)

    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    bar = ax.bar(data[kolom_x].astype(str), nilai, color=warna, edgecolor="#666666", linewidth=0.4)
    for b, v in zip(bar, nilai):
        if pd.notna(v):
            teks = f"{v:.1f}%" if persen else f"{v:,.0f}"
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height(),
                teks,
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    ax.set_ylabel(label_y, fontsize=8)
    atas = float(nilai.max()) if nilai.notna().any() else 1
    ax.set_ylim(0, max(atas * 1.18, 5))
    ax.tick_params(axis="both", labelsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _simpan_grafik(fig)


def _grafik_stacked_evaluasi(pivot_df, urutan=None):
    """Stacked bar komposisi Hasil Evaluasi (%) per grup (Kabupaten/ISP),
    memakai palet warna kategori `WARNA_HASIL_EVALUASI` yang sama
    dengan dashboard."""
    if pivot_df is None or pivot_df.empty:
        return None
    urutan = urutan or URUTAN_HASIL_EVALUASI
    kolom_pakai = [k for k in urutan if k in pivot_df.columns]
    if not kolom_pakai:
        return None

    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    bawah = pd.Series(0.0, index=pivot_df.index)
    label_x = pivot_df.index.astype(str)
    for kategori in kolom_pakai:
        nilai = pivot_df[kategori].astype(float)
        warna = WARNA_HASIL_EVALUASI.get(kategori, "#999999")
        ax.bar(label_x, nilai, bottom=bawah, label=kategori, color=warna, edgecolor="white", linewidth=0.3)
        bawah = bawah + nilai
    ax.set_ylabel("Persentase (%)", fontsize=8)
    ax.tick_params(axis="both", labelsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.32),
        ncol=3,
        fontsize=6.5,
        frameon=False,
    )
    fig.tight_layout()
    return _simpan_grafik(fig)


def _grafik_area_tren_penggunaan(pivot_df, urutan=None):
    """Stacked area chart tren Penggunaan (%) per periode, memakai
    palet warna kategori `WARNA_PENGGUNAAN` yang sama dengan dashboard."""
    if pivot_df is None or pivot_df.empty:
        return None
    urutan = urutan or URUTAN_PENGGUNAAN
    kolom_pakai = [k for k in urutan if k in pivot_df.columns]
    if not kolom_pakai:
        return None

    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    x = range(len(pivot_df.index))
    ys = [pivot_df[k].astype(float).values for k in kolom_pakai]
    warna = [WARNA_PENGGUNAAN.get(k, "#999999") for k in kolom_pakai]
    ax.stackplot(x, ys, labels=kolom_pakai, colors=warna)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot_df.index.astype(str), rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Persentase (%)", fontsize=8)
    ax.set_ylim(0, 100)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.35),
        ncol=4,
        fontsize=6,
        frameon=False,
    )
    fig.tight_layout()
    return _simpan_grafik(fig)


def _grafik_pie_prioritas(df, kolom="Kondisi_Evaluasi_Terkini"):
    """Pie chart komposisi kategori (Tidak Aktif vs Belum Terpasang) di
    antara lokasi prioritas / Desa Bermasalah."""
    if df is None or df.empty or kolom not in df.columns:
        return None
    jumlah = df[kolom].value_counts()
    if jumlah.empty:
        return None
    warna = [WARNA_HASIL_EVALUASI.get(k, "#999999") for k in jumlah.index]

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.pie(
        jumlah.values,
        labels=jumlah.index,
        autopct="%.1f%%",
        colors=warna,
        textprops={"fontsize": 8},
        wedgeprops={"edgecolor": "white", "linewidth": 0.6},
    )
    ax.set_title("Komposisi Desa Bermasalah", fontsize=9)
    fig.tight_layout()
    return _simpan_grafik(fig, lebar_cm=8)


def _grafik_bar_top_kabupaten(df, kolom="Kabupaten", n=15, lebar_cm=9.0):
    """Horizontal bar: Kabupaten dengan jumlah Desa Bermasalah terbanyak."""
    if df is None or df.empty or kolom not in df.columns:
        return None
    jumlah = df[kolom].value_counts().sort_values(ascending=False).head(n)
    if jumlah.empty:
        return None

    fig, ax = plt.subplots(figsize=(4.6, max(2.4, 0.32 * len(jumlah))))
    ax.barh(jumlah.index[::-1].astype(str), jumlah.values[::-1], color="#AD0000")
    for i, v in enumerate(jumlah.values[::-1]):
        ax.text(v, i, f" {v}", va="center", fontsize=7.5)
    ax.set_xlabel("Jumlah Desa Bermasalah", fontsize=8)
    ax.tick_params(axis="both", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _simpan_grafik(fig, lebar_cm=lebar_cm)


def _kpi_tabel(kpi):
    baris = [
        ["Total Record", _fmt_angka(kpi["total_record"])],
        ["Total Lokasi", _fmt_angka(kpi["total_lokasi"])],
        ["Total Kabupaten", _fmt_angka(kpi["total_kabupaten"])],
        ["Total ISP", _fmt_angka(kpi["total_isp"])],
    ]
    return _gaya_tabel([["Metrik", "Nilai"]] + baris, col_widths=[8 * cm, 4 * cm])


def _distribusi_tabel(df, nama_kategori, nama_persen):
    if df is None or df.empty:
        return _gaya_tabel([["(tidak ada data)"]])
    baris = [
        [_sel(r[nama_kategori]), _fmt_angka(r.get("Jumlah")), f"{_fmt_angka(r.get(nama_persen))}%"]
        for _, r in df.iterrows()
    ]
    return _gaya_tabel(
        [["KATEGORI", "JUMLAH", "PERSENTASE"]] + baris,
        col_widths=[7 * cm, 3.5 * cm, 4 * cm],
    )


def _grup_tabel_komposisi(df, kolom_grup):
    if df is None or df.empty:
        return _gaya_tabel([["(tidak ada data)"]])
    hasil_pivot = df.pivot_table(
        index=kolom_grup, columns="Hasil Evaluasi", values="Persentase", aggfunc="first"
    ).fillna(0)
    urutan = [k for k in an.URUTAN_HASIL_EVALUASI if k in hasil_pivot.columns]
    hasil_pivot = hasil_pivot[urutan]
    baris = [
        [
            _sel(idx),
            *[f"{_fmt_angka(v)}%" for v in row],
            _fmt_angka(row.sum()),
        ]
        for idx, row in hasil_pivot.iterrows()
    ]
    header = [str(k.upper()).replace("_", " ") for k in ([kolom_grup] + urutan + ["TOTAL"])]
    return _gaya_tabel([header] + baris, col_widths=[3.5 * cm] + [2.0 * cm] * (len(urutan) + 1))


def _grup_tabel_proporsi(df, kolom_grup):
    if df is None or df.empty:
        return _gaya_tabel([["(tidak ada data)"]])
    baris = [
        [
            _sel(r[kolom_grup]),
            _fmt_angka(r["Jumlah_Lokasi"]),
            _fmt_angka(r["Jumlah_Bermasalah"]),
            f"{_fmt_angka(r['Persentase Bermasalah'])}%",
        ]
        for _, r in df.iterrows()
    ]
    return _gaya_tabel(
        [
            ["GRUP / KABUPATEN / ISP", "JUMLAH LOKASI", "JUMLAH BERMASALAH", "PERSENTASE BERMASALAH"],
        ]
        + baris,
        col_widths=[6 * cm, 3 * cm, 3 * cm, 4.5 * cm],
    )


def _prioritas_tabel(df, kolom_label):
    """
    Tabel Lokasi Prioritas.

    Hanya menampilkan kolom yang ada di `kolom_label` (whitelist + label),
    dengan urutan mengikuti urutan dict tersebut -- ini penting supaya
    kolom seperti "Location ID" (gabungan Kabupaten|Kecamatan|Desa yang
    bisa >50 karakter) dan kolom duplikat lain tidak ikut ditampilkan dan
    membuat tabel kepenuhan/tabrakan antar kolom. Nilai boolean diubah
    menjadi "Ya"/"Tidak" agar lebih ringkas dan mudah dibaca.
    """
    if df is None or df.empty:
        return _gaya_tabel([["(tidak ada data)"]])

    kolom_terpilih = [k for k in kolom_label if k in df.columns]
    tampil = df[kolom_terpilih].copy()
    for k in tampil.columns:
        if tampil[k].dtype == bool:
            tampil[k] = tampil[k].map({True: "Ya", False: "Tidak"})

    # Lebar kolom (cm) dipesan sesuai kebutuhan tampilan masing-masing
    # kolom: nama wilayah/ISP butuh ruang lebih, kolom status/angka
    # cukup sempit. Total dijaga di bawah lebar halaman A4 usable
    # (~18 cm dengan margin 1.5 cm kiri-kanan).
    lebar_per_kolom = {
        "Kabupaten": 2.3,
        "Kecamatan": 2.3,
        "Desa": 2.5,
        "ISP": 2.1,
        "Kondisi_Evaluasi_Terkini": 2.3,
        "Total_Periode_Tercatat": 1.5,
        "Jumlah_Periode_Penggunaan_Bermasalah": 1.7,
        "Persentase Periode Bermasalah": 1.7,
        "Desa Bermasalah": 1.4,
    }
    lebar_default = 2.0
    col_widths = [
        lebar_per_kolom.get(k, lebar_default) * cm for k in kolom_terpilih
    ]

    return _gaya_tabel(
        _tabel_dari_df(tampil, kolom_label=kolom_label),
        col_widths=col_widths,
    )


def buat_pdf(df):
    """
    Membangun seluruh laporan PDF dari DataFrame ter-filter.

    Catatan: bagian "Detail Data" (data mentah baris-per-baris) SENGAJA
    tidak disertakan dalam PDF -- lihat catatan modul di bagian atas
    file ini. Gunakan tombol unduh CSV pada tab Detail Data di dashboard
    jika data mentah ter-filter dibutuhkan.

    Mengembalikan bytes PDF.
    """
    bufer = io.BytesIO()
    doc = SimpleDocTemplate(
        bufer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.5 * cm,
        title=JUDUL,
        author="Dashboard Analisis Internet Desa",
    )
    styles = _gaya()
    elemen: list = []

    # ===== HALAMAN JUDUL =====
    elemen.append(Spacer(1, 2 * cm))
    elemen.append(Paragraph(JUDUL, styles["judul"]))
    elemen.append(Spacer(1, 0.5 * cm))
    elemen.append(
        Paragraph(
            "Laporan komprehensif hasil analisis kondisi layanan "
            "Internet Desa. Data bersumber dari"
            " file Data Master yang diunggah ke dashboard.",
            styles["isi"],
        )
    )
    elemen.append(Spacer(1, 1 * cm))
    elemen.append(
        Paragraph(
            f"Dibuat pada: {datetime.now().strftime('%d %B %Y, %H:%M')}",
            styles["kecil"],
        )
    )
    elemen.append(Paragraph(f"Total lokasi dalam laporan: {_fmt_angka(df['Location ID'].nunique())}", styles["kecil"]))
    elemen.append(PageBreak())

    # ===== 1. RINGKASAN UMUM =====
    elemen.append(Paragraph("1. Ringkasan Umum", styles["bab"]))
    kpi = an.get_kpi_summary(df)
    elemen.append(_kpi_tabel(kpi))
    elemen.append(Spacer(1, 0.5 * cm))

    elemen.append(Paragraph("1.1 Insight Utama", styles["sub"]))
    daftar_insight = ins.generate_all_insights(df)
    for teks in daftar_insight or []:
        elemen.append(Paragraph("• " + _markdown_ke_reportlab(teks), styles["kecil"]))
    elemen.append(PageBreak())

    elemen.append(Paragraph("1.2 Distribusi Hasil Evaluasi (per lokasi)", styles["sub"]))
    dist_eval = an.distribusi_hasil_evaluasi(df)
    elemen.append(_distribusi_tabel(dist_eval, "Hasil Evaluasi", "Persentase"))
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_dist_eval = _grafik_bar_persentase(
        dist_eval, "Hasil Evaluasi", "Persentase", urutan=URUTAN_HASIL_EVALUASI
    )
    if grafik_dist_eval:
        elemen.append(grafik_dist_eval)
    elemen.append(Spacer(1, 0.5 * cm))

    elemen.append(Paragraph("1.3 Distribusi Penggunaan (seluruh baris ter-filter)", styles["sub"]))
    dist_peng = an.distribusi_penggunaan(df)
    elemen.append(_distribusi_tabel(dist_peng, "Penggunaan", "Persentase"))
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_dist_peng = _grafik_bar_persentase(
        dist_peng, "Penggunaan", "Persentase", urutan=URUTAN_PENGGUNAAN
    )
    if grafik_dist_peng:
        elemen.append(grafik_dist_peng)
    elemen.append(PageBreak())

    # ===== 2. ANALISIS WILAYAH (KABUPATEN) =====
    elemen.append(Paragraph("2. Analisis Wilayah (per Kabupaten)", styles["bab"]))
    komposisi_kab, jumlah_kab = an.komposisi_evaluasi_per_grup(df, "Kabupaten")
    elemen.append(Paragraph("2.1 Komposisi Hasil Evaluasi per Kabupaten (%)", styles["sub"]))
    elemen.append(_grup_tabel_komposisi(komposisi_kab, "Kabupaten"))
    elemen.append(Spacer(1, 0.4 * cm))
    pivot_kab = komposisi_kab.pivot_table(
        index="Kabupaten", columns="Hasil Evaluasi", values="Persentase", aggfunc="first"
    ).fillna(0)
    grafik_komposisi_kab = _grafik_stacked_evaluasi(pivot_kab)
    if grafik_komposisi_kab:
        elemen.append(grafik_komposisi_kab)
    elemen.append(Spacer(1, 0.5 * cm))
    elemen.append(Paragraph("2.2 Proporsi Desa Bermasalah per Kabupaten", styles["sub"]))
    proporsi_kab = an.proporsi_bermasalah_per_grup(df, "Kabupaten")
    elemen.append(_grup_tabel_proporsi(proporsi_kab, "Kabupaten"))
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_proporsi_kab = _grafik_bar_persentase(
        proporsi_kab, "Kabupaten", "Persentase Bermasalah"
    )
    if grafik_proporsi_kab:
        elemen.append(grafik_proporsi_kab)
    elemen.append(Spacer(1, 0.5 * cm))
    elemen.append(Paragraph("2.3 Jumlah Lokasi per Kabupaten", styles["sub"]))
    elemen.append(_gaya_tabel(_tabel_dari_df(jumlah_kab), col_widths=[4 * cm, 3 * cm]))
    elemen.append(PageBreak())

    # ===== 3. ANALISIS ISP =====
    elemen.append(Paragraph("3. Analisis ISP", styles["bab"]))
    komposisi_isp, jumlah_isp = an.komposisi_evaluasi_per_grup(df, "ISP")
    elemen.append(Paragraph("3.1 Komposisi Hasil Evaluasi per ISP (%)", styles["sub"]))
    elemen.append(_grup_tabel_komposisi(komposisi_isp, "ISP"))
    elemen.append(Spacer(1, 0.4 * cm))
    pivot_isp = komposisi_isp.pivot_table(
        index="ISP", columns="Hasil Evaluasi", values="Persentase", aggfunc="first"
    ).fillna(0)
    grafik_komposisi_isp = _grafik_stacked_evaluasi(pivot_isp)
    if grafik_komposisi_isp:
        elemen.append(grafik_komposisi_isp)
    elemen.append(Spacer(1, 0.5 * cm))
    elemen.append(Paragraph("3.2 Proporsi Desa Bermasalah per ISP", styles["sub"]))
    proporsi_isp = an.proporsi_bermasalah_per_grup(df, "ISP")
    elemen.append(_grup_tabel_proporsi(proporsi_isp, "ISP"))
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_proporsi_isp = _grafik_bar_persentase(proporsi_isp, "ISP", "Persentase Bermasalah")
    if grafik_proporsi_isp:
        elemen.append(grafik_proporsi_isp)
    elemen.append(Spacer(1, 0.5 * cm))
    elemen.append(Paragraph("3.3 Jumlah Lokasi per ISP", styles["sub"]))
    elemen.append(_gaya_tabel(_tabel_dari_df(jumlah_isp), col_widths=[4 * cm, 3 * cm]))
    elemen.append(PageBreak())

    # ===== 4. ANALISIS TEMPORAL =====
    elemen.append(Paragraph("4. Analisis Temporal", styles["bab"]))
    elemen.append(
        Paragraph(
            "Catatan: Pada dataset ini kolom Hasil Evaluasi bersifat statis per lokasi, "
            "sehingga tren waktu yang bermakna dihitung dari kolom Penggunaan.",
            styles["kecil"],
        )
    )
    elemen.append(Paragraph("4.1 Jumlah Lokasi Tercatat per Periode", styles["sub"]))
    observasi = an.jumlah_observasi_per_periode(df)
    elemen.append(
        _gaya_tabel(
            _tabel_dari_df(observasi, kolom_label={"Periode Label": "Periode"}),
            col_widths=[7 * cm, 5 * cm, 5 * cm],
        )
    )
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_observasi = _grafik_bar_persentase(
        observasi,
        "Periode Label",
        "Jumlah Lokasi Tercatat",
        label_y="Jumlah Lokasi",
        persen=False,
    )
    if grafik_observasi:
        elemen.append(grafik_observasi)
    elemen.append(Spacer(1, 0.4 * cm))
    elemen.append(Paragraph("4.2 Distribusi Penggunaan per Periode (%)", styles["sub"]))
    tren = an.tren_penggunaan_bulanan(df)
    # Urutan periode KRONOLOGIS (Januari -> dst mengikuti Periode Urutan),
    # bukan urutan abjad label bulan. `pivot_table` mengurutkan index
    # secara alfabetis secara default, jadi urutan baris harus dipaksa
    # ulang lewat `reindex` memakai urutan asli dari `Periode Urutan`.
    urutan_periode_pdf = (
        tren[["Periode Urutan", "Periode Label"]]
        .drop_duplicates()
        .sort_values("Periode Urutan")["Periode Label"]
        .tolist()
    )
    # pivot: baris = periode, kolom = kategori penggunaan
    tren_p = tren.pivot_table(
        index="Periode Label", columns="Penggunaan", values="Persentase", aggfunc="first"
    ).fillna(0)
    tren_p = tren_p.reindex(urutan_periode_pdf)
    p_urutan = [k for k in an.URUTAN_PENGGUNAAN if k in tren_p.columns]
    tren_p = tren_p[p_urutan]
    baris_tren = [
        [_sel(idx), *[f"{_fmt_angka(v)}%" for v in row]]
        for idx, row in tren_p.iterrows()
    ]
    lebar_periode = 3 * cm
    lebar_sisa = (18 * cm - lebar_periode) / max(len(p_urutan), 1)
    elemen.append(
        _gaya_tabel(
            [["PERIODE"] + [str(k) for k in p_urutan]] + baris_tren,
            col_widths=[lebar_periode] + [lebar_sisa] * len(p_urutan),
        )
    )
    elemen.append(Spacer(1, 0.4 * cm))
    grafik_tren = _grafik_area_tren_penggunaan(tren_p, urutan=p_urutan)
    if grafik_tren:
        elemen.append(grafik_tren)
    elemen.append(PageBreak())

    # ===== 5. LOKASI PRIORITAS =====
    elemen.append(Paragraph("5. Lokasi Prioritas Monitoring", styles["bab"]))
    elemen.append(
        Paragraph(
            "Daftar berikut HANYA memuat Desa Bermasalah, yaitu lokasi dengan "
            "kondisi evaluasi terkini Tidak Aktif atau Belum Terpasang. "
            "Kategori Kurang Optimal dan Tidak Optimal tetap ditampilkan pada "
            "bagian analisis lain sebagai hasil evaluasi, tetapi tidak "
            "dimasukkan ke daftar prioritas ini.",
            styles["kecil"],
        )
    )
    prioritas_semua = an.lokasi_prioritas(df)
    prioritas = prioritas_semua[prioritas_semua["Desa Bermasalah"]].copy()

    if prioritas.empty:
        elemen.append(Spacer(1, 0.3 * cm))
        elemen.append(
            Paragraph(
                "Tidak ada Desa Bermasalah (Tidak Aktif / Belum Terpasang) pada "
                "data ter-filter saat ini.",
                styles["isi"],
            )
        )
    else:
        elemen.append(
            Paragraph(
                f"Total Desa Bermasalah: {_fmt_angka(len(prioritas))} lokasi.",
                styles["kecil"],
            )
        )
        elemen.append(Spacer(1, 0.3 * cm))

        grafik_pie_prioritas = _grafik_pie_prioritas(prioritas)
        grafik_top_kab = _grafik_bar_top_kabupaten(prioritas)
        if grafik_pie_prioritas or grafik_top_kab:
            sel_kiri = [grafik_pie_prioritas] if grafik_pie_prioritas else [Spacer(1, 1)]
            sel_kanan = [grafik_top_kab] if grafik_top_kab else [Spacer(1, 1)]
            elemen.append(
                Table(
                    [[sel_kiri, sel_kanan]],
                    colWidths=[8.5 * cm, 9 * cm],
                )
            )
        elemen.append(Spacer(1, 0.4 * cm))

        label_prioritas = {
            "Kabupaten": "Kabupaten",
            "Kecamatan": "Kecamatan",
            "Desa": "Desa",
            "ISP": "ISP",
            "Kondisi_Evaluasi_Terkini": "Kondisi Terkini",
            "Total_Periode_Tercatat": "Total Periode",
            "Jumlah_Periode_Penggunaan_Bermasalah": "Jml Periode Bermasalah",
            "Persentase Periode Bermasalah": "Pers. Periode Bermasalah",
            "Desa Bermasalah": "Desa Bermasalah",
        }
        elemen.append(_prioritas_tabel(prioritas, label_prioritas))

    # Catatan: bagian "Detail Data" sengaja tidak disertakan dalam PDF.
    # Lihat docstring modul di bagian atas file ini.

    doc.build(
        elemen,
        onFirstPage=_gambar_header_footer,
        onLaterPages=_gambar_header_footer,
    )
    return bufer.getvalue()


def buat_pdf_insight(df):
    """
    Membangun PDF ringkas yang hanya memuat Insight Utama (beserta KPI
    singkat sebagai konteks), tanpa seluruh tabel analisis pada
    `buat_pdf`. Dipakai oleh tombol ekspor yang ada langsung di bagian
    Insight Utama pada tab Overview.

    Mengembalikan bytes PDF.
    """
    judul = "Laporan Insight - Internet Desa"
    bufer = io.BytesIO()
    doc = SimpleDocTemplate(
        bufer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.5 * cm,
        title=judul,
        author="Dashboard Analisis Internet Desa",
    )
    styles = _gaya()
    elemen: list = []

    elemen.append(Paragraph(judul, styles["judul"]))
    elemen.append(Spacer(1, 0.3 * cm))
    elemen.append(
        Paragraph(
            f"Dibuat pada: {datetime.now().strftime('%d %B %Y, %H:%M')}",
            styles["kecil"],
        )
    )
    elemen.append(
        Paragraph(
            f"Total lokasi dalam laporan: {_fmt_angka(df['Location ID'].nunique())}",
            styles["kecil"],
        )
    )
    elemen.append(Spacer(1, 0.5 * cm))

    elemen.append(Paragraph("Ringkasan KPI", styles["sub"]))
    kpi = an.get_kpi_summary(df)
    elemen.append(_kpi_tabel(kpi))
    elemen.append(Spacer(1, 0.5 * cm))

    elemen.append(Paragraph("Distribusi Hasil Evaluasi (per lokasi)", styles["sub"]))
    dist_eval = an.distribusi_hasil_evaluasi(df)
    grafik_dist_eval = _grafik_bar_persentase(
        dist_eval, "Hasil Evaluasi", "Persentase", urutan=URUTAN_HASIL_EVALUASI
    )
    if grafik_dist_eval:
        elemen.append(grafik_dist_eval)
    elemen.append(Spacer(1, 0.6 * cm))

    elemen.append(Paragraph("Insight Utama", styles["sub"]))
    daftar_insight = ins.generate_all_insights(df)
    if daftar_insight:
        for teks in daftar_insight:
            elemen.append(Paragraph("• " + _markdown_ke_reportlab(teks), styles["isi"]))
    else:
        elemen.append(
            Paragraph(
                "Belum ada insight yang dapat dihitung dari data terfilter saat ini.",
                styles["isi"],
            )
        )

    doc.build(
        elemen,
        onFirstPage=_gambar_header_footer_insight,
        onLaterPages=_gambar_header_footer_insight,
    )
    return bufer.getvalue()


def _gambar_header_footer_insight(canvas, doc):
    """Header & footer untuk laporan insight (judul lebih singkat)."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_WARNA_JUDUL)
    canvas.drawString(1.5 * cm, A4[1] - 1.2 * cm, "Laporan Insight - Internet Desa")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(
        A4[0] - 1.5 * cm, 1.0 * cm, f"Halaman {doc.page}"
    )
    canvas.setStrokeColor(colors.HexColor("#B8C6D6"))
    canvas.setLineWidth(0.5)
    canvas.line(1.5 * cm, A4[1] - 1.4 * cm, A4[0] - 1.5 * cm, A4[1] - 1.4 * cm)
    canvas.restoreState()


def _gambar_header_footer(canvas, doc):
    """Gambar header & footer pada setiap halaman laporan."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_WARNA_JUDUL)
    canvas.drawString(1.5 * cm, A4[1] - 1.2 * cm, JUDUL)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(
        A4[0] - 1.5 * cm, 1.0 * cm, f"Halaman {doc.page}"
    )
    canvas.setStrokeColor(colors.HexColor("#B8C6D6"))
    canvas.setLineWidth(0.5)
    canvas.line(1.5 * cm, A4[1] - 1.4 * cm, A4[0] - 1.5 * cm, A4[1] - 1.4 * cm)
    canvas.restoreState()
