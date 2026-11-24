# Panduan Lengkap untuk Linux (Fedora, Ubuntu/Debian, Arch)

Dari nol sampai kalian bisa melihat laporan dengan **data asli** (Open-Meteo dan USGS).
Panduan yang lebih panjang khusus Fedora ada di [PANDUAN_FEDORA.md](PANDUAN_FEDORA.md).
Perkiraan waktu: 15 sampai 30 menit. Kali pertama butuh internet.

> Virtual environment (`venv`) dan library dipasang **otomatis** saat pertama kali program
> dijalankan. Kalian TIDAK perlu mengetik `python -m venv venv` atau `source venv/bin/activate`.
> Di Linux juga **tidak perlu mengatur PATH**.

---

## LANGKAH 1: Cek Python dan paket pendukung

```bash
python3 --version        # atau: python --version
```
Butuh Python 3.9 atau lebih baru. Jika perlu, pasang Python dan modul venv:

| Distro | Perintah |
|---|---|
| Fedora | `sudo dnf install -y python3 python3-pip unzip` |
| Ubuntu / Debian / Mint | `sudo apt update && sudo apt install -y python3 python3-venv python3-pip unzip` |
| Arch / Manjaro | `sudo pacman -S --needed python python-pip unzip` |

> Di Ubuntu/Debian, paket `python3-venv` **wajib** ada agar pembuatan venv otomatis berhasil.
> Kalau di sistem kalian perintahnya `python3` (bukan `python`), pakai `python3` di semua perintah di bawah.

## LANGKAH 2: Ekstrak proyek

```bash
cd ~/Downloads
unzip pipeline_cuaca_gempa.zip
cd pipeline_cuaca_gempa
ls
```
Harus terlihat: `README.md  config  data  logs  output  requirements.txt  run_pipeline.py  siapkan_env.py  src  tests  unduh_data.py`.

> Kalau folder kalian punya spasi, beri tanda kutip, contoh:
> `cd "$HOME/Documents/project akuisi data/pipeline_cuaca_gempa"`

## LANGKAH 3: (Hanya jika ada sisa data lama) bersihkan hasil lama

Zip terbaru sudah bersih, jadi biasanya **lewati**. Jika folder pernah berisi hasil lama:
```bash
rm -f data/raw/*.json data/processed/*.csv data/kunci/*.csv output/*.csv output/*.md logs/*.log
```

## LANGKAH 4: Cek internet

```bash
curl -sI https://archive-api.open-meteo.com | head -1
curl -sI https://earthquake.usgs.gov | head -1
```
Tiap baris harus menunjukkan `HTTP/...`. Kalau kosong, cek koneksi, VPN, atau proxy.

## LANGKAH 5: Unduh data asli

```bash
python3 unduh_data.py
```
Kali pertama muncul `[siapkan_env] Library belum terpasang...` lalu pemasangan otomatis (1 sampai 2 menit),
setelah itu unduhan dimulai. Hasil yang benar:
```
[Open-Meteo] Berhasil (HTTP 200, ... byte)
[USGS] Berhasil (HTTP 200, ... byte)
Cuaca : 8,784 jam      (sumber: API)
Gempa : 3xx kejadian   (sumber: API)
Data asli siap. Lanjutkan dengan: python run_pipeline.py
```
Cek: `ls -lh data/raw/`

## LANGKAH 6: Jalankan pipeline (SATU perintah)

```bash
python3 run_pipeline.py
```
Sekitar 20 detik. Akhirnya: `SELESAI dalam ... detik`. Label sumber di laporan: **CACHE** (data asli hasil Langkah 5).

## LANGKAH 7: Lihat output

```bash
ls -lh output/ data/processed/ data/kunci/ logs/
less output/laporan_evaluasi.md            # keluar dengan tombol q
xdg-open output/laporan_evaluasi.md        # buka di aplikasi
xdg-open output/tabel_anomali.csv          # buka di LibreOffice Calc
column -s, -t < output/metrik_detektor.csv # lihat cepat di terminal
less logs/pipeline.log
grep -E "WARNING|ERROR" logs/pipeline.log  # hanya peringatan dan error
```

