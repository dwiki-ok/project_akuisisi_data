# Panduan Lengkap untuk Linux Fedora (Pemula)

Panduan ini dari nol sampai kalian bisa melihat laporan dengan **data asli**.
Semua perintah diketik di **Terminal** (tekan tombol Super/Windows, ketik `Terminal`, Enter).
Setiap blok perintah bisa disalin dan ditempel (di Terminal: `Ctrl+Shift+V`).

Perkiraan waktu: 15 sampai 30 menit.

---

## JALUR CEPAT (OTOMATIS, tanpa membuat venv manual)

Proyek ini menyiapkan lingkungannya sendiri. Saat pertama kali menjalankan `python unduh_data.py`
atau `python run_pipeline.py`, program otomatis membuat folder `venv/`, memasang library,
lalu menjalankan ulang dirinya. Jadi **Langkah 2 dan 3 di bawah TIDAK perlu dilakukan manual**
(kalian tidak perlu mengetik `python -m venv venv` maupun `source venv/bin/activate`).
Hanya kali pertama butuh internet dan menunggu 1 sampai 2 menit.

```bash
cd "$HOME/Documents/project akuisi data/pipeline_cuaca_gempa"
rm -f data/raw/*SINTETIS*.json data/processed/*.csv data/kunci/*.csv output/*.csv output/laporan_evaluasi.md logs/*.log
python unduh_data.py
python run_pipeline.py
venv/bin/python -m pytest tests -v      # uji (setelah venv terbentuk)
```
Langkah 2 dan 3 di bawah hanya sebagai cadangan jika instalasi otomatis gagal.

---

## LANGKAH 0: Cek Python

```bash
python --version
```
Harus muncul `Python 3.x.x` (versi 3.9 ke atas). Kalian sudah punya 3.14.10, jadi aman.
Di Linux **tidak perlu mengatur PATH**.

---

## LANGKAH 1: Siapkan folder proyek

1. Unduh `pipeline_cuaca_gempa.zip` dari thread ini (biasanya masuk ke folder `~/Downloads`).
2. Ekstrak:
   ```bash
   cd ~/Downloads
   unzip pipeline_cuaca_gempa.zip
   ```
   Kalau muncul `unzip: command not found`, pasang dulu:
   ```bash
   sudo dnf install -y unzip
   ```
3. Masuk ke foldernya:
   ```bash
   cd pipeline_cuaca_gempa
   ls
   ```
   Harus terlihat: `README.md  config  data  logs  output  requirements.txt  run_pipeline.py  src  tests  unduh_data.py ...`

> Kalau kalian memindahkan folder ke tempat lain (mis. `~/Documents`), ganti `~/Downloads` dengan lokasi itu.

---

## LANGKAH 2: Buat virtual environment (ruang library khusus proyek)

Fedora melarang `pip install` langsung ke sistem. Solusinya virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```
Tanda berhasil: di awal baris terminal muncul **`(venv)`**.

Kalau muncul error `No module named venv` atau `ensurepip`:
```bash
sudo dnf install -y python3-pip
```
lalu ulangi dua perintah di atas.

---

## LANGKAH 3: Pasang library

```bash
pip install -r requirements.txt
```
Ini memasang `pandas`, `numpy`, `requests`, `pytest`. Butuh internet, tunggu sampai selesai
(tulisan `Successfully installed ...`).

Cek:
```bash
python -c "import pandas, numpy, requests; print('library OK')"
```

> Kalau `pip install` gagal karena Python 3.14 terlalu baru untuk salah satu library,
> pakai Python 3.12:
> ```bash
> sudo dnf install -y python3.12
> deactivate; rm -rf venv
> python3.12 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

---

## LANGKAH 4: Hapus data contoh sintetis (WAJIB)

Zip yang kalian terima berisi hasil contoh dari data **palsu (sintetis)**. Hapus supaya tidak tertukar:

```bash
rm -f data/raw/*SINTETIS*.json data/processed/*.csv data/kunci/*.csv output/*.csv output/laporan_evaluasi.md logs/*.log
```
Ini hanya menghapus file hasil, bukan kode dan bukan folder.

---

## LANGKAH 5: Cek internet

