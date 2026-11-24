"""
uji_kualitas.py - TAHAP 5: uji otomatis berbasis `assert` pada data gabungan.

Setiap fungsi uji memakai `assert`. Jika syarat tidak terpenuhi,
Python melempar AssertionError dan uji dianggap GAGAL.
Fungsi jalankan_semua_uji() menjalankan semuanya dan mencatat hasilnya ke log.

File tests/test_kualitas.py memanggil fungsi yang sama lewat pytest.
"""

import pandas as pd

from src.utils import get_logger


def uji_jumlah_kolom(df, cfg):
    """Uji 1: jumlah kolom utama minimal sesuai config dan kolom utama ada."""
    kolom_utama = ["waktu_lokal", "temperature_2m", "relative_humidity_2m",
                   "pressure_msl", "gempa_jumlah", "gempa_mag_maks"]
    ada = [k for k in kolom_utama if k in df.columns]
    assert len(ada) >= cfg["validasi"]["min_kolom_utama"], \
        f"Kolom utama hanya {len(ada)}: {ada}"
    assert len(ada) == len(kolom_utama), f"Kolom utama hilang: {set(kolom_utama) - set(ada)}"


def uji_tipe_dan_rentang(df, cfg):
    """Uji 2: tipe data benar dan nilai berada dalam rentang fisis."""
    assert pd.api.types.is_datetime64_any_dtype(df["waktu_lokal"]), "waktu_lokal bukan datetime"
    assert str(df["waktu_lokal"].dt.tz) == cfg["zona_waktu"], \
        f"Zona waktu {df['waktu_lokal'].dt.tz}, seharusnya {cfg['zona_waktu']}"
    for kolom, (bawah, atas) in cfg["validasi"]["rentang_nilai"].items():
        if kolom not in df.columns:
            continue
        assert pd.api.types.is_numeric_dtype(df[kolom]), f"{kolom} bukan angka"
        nilai = df[kolom].dropna()
        assert nilai.between(bawah, atas).all(), \
            f"{kolom} di luar rentang [{bawah}, {atas}]: min={nilai.min()}, maks={nilai.max()}"


def uji_kunci_join_non_null(df, cfg):
    """Uji 3: kolom kunci penggabungan tidak boleh kosong."""
    for k in cfg["validasi"]["kolom_kunci_join"]:
        assert df[k].notna().all(), f"Kunci join {k} punya {df[k].isna().sum()} nilai kosong"


def uji_tanpa_duplikat_timestamp(df, cfg):
    """Uji 4: tidak ada stempel waktu kunci yang dobel."""
    dup = df["waktu_lokal"].duplicated().sum()
    assert dup == 0, f"Ada {dup} timestamp duplikat"


def uji_jumlah_baris(df, cfg):
    """Uji 5: minimal N baris (atau seluruh rentang jam terakuisisi utuh)."""
    mulai = pd.Timestamp(cfg["periode"]["tanggal_mulai"])
    selesai = pd.Timestamp(cfg["periode"]["tanggal_selesai"]) + pd.Timedelta(hours=23)
    jam_harapan = int((selesai - mulai) / pd.Timedelta(hours=1)) + 1
    assert len(df) >= cfg["validasi"]["min_baris"] or len(df) == jam_harapan, \
        f"Hanya {len(df)} baris; perlu >= {cfg['validasi']['min_baris']} atau {jam_harapan} (rentang penuh)"


DAFTAR_UJI = [uji_jumlah_kolom, uji_tipe_dan_rentang, uji_kunci_join_non_null,
              uji_tanpa_duplikat_timestamp, uji_jumlah_baris]


def jalankan_semua_uji(df, cfg):
    """Jalankan semua uji; kembalikan list hasil [{'uji', 'status', 'pesan'}]."""
    log = get_logger()
    hasil = []
    for fungsi in DAFTAR_UJI:
        try:
            fungsi(df, cfg)
            hasil.append({"uji": fungsi.__name__, "status": "LULUS", "pesan": fungsi.__doc__.strip()})
            log.info(f"UJI {fungsi.__name__}: LULUS")
        except AssertionError as e:
            hasil.append({"uji": fungsi.__name__, "status": "GAGAL", "pesan": str(e)})
            log.error(f"UJI {fungsi.__name__}: GAGAL -> {e}")
    lulus = sum(h["status"] == "LULUS" for h in hasil)
    log.info(f"Ringkasan uji assert: {lulus}/{len(hasil)} lulus")
    return hasil
