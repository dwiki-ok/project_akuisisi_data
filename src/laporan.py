"""
laporan.py - TAHAP 11: membuat laporan evaluasi otomatis.

Keluaran di folder output/:
- tabel_anomali.csv          : semua lonjakan yang ditemukan detektor (+ status TP/FP)
- metrik_detektor.csv        : precision, recall, F1
- statistik_per_jam.csv      : ringkasan per jam 00-23 WIB
- korelasi.csv               : hasil uji korelasi harian
- hasil_uji_assert.csv       : hasil uji kualitas data
- hasil_simulasi_gagal.csv   : hasil 3 skenario gagal
- laporan_evaluasi.md        : laporan lengkap yang bisa dibaca manusia
"""

from datetime import datetime

import pandas as pd

from src.utils import get_logger, path_proyek


def tabel_md(df, desimal=3):
    """Ubah DataFrame menjadi tabel Markdown (tanpa library tambahan)."""
    df = df.copy()
    for k in df.columns:
        if pd.api.types.is_float_dtype(df[k]):
            df[k] = df[k].round(desimal)
    kepala = "| " + " | ".join(map(str, df.columns)) + " |"
    garis = "|" + "|".join("---" for _ in df.columns) + "|"
    isi = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in baris) + " |"
           for baris in df.itertuples(index=False)]
    return "\n".join([kepala, garis] + isi)


BATASAN_KORELASI = """\
1. **Korelasi bukan sebab-akibat.** Angka r hanya menunjukkan dua variabel naik/turun
   bersamaan, bukan bahwa cuaca menyebabkan gempa (atau sebaliknya).
2. **Batasan fisis.** Gempa tektonik dipicu oleh akumulasi tegangan lempeng di kedalaman
   puluhan kilometer selama bertahun-tahun. Perubahan tekanan udara harian (beberapa hPa)
   sangat kecil dibanding tegangan tersebut, sehingga hubungan kuat memang tidak diharapkan.
3. **Data cuaca satu titik.** Cuaca diambil di titik pusat wilayah, sedangkan gempa tersebar
   dalam radius ratusan km dan sebagian besar terjadi di laut.
4. **Gempa jarang (data didominasi nol).** Banyak hari tanpa gempa; Pearson sensitif terhadap
   pencilan (satu hari dengan gempa susulan beruntun), karena itu Spearman juga dilaporkan.
5. **Autokorelasi.** Data harian berurutan tidak saling bebas (cuaca hari ini mirip kemarin,
   gempa susulan berkelompok), sehingga p-value cenderung terlalu optimis.
6. **Uji berganda.** Beberapa pasangan diuji sekaligus; dengan ambang 5%, kira-kira 1 dari 20
   pasangan bisa tampak "signifikan" secara kebetulan.
7. **p-value perkiraan.** Dihitung dengan pendekatan normal (tanpa scipy), cukup untuk n > 30.
8. **Satu tahun pengamatan** belum mewakili variasi musiman jangka panjang.
"""


