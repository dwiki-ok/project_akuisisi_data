# Pipeline Otomatis Cuaca dan Gempa

**Workshop Akuisisi Data, Proyek Akhir. Topik 5: Log dan Pipeline Otomatis. Kelompok 8.**
Studi kasus A: data cuaca (Open-Meteo, JSON) digabung dengan data gempa (USGS, GeoJSON)
menurut **waktu** dan **lokasi**.

> **Mau langsung praktik sampai melihat output data asli?**
> - Windows: [PANDUAN_WINDOWS.md](PANDUAN_WINDOWS.md)
> - Linux (Fedora, Ubuntu, Arch): [PANDUAN_LINUX.md](PANDUAN_LINUX.md), khusus Fedora lebih rinci: [PANDUAN_FEDORA.md](PANDUAN_FEDORA.md)
> Urutan singkat: `python unduh_data.py` -> `python run_pipeline.py`. Library dan venv dipasang otomatis saat pertama kali dijalankan (siapkan_env.py).

**Sumber data (legal):** Open-Meteo (CC BY 4.0) dan USGS (domain publik). Cantumkan atribusi:
"Weather data by Open-Meteo.com; earthquake data from USGS".

---

## Panduan cepat (ringkas)

Library dan venv dipasang OTOMATIS saat pertama kali dijalankan, jadi tidak perlu `python -m venv`.
Butuh Python 3.9+ dan internet pada kali pertama.

**Windows (Command Prompt di folder proyek):**
```
python unduh_data.py
python run_pipeline.py
venv\Scripts\python.exe -m pytest tests -v
notepad output\laporan_evaluasi.md
```
Saat memasang Python, centang "Add python.exe to PATH". Rincian: [PANDUAN_WINDOWS.md](PANDUAN_WINDOWS.md).

**Linux (Terminal di folder proyek):**
```
python3 unduh_data.py
python3 run_pipeline.py
venv/bin/python -m pytest tests -v
less output/laporan_evaluasi.md
```
Di Ubuntu/Debian pasang dulu `sudo apt install python3-venv`. Rincian: [PANDUAN_LINUX.md](PANDUAN_LINUX.md).

---

## 1. Proyek ini tentang apa? (penjelasan untuk pemula)

Bayangkan sebuah "pabrik data" yang bekerja otomatis dengan satu tombol:

1. **Mengambil bahan**: mengunduh data cuaca per jam dan daftar kejadian gempa dari internet.
2. **Memeriksa bahan**: apakah kolom yang dibutuhkan lengkap?
3. **Mencuci bahan**: membuang data dobel/rusak, merapikan teks, menyamakan jam ke WIB.
4. **Merakit**: menggabungkan cuaca dan gempa berdasarkan jam yang sama dan wilayah yang sama.
5. **Kontrol kualitas**: uji otomatis (`assert`) bahwa hasilnya benar.
6. **Mencari kejanggalan**: mendeteksi "lonjakan" (nilai yang tiba-tiba melonjak/anjlok).
7. **Menilai detektor**: kita sengaja menyelipkan kejanggalan palsu yang kita catat di
   "kunci jawaban", lalu mengukur berapa banyak yang ditemukan detektor (precision & recall).
8. **Uji ketahanan**: sengaja membuat 3 kegagalan (file hilang, kolom kurang, internet mati)
   dan memastikan program tidak crash, tetapi mencatat pesan yang jelas di log.
9. **Menulis laporan** secara otomatis.

Semua langkah dicatat di **file log** (`logs/pipeline.log`) dan semua angka penting
(alamat API, koordinat, ambang batas, nama file) disimpan di **file konfigurasi**
`config/config.json`, bukan ditulis langsung di dalam kode.

---

## 2. Struktur folder

