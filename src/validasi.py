"""
validasi.py - TAHAP 2: mengubah JSON mentah menjadi tabel dan memeriksa skemanya.

Validasi dilakukan SEBELUM pembersihan (sesuai proposal): kalau kolom
wajib hilang, pipeline berhenti teratur dengan pesan log yang jelas,
bukan crash di tengah jalan dengan error yang membingungkan.
"""

import pandas as pd

from src.utils import SkemaError, get_logger


def cuaca_json_ke_dataframe(data_json):
    """Ambil bagian 'hourly' dari JSON Open-Meteo menjadi DataFrame."""
    if not isinstance(data_json, dict) or "hourly" not in data_json:
        raise SkemaError("JSON cuaca tidak punya bagian 'hourly' (struktur API berubah?)")
    hourly = data_json["hourly"]
    # Semua daftar di 'hourly' harus sama panjang
    panjang = {k: len(v) for k, v in hourly.items()}
    if len(set(panjang.values())) > 1:
        raise SkemaError(f"Panjang kolom cuaca tidak sama: {panjang}")
    return pd.DataFrame(hourly)


def gempa_geojson_ke_dataframe(data_json):
    """Ratakan (flatten) GeoJSON USGS: satu feature -> satu baris tabel."""
    if not isinstance(data_json, dict) or "features" not in data_json:
        raise SkemaError("JSON gempa tidak punya bagian 'features' (bukan GeoJSON?)")
    baris = []
    for f in data_json["features"]:
        prop = f.get("properties", {}) or {}
        koord = (f.get("geometry") or {}).get("coordinates") or [None, None, None]
        baris.append({
            "id": f.get("id"),
            "time": prop.get("time"),
            "mag": prop.get("mag"),
            "place": prop.get("place"),
            "type": prop.get("type"),
            "longitude": koord[0],
            "latitude": koord[1],
            "depth": koord[2] if len(koord) > 2 else None,
        })
    return pd.DataFrame(baris, columns=["id", "time", "mag", "place", "type",
                                        "longitude", "latitude", "depth"])


def validasi_skema(df, kolom_wajib, nama_data):
    """Pastikan semua kolom wajib ada. Lempar SkemaError jika ada yang kurang."""
    log = get_logger()
    kurang = [k for k in kolom_wajib if k not in df.columns]
    if kurang:
        raise SkemaError(f"Data {nama_data}: kolom wajib tidak ditemukan {kurang}. "
                         f"Kolom yang tersedia: {list(df.columns)}")
    log.info(f"Validasi skema {nama_data}: OK ({len(df):,} baris, {len(df.columns)} kolom, "
             f"semua {len(kolom_wajib)} kolom wajib ada)")
    return True