def buat_laporan(cfg, ringkasan, hasil_uji, info_join, metrik, df_deteksi_status,
                 stat_jam, korelasi, hasil_simulasi):
    log = get_logger()
    out = path_proyek(cfg["path"]["folder_output"])
    out.mkdir(parents=True, exist_ok=True)

    # ---- Simpan tabel-tabel CSV ----
    df_deteksi_status.to_csv(out / "tabel_anomali.csv", index=False)
    metrik.to_csv(out / "metrik_detektor.csv", index=False)
    stat_jam.to_csv(out / "statistik_per_jam.csv", index=False)
    korelasi.to_csv(out / "korelasi.csv", index=False)
    pd.DataFrame(hasil_uji).to_csv(out / "hasil_uji_assert.csv", index=False)
    if hasil_simulasi is not None:
        hasil_simulasi.to_csv(out / "hasil_simulasi_gagal.csv", index=False)

    # ---- Susun laporan Markdown ----
    sumber = ringkasan["sumber_cuaca"], ringkasan["sumber_gempa"]
    peringatan = ""
    if "SINTETIS" in sumber:
        peringatan = ("> **PERINGATAN: sebagian/seluruh data pada laporan ini adalah DATA SINTETIS** "
                      "(API tidak dapat dihubungi dan belum ada cache). Angka di bawah hanya "
                      "membuktikan pipeline berjalan benar, BUKAN hasil penelitian. Jalankan ulang "
                      "dengan koneksi internet untuk memakai data asli Open-Meteo dan USGS.\n")

    tot = metrik.iloc[-1]
    jam_top = stat_jam.sort_values("lonjakan_terdeteksi", ascending=False).head(3)
    jam_gempa = stat_jam.sort_values("gempa_total", ascending=False).head(3)
    lulus = sum(h["status"] == "LULUS" for h in hasil_uji)
    w, p, d = cfg["wilayah"], cfg["periode"], cfg["detektor"]

    teks = f"""# Laporan Evaluasi Pipeline Cuaca dan Gempa

{cfg['proyek']['kelompok']}
Dibuat otomatis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{peringatan}
## 1. Ringkasan data

| Item | Nilai |
|---|---|
| Wilayah | {w['nama']} (pusat {w['lat_pusat']}, {w['lon_pusat']}; radius {w['radius_km']} km) |
| Periode | {p['tanggal_mulai']} s.d. {p['tanggal_selesai']} (zona waktu {cfg['zona_waktu']}) |
| Sumber cuaca | Open-Meteo, label: **{sumber[0]}** |
| Sumber gempa | USGS GeoJSON, label: **{sumber[1]}** |
| Baris cuaca mentah / bersih | {ringkasan['baris_cuaca_mentah']:,} / {ringkasan['baris_cuaca_bersih']:,} |
| Kejadian gempa mentah / bersih | {ringkasan['baris_gempa_mentah']:,} / {ringkasan['baris_gempa_bersih']:,} |
| Baris data gabungan | **{ringkasan['baris_gabungan']:,}** (target minimal {cfg['validasi']['min_baris']:,}) |
| Jumlah kolom data gabungan | {ringkasan['kolom_gabungan']} |
| Duplikat timestamp kunci | {ringkasan['duplikat_timestamp']} |

### Sumber data dan lisensi

- Cuaca: **Open-Meteo Historical Weather API** (https://open-meteo.com), lisensi CC BY 4.0, gratis untuk penggunaan non-komersial. *Weather data by Open-Meteo.com.*
- Gempa: **USGS Earthquake Catalog (FDSN Event API)** (https://earthquake.usgs.gov), domain publik. *Earthquake data from USGS.*
- Arti label sumber: `API` = baru diunduh, `CACHE` = dibaca dari unduhan sebelumnya di `data/raw/`, `SINTETIS` = data palsu cadangan (BUKAN data asli).

## 2. Akurasi penyelarasan (join) waktu dan lokasi

Gempa disaring dengan jarak haversine <= {w['radius_km']} km dari titik pusat, lalu waktu
gempa dibulatkan ke jam (floor) dan dicocokkan ke jam cuaca dalam zona {cfg['zona_waktu']}.

| Item | Nilai |
|---|---|
| Gempa bersih | {info_join['jumlah_gempa_bersih']} |
| Gempa berhasil dipasangkan ke jam cuaca | {info_join['gempa_berhasil_dipasangkan']} ({info_join['persen_gempa_dipasangkan']}%) |
| Jam yang memiliki gempa | {info_join['jam_dengan_gempa']} dari {info_join['jumlah_jam_cuaca']:,} jam |
| Selisih waktu maksimum gempa ke jam acuan | {info_join['selisih_waktu_maks_menit']} menit (selalu < 60 karena floor) |

## 3. Uji kualitas otomatis (assert): {lulus}/{len(hasil_uji)} lulus

{tabel_md(pd.DataFrame(hasil_uji))}

## 4. Statistik per jam (WIB)

{tabel_md(stat_jam, 2)}

**Jam dengan lonjakan terdeteksi terbanyak:** {', '.join(f"{int(r.jam):02d}:00 ({int(r.lonjakan_terdeteksi)} lonjakan)" for r in jam_top.itertuples())}.

**Jam dengan gempa terbanyak:** {', '.join(f"{int(r.jam):02d}:00 ({int(r.gempa_total)} gempa)" for r in jam_gempa.itertuples())}.

## 5. Kinerja detektor lonjakan (moving average + k·sigma)

Aturan: jendela {d['jendela_jam']} jam sebelumnya, k = {d['k_sigma']}, toleransi waktu evaluasi
{cfg['evaluasi']['toleransi_jam']} jam. Kunci anomali dibaca hanya oleh modul evaluasi,
tidak oleh detektor.

{tabel_md(metrik)}

- **Precision {tot['precision']:.1%}**: dari {int(tot['terdeteksi'])} alarm, {int(tot['TP'])} benar-benar anomali tertanam.
- **Recall {tot['recall']:.1%}**: dari {int(tot['anomali_di_kunci'])} anomali tertanam, {int(tot['anomali_di_kunci'] - tot['FN'])} tertangkap.
- Anomali yang terlewat (FN) umumnya yang berukuran kecil (mendekati {cfg['penanaman_anomali']['besar_min_sigma']}σ)
  dan kebetulan searah dengan pola harian, sehingga tidak keluar dari batas {d['k_sigma']}σ.

## 6. Uji korelasi cuaca vs gempa (agregasi harian)

{tabel_md(korelasi, 4)}

### Batasan uji korelasi

{BATASAN_KORELASI}
## 7. Simulasi 3 skenario gagal

{tabel_md(hasil_simulasi) if hasil_simulasi is not None else "_Simulasi dinonaktifkan di config._"}

Semua pesan di atas juga tercatat di `{cfg['path']['file_log']}`.

## 8. Berkas keluaran

- `output/tabel_anomali.csv`, `output/metrik_detektor.csv`, `output/statistik_per_jam.csv`
- `output/korelasi.csv`, `output/hasil_uji_assert.csv`, `output/hasil_simulasi_gagal.csv`
- `{cfg['path']['file_data_gabungan']}` (data gabungan bersih)
- `{cfg['path']['file_kunci_anomali']}` (berkas kunci anomali, terpisah)
- `{cfg['path']['file_log']}` (log eksekusi)
"""
    path_md = out / "laporan_evaluasi.md"
    path_md.write_text(teks, encoding="utf-8")
    log.info(f"Laporan evaluasi ditulis ke {path_md}")
    return path_md
