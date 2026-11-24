"""
penggabungan.py - TAHAP 4: menggabungkan cuaca dan gempa menurut WAKTU dan LOKASI.

Cara menggabungkan:
- LOKASI : gempa sudah disaring hanya yang berada dalam radius wilayah
           (lihat pembersihan.py), cuaca diambil di titik pusat wilayah.
- WAKTU  : waktu gempa dibulatkan ke bawah ke jam terdekat (floor),
           mis. 14:37 WIB -> 14:00 WIB, lalu dicocokkan dengan jam cuaca.
           Beberapa gempa di jam yang sama digabung (jumlah, magnitudo maks, dst.).

Hasilnya: SATU baris per jam (kunci = waktu_lokal), berisi cuaca + ringkasan gempa.
Jam tanpa gempa tetap ada dengan gempa_jumlah = 0.
"""

import pandas as pd

from src.utils import get_logger


def gabungkan(df_cuaca, df_gempa, label_sumber):
    """Left join cuaca (per jam) dengan ringkasan gempa per jam.

    Mengembalikan (df_gabungan, info_join) di mana info_join berisi angka
    akurasi penyelarasan untuk laporan (pertanyaan eksplorasi no. 1).
    """
    log = get_logger()
    g = df_gempa.copy()
    g["waktu_lokal"] = g["waktu_lokal"].dt.floor("h")      # bulatkan ke jam

    ringkas = g.groupby("waktu_lokal").agg(
        gempa_jumlah=("id", "count"),
        gempa_mag_maks=("mag", "max"),
        gempa_mag_rata=("mag", "mean"),
        gempa_kedalaman_rata=("depth", "mean"),
        gempa_jarak_min_km=("jarak_ke_pusat_km", "min"),
    ).reset_index()

    df = df_cuaca.merge(ringkas, on="waktu_lokal", how="left", validate="one_to_one")
    df["gempa_jumlah"] = df["gempa_jumlah"].fillna(0).astype(int)
    df["sumber_data"] = label_sumber

    # --- Ukuran akurasi penyelarasan ---
    cocok = int(df["gempa_jumlah"].sum())
    total = len(df_gempa)
    info_join = {
        "jumlah_jam_cuaca": len(df_cuaca),
        "jumlah_gempa_bersih": total,
        "gempa_berhasil_dipasangkan": cocok,
        "persen_gempa_dipasangkan": round(100 * cocok / total, 2) if total else 0.0,
        "jam_dengan_gempa": int((df["gempa_jumlah"] > 0).sum()),
        "selisih_waktu_maks_menit": round(
            ((df_gempa["waktu_lokal"] - df_gempa["waktu_lokal"].dt.floor("h"))
             .dt.total_seconds().max() or 0) / 60, 1),
    }
    log.info(f"Penggabungan: {len(df):,} baris; {cocok}/{total} gempa dipasangkan "
             f"({info_join['persen_gempa_dipasangkan']}%) ke {info_join['jam_dengan_gempa']} jam")
    if cocok < total:
        log.warning(f"Penggabungan: {total - cocok} gempa tidak punya pasangan jam cuaca "
                    f"(kemungkinan di luar rentang tanggal)")
    return df, info_join
