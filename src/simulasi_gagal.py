"""
simulasi_gagal.py - TAHAP 10: menguji ketahanan (fault tolerance) pipeline.

Kita SENGAJA membuat 3 jenis kegagalan, lalu memastikan:
  (a) error tertangkap (program tidak crash),
  (b) pesan yang jelas tercatat di file log.

Skenario:
  1. File konfigurasi / file input hilang
  2. Kolom wajib tidak lengkap
  3. Jaringan mati (koneksi ditolak) dan timeout

Semua skenario berjalan pada SALINAN config, jadi data asli tidak tersentuh.
"""

import copy
import socket

import pandas as pd

from src import akuisisi, validasi
from src.utils import AkuisisiError, ConfigError, SkemaError, get_logger, load_config, path_proyek


def _jalankan(nama, fungsi, error_diharapkan):
    """Jalankan satu skenario; catat apakah error tertangani dengan benar."""
    log = get_logger()
    log.info(f"--- SIMULASI: {nama} ---")
    try:
        fungsi()
    except error_diharapkan as e:
        log.error(f"[SIMULASI] {nama} -> TERTANGANI: {type(e).__name__}: {e}")
        return {"skenario": nama, "status": "TERTANGANI", "jenis_error": type(e).__name__, "pesan_log": str(e)}
    except Exception as e:  # error lain yang tidak kita duga
        log.critical(f"[SIMULASI] {nama} -> ERROR TAK TERDUGA: {type(e).__name__}: {e}")
        return {"skenario": nama, "status": "TIDAK TERDUGA", "jenis_error": type(e).__name__, "pesan_log": str(e)}
    log.error(f"[SIMULASI] {nama} -> tidak ada error padahal seharusnya ada!")
    return {"skenario": nama, "status": "TIDAK GAGAL", "jenis_error": "-", "pesan_log": "-"}


def simulasi_config_hilang():
    load_config("config/config_yang_tidak_ada.json")


def simulasi_file_input_hilang(cfg):
    path = path_proyek(cfg["path"]["folder_processed"]) / "file_input_yang_tidak_ada.csv"
    if not path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {path}")
    pd.read_csv(path)


def simulasi_kolom_kurang(cfg, data_cuaca_json):
    rusak = copy.deepcopy(data_cuaca_json)
    rusak["hourly"].pop("pressure_msl", None)        # hapus satu kolom wajib
    df = validasi.cuaca_json_ke_dataframe(rusak)
    validasi.validasi_skema(df, cfg["validasi"]["kolom_wajib_cuaca"], "cuaca (simulasi rusak)")


def _cfg_jaringan_gagal(cfg, url):
    c = copy.deepcopy(cfg)
    s = cfg["simulasi_gagal"]
    c["api"]["open_meteo"]["url"] = url
    c["jaringan"] = {"timeout_detik": s["timeout_detik"], "maks_percobaan": s["maks_percobaan"],
                     "jeda_awal_detik": s["jeda_awal_detik"]}
    c["cache"]["gunakan_cache"] = False              # paksa benar-benar ke jaringan
    c["fallback_sintetis"]["aktif"] = False          # tanpa cadangan -> harus error rapi
    c["path"]["folder_raw"] = "data/raw/_simulasi"   # jangan timpa cache asli
    return c


class ServerDiam:
    """Server lokal yang menerima koneksi tetapi TIDAK PERNAH menjawab.

    Dipakai untuk mensimulasikan API yang lambat/hang sehingga request
    pasti terkena TIMEOUT. Bekerja tanpa internet (hanya di 127.0.0.1).
    """

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))   # port 0 = pilih port kosong otomatis
        self.sock.listen(5)                # koneksi diterima sistem, tapi tidak dibalas
        self.url = f"http://127.0.0.1:{self.sock.getsockname()[1]}/lambat"
        return self

    def __exit__(self, *args):
        self.sock.close()


def simulasi_timeout(cfg):
    with ServerDiam() as server:
        akuisisi.akuisisi_cuaca(_cfg_jaringan_gagal(cfg, server.url))


def jalankan_semua_simulasi(cfg, data_cuaca_json):
    s = cfg["simulasi_gagal"]
    hasil = [
        _jalankan("1a. File konfigurasi hilang", simulasi_config_hilang, ConfigError),
        _jalankan("1b. File input data hilang", lambda: simulasi_file_input_hilang(cfg), FileNotFoundError),
        _jalankan("2. Kolom wajib tidak lengkap", lambda: simulasi_kolom_kurang(cfg, data_cuaca_json), SkemaError),
        _jalankan("3a. Jaringan mati (koneksi ditolak)",
                  lambda: akuisisi.akuisisi_cuaca(_cfg_jaringan_gagal(cfg, s["url_jaringan_mati"])), AkuisisiError),
        _jalankan("3b. Server tidak menjawab (timeout)", lambda: simulasi_timeout(cfg), AkuisisiError),
    ]
    get_logger().info(f"Ringkasan simulasi: {sum(h['status'] == 'TERTANGANI' for h in hasil)}/{len(hasil)} "
                      f"skenario gagal tertangani tanpa crash")
    return pd.DataFrame(hasil)
