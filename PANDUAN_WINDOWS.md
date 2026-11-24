# Panduan Lengkap untuk Windows (Pemula)

Dari nol sampai kalian bisa melihat laporan dengan **data asli** (Open-Meteo dan USGS).
Perkiraan waktu: 15 sampai 30 menit. Kali pertama butuh internet.

> Catatan: virtual environment (`venv`) dan library dipasang **otomatis** saat pertama kali
> program dijalankan. Kalian TIDAK perlu mengetik `python -m venv venv` atau mengaktifkannya.

---

## LANGKAH 1: Pasang Python

1. Buka https://www.python.org/downloads/ lalu unduh Python 3.10 atau lebih baru (tombol kuning "Download Python").
2. Jalankan installer. **Centang kotak "Add python.exe to PATH"** di bagian bawah jendela pertama, lalu klik **Install Now**.
3. Tutup installer, lalu buka terminal baru (lihat Langkah 3) dan cek:
   ```
   python --version
   ```
   Harus muncul `Python 3.x.x`. Kalau yang muncul pesan "Python was not found" / membuka Microsoft Store:
   - ulangi instalasi dengan mencentang "Add python.exe to PATH", atau
   - coba `py --version` (Python Launcher). Kalau `py` berhasil, pakai `py` sebagai pengganti `python` di semua perintah di bawah.
   - atau matikan alias Store: Settings > Apps > Advanced app settings > App execution aliases > matikan `python.exe` dan `python3.exe`.

## LANGKAH 2: Ekstrak proyek

1. Unduh `pipeline_cuaca_gempa.zip` dari thread ini (biasanya di folder **Downloads**).
2. Klik kanan zip > **Extract All...** > Extract. Misalnya hasilnya:
   `C:\Users\NamaKamu\Documents\pipeline_cuaca_gempa`
3. Pastikan di dalamnya langsung terlihat `run_pipeline.py`, `unduh_data.py`, folder `src`, `config`, dst.
   (Kalau ada folder ganda `pipeline_cuaca_gempa\pipeline_cuaca_gempa`, masuk ke yang paling dalam.)

## LANGKAH 3: Buka terminal di folder proyek

Cara termudah:
1. Buka folder proyek di File Explorer.
2. Klik **kolom alamat** (di atas), hapus isinya, ketik `cmd`, tekan Enter.
3. Jendela hitam (Command Prompt) terbuka tepat di folder proyek.

Atau lewat perintah (ganti NamaKamu; pakai tanda kutip kalau path ada spasi):
```
cd "C:\Users\NamaKamu\Documents\pipeline_cuaca_gempa"
```
Cek isi folder:
```
dir
```

## LANGKAH 4: (Hanya jika ada sisa data lama) bersihkan hasil lama

Zip terbaru sudah bersih, jadi biasanya **lewati langkah ini**. Jika folder kalian pernah berisi hasil lama:
```
del /q data\raw\*.json data\processed\*.csv data\kunci\*.csv output\*.csv output\*.md logs\*.log
```
(Pesan "Could Not Find ..." boleh diabaikan. Ini hanya menghapus file hasil, bukan kode.)

## LANGKAH 5: Unduh data asli

```
python unduh_data.py
```
Kali pertama, kalian akan melihat `[siapkan_env] Library belum terpasang...` lalu pemasangan otomatis
(1 sampai 2 menit). Setelah itu unduhan dimulai. Hasil yang benar:
```
[Open-Meteo] Berhasil (HTTP 200, ... byte)
[USGS] Berhasil (HTTP 200, ... byte)
Cuaca : 8,784 jam      (sumber: API)
Gempa : 3xx kejadian   (sumber: API)
Data asli siap. Lanjutkan dengan: python run_pipeline.py
```
Cek file unduhan:
```
dir data\raw
```
Harus ada `cuaca_openmeteo_2024-01-01_2024-12-31.json` dan `gempa_usgs_2024-01-01_2024-12-31.json`.

## LANGKAH 6: Jalankan pipeline (SATU perintah)

```
python run_pipeline.py
```
Tunggu sekitar 20 detik. Di akhir muncul `SELESAI dalam ... detik`. Label sumber data di laporan
akan **CACHE** (artinya data asli hasil unduhan Langkah 5).

## LANGKAH 7: Lihat output