```bash
curl -sI https://archive-api.open-meteo.com | head -1
curl -sI https://earthquake.usgs.gov | head -1
```
Tiap baris harus menunjukkan `HTTP/...` (200, 301, atau 404 tidak masalah, yang penting ada jawaban).
Kalau kosong atau error, internet/VPN/proxy kalian bermasalah. Lihat Bagian Masalah Umum.

---

## LANGKAH 6: Unduh data asli

```bash
python unduh_data.py
```
Keluaran yang benar kira-kira:
```
[Open-Meteo] Berhasil (HTTP 200, ... byte)
[USGS] Berhasil (HTTP 200, ... byte)
Cuaca : 8,784 jam      (sumber: API)
Gempa : 3xx kejadian   (sumber: API)
Data asli siap. Lanjutkan dengan: python run_pipeline.py
```
Cek file yang terunduh:
```bash
ls -lh data/raw/
```
Harus ada `cuaca_openmeteo_2024-01-01_2024-12-31.json` dan `gempa_usgs_2024-01-01_2024-12-31.json`.

---

## LANGKAH 7: Jalankan pipeline (SATU perintah)

```bash
python run_pipeline.py
```
Kalian akan melihat 11 tahap berjalan di layar. Akhirnya:
```
SELESAI dalam ... detik. Laporan: output/laporan_evaluasi.md
```
Tahap 1 menulis `Memakai cache lokal`, artinya data asli dari Langkah 6 dipakai
(label sumber di laporan: **CACHE**, bukan SINTETIS).

Kalau tampil error, lihat Bagian Masalah Umum, atau salin tulisan errornya ke thread ini.

---

## LANGKAH 8: Lihat output

### 8a. Daftar semua hasil
```bash
ls -lh output/ data/processed/ data/kunci/ logs/
```

### 8b. Laporan utama
```bash
less output/laporan_evaluasi.md        # keluar dengan tombol q
```
atau buka dengan aplikasi:
```bash
xdg-open output/laporan_evaluasi.md
```
(Lebih enak dibaca di VS Code atau gedit. Tabel Markdown tampil rapi di VS Code dengan `Ctrl+Shift+V`.)

### 8c. Tabel CSV
```bash
xdg-open output/tabel_anomali.csv      # dibuka di LibreOffice Calc
```
Atau lihat cepat di terminal:
```bash
column -s, -t < output/metrik_detektor.csv
head -n 10 output/tabel_anomali.csv
```

### 8d. Log
```bash
less logs/pipeline.log
grep -E "WARNING|ERROR" logs/pipeline.log      # hanya peringatan dan error
```

### 8e. Daftar berkas hasil dan artinya

| Berkas | Isi |
|---|---|
| `output/laporan_evaluasi.md` | Laporan utama otomatis |
| `output/tabel_anomali.csv` | Tabel lonjakan yang ditemukan detektor (status TP/FP) |
| `output/metrik_detektor.csv` | Precision, recall, F1 |
| `output/statistik_per_jam.csv` | Statistik per jam 00 sampai 23 WIB |
| `output/korelasi.csv` | Korelasi cuaca vs gempa |
| `output/hasil_uji_assert.csv` | Hasil 5 uji assert |
| `output/hasil_simulasi_gagal.csv` | Hasil 5 skenario gagal |
| `data/processed/data_gabungan.csv` | Data gabungan cuaca + gempa (1 baris per jam) |
| `data/kunci/kunci_anomali.csv` | Kunci jawaban anomali (terpisah dari detektor) |
| `logs/pipeline.log` | Log contoh eksekusi |

---

## LANGKAH 9: Cara membaca laporan (checklist)

Buka `output/laporan_evaluasi.md` lalu periksa:

1. **Bagian 1**: sumber cuaca dan gempa berlabel **CACHE** atau **API**. Kalau **SINTETIS**, ulangi Langkah 4 sampai 7.
   Baris gabungan harus >= 5.000 (untuk setahun: 8.784). Duplikat timestamp = 0.
2. **Bagian 2**: persentase gempa dipasangkan ke jam cuaca (idealnya mendekati 100%).
3. **Bagian 3**: semua uji assert **LULUS** (5/5).
4. **Bagian 4**: statistik per jam. Suhu biasanya paling tinggi sekitar siang (11 sampai 14 WIB).
5. **Bagian 5**: precision dan recall detektor.
   - Precision = dari semua alarm, berapa persen benar.
   - Recall = dari semua anomali tertanam, berapa persen tertangkap.
