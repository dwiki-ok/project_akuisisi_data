"""
analisis.py - TAHAP 9: statistik per jam dan uji korelasi.

1. statistik_per_jam(): untuk tiap jam dalam sehari (00-23 WIB) hitung
   rata-rata/simpangan baku cuaca, jumlah gempa, dan jumlah lonjakan terdeteksi.
2. uji_korelasi(): agregasi data ke HARIAN, lalu hitung korelasi Pearson
   (hubungan linear) dan Spearman (hubungan berurutan/monoton) antara
   variabel cuaca dan aktivitas gempa, beserta p-value perkiraan.

Kenapa harian? Gempa per jam hampir selalu 0, sehingga korelasi per jam
akan sangat lemah dan menyesatkan. Agregasi harian membuat datanya lebih padat.
"""

import math

import numpy as np
import pandas as pd

from src.utils import get_logger


def statistik_per_jam(df, df_deteksi):
    """Ringkasan per jam (0-23 WIB)."""
    d = df.copy()
    d["jam"] = d["waktu_lokal"].dt.hour
    stat = d.groupby("jam").agg(
        suhu_rata=("temperature_2m", "mean"),
        suhu_std=("temperature_2m", "std"),
        kelembapan_rata=("relative_humidity_2m", "mean"),
        tekanan_rata=("pressure_msl", "mean"),
        tekanan_std=("pressure_msl", "std"),
        hujan_rata_mm=("precipitation", "mean"),
        gempa_total=("gempa_jumlah", "sum"),
        gempa_mag_rata=("gempa_mag_rata", "mean"),
    ).round(3)
    lonjakan = df_deteksi.groupby("jam").size() if len(df_deteksi) else pd.Series(dtype=int)
    stat["lonjakan_terdeteksi"] = lonjakan.reindex(stat.index, fill_value=0).astype(int)
    return stat.reset_index()


def _pearson(x, y):
    """Koefisien korelasi Pearson r."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _p_value(r, n):
    """p-value dua sisi PERKIRAAN (pendekatan normal untuk statistik t).

    Cukup akurat untuk n besar (n > 30). Tidak memakai scipy agar
    dependensi proyek tetap sedikit.
    """
    if n < 4 or math.isnan(r) or abs(r) >= 1:
        return float("nan")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return math.erfc(abs(t) / math.sqrt(2))


def data_harian(df):
    """Agregasi data per jam menjadi per hari (tanggal WIB)."""
    d = df.copy()
    d["tanggal"] = d["waktu_lokal"].dt.date
    h = d.groupby("tanggal").agg(
        temperature_2m=("temperature_2m", "mean"),
        pressure_msl=("pressure_msl", "mean"),
        precipitation=("precipitation", "sum"),
        gempa_jumlah=("gempa_jumlah", "sum"),
        gempa_mag_maks=("gempa_mag_maks", "max"),
    )
    # Perubahan tekanan dari hari sebelumnya (hPa)
    h["delta_tekanan"] = h["pressure_msl"].diff()
    return h


def uji_korelasi(df, cfg):
    """Hitung korelasi untuk pasangan variabel di config."""
    log = get_logger()
    h = data_harian(df)
    hasil = []
    for a, b in cfg["korelasi"]["pasangan"]:
        pas = h[[a, b]].dropna()
        n = len(pas)
        r_p = _pearson(pas[a], pas[b])
        r_s = _pearson(pas[a].rank(), pas[b].rank())   # Spearman = Pearson pada peringkat
        p = _p_value(r_p, n)
        kekuatan = ("sangat lemah" if abs(r_p) < 0.1 else "lemah" if abs(r_p) < 0.3
                    else "sedang" if abs(r_p) < 0.5 else "kuat")
        hasil.append({"variabel_x": a, "variabel_y": b, "n_hari": n,
                      "pearson_r": round(r_p, 4), "spearman_rho": round(r_s, 4),
                      "p_value_perkiraan": round(p, 4), "signifikan_5persen": bool(p < 0.05),
                      "kekuatan": kekuatan})
        log.info(f"Korelasi {a} vs {b}: r={r_p:.3f}, rho={r_s:.3f}, p~{p:.3f} ({kekuatan})")
    return pd.DataFrame(hasil)
