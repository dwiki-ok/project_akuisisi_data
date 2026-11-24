"""
utils.py - Fungsi bantu yang dipakai semua tahap pipeline.

Isinya:
1. Kelas error khusus (supaya pesan kegagalan jelas dan bisa ditangkap rapi).
2. load_config()  -> membaca file konfigurasi JSON.
3. setup_logging() -> menyiapkan pencatatan log ke file + layar.
4. path_proyek()  -> mengubah path relatif di config menjadi path lengkap.
"""

import json
import logging
import os
from pathlib import Path

# Folder akar proyek = satu tingkat di atas folder src/
AKAR_PROYEK = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Error khusus
# ---------------------------------------------------------------------------
class PipelineError(Exception):
    """Induk semua error pipeline. Kalau ini muncul, pipeline berhenti teratur."""


class ConfigError(PipelineError):
    """File konfigurasi hilang atau isinya rusak."""


class AkuisisiError(PipelineError):
    """Data gagal diambil (jaringan mati, timeout, API error) dan tidak ada cadangan."""


class SkemaError(PipelineError):
    """Kolom wajib tidak lengkap atau struktur data berubah."""


# ---------------------------------------------------------------------------
# 2. Membaca konfigurasi
# ---------------------------------------------------------------------------
def load_config(path_config):
    """Baca file config JSON dan kembalikan sebagai dictionary Python.

    Jika file tidak ada atau formatnya salah, kita lempar ConfigError
    dengan pesan yang menyebut path yang dicari, supaya mudah diperbaiki.
    """
    path_config = Path(path_config)
    if not path_config.is_absolute():
        path_config = AKAR_PROYEK / path_config

    # Pemeriksaan keberadaan berkas (rencana cadangan risiko no. 2 di proposal)
    if not path_config.exists():
        raise ConfigError(f"File konfigurasi tidak ditemukan: {path_config}")

    try:
        with open(path_config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Format JSON pada {path_config} rusak: {e}") from e

    # Cek bagian-bagian penting ada di config
    bagian_wajib = ["wilayah", "periode", "zona_waktu", "api", "jaringan", "path",
                    "validasi", "penanaman_anomali", "detektor"]
    hilang = [b for b in bagian_wajib if b not in cfg]
    if hilang:
        raise ConfigError(f"Bagian config berikut tidak ada di {path_config}: {hilang}")
    return cfg


def path_proyek(path_relatif):
    """Ubah path relatif dari config (mis. 'data/raw') menjadi path absolut."""
    p = Path(path_relatif)
    return p if p.is_absolute() else AKAR_PROYEK / p


# ---------------------------------------------------------------------------
# 3. Logging
# ---------------------------------------------------------------------------
def setup_logging(path_log, level=logging.INFO):
    """Siapkan logger bernama 'pipeline' yang menulis ke file DAN ke layar.

    Format setiap baris log:  2024-11-24 20:00:00 | INFO | akuisisi | pesan
    """
    path_log = path_proyek(path_log)
    os.makedirs(path_log.parent, exist_ok=True)

    logger = logging.getLogger("pipeline")
    logger.setLevel(level)
    logger.handlers.clear()  # cegah log dobel kalau fungsi dipanggil ulang

    format_log = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(module)-15s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # mode="w" -> file log ditimpa setiap pipeline dijalankan ulang
    handler_file = logging.FileHandler(path_log, mode="w", encoding="utf-8")
    handler_file.setFormatter(format_log)
    logger.addHandler(handler_file)

    handler_layar = logging.StreamHandler()
    handler_layar.setFormatter(format_log)
    logger.addHandler(handler_layar)
    return logger


def get_logger():
    """Ambil logger 'pipeline' yang sudah disiapkan setup_logging()."""
    return logging.getLogger("pipeline")