| Berkas | Cara membuka (di Command Prompt) |
|---|---|
| `output\laporan_evaluasi.md` | `notepad output\laporan_evaluasi.md` (atau buka di VS Code, tekan `Ctrl+Shift+V` untuk tampilan rapi) |
| `output\tabel_anomali.csv` | `start output\tabel_anomali.csv` (terbuka di Excel) |
| `output\metrik_detektor.csv` | `start output\metrik_detektor.csv` |
| `output\statistik_per_jam.csv` | `start output\statistik_per_jam.csv` |
| `output\korelasi.csv` | `start output\korelasi.csv` |
| `output\hasil_simulasi_gagal.csv` | `start output\hasil_simulasi_gagal.csv` |
| `data\processed\data_gabungan.csv` | `start data\processed\data_gabungan.csv` |
| `data\kunci\kunci_anomali.csv` | `start data\kunci\kunci_anomali.csv` |
| `logs\pipeline.log` | `notepad logs\pipeline.log` |

Buka seluruh folder hasil: `start output`

### Daftar centang membaca laporan
1. **Bagian 1:** sumber berlabel **CACHE** atau **API**; baris gabungan >= 5.000 (setahun: 8.784); duplikat timestamp = 0.
2. **Bagian 2:** persentase gempa yang dipasangkan ke jam cuaca (idealnya mendekati 100%).
3. **Bagian 3:** semua uji assert **LULUS** (5/5).
4. **Bagian 4:** statistik per jam (suhu tertinggi biasanya sekitar siang).
5. **Bagian 5:** precision (dari semua alarm, berapa persen benar) dan recall (dari semua anomali, berapa persen tertangkap).
6. **Bagian 6:** korelasi cuaca vs gempa, hampir pasti lemah. Itu wajar karena gempa tektonik tidak dipicu cuaca. Jelaskan bersama daftar batasan di laporan.
7. **Bagian 7:** semua skenario gagal berstatus **TERTANGANI**.

## LANGKAH 8: Uji otomatis (pytest)

Setelah langkah 5 atau 6, folder `venv` sudah ada. Jalankan:
```
venv\Scripts\python.exe -m pytest tests -v
```
Harus `8 passed`.

## LANGKAH 9: Mengubah pengaturan tanpa mengubah kode

Buka `config\config.json` dengan Notepad (`notepad config\config.json`).

| Tujuan | Yang diubah |
|---|---|
| Detektor lebih sensitif (recall naik) | `detektor.k_sigma` dari 4.0 menjadi 3.0 |
| Wilayah lain | `wilayah.lat_pusat`, `lon_pusat`, `radius_km` |
| Gempa terlalu sedikit | perbesar `radius_km` atau perpanjang `periode` |

Jika mengubah `wilayah` atau `periode`: jalankan lagi `python unduh_data.py` lalu `python run_pipeline.py`.
Jika hanya mengubah `k_sigma`: cukup `python run_pipeline.py`.

## LANGKAH 10: Demo skenario gagal (untuk presentasi)

1. Config hilang:
   ```
   python run_pipeline.py --config config\tidak_ada.json
   echo %ERRORLEVEL%
   type logs\pipeline_error.log
   ```
   `%ERRORLEVEL%` bernilai 1 (berhenti rapi, bukan crash).
2. Jaringan mati: matikan Wi-Fi, hapus cache (`del data\raw\*.json`), jalankan `python unduh_data.py`.
   Hasilnya pesan KONEKSI GAGAL dan percobaan ulang 3 kali. Nyalakan Wi-Fi lalu ulangi.
3. Kolom kurang dan timeout otomatis diuji di tahap 10 pipeline (lihat `output\hasil_simulasi_gagal.csv`).

## Masalah umum

| Masalah | Solusi |
|---|---|
| `'python' is not recognized` | Instal ulang dengan centang "Add to PATH", atau pakai `py` |
| Terminal dibuka sebelum instal selesai | Tutup dan buka Command Prompt baru |
| `GAGAL membuat venv` / `GAGAL memasang library` | Cek internet, matikan VPN, jalankan ulang perintahnya. Atau manual: `python -m venv venv` lalu `venv\Scripts\pip install -r requirements.txt` |
| Antivirus memblokir pemasangan | Izinkan folder proyek, jalankan ulang |
| `UNDUH GAGAL ... KONEKSI GAGAL` | Cek internet, buka https://open-meteo.com dan https://earthquake.usgs.gov di browser, coba lagi |
| `HTTP 429` | Tunggu beberapa menit lalu ulangi |
| Gempa sangat sedikit (< 30) | Perbesar `radius_km`, hapus `data\raw\*.json`, unduh ulang |
| Excel menampilkan semua kolom dalam satu kolom | Data > Text to Columns > Delimited > Comma |

## Ringkasan perintah (Command Prompt)

```
cd "C:\Users\NamaKamu\Documents\pipeline_cuaca_gempa"
python unduh_data.py
python run_pipeline.py
venv\Scripts\python.exe -m pytest tests -v
notepad output\laporan_evaluasi.md
```

## Atribusi data (cantumkan di laporan dan presentasi)

- Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com
- Earthquake data from USGS (domain publik), https://earthquake.usgs.gov
