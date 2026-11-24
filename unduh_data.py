"""
unduh_data.py - Mengunduh DATA ASLI (Open-Meteo + USGS) dan menyimpannya ke data/raw/.

Jalankan SEBELUM run_pipeline.py kalau ingin memastikan datanya benar-benar asli:
    python unduh_data.py

Beda dengan run_pipeline.py: skrip ini TIDAK memakai data sintetis sebagai cadangan.
Kalau internet bermasalah, skrip ini berhenti dan menjelaskan kenapa, sehingga
kalian tidak tertukar antara data asli dan data palsu.

Atribusi (wajib dicantumkan di laporan):
- Weather data by Open-Meteo.com (lisensi CC BY 4.0, https://open-meteo.com)
- Earthquake data from USGS (domain publik, https://earthquake.usgs.gov)
"""

import copy
import sys

import siapkan_env

siapkan_env.pastikan()   # siapkan venv + library otomatis kalau belum ada

from src import akuisisi
from src.utils import PipelineError, load_config, path_proyek, setup_logging


def main():
    try:
        cfg = load_config("config/config.json")
    except PipelineError as e:
        print(f"GAGAL membaca config: {e}")
        return 1

    log = setup_logging("logs/unduh_data.log")
    cfg = copy.deepcopy(cfg)
    cfg["fallback_sintetis"]["aktif"] = False   # JANGAN pernah pakai data palsu di sini

    log.info("Mengunduh data asli. Kalau sudah ada cache, file cache dipakai (hapus file di data/raw/ untuk unduh ulang).")
    try:
        cuaca, s1 = akuisisi.akuisisi_cuaca(cfg)
        gempa, s2 = akuisisi.akuisisi_gempa(cfg)
    except PipelineError as e:
        log.error(f"UNDUH GAGAL: {e}")
        log.error("Cek: (1) laptop terhubung internet, (2) buka https://open-meteo.com dan "
                  "https://earthquake.usgs.gov di browser, (3) coba lagi beberapa menit kemudian.")
        return 1

    n_cuaca = len(cuaca["hourly"]["time"])
    n_gempa = len(gempa["features"])
    log.info("=" * 60)
    log.info(f"Cuaca : {n_cuaca:,} jam      (sumber: {s1})")
    log.info(f"Gempa : {n_gempa:,} kejadian (sumber: {s2})")
    log.info(f"File tersimpan di: {path_proyek(cfg['path']['folder_raw'])}")
    if n_gempa < 30:
        log.warning("Gempa sangat sedikit. Perbesar wilayah.radius_km atau perpanjang periode di config.json.")
    log.info("Data asli siap. Lanjutkan dengan: python run_pipeline.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
