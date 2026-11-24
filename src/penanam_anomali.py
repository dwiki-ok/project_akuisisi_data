"""
penanam_anomali.py - TAHAP 6: menanam anomali sintetis + membuat BERKAS KUNCI.

Tujuannya: kita perlu "kunci jawaban" untuk mengukur seberapa bagus detektor.
Caranya:
1. Salin data gabungan.
2. Pilih beberapa jam secara acak (seed tetap -> hasil selalu sama).
3. Tambahkan lonjakan (naik atau turun) sebesar 3-8 kali simpangan baku kolom.
4. Simpan data yang sudah ditanami ke data/processed/data_uji_anomali.csv
   -> INI yang dibaca detektor.
5. Simpan daftar jam + kolom yang ditanami ke data/kunci/kunci_anomali.csv
   -> INI kunci jawaban. Detektor TIDAK BOLEH membacanya
      (diperiksa otomatis oleh tests/test_kualitas.py).
"""

import numpy as np
import pandas as pd

from src.utils import get_logger, path_proyek


def tanam_anomali(df, cfg):
    """Kembalikan (df_dengan_anomali, df_kunci) dan simpan keduanya ke file."""
    log = get_logger()
    p = cfg["penanaman_anomali"]
    rng = np.random.default_rng(p["seed"])
    df_uji = df.copy()
    kunci = []

    for kolom in p["kolom"]:
        sigma = df[kolom].std()
        # Hindari 48 jam pertama (detektor butuh jendela riwayat) dan jaga jarak
        # antar anomali >= 48 jam supaya satu lonjakan tidak menutupi yang lain.
        kandidat = np.arange(48, len(df_uji) - 1)
        dipilih = []
        while len(dipilih) < p["jumlah_per_kolom"] and len(kandidat):
            i = int(rng.choice(kandidat))
            dipilih.append(i)
            kandidat = kandidat[np.abs(kandidat - i) >= 48]

        for i in sorted(dipilih):
            besar = rng.uniform(p["besar_min_sigma"], p["besar_maks_sigma"])
            arah = rng.choice([-1, 1])
            asli = df_uji.at[i, kolom]
            baru = asli + arah * besar * sigma
            # Kelembapan dsb. tidak boleh keluar batas fisis -> cukup dibalik arahnya
            bawah, atas = cfg["validasi"]["rentang_nilai"].get(kolom, (-np.inf, np.inf))
            if not (bawah <= baru <= atas):
                baru = asli - arah * besar * sigma
            df_uji.at[i, kolom] = round(baru, 2)
            kunci.append({"waktu_lokal": df_uji.at[i, "waktu_lokal"], "kolom": kolom,
                          "nilai_asli": asli, "nilai_ditanam": round(baru, 2),
                          "besar_sigma": round(besar, 2)})

    df_kunci = pd.DataFrame(kunci).sort_values("waktu_lokal").reset_index(drop=True)

    path_kunci = path_proyek(cfg["path"]["file_kunci_anomali"])
    path_kunci.parent.mkdir(parents=True, exist_ok=True)
    df_kunci.to_csv(path_kunci, index=False)
    path_uji = path_proyek(cfg["path"]["file_data_uji_anomali"])
    df_uji.to_csv(path_uji, index=False)
    log.info(f"Penanaman: {len(df_kunci)} anomali sintetis ditanam pada {p['kolom']}")
    log.info(f"Penanaman: berkas kunci -> {path_kunci} (terisolasi dari detektor)")
    log.info(f"Penanaman: data uji -> {path_uji}")
    return df_uji, df_kunci
