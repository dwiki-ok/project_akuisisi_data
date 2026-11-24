"""
pembersihan.py - TAHAP 3: membersihkan data dan menyeragamkan zona waktu.

Yang dilakukan:
- Cuaca : cek format waktu dengan REGEX, ubah UTC -> Asia/Jakarta,
          buang duplikat jam, ubah tipe ke angka, tandai nilai di luar rentang.
- Gempa : buang duplikat id, buang yang bukan 'earthquake', buang magnitudo
          kosong, rapikan teks lokasi dan pecah dengan REGEX menjadi
          jarak_km / arah / kota_terdekat / negara, ubah waktu ke Asia/Jakarta,
          hitung jarak ke titik pusat dan buang yang di luar radius.
"""

import re

import numpy as np
import pandas as pd

from src.utils import get_logger

# Pola ISO dari Open-Meteo, contoh: 2024-01-01T00:00
POLA_WAKTU_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

# Pola teks lokasi USGS, contoh: "97 km SSW of Jember, Indonesia"
#   (?P<jarak>...)  -> angka jarak (boleh desimal)
#   (?P<arah>...)   -> arah mata angin 1-3 huruf (N, SSW, ENE, ...)
#   (?P<kota>...)   -> nama kota terdekat
#   (?P<negara>...) -> teks setelah koma terakhir (opsional)
POLA_TEMPAT = re.compile(
    r"^(?P<jarak>\d+(?:\.\d+)?)\s*km\s+(?P<arah>[NSEW]{1,3})\s+of\s+(?P<kota>[^,]+?)\s*(?:,\s*(?P<negara>.+))?$",
    re.IGNORECASE,
)


def jarak_haversine_km(lat1, lon1, lat2, lon2):
    """Jarak garis lurus di permukaan bumi (km) antara dua titik koordinat."""
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def rapikan_teks(teks):
    """Hapus spasi ganda, spasi sebelum koma, dan spasi di ujung (pakai regex)."""
    if not isinstance(teks, str):
        return teks
    teks = re.sub(r"\s+", " ", teks).strip()          # banyak spasi -> satu spasi
    teks = re.sub(r"\s*,\s*", ", ", teks)              # ' ,x' -> ', x'
    teks = re.sub(r"(\d)\s*km\b", r"\1 km", teks)      # '97km' -> '97 km'
    return teks


def pecah_tempat(teks):
    """Pecah teks lokasi USGS menjadi 4 bagian. Jika pola tidak cocok -> NaN."""
    m = POLA_TEMPAT.match(teks) if isinstance(teks, str) else None
    if not m:
        return pd.Series({"jarak_km": np.nan, "arah": None, "kota_terdekat": None,
                          "negara": teks.split(",")[-1].strip() if isinstance(teks, str) else None})
    return pd.Series({"jarak_km": float(m.group("jarak")), "arah": m.group("arah").upper(),
                      "kota_terdekat": m.group("kota").strip(), "negara": m.group("negara")})


