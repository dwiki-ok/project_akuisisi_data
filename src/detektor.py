"""
detektor.py - TAHAP 7: mendeteksi lonjakan dengan BATAS DINAMIS.

Aturan (moving average + k·sigma):
    rata2_t  = rata-rata  N jam SEBELUM jam t
    sigma_t  = simpangan baku N jam SEBELUM jam t
    batas atas  = rata2_t + k * sigma_t
    batas bawah = rata2_t - k * sigma_t
    Jika nilai jam t keluar dari batas -> ditandai LONJAKAN.

Disebut "dinamis" karena batasnya ikut bergeser mengikuti data terbaru,
tidak satu angka tetap untuk sepanjang tahun.

ATURAN PENTING: modul ini hanya membaca data uji (path dari argumen).
Modul ini TIDAK mengenal dan TIDAK membuka berkas kunci anomali.
"""

import pandas as pd

from src.utils import get_logger


def hitung_batas_dinamis(seri, jendela, k):
    """Hitung rata-rata bergerak, sigma bergerak, batas atas/bawah untuk satu kolom.

    shift(1) -> jam t sendiri tidak ikut dihitung, jadi lonjakan tidak
    'menyamarkan' dirinya sendiri dengan menaikkan rata-rata/sigma.
    """
    riwayat = seri.shift(1).rolling(window=jendela, min_periods=jendela)
    rata2 = riwayat.mean()
    sigma = riwayat.std()
    return rata2, sigma, rata2 + k * sigma, rata2 - k * sigma


def deteksi_lonjakan(path_data_uji, cfg_detektor, zona_waktu):
    """Baca data uji dari CSV, deteksi lonjakan, kembalikan tabel kejadian anomali."""
    log = get_logger()
    df = pd.read_csv(path_data_uji)
    df["waktu_lokal"] = pd.to_datetime(df["waktu_lokal"], utc=True).dt.tz_convert(zona_waktu)

    jendela, k = cfg_detektor["jendela_jam"], cfg_detektor["k_sigma"]
    temuan = []
    for kolom in cfg_detektor["kolom"]:
        rata2, sigma, atas, bawah = hitung_batas_dinamis(df[kolom], jendela, k)
        lonjak = (df[kolom] > atas) | (df[kolom] < bawah)
        for i in df.index[lonjak.fillna(False)]:
            temuan.append({
                "waktu_lokal": df.at[i, "waktu_lokal"],
                "jam": df.at[i, "waktu_lokal"].hour,
                "kolom": kolom,
                "nilai": df.at[i, kolom],
                "rata2_bergerak": round(rata2[i], 2),
                "sigma_bergerak": round(sigma[i], 3),
                "batas_bawah": round(bawah[i], 2),
                "batas_atas": round(atas[i], 2),
                "skor_z": round((df.at[i, kolom] - rata2[i]) / sigma[i], 2) if sigma[i] else None,
                "arah": "NAIK" if df.at[i, kolom] > atas[i] else "TURUN",
            })
        log.info(f"Detektor [{kolom}]: jendela={jendela} jam, k={k} -> {int(lonjak.sum())} lonjakan")

    kolom_hasil = ["waktu_lokal", "jam", "kolom", "nilai", "rata2_bergerak", "sigma_bergerak",
                   "batas_bawah", "batas_atas", "skor_z", "arah"]
    return pd.DataFrame(temuan, columns=kolom_hasil).sort_values("waktu_lokal").reset_index(drop=True)
