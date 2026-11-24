"""
data_sintetis.py - Pembuat data CADANGAN (fallback) jika API tidak bisa dihubungi.

PENTING: data dari modul ini BUKAN data asli. Dipakai hanya agar pipeline
tetap bisa diuji ketika internet mati dan belum ada cache. Setiap data
sintetis diberi label "SINTETIS" di nama file, di log, dan di laporan.

Bentuk datanya SAMA PERSIS dengan format JSON API asli, sehingga kode
pembersihan dan analisis yang dipakai juga sama:
- Open-Meteo : {"hourly": {"time": [...], "temperature_2m": [...], ...}}
- USGS       : GeoJSON {"features": [{"properties": {...}, "geometry": {...}}]}

Kita juga sengaja menyelipkan sedikit data "kotor" (spasi berlebih,
duplikat, magnitudo kosong, tipe bukan gempa) supaya tahap pembersihan
benar-benar punya pekerjaan.
"""

import math

import numpy as np
import pandas as pd

KOTA_SEKITAR = ["Banyuwangi", "Jember", "Malang", "Lumajang", "Denpasar",
                "Singaraja", "Mataram", "Probolinggo", "Blitar", "Pacitan"]
ARAH = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def buat_cuaca_sintetis(cfg):
    """Buat data cuaca per jam berformat Open-Meteo (waktu dalam UTC)."""
    rng = np.random.default_rng(cfg["fallback_sintetis"]["seed"])
    waktu = pd.date_range(cfg["periode"]["tanggal_mulai"],
                          pd.Timestamp(cfg["periode"]["tanggal_selesai"]) + pd.Timedelta(hours=23),
                          freq="h", tz="UTC")
    n = len(waktu)
    jam_lokal = (waktu.hour + 7) % 24                      # WIB = UTC+7
    hari_ke = np.asarray(waktu.dayofyear)

    # Suhu: pola harian (puncak ~jam 13 WIB) + sedikit pola musiman + derau
    suhu = (27.5 + 3.5 * np.sin(2 * np.pi * (jam_lokal - 7) / 24)
            + 0.8 * np.cos(2 * np.pi * (hari_ke - 30) / 366)
            + rng.normal(0, 0.6, n))
    # Kelembapan: kebalikan suhu (siang kering, malam lembap)
    lembap = np.clip(80 - 2.8 * (suhu - 27.5) + rng.normal(0, 3, n), 35, 100)
    # Tekanan: pasang-surut atmosfer 12 jam + variasi lambat (random walk halus)
    lambat = np.cumsum(rng.normal(0, 0.08, n))
    lambat = lambat - pd.Series(lambat).rolling(24 * 10, min_periods=1).mean().to_numpy()
    tekanan = (1010 + 1.2 * np.cos(2 * np.pi * (jam_lokal - 10) / 12) + lambat
               + rng.normal(0, 0.15, n))
    # Hujan: lebih sering di musim hujan (Nov-Mar) dan sore hari
    musim_hujan = np.isin(np.asarray(waktu.month), [11, 12, 1, 2, 3])
    peluang = np.where(musim_hujan, 0.12, 0.03) * np.where((jam_lokal >= 13) & (jam_lokal <= 19), 2, 1)
    hujan = np.where(rng.random(n) < peluang, rng.gamma(1.2, 2.5, n), 0.0)
    angin = np.abs(rng.normal(3.5, 1.5, n))

    return {
        "latitude": cfg["wilayah"]["lat_pusat"],
        "longitude": cfg["wilayah"]["lon_pusat"],
        "timezone": "GMT",
        "SUMBER": "SINTETIS - bukan data asli Open-Meteo",
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C", "relative_humidity_2m": "%",
                         "pressure_msl": "hPa", "precipitation": "mm", "wind_speed_10m": "km/h"},
        "hourly": {
            "time": [t.strftime("%Y-%m-%dT%H:%M") for t in waktu],
            "temperature_2m": np.round(suhu, 1).tolist(),
            "relative_humidity_2m": np.round(lembap).astype(int).tolist(),
            "pressure_msl": np.round(tekanan, 1).tolist(),
            "precipitation": np.round(hujan, 1).tolist(),
            "wind_speed_10m": np.round(angin, 1).tolist(),
        },
    }


def _titik_acak_dalam_radius(rng, lat0, lon0, radius_km):
    """Ambil satu titik acak di dalam lingkaran (radius_km) sekitar pusat."""
    r = radius_km * math.sqrt(rng.random())
    sudut = rng.random() * 2 * math.pi
    dlat = (r * math.cos(sudut)) / 111.0
    dlon = (r * math.sin(sudut)) / (111.0 * math.cos(math.radians(lat0)))
    return lat0 + dlat, lon0 + dlon


def buat_gempa_sintetis(cfg):
    """Buat katalog gempa berformat GeoJSON USGS."""
    rng = np.random.default_rng(cfg["fallback_sintetis"]["seed"] + 1)
    w = cfg["wilayah"]
    mulai = pd.Timestamp(cfg["periode"]["tanggal_mulai"], tz="UTC")
    selesai = pd.Timestamp(cfg["periode"]["tanggal_selesai"], tz="UTC") + pd.Timedelta(days=1)
    total_detik = (selesai - mulai).total_seconds()
    n = int(cfg["fallback_sintetis"]["jumlah_gempa_per_tahun"] * total_detik / (365 * 86400))
    mag_min = cfg["api"]["usgs"]["magnitudo_min"]

    fitur = []
    for i in range(n):
        lat, lon = _titik_acak_dalam_radius(rng, w["lat_pusat"], w["lon_pusat"], w["radius_km"] * 1.1)
        # Hukum Gutenberg-Richter: gempa kecil jauh lebih sering dari gempa besar
        mag = round(mag_min + rng.exponential(1 / (1.0 * math.log(10))), 1)
        waktu = mulai + pd.Timedelta(seconds=float(rng.random() * total_detik))
        tempat = f"{rng.integers(5, 250)} km {rng.choice(ARAH)} of {rng.choice(KOTA_SEKITAR)}, Indonesia"
        fitur.append({
            "type": "Feature",
            "id": f"syn{i:05d}",
            "properties": {
                "mag": mag, "place": tempat, "time": int(waktu.timestamp() * 1000),
                "type": "earthquake", "magType": "mb", "status": "reviewed",
            },
            "geometry": {"type": "Point",
                         "coordinates": [round(lon, 4), round(lat, 4), round(float(rng.gamma(2, 25)), 1)]},
        })

    # --- Sisipkan data kotor agar tahap pembersihan teruji ---
    if fitur:
        fitur[0]["properties"]["place"] = "  97km  SSW of   Jember ,Indonesia  "   # spasi berantakan
        fitur[1]["properties"]["mag"] = None                                    # magnitudo kosong
        fitur[2]["properties"]["type"] = "quarry blast"                         # bukan gempa
        fitur.append(dict(fitur[3]))                                            # duplikat id
        fitur[4]["properties"]["place"] = "Java, Indonesia"                     # tanpa jarak/arah

    return {
        "type": "FeatureCollection",
        "SUMBER": "SINTETIS - bukan data asli USGS",
        "metadata": {"title": "USGS Earthquakes (SINTETIS)", "count": len(fitur)},
        "features": fitur,
    }