```
pipeline_cuaca_gempa/
├── siapkan_env.py           <- membuat venv + memasang library otomatis
├── unduh_data.py            <- unduh data ASLI (tanpa cadangan sintetis)
├── run_pipeline.py          <- SATU perintah untuk menjalankan semuanya
├── PANDUAN_WINDOWS.md       <- panduan lengkap Windows
├── PANDUAN_LINUX.md         <- panduan lengkap Linux (Fedora/Ubuntu/Arch)
├── PANDUAN_FEDORA.md        <- panduan rinci khusus Fedora
├── requirements.txt         <- daftar library Python yang dibutuhkan
├── config/
│   └── config.json          <- SEMUA parameter (endpoint, koordinat, ambang, path)
├── src/                     <- kode program, satu file per tahap
│   ├── utils.py             <- baca config, siapkan log, kelas error
│   ├── akuisisi.py          <- TAHAP 1: ambil data API (timeout, retry, cache)
│   ├── data_sintetis.py     <- cadangan data palsu berlabel jika internet mati
│   ├── validasi.py          <- TAHAP 2: JSON -> tabel, cek kolom wajib
│   ├── pembersihan.py       <- TAHAP 3: regex, zona waktu WIB, buang duplikat
│   ├── penggabungan.py      <- TAHAP 4: join per jam + filter radius lokasi
│   ├── uji_kualitas.py      <- TAHAP 5: 5 uji assert
│   ├── penanam_anomali.py   <- TAHAP 6: tanam anomali + tulis berkas kunci
│   ├── detektor.py          <- TAHAP 7: moving average + k·sigma (TIDAK baca kunci)
│   ├── evaluasi.py          <- TAHAP 8: precision & recall
│   ├── analisis.py          <- TAHAP 9: statistik per jam + korelasi
│   ├── simulasi_gagal.py    <- TAHAP 10: 3 skenario gagal
│   └── laporan.py           <- TAHAP 11: laporan otomatis
├── data/
│   ├── raw/                 <- JSON mentah (cache) dari API
│   ├── processed/           <- data bersih & data gabungan (.csv)
│   └── kunci/               <- kunci_anomali.csv (kunci jawaban, terpisah!)
├── logs/
│   └── pipeline.log         <- log contoh hasil eksekusi
├── tests/
│   └── test_kualitas.py     <- uji dengan pytest
└── output/                  <- laporan_evaluasi.md + tabel .csv
```

---

## 3. Cara menjalankan (step by step)

### Langkah 1: Pasang Python
Pastikan Python 3.9 atau lebih baru sudah terpasang. Cek di terminal / Command Prompt:
```bash
python --version
```

### Langkah 2: Masuk ke folder proyek
```bash
cd pipeline_cuaca_gempa
```

