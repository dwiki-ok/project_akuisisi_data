"""
siapkan_env.py - Menyiapkan virtual environment dan library SECARA OTOMATIS.

Dipanggil paling awal oleh run_pipeline.py dan unduh_data.py. Alurnya:
1. Kalau library (pandas, numpy, requests) sudah ada -> tidak melakukan apa-apa.
2. Kalau belum ada:
   a. buat folder venv/ di dalam proyek (kalau belum ada),
   b. pasang library dari requirements.txt ke venv/,
   c. jalankan ulang perintah yang sama memakai Python milik venv/.

Jadi pengguna cukup mengetik `python run_pipeline.py`, tanpa membuat atau
mengaktifkan venv secara manual. Hanya butuh internet pada kali pertama.
"""

import os
import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent
VENV = AKAR / "venv"
PYTHON_VENV = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PENANDA = "PIPELINE_ENV_SIAP"          # mencegah pengulangan tanpa akhir


def _library_lengkap():
    try:
        import numpy, pandas, requests  # noqa: F401
        return True
    except ImportError:
        return False


def _jalankan(perintah):
    return subprocess.run(perintah, check=False).returncode == 0


def pastikan():
    """Pastikan library tersedia; kalau tidak, siapkan venv lalu jalankan ulang program."""
    if _library_lengkap():
        return

    if os.environ.get(PENANDA):
        sys.exit("GAGAL: library masih belum lengkap setelah instalasi otomatis.\n"
                 "Coba manual: venv/bin/pip install -r requirements.txt  (lalu kirim pesan errornya).")

    print("[siapkan_env] Library belum terpasang. Menyiapkan lingkungan otomatis (hanya sekali)...")
    if not PYTHON_VENV.exists():
        print(f"[siapkan_env] Membuat virtual environment di: {VENV}")
        if not _jalankan([sys.executable, "-m", "venv", str(VENV)]):
            sys.exit("GAGAL membuat venv. Di Fedora coba: sudo dnf install -y python3-pip  "
                     "(Debian/Ubuntu: sudo apt install python3-venv)")

    print("[siapkan_env] Memasang library dari requirements.txt (butuh internet)...")
    if not _jalankan([str(PYTHON_VENV), "-m", "pip", "install", "-q", "-r", str(AKAR / "requirements.txt")]):
        sys.exit("GAGAL memasang library. Cek koneksi internet lalu jalankan ulang perintahnya.")

    print("[siapkan_env] Selesai. Menjalankan ulang program memakai venv...\n")
    os.environ[PENANDA] = "1"
    os.execv(str(PYTHON_VENV), [str(PYTHON_VENV)] + sys.argv)
