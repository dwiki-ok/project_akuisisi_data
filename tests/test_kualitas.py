"""
tests/test_kualitas.py - uji otomatis yang bisa dijalankan dengan pytest.

Jalankan SETELAH run_pipeline.py (butuh data/processed/data_gabungan.csv):
    python -m pytest tests -v

Isi:
- 5 uji kualitas data gabungan (memakai fungsi assert di src/uji_kualitas.py)
- 1 uji isolasi: memastikan modul detektor tidak membaca berkas kunci anomali
- 2 uji kecil untuk regex pembersihan lokasi
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

from src import pembersihan, uji_kualitas  # noqa: E402
from src.utils import load_config, path_proyek  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return load_config("config/config.json")


@pytest.fixture(scope="module")
def df(cfg):
    path = path_proyek(cfg["path"]["file_data_gabungan"])
    if not path.exists():
        pytest.skip("Jalankan dulu: python run_pipeline.py")
    d = pd.read_csv(path)
    d["waktu_lokal"] = pd.to_datetime(d["waktu_lokal"], utc=True).dt.tz_convert(cfg["zona_waktu"])
    return d


def test_jumlah_kolom(df, cfg):
    uji_kualitas.uji_jumlah_kolom(df, cfg)


def test_tipe_dan_rentang(df, cfg):
    uji_kualitas.uji_tipe_dan_rentang(df, cfg)


def test_kunci_join_non_null(df, cfg):
    uji_kualitas.uji_kunci_join_non_null(df, cfg)


def test_tanpa_duplikat_timestamp(df, cfg):
    uji_kualitas.uji_tanpa_duplikat_timestamp(df, cfg)


def test_jumlah_baris(df, cfg):
    uji_kualitas.uji_jumlah_baris(df, cfg)


def test_detektor_tidak_membaca_kunci():
    """Kode detektor tidak boleh menyebut berkas kunci sama sekali."""
    kode = (AKAR / "src" / "detektor.py").read_text(encoding="utf-8")
    baris_kode = [b for b in kode.splitlines() if not b.strip().startswith("#")]
    kode_tanpa_docstring = "\n".join(baris_kode).split('"""')[2::2]  # bagian di luar docstring
    gabung = "\n".join(kode_tanpa_docstring)
    assert "kunci" not in gabung.lower(), "detektor.py menyebut 'kunci' di luar komentar!"
    assert "file_kunci_anomali" not in kode


def test_regex_lokasi_normal():
    hasil = pembersihan.pecah_tempat("97 km SSW of Jember, Indonesia")
    assert hasil["jarak_km"] == 97.0
    assert hasil["arah"] == "SSW"
    assert hasil["kota_terdekat"] == "Jember"
    assert hasil["negara"] == "Indonesia"


def test_regex_lokasi_berantakan():
    rapi = pembersihan.rapikan_teks("  97km  SSW of   Jember ,Indonesia  ")
    assert rapi == "97 km SSW of Jember, Indonesia"
    assert pd.isna(pembersihan.pecah_tempat("Java, Indonesia")["jarak_km"])