### Langkah 3 (disarankan): Buat virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate
```

### Langkah 4: Pasang library
```bash
pip install -r requirements.txt
```
Hanya butuh 4 library: `pandas`, `numpy`, `requests`, `pytest`.

### Langkah 5: Jalankan pipeline (SATU perintah)
```bash
python run_pipeline.py
```
Tunggu sampai muncul tulisan `SELESAI dalam ... detik`.

### Langkah 6: Lihat hasilnya
- Buka `output/laporan_evaluasi.md` (bisa dibuka di VS Code, lalu tekan `Ctrl+Shift+V` untuk preview).
- Buka `output/tabel_anomali.csv` dengan Excel.
- Buka `logs/pipeline.log` untuk melihat catatan setiap langkah.

### Langkah 7 (opsional): Jalankan uji dengan pytest
```bash
python -m pytest tests -v
```
Harus muncul `8 passed`.

### Opsi tambahan
```bash
python run_pipeline.py --tanpa-simulasi              # lewati simulasi 3 skenario gagal
python run_pipeline.py --config config/config.json   # pakai file config tertentu
```

---

## 4. PENTING: data asli vs data sintetis

Pipeline mencoba sumber data dengan urutan ini:

| Urutan | Sumber | Label di laporan |
|---|---|---|
| 1 | Cache lokal di `data/raw/` (kalau sudah pernah berhasil unduh) | `CACHE` |
| 2 | API internet (Open-Meteo & USGS) | `API` |
| 3 | Data sintetis: **NONAKTIF** (`fallback_sintetis.aktif = false` di config). Kalau 1 dan 2 gagal, pipeline berhenti dengan pesan jelas | - |

- Saat pertama kali dijalankan **dengan internet**, data asli diunduh dan disimpan ke
  `data/raw/cuaca_openmeteo_2024-01-01_2024-12-31.json` dan `data/raw/gempa_usgs_...json`.
  Setelah itu pipeline bisa dijalankan **tanpa internet** dan hasilnya sama persis.
- Semua data dan hasil contoh yang memakai data sintetis sudah **dihapus**. Folder `data/` dan `output/` kosong sampai kalian menjalankan pipeline dengan internet.
- (Catatan lama:) hasil contoh sebelumnya dibuat di server tanpa internet dengan data **SINTETIS**. Laporannya diberi peringatan
  besar. **Untuk laporan tugas, jalankan ulang di laptop kalian yang terhubung internet**,
  maka label akan berubah menjadi `API` lalu `CACHE`.
- File sintetis disimpan dengan nama `..._SINTETIS.json` dan TIDAK pernah dianggap cache.
- Ingin mengunduh ulang data asli? Hapus file `.json` di `data/raw/` lalu jalankan lagi.

---

## 5. Penjelasan tiap tahap

### Tahap 1: Akuisisi (`src/akuisisi.py`)
- `requests.get(..., timeout=30)` -> request dibatalkan jika lebih dari 30 detik.
- `try-except` menangkap `Timeout`, `ConnectionError`, error HTTP 429/5xx.
- **Retry** maksimal 3 kali dengan jeda **bertahap** 2 s, 4 s (exponential backoff).
- JSON mentah disimpan ke `data/raw/` (cache).
- Cuaca diminta dalam UTC, wilayah titik pusat `(-8.5, 113.0)`.
- Gempa diminta dalam radius 500 km dari titik pusat, magnitudo >= 2.5.

### Tahap 2: Validasi skema (`src/validasi.py`)
- JSON diubah menjadi tabel (DataFrame).
- Dicek apakah semua **kolom wajib** di config ada. Jika tidak, muncul `SkemaError` dan
  pipeline berhenti rapi dengan pesan yang menyebut kolom apa yang hilang.

### Tahap 3: Pembersihan (`src/pembersihan.py`)
- **Regex 1** memeriksa format waktu cuaca `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$`.
- **Regex 2** merapikan teks lokasi gempa (`"  97km  SSW of   Jember ,Indonesia"` ->
  `"97 km SSW of Jember, Indonesia"`).
- **Regex 3** memecah teks lokasi menjadi kolom `jarak_km`, `arah`, `kota_terdekat`, `negara`.
- Waktu UTC diubah ke **Asia/Jakarta (WIB)**.
- Membuang: id gempa dobel, kejadian bukan `earthquake`, magnitudo kosong,
  gempa di luar radius (dihitung ulang dengan rumus **haversine**), jam cuaca dobel.
- Nilai di luar rentang fisis (mis. kelembapan > 100%) diubah menjadi kosong lalu diisi
  interpolasi bila celahnya <= 3 jam.

### Tahap 4: Penggabungan (`src/penggabungan.py`)
- Waktu gempa dibulatkan ke bawah ke jam (14:37 -> 14:00).
- Gempa di jam yang sama diringkas: `gempa_jumlah`, `gempa_mag_maks`, `gempa_mag_rata`,
  `gempa_kedalaman_rata`, `gempa_jarak_min_km`.
- **Left join** ke tabel cuaca: setiap jam tetap ada (8.784 jam untuk tahun 2024),
  jam tanpa gempa diberi `gempa_jumlah = 0`.
- Dicatat persentase gempa yang berhasil mendapat pasangan jam (akurasi penyelarasan).

### Tahap 5: Uji assert (`src/uji_kualitas.py`)
| Uji | Yang diperiksa |
|---|---|
| `uji_jumlah_kolom` | minimal 4 kolom utama, 6 kolom utama ada |
| `uji_tipe_dan_rentang` | waktu bertipe datetime WIB, angka dalam rentang fisis |
| `uji_kunci_join_non_null` | kolom `waktu_lokal` tidak ada yang kosong |
| `uji_tanpa_duplikat_timestamp` | tidak ada jam dobel |
| `uji_jumlah_baris` | >= 5.000 baris atau seluruh rentang jam utuh |

### Tahap 6: Penanaman anomali (`src/penanam_anomali.py`)
- Dipilih acak (seed tetap = 7) 20 jam untuk suhu dan 20 jam untuk tekanan.
- Nilainya digeser naik/turun sebesar 3 sampai 8 kali simpangan baku.
- Data yang sudah ditanami -> `data/processed/data_uji_anomali.csv` (dibaca detektor).
- Daftar jam yang ditanami -> `data/kunci/kunci_anomali.csv` (kunci jawaban).

### Tahap 7: Detektor (`src/detektor.py`)
Untuk setiap jam *t*:
```
rata2  = rata-rata 24 jam sebelum t
sigma  = simpangan baku 24 jam sebelum t
LONJAKAN jika  nilai_t > rata2 + k*sigma   atau   nilai_t < rata2 - k*sigma   (k = 4)
```
Detektor **tidak pernah membaca** berkas kunci. Ini dibuktikan oleh uji
`test_detektor_tidak_membaca_kunci` di `tests/test_kualitas.py`.

### Tahap 8: Evaluasi (`src/evaluasi.py`)
- **TP**: alarm benar, **FP**: alarm palsu, **FN**: anomali terlewat.
- `precision = TP / (TP + FP)`: dari semua alarm, berapa yang benar.
- `recall    = TP / (TP + FN)`: dari semua anomali, berapa yang tertangkap.

### Tahap 9: Analisis (`src/analisis.py`)
- **Statistik per jam** (00 sampai 23 WIB): rata-rata suhu, kelembapan, tekanan, hujan,
  jumlah gempa, jumlah lonjakan.
- **Korelasi harian** (Pearson & Spearman) antara perubahan tekanan, suhu, hujan dan jumlah /
  magnitudo gempa, dengan p-value perkiraan dan **daftar batasan** (korelasi bukan sebab-akibat, dll.).

### Tahap 10: Simulasi gagal (`src/simulasi_gagal.py`)
| Skenario | Cara membuatnya | Error yang tertangkap |
|---|---|---|
| 1a. Config hilang | baca `config_yang_tidak_ada.json` | `ConfigError` |
| 1b. File input hilang | baca CSV yang tidak ada | `FileNotFoundError` |
| 2. Kolom kurang | hapus kolom `pressure_msl` lalu validasi | `SkemaError` |
| 3a. Jaringan mati | request ke port tertutup `127.0.0.1:9` | `AkuisisiError` (ConnectionError) |
| 3b. Timeout | server lokal yang tidak pernah menjawab | `AkuisisiError` (ReadTimeout) |

Semua tercatat di `logs/pipeline.log` dan `output/hasil_simulasi_gagal.csv`.
Coba juga sendiri: `python run_pipeline.py --config config/tidak_ada.json`, program
berhenti rapi (exit code 1) dan menulis pesan ke `logs/pipeline_error.log`.

### Tahap 11: Laporan (`src/laporan.py`)
Menulis `output/laporan_evaluasi.md` dan semua tabel `.csv`.

---

## 6. Mengubah pengaturan tanpa mengubah kode

Semua di `config/config.json`. Contoh:

| Ingin... | Ubah |
|---|---|
| Wilayah lain | `wilayah.lat_pusat`, `wilayah.lon_pusat`, `wilayah.radius_km` |
| Rentang waktu lebih panjang | `periode.tanggal_mulai`, `periode.tanggal_selesai` |
| Detektor lebih/kurang sensitif | `detektor.k_sigma` (kecil = lebih sensitif), `detektor.jendela_jam` |
| Gempa lebih banyak | turunkan `api.usgs.magnitudo_min` atau perbesar `radius_km` |
| Retry lebih sabar | `jaringan.timeout_detik`, `jaringan.maks_percobaan` |

Setelah mengubah wilayah/periode, nama file cache otomatis ikut berubah, jadi data baru
akan diunduh.

---

## 7. Hubungan dengan proposal

| Proposal | Di mana |
|---|---|
| Struktur folder modular + config JSON | Bagian 2, `config/config.json` |
| Fungsi terpisah tiap tahap | `src/*.py` |
| Timeout, try-except, retry, cache JSON mentah | `src/akuisisi.py` |
| Regex + zona waktu Asia/Jakarta | `src/pembersihan.py` |
| Minimal 3 uji assert | `src/uji_kualitas.py` (5 uji) + `tests/` |
| >= 5.000 baris, tanpa duplikat timestamp | 8.784 baris, uji 4 dan 5 |
| Moving average + k·σ | `src/detektor.py` |
| Berkas kunci terpisah, tidak dibaca detektor | `data/kunci/`, uji isolasi |
| Precision & recall | `src/evaluasi.py`, `output/metrik_detektor.csv` |
| 3 skenario gagal tanpa crash | `src/simulasi_gagal.py` |
| Logging ke file | `logs/pipeline.log` |
| Satu perintah | `python run_pipeline.py` |
| Laporan otomatis + batasan korelasi | `output/laporan_evaluasi.md` |
