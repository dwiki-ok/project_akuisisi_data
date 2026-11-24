"""
akuisisi.py - TAHAP 1: mengambil data mentah dari internet.

Sumber:
- Open-Meteo Archive API  -> cuaca per jam (format JSON)
- USGS FDSN Event API     -> katalog gempa (format GeoJSON)

Fitur ketahanan (sesuai proposal bagian "Risiko dan cadangan"):
1. timeout     : request tidak boleh menggantung selamanya.
2. try-except  : semua error jaringan ditangkap, dicatat di log.
3. retry       : dicoba ulang beberapa kali dengan jeda bertahap (2s, 4s, 8s ...).
4. cache       : JSON mentah yang berhasil diunduh disimpan di data/raw/,
                 sehingga pipeline bisa dijalankan ulang secara OFFLINE.
5. fallback    : kalau API gagal dan cache belum ada, pakai data SINTETIS
                 (diberi label jelas) agar pipeline tetap bisa diuji.
"""

import json
import time

import requests

from src import data_sintetis
from src.utils import AkuisisiError, get_logger, path_proyek


# ---------------------------------------------------------------------------
# Fungsi inti: GET dengan timeout + retry
# ---------------------------------------------------------------------------
def ambil_json_dengan_retry(url, params, timeout, maks_percobaan, jeda_awal, nama_sumber="API"):
    """Kirim HTTP GET dan kembalikan isi JSON. Dicoba ulang jika gagal.

    Jeda antar percobaan naik dua kali lipat (exponential backoff):
    percobaan 1 gagal -> tunggu jeda_awal, percobaan 2 gagal -> tunggu 2x, dst.
    Melempar AkuisisiError jika semua percobaan gagal.
    """
    log = get_logger()
    error_terakhir = None

    for percobaan in range(1, maks_percobaan + 1):
        try:
            log.info(f"[{nama_sumber}] Percobaan {percobaan}/{maks_percobaan}: GET {url}")
            resp = requests.get(url, params=params, timeout=timeout)

            # 429 = rate limit, 5xx = server sedang bermasalah -> layak dicoba ulang
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code} (server sibuk / rate limit)")
            # 4xx lain = permintaan kita salah (parameter keliru) -> percuma diulang
            if resp.status_code >= 400:
                raise AkuisisiError(f"[{nama_sumber}] HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            log.info(f"[{nama_sumber}] Berhasil (HTTP {resp.status_code}, {len(resp.content):,} byte)")
            return data

        except requests.Timeout as e:
            error_terakhir = e
            log.warning(f"[{nama_sumber}] TIMEOUT: tidak ada respons dalam {timeout} detik")
        except requests.ConnectionError as e:
            error_terakhir = e
            log.warning(f"[{nama_sumber}] KONEKSI GAGAL (jaringan mati / host tidak terjangkau): "
                        f"{type(e).__name__}")
        except requests.HTTPError as e:
            error_terakhir = e
            log.warning(f"[{nama_sumber}] {e}")
        except ValueError as e:  # respons bukan JSON yang sah
            error_terakhir = e
            log.warning(f"[{nama_sumber}] Respons bukan JSON yang valid: {e}")

        if percobaan < maks_percobaan:
            jeda = jeda_awal * (2 ** (percobaan - 1))
            log.info(f"[{nama_sumber}] Menunggu {jeda:.1f} detik sebelum mencoba lagi...")
            time.sleep(jeda)

    raise AkuisisiError(f"[{nama_sumber}] Gagal setelah {maks_percobaan} percobaan. "
                        f"Error terakhir: {type(error_terakhir).__name__}: {error_terakhir}")


# ---------------------------------------------------------------------------
# Cache JSON mentah
# ---------------------------------------------------------------------------
def _path_cache(cfg, nama):
    p = cfg["periode"]
    return path_proyek(cfg["path"]["folder_raw"]) / f"{nama}_{p['tanggal_mulai']}_{p['tanggal_selesai']}.json"


def _simpan_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _baca_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ambil_dengan_cadangan(cfg, nama_cache, fungsi_api, fungsi_sintetis, nama_sumber):
    """Pola umum: CACHE -> API (+simpan cache) -> SINTETIS -> error.

    Mengembalikan (data_json, label_sumber) dengan label "CACHE", "API", atau "SINTETIS".
    """
    log = get_logger()
    path_cache = _path_cache(cfg, nama_cache)

    # 1) Pakai cache kalau ada (pipeline bisa jalan offline & hasil sama persis)
    if cfg["cache"]["gunakan_cache"] and path_cache.exists():
        log.info(f"[{nama_sumber}] Memakai cache lokal: {path_cache}")
        return _baca_json(path_cache), "CACHE"

    # 2) Ambil dari API
    try:
        data = fungsi_api()
        _simpan_json(data, path_cache)
        log.info(f"[{nama_sumber}] JSON mentah disimpan ke cache: {path_cache}")
        return data, "API"
    except AkuisisiError as e:
        log.error(f"[{nama_sumber}] Akuisisi API gagal: {e}")

    # 3) Cadangan terakhir: data sintetis berlabel
    if cfg.get("fallback_sintetis", {}).get("aktif", False):
        log.warning(f"[{nama_sumber}] MEMAKAI DATA SINTETIS (bukan data asli) sebagai cadangan!")
        data = fungsi_sintetis(cfg)
        _simpan_json(data, path_proyek(cfg["path"]["folder_raw"]) / f"{nama_cache}_SINTETIS.json")
        return data, "SINTETIS"

    raise AkuisisiError(f"[{nama_sumber}] Tidak ada data: API gagal, cache tidak ada, "
                        f"fallback sintetis nonaktif.")


# ---------------------------------------------------------------------------
# Fungsi akuisisi per sumber
# ---------------------------------------------------------------------------
def akuisisi_cuaca(cfg):
    """Ambil cuaca per jam dari Open-Meteo untuk titik pusat wilayah.

    Waktu diminta dalam UTC (timezone=GMT); konversi ke Asia/Jakarta
    dilakukan di tahap pembersihan supaya seragam dengan data gempa.
    """
    api, jar = cfg["api"]["open_meteo"], cfg["jaringan"]
    params = {
        "latitude": cfg["wilayah"]["lat_pusat"],
        "longitude": cfg["wilayah"]["lon_pusat"],
        "start_date": cfg["periode"]["tanggal_mulai"],
        "end_date": cfg["periode"]["tanggal_selesai"],
        "hourly": ",".join(api["variabel_per_jam"]),
        "timezone": "GMT",
    }
    return _ambil_dengan_cadangan(
        cfg, "cuaca_openmeteo",
        lambda: ambil_json_dengan_retry(api["url"], params, jar["timeout_detik"],
                                        jar["maks_percobaan"], jar["jeda_awal_detik"], "Open-Meteo"),
        data_sintetis.buat_cuaca_sintetis, "Open-Meteo")


def akuisisi_gempa(cfg):
    """Ambil katalog gempa dari USGS dalam radius tertentu dari titik pusat."""
    api, jar, w = cfg["api"]["usgs"], cfg["jaringan"], cfg["wilayah"]
    params = {
        "format": api["format"],
        "starttime": cfg["periode"]["tanggal_mulai"],
        "endtime": f"{cfg['periode']['tanggal_selesai']}T23:59:59",
        "latitude": w["lat_pusat"],
        "longitude": w["lon_pusat"],
        "maxradiuskm": w["radius_km"],
        "minmagnitude": api["magnitudo_min"],
        "orderby": "time-asc",
    }
    return _ambil_dengan_cadangan(
        cfg, "gempa_usgs",
        lambda: ambil_json_dengan_retry(api["url"], params, jar["timeout_detik"],
                                        jar["maks_percobaan"], jar["jeda_awal_detik"], "USGS"),
        data_sintetis.buat_gempa_sintetis, "USGS")