| Berkas | Isi |
|---|---|
| `output/laporan_evaluasi.md` | Laporan utama otomatis |
| `output/tabel_anomali.csv` | Lonjakan yang ditemukan detektor (status TP/FP) |
| `output/metrik_detektor.csv` | Precision, recall, F1 |
| `output/statistik_per_jam.csv` | Statistik per jam 00 sampai 23 WIB |
| `output/korelasi.csv` | Korelasi cuaca vs gempa |
| `output/hasil_uji_assert.csv` | Hasil 5 uji assert |
| `output/hasil_simulasi_gagal.csv` | Hasil 5 skenario gagal |
| `data/processed/data_gabungan.csv` | Data gabungan (1 baris per jam) |
| `data/kunci/kunci_anomali.csv` | Kunci jawaban anomali (terpisah dari detektor) |
| `logs/pipeline.log` | Log eksekusi |

### Daftar centang membaca laporan
1. **Bagian 1:** sumber berlabel **CACHE** atau **API**; baris gabungan >= 5.000 (setahun: 8.784); duplikat timestamp = 0.
2. **Bagian 2:** persentase gempa dipasangkan ke jam cuaca (idealnya mendekati 100%).
3. **Bagian 3:** semua uji assert **LULUS** (5/5).
4. **Bagian 4:** statistik per jam.
5. **Bagian 5:** precision (dari semua alarm, berapa persen benar) dan recall (dari semua anomali, berapa persen tertangkap).
6. **Bagian 6:** korelasi, hampir pasti lemah. Wajar, karena gempa tektonik tidak dipicu cuaca.
7. **Bagian 7:** semua skenario gagal **TERTANGANI**.

## LANGKAH 8: Uji otomatis (pytest)

```bash
venv/bin/python -m pytest tests -v
```
Harus `8 passed`.

## LANGKAH 9: Mengubah pengaturan tanpa mengubah kode

```bash
nano config/config.json        # atau gedit / code
```
| Tujuan | Yang diubah |
|---|---|
| Detektor lebih sensitif (recall naik) | `detektor.k_sigma` dari 4.0 menjadi 3.0 |
| Wilayah lain | `wilayah.lat_pusat`, `lon_pusat`, `radius_km` |
| Gempa terlalu sedikit | perbesar `radius_km` atau perpanjang `periode` |

Jika mengubah `wilayah` atau `periode`: `python3 unduh_data.py` lalu `python3 run_pipeline.py`.
Jika hanya `k_sigma`: cukup `python3 run_pipeline.py`.

## LANGKAH 10: Demo skenario gagal (untuk presentasi)

```bash
python3 run_pipeline.py --config config/tidak_ada.json
echo $?                          # 1 = berhenti rapi, bukan crash
cat logs/pipeline_error.log
```
Jaringan mati: matikan Wi-Fi, `rm data/raw/*.json`, jalankan `python3 unduh_data.py`; hasilnya pesan KONEKSI GAGAL
dan percobaan ulang 3 kali. Nyalakan Wi-Fi lalu ulangi. Kolom kurang dan timeout sudah otomatis diuji di tahap 10
pipeline (`output/hasil_simulasi_gagal.csv`).

## Masalah umum

| Masalah | Solusi |
|---|---|
| `python: command not found` | Pakai `python3`, atau pasang Python (Langkah 1) |
| `GAGAL membuat venv` (Ubuntu/Debian) | `sudo apt install -y python3-venv`, lalu jalankan ulang |
| `GAGAL memasang library` | Cek internet, jalankan ulang. Atau manual: `venv/bin/pip install -r requirements.txt` |
| Library gagal dipasang di Python yang sangat baru | Pakai Python 3.12: Fedora `sudo dnf install python3.12` (lalu `rm -rf venv` dan jalankan `python3.12 unduh_data.py`) |
| `UNDUH GAGAL ... KONEKSI GAGAL` | Cek internet (Langkah 4), matikan VPN/proxy, coba lagi |
| `HTTP 429` | Tunggu beberapa menit lalu ulangi |
| `Permission denied` | Pastikan foldernya milik kalian: `ls -ld .` |
| Gempa sangat sedikit (< 30) | Perbesar `radius_km`, `rm data/raw/*.json`, unduh ulang |

## Ringkasan perintah

```bash
cd ~/Downloads && unzip pipeline_cuaca_gempa.zip && cd pipeline_cuaca_gempa
python3 unduh_data.py
python3 run_pipeline.py
venv/bin/python -m pytest tests -v
less output/laporan_evaluasi.md
```

## Atribusi data (cantumkan di laporan dan presentasi)

- Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com
- Earthquake data from USGS (domain publik), https://earthquake.usgs.gov
