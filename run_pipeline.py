"""
run_pipeline.py - SATU PERINTAH untuk menjalankan seluruh pipeline.

Cara pakai (dari dalam folder pipeline_cuaca_gempa):
    python run_pipeline.py
    python run_pipeline.py --config config/config.json
    python run_pipeline.py --tanpa-simulasi      (lewati simulasi 3 skenario gagal)

Urutan tahap:
  0. Baca config + siapkan log
  1. Akuisisi      : cuaca (Open-Meteo) + gempa (USGS)  [cache / API / sintetis]
  2. Validasi      : JSON -> tabel, cek kolom wajib
  3. Pembersihan   : regex, zona waktu Asia/Jakarta, duplikat, rentang nilai
  4. Penggabungan  : join per jam + filter radius lokasi
  5. Uji assert    : kualitas data gabungan
  6. Penanaman     : anomali sintetis + berkas kunci terpisah
  7. Deteksi       : moving average + k·sigma (tanpa melihat kunci)
  8. Evaluasi      : precision & recall terhadap kunci
  9. Analisis      : statistik per jam + korelasi
 10. Simulasi gagal: 3 skenario
 11. Laporan       : output/laporan_evaluasi.md + tabel CSV
"""

import argparse
import sys
import time

import siapkan_env

siapkan_env.pastikan()   # siapkan venv + library otomatis kalau belum ada

from src import (akuisisi, analisis, detektor, evaluasi, laporan, pembersihan,
                 penanam_anomali, penggabungan, simulasi_gagal, uji_kualitas, validasi)
from src.utils import PipelineError, load_config, path_proyek, setup_logging


def jalankan(path_config, dengan_simulasi=True):
    # ---- 0. Config + log ----
    try:
        cfg = load_config(path_config)
    except PipelineError as e:
        # Log belum bisa ke file (path log ada di config), jadi tulis ke file cadangan
        log = setup_logging("logs/pipeline_error.log")
        log.error(f"Pipeline dihentikan: {e}")
        return 1

    log = setup_logging(cfg["path"]["file_log"])
    mulai = time.time()
    log.info("=" * 70)
    log.info(f"MULAI {cfg['proyek']['nama']} | config: {path_config}")
    log.info("=" * 70)

    try:
        # ---- 1. Akuisisi ----
        log.info("TAHAP 1: Akuisisi data")
        json_cuaca, sumber_cuaca = akuisisi.akuisisi_cuaca(cfg)
        json_gempa, sumber_gempa = akuisisi.akuisisi_gempa(cfg)

        # ---- 2. Validasi skema ----
        log.info("TAHAP 2: Validasi skema")
        df_cuaca = validasi.cuaca_json_ke_dataframe(json_cuaca)
        df_gempa = validasi.gempa_geojson_ke_dataframe(json_gempa)
        validasi.validasi_skema(df_cuaca, cfg["validasi"]["kolom_wajib_cuaca"], "cuaca")
        validasi.validasi_skema(df_gempa, cfg["validasi"]["kolom_wajib_gempa"], "gempa")

        # ---- 3. Pembersihan ----
        log.info("TAHAP 3: Pembersihan (regex + zona waktu)")
        cuaca_bersih = pembersihan.bersihkan_cuaca(df_cuaca, cfg)
        gempa_bersih = pembersihan.bersihkan_gempa(df_gempa, cfg)
        gempa_bersih.to_csv(path_proyek(cfg["path"]["file_gempa_bersih"]), index=False)

        # ---- 4. Penggabungan ----
        log.info("TAHAP 4: Penggabungan waktu + lokasi")
        label = sumber_cuaca if sumber_cuaca == sumber_gempa else f"cuaca={sumber_cuaca};gempa={sumber_gempa}"
        df_gab, info_join = penggabungan.gabungkan(cuaca_bersih, gempa_bersih, label)
        df_gab.to_csv(path_proyek(cfg["path"]["file_data_gabungan"]), index=False)

        # ---- 5. Uji assert ----
        log.info("TAHAP 5: Uji kualitas (assert)")
        hasil_uji = uji_kualitas.jalankan_semua_uji(df_gab, cfg)
        if any(h["status"] == "GAGAL" for h in hasil_uji):
            log.warning("Ada uji kualitas yang GAGAL - analisis tetap dilanjutkan, cek laporan.")

        # ---- 6. Penanaman anomali ----
        log.info("TAHAP 6: Penanaman anomali sintetis")
        penanam_anomali.tanam_anomali(df_gab, cfg)

        # ---- 7. Deteksi (hanya membaca data uji, bukan kunci) ----
        log.info("TAHAP 7: Deteksi lonjakan batas dinamis")
        df_deteksi = detektor.deteksi_lonjakan(path_proyek(cfg["path"]["file_data_uji_anomali"]),
                                               cfg["detektor"], cfg["zona_waktu"])

        # ---- 8. Evaluasi ----
        log.info("TAHAP 8: Evaluasi precision dan recall")
        metrik, deteksi_status, _ = evaluasi.evaluasi_detektor(df_deteksi, cfg)

        # ---- 9. Analisis ----
        log.info("TAHAP 9: Statistik per jam + korelasi")
        stat_jam = analisis.statistik_per_jam(df_gab, df_deteksi)
        korelasi = analisis.uji_korelasi(df_gab, cfg)

        # ---- 10. Simulasi gagal ----
        hasil_sim = None
        if dengan_simulasi and cfg.get("simulasi_gagal", {}).get("aktif", False):
            log.info("TAHAP 10: Simulasi 3 skenario gagal")
            hasil_sim = simulasi_gagal.jalankan_semua_simulasi(cfg, json_cuaca)

        # ---- 11. Laporan ----
        log.info("TAHAP 11: Laporan otomatis")
        ringkasan = {
            "sumber_cuaca": sumber_cuaca, "sumber_gempa": sumber_gempa,
            "baris_cuaca_mentah": len(df_cuaca), "baris_cuaca_bersih": len(cuaca_bersih),
            "baris_gempa_mentah": len(df_gempa), "baris_gempa_bersih": len(gempa_bersih),
            "baris_gabungan": len(df_gab), "kolom_gabungan": len(df_gab.columns),
            "duplikat_timestamp": int(df_gab["waktu_lokal"].duplicated().sum()),
        }
        laporan.buat_laporan(cfg, ringkasan, hasil_uji, info_join, metrik, deteksi_status,
                             stat_jam, korelasi, hasil_sim)

    except PipelineError as e:
        # Kegagalan yang sudah kita antisipasi -> berhenti teratur
        log.error(f"Pipeline dihentikan secara teratur: {type(e).__name__}: {e}")
        return 1
    except FileNotFoundError as e:
        log.error(f"Pipeline dihentikan: file tidak ditemukan: {e}")
        return 1
    except Exception:
        # Kegagalan yang tidak terduga -> tetap dicatat lengkap (traceback) di log
        log.exception("Pipeline berhenti karena error tak terduga")
        return 2

    log.info(f"SELESAI dalam {time.time() - mulai:.1f} detik. Laporan: output/laporan_evaluasi.md")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline otomatis cuaca + gempa")
    parser.add_argument("--config", default="config/config.json", help="path file konfigurasi JSON")
    parser.add_argument("--tanpa-simulasi", action="store_true", help="lewati simulasi skenario gagal")
    args = parser.parse_args()
    sys.exit(jalankan(args.config, dengan_simulasi=not args.tanpa_simulasi))