6. **Bagian 6**: korelasi. Hampir pasti lemah (r mendekati 0). Itu wajar: gempa tektonik tidak dipicu cuaca. Jelaskan bersama batasan yang tertulis di laporan.
7. **Bagian 7**: semua skenario gagal berstatus **TERTANGANI**.

---

## LANGKAH 10: Uji otomatis (pytest)

```bash
venv/bin/python -m pytest tests -v
```
Harus `8 passed`. (Pakai `venv/bin/python` supaya memakai library di venv tanpa mengaktifkannya.)

---

## LANGKAH 11: Coba mengubah pengaturan (tanpa mengubah kode)

Edit `config/config.json` dengan editor teks, mis.:
```bash
gedit config/config.json        # atau: nano config/config.json
```

| Tujuan | Yang diubah |
|---|---|
| Detektor lebih sensitif (recall naik) | `detektor.k_sigma` dari 4.0 menjadi 3.0 |
| Wilayah lain | `wilayah.lat_pusat`, `lon_pusat`, `radius_km` |
| Gempa terlalu sedikit | perbesar `radius_km` atau perpanjang `periode` |

Kalau mengubah `wilayah` atau `periode`, unduh ulang: `python unduh_data.py`, lalu `python run_pipeline.py`.
Kalau hanya mengubah `k_sigma`, cukup `python run_pipeline.py`.

---

## LANGKAH 12: Mencoba skenario gagal sendiri (untuk demo presentasi)

1. **Config hilang:**
   ```bash
   python run_pipeline.py --config config/tidak_ada.json
   echo $?                              # menampilkan 1 (berhenti rapi, bukan crash)
   cat logs/pipeline_error.log
   ```
2. **Jaringan mati:** matikan Wi-Fi, hapus cache (`rm data/raw/*.json`), jalankan `python unduh_data.py`.
   Hasilnya pesan KONEKSI GAGAL dan percobaan ulang 3 kali, tanpa crash.
3. Nyalakan lagi Wi-Fi dan jalankan ulang `python unduh_data.py`.
4. **Kolom kurang dan timeout:** sudah otomatis diuji di tahap 10 `run_pipeline.py`
   (lihat `output/hasil_simulasi_gagal.csv`).

---

## Pemakaian di hari berikutnya

```bash
cd ~/Downloads/pipeline_cuaca_gempa
source venv/bin/activate
python run_pipeline.py          # data sudah di cache, bisa tanpa internet
```
Selesai bekerja: `deactivate`.

---

## Masalah umum

| Masalah | Solusi |
|---|---|
| `error: externally-managed-environment` | Kalian belum memakai venv. Jalankan Langkah 2 dan pastikan ada `(venv)` |
| `ModuleNotFoundError` | Seharusnya tidak terjadi lagi (venv otomatis). Kalau terjadi: `venv/bin/pip install -r requirements.txt` |
| `python: command not found` | Pakai `python3` sebagai gantinya, atau `sudo dnf install python3` |
| `UNDUH GAGAL ... KONEKSI GAGAL` | Cek internet (Langkah 5), matikan VPN/proxy, coba lagi |
| `HTTP 429` | Terlalu sering meminta data. Tunggu beberapa menit lalu ulangi |
| `Permission denied` saat menghapus/menulis | Pastikan foldernya milik kalian: `ls -ld .` |
| Laporan bertuliskan SINTETIS | Ulangi Langkah 4, 6, 7 |
| Gempa sangat sedikit (< 30) | Perbesar `radius_km` di config, hapus `data/raw/*.json`, unduh ulang |
| Ingin mengulang bersih dari awal | `rm -rf data/raw/*.json data/processed/*.csv data/kunci/*.csv output/* logs/*` |

---

## Ringkasan perintah

```bash
cd ~/Downloads && unzip pipeline_cuaca_gempa.zip && cd pipeline_cuaca_gempa
rm -f data/raw/*SINTETIS*.json data/processed/*.csv data/kunci/*.csv output/*.csv output/laporan_evaluasi.md logs/*.log
python unduh_data.py
python run_pipeline.py
venv/bin/python -m pytest tests -v
less output/laporan_evaluasi.md
```
(venv dibuat otomatis oleh program pada saat pertama dijalankan.)

## Atribusi data (cantumkan di laporan dan presentasi)

- Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com
- Earthquake data from USGS (domain publik), https://earthquake.usgs.gov