def bersihkan_cuaca(df, cfg):
    """Bersihkan data cuaca per jam. Mengembalikan DataFrame bersih."""
    log = get_logger()
    n_awal = len(df)
    df = df.copy()

    # 1) Regex: pastikan setiap stempel waktu berformat ISO yang benar
    cocok = df["time"].astype(str).str.match(POLA_WAKTU_ISO)
    if (~cocok).sum():
        log.warning(f"Cuaca: {(~cocok).sum()} baris format waktu salah -> dibuang")
    df = df[cocok]

    # 2) Ubah ke datetime UTC lalu ke zona waktu Asia/Jakarta (WIB)
    df["waktu_utc"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M", utc=True)
    df["waktu_lokal"] = df["waktu_utc"].dt.tz_convert(cfg["zona_waktu"])

    # 3) Ubah semua kolom variabel ke angka (teks aneh -> NaN)
    variabel = [v for v in cfg["api"]["open_meteo"]["variabel_per_jam"] if v in df.columns]
    for v in variabel:
        df[v] = pd.to_numeric(df[v], errors="coerce")

    # 4) Nilai di luar rentang fisis -> NaN (bukan dibuang barisnya, supaya jam tetap lengkap)
    for kolom, (bawah, atas) in cfg["validasi"]["rentang_nilai"].items():
        if kolom in df.columns:
            salah = ~df[kolom].between(bawah, atas) & df[kolom].notna()
            if salah.sum():
                log.warning(f"Cuaca: {salah.sum()} nilai {kolom} di luar [{bawah}, {atas}] -> NaN")
                df.loc[salah, kolom] = np.nan

    # 5) Isi celah kecil (maks 3 jam) dengan interpolasi linear
    kosong_awal = int(df[variabel].isna().sum().sum())
    df[variabel] = df[variabel].interpolate(limit=3, limit_direction="both")
    if kosong_awal:
        log.info(f"Cuaca: {kosong_awal} sel kosong, sisa setelah interpolasi "
                 f"{int(df[variabel].isna().sum().sum())}")

    # 6) Buang duplikat jam (kunci join harus unik)
    df = df.drop_duplicates(subset="waktu_lokal").sort_values("waktu_lokal").reset_index(drop=True)
    df = df.drop(columns=["time"])
    log.info(f"Pembersihan cuaca: {n_awal:,} -> {len(df):,} baris")
    return df


def bersihkan_gempa(df, cfg):
    """Bersihkan katalog gempa. Mengembalikan DataFrame satu baris per kejadian."""
    log = get_logger()
    n_awal = len(df)
    df = df.copy()

    # 1) Duplikat kejadian (id sama)
    dup = df.duplicated(subset="id").sum()
    df = df.drop_duplicates(subset="id")
    # 2) Hanya kejadian bertipe earthquake (buang ledakan tambang, dll.)
    bukan_gempa = (df["type"] != "earthquake").sum()
    df = df[df["type"] == "earthquake"]
    # 3) Ubah ke angka dan buang magnitudo / koordinat kosong
    for k in ["mag", "longitude", "latitude", "depth"]:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    tanpa_mag = df[["mag", "latitude", "longitude"]].isna().any(axis=1).sum()
    df = df.dropna(subset=["mag", "latitude", "longitude"])
    log.info(f"Gempa: buang {dup} duplikat, {bukan_gempa} bukan-gempa, {tanpa_mag} tanpa mag/koordinat")

    # 4) Regex: rapikan teks lokasi lalu pecah menjadi kolom terstruktur
    df["place"] = df["place"].apply(rapikan_teks)
    df = pd.concat([df.reset_index(drop=True),
                    df["place"].apply(pecah_tempat).reset_index(drop=True)], axis=1)
    gagal = df["jarak_km"].isna().sum()
    log.info(f"Gempa: regex lokasi cocok {len(df) - gagal}/{len(df)} baris "
             f"({gagal} berformat lain, mis. 'Java, Indonesia')")

    # 5) Waktu: USGS memberi milidetik sejak 1970 (UTC) -> Asia/Jakarta
    df["waktu_utc"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["waktu_lokal"] = df["waktu_utc"].dt.tz_convert(cfg["zona_waktu"])
    df = df.drop(columns=["time"])

    # 6) Filter lokasi: hitung jarak ke pusat wilayah dan buang yang di luar radius
    w = cfg["wilayah"]
    df["jarak_ke_pusat_km"] = jarak_haversine_km(w["lat_pusat"], w["lon_pusat"],
                                                 df["latitude"], df["longitude"]).round(1)
    luar = (df["jarak_ke_pusat_km"] > w["radius_km"]).sum()
    df = df[df["jarak_ke_pusat_km"] <= w["radius_km"]]
    log.info(f"Gempa: {luar} kejadian di luar radius {w['radius_km']} km dibuang")

    df = df.sort_values("waktu_lokal").reset_index(drop=True)
    log.info(f"Pembersihan gempa: {n_awal:,} -> {len(df):,} kejadian")
    return df
