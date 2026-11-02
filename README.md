# Alat Bantu Data Skripsi: ESG Disclosure & Rasio Keuangan

Proyek ini berisi **dua program** yang bekerja dari file PDF:

| Program | Membaca | Mengisi | Perintah |
|---|---|---|---|
| **A. Skor ESG Disclosure** (folder `esg_disclosure/`) | Laporan Keberlanjutan | sheet **ESGD** di *DATA SKRIPSI.xlsx* | `python3 esg.py ...` |
| **B. Rasio Keuangan** (folder `rasio_keuangan/`) | Laporan Tahunan (laporan keuangan auditan) | sheet **CoD** & **Vab. X** di *RATIO DATA SKRIPSI.xlsx* | `python3 rasio.py ...` |

Keduanya mengikuti contoh perusahaan **DEWA** yang sudah diisi manual, dan bisa dipakai untuk
**perusahaan mana pun**: cukup tambahkan folder baru berisi PDF laporannya.

Bagian 1–10 menjelaskan program A. Program B dijelaskan di [bagian 11](#11-program-b-rasio-keuangan-cost-of-debt--vab-x).

---

## Daftar isi
1. [Status hasil saat ini](#1-status-hasil-saat-ini)
2. [Persiapan (sekali saja)](#2-persiapan-sekali-saja)
3. [Menyiapkan folder data](#3-menyiapkan-folder-data)
4. [Menjalankan program](#4-menjalankan-program)
5. [Membaca hasil](#5-membaca-hasil)
6. [Aturan penilaian yang dipakai](#6-aturan-penilaian-yang-dipakai)
7. [Cara kerja program (Python & Machine Learning)](#7-cara-kerja-program-python--machine-learning)
8. [Menambah perusahaan lain](#8-menambah-perusahaan-lain)
9. [Melatih ulang & menguji model](#9-melatih-ulang--menguji-model)
10. [Masalah yang sering terjadi](#10-masalah-yang-sering-terjadi)
11. [Program B: Rasio Keuangan (Cost of Debt & Vab. X)](#11-program-b-rasio-keuangan-cost-of-debt--vab-x)

---

## 1. Status hasil saat ini

Seluruh **25 laporan** (DOID, DSSA, ELSA, INDY, ITMG × 2020–2024) sudah dinilai. File hasil ada di folder [`hasil/`](hasil):

| File | Isi |
|---|---|
| `hasil/DATA SKRIPSI - HASIL.xlsx` | Excel DATA SKRIPSI dengan sheet ESGD terisi untuk kelima perusahaan (DEWA tetap seperti aslinya) |
| `hasil/BUKTI PENILAIAN - DATA SKRIPSI.xlsx` | Ringkasan skor + alasan/bukti setiap poin (halaman PDF) |

**Skor ESG Disclosure**

| Perusahaan | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| DEWA (manual, dikoreksi) | 0,6849 | 0,5391 | 0,7500 | 0,7812 | 0,7812 |
| DOID | 0,3278 | 0,3490 | 0,8229 | 0,8854 | 0,8646 |
| DSSA | 0,3490 | 0,3490 | 0,6250 | 0,6458 | 0,7188 |
| ELSA | 0,3125 | 0,4062 | 0,3958 | 0,7812 | 0,7812 |
| INDY | 0,2757 | 0,8646 | 0,9062 | 0,8542 | 0,9167 |
| ITMG | 0,7448 | 0,7188 | 0,8750 | 1,0000 | 1,0000 |

**Akurasi terhadap penilaian manual DEWA (5 tahun, setelah koreksi): 590 dari 590 baris sama (100%).**
Empat nilai manual DEWA dikoreksi sesuai aturan (sudah dikonfirmasi): 2020 item 405-1 → 1 (indeks
hal. 149–150); 2021 item 405-1 → 0; 2022 item 410-1 dan 411-1 → 0 (nomor item tidak tertulis di laporan).
Di file hasil, blok DEWA memakai nilai yang sudah dikoreksi ini.

**Hal yang perlu Anda ketahui sebelum memakai hasil:**
- Penilaian **hanya berdasarkan nomor item** (2-1, 102-1, 305-1, dst.). Pembahasan topik tanpa
  menuliskan nomor itemnya **tidak** dihitung.
- Item yang **tercantum di indeks GRI tetapi kolom halamannya kosong/"-"** diberi **0**, kecuali
  nomor item itu tertulis di bagian lain laporan (baris ini ditandai oranye di file bukti).
- Kolom halaman/lokasi boleh berisi **angka halaman** atau **lokasi tertulis** (mis. "Appendix",
  "Lampiran", "Laporan Tahunan", alamat website) → poin 1. Contoh: INDY 2023 item 405-2 ("Appendix").
- **Daftar nomor item di pembuka bab** (mis. INDY 2020: "GRI ▶ 301-1, 302-1, 302-2, …") **tidak**
  dihitung, karena hanya judul/daftar isi bab tanpa penjelasan.
- Indeks GRI **INDY 2020** susunannya tidak rapi di sumbernya (satu kode dipakai untuk beberapa topik,
  mis. "GRI 301-1" muncul untuk bahan dan energi), jadi skornya sebaiknya dicek manual.
- **ITMG 2023 dan 2024 bernilai 1,0000** karena seluruh 96 item tercantum lengkap dengan halaman di indeks GRI.
- Laporan tahun 2020–2021 yang memakai opsi "Core" GRI 2016 hanya mencantumkan sebagian item 102-x
  sehingga skornya lebih rendah (itu sifat laporannya, bukan kesalahan baca).

## 2. Persiapan (sekali saja)

### a. Pasang Python
- **Windows**: unduh dari <https://www.python.org/downloads/> → saat memasang, **centang "Add Python to PATH"**.
- **Mac**: unduh dari <https://www.python.org/downloads/> lalu pasang seperti aplikasi biasa.

Cek dengan membuka **Terminal** (Mac) atau **Command Prompt** (Windows), lalu ketik:

```bash
python3 --version
```

(Di Windows, jika `python3` tidak dikenal, pakai `python` sebagai gantinya di semua perintah.)

### b. Unduh program ini
Di GitHub klik tombol hijau **Code → Download ZIP**, lalu ekstrak. Atau dengan git:

```bash
git clone https://github.com/MikaelSilvano/ESG.git
```

### c. Pasang paket yang dibutuhkan
Buka Terminal/Command Prompt **di dalam folder program** (folder yang berisi `esg.py`), lalu:

```bash
python3 -m pip install -r requirements.txt
```

---

## 3. Menyiapkan folder data

Salin folder **SKRIPSI** Anda ke dalam folder program, sehingga susunannya seperti ini:

```
ESG/                              <- folder program ini
├── esg.py
├── SKRIPSI/
│   ├── DATA SKRIPSI.xlsx         <- Excel dengan sheet "ESGD"
│   ├── RATIO DATA SKRIPSI.xlsx   <- Excel dengan sheet "CoD", "Vab. X", "kurs" (program B)
│   ├── LAPORAN TAHUNAN/          <- PDF laporan tahunan (program B), susunan sama: KODE/tahun.pdf
│   └── LAPORAN KEBERLANJUTAN/
│       ├── DEWA/  2020.pdf  2021.pdf  2022.pdf  2023.pdf  2024.pdf
│       ├── DOID/  2020.pdf  2021.pdf  ...
│       ├── DSSA/  ...
│       ├── ELSA/  ...
│       ├── INDY/  ...
│       └── ITMG/  ...
```

Aturan sederhana:
- **Nama folder = kode perusahaan** (DOID, ITMG, dst.).
- **Nama file PDF harus memuat tahun** (`2022.pdf`, `SR 2022.pdf`, `Laporan_2022.pdf` semuanya bisa).
- Jika satu tahun terdiri dari beberapa PDF, taruh saja semuanya; halamannya digabung otomatis.

> Folder `SKRIPSI/` tidak ikut terunggah ke GitHub (sudah diatur di `.gitignore`), jadi data Anda tetap di komputer Anda.

---

## 4. Menjalankan program

Buka Terminal/Command Prompt di folder program, lalu ketik:

```bash
python3 esg.py nilai
```

Selesai. Program akan:
1. Membaca semua folder perusahaan di `SKRIPSI/LAPORAN KEBERLANJUTAN`.
2. **Melewati perusahaan yang sudah terisi** di Excel (mis. DEWA), lalu menilai sisanya.
3. Menyimpan hasil ke folder `hasil/` (Excel asli **tidak diubah**).

Contoh tampilan saat berjalan:

```
== ITMG
   2020: 2020.pdf
      175 halaman, indeks GRI di hal. PDF 162-169 (GRI 2016), 1 dtk
      skor ESG Disclosure = 0.7448
```

### Pilihan tambahan (opsional)

| Kebutuhan | Perintah |
|---|---|
| Hanya perusahaan tertentu | `python3 esg.py nilai --perusahaan DOID ITMG` |
| Lokasi folder/Excel berbeda | `python3 esg.py nilai --laporan "D:/SKRIPSI/LAPORAN KEBERLANJUTAN" --excel "D:/SKRIPSI/DATA SKRIPSI.xlsx"` |
| Menilai ulang perusahaan yang sudah terisi | `python3 esg.py nilai --perusahaan ITMG --timpa` |
| Tanpa pemeriksaan model ML | `python3 esg.py nilai --tanpa-ml` |
| Nama file hasil sendiri | `python3 esg.py nilai --output "hasil/ESGD final.xlsx"` |

---

## 5. Membaca hasil

### `hasil/DATA SKRIPSI - HASIL.xlsx`
Sama persis dengan Excel Anda, ditambah blok kolom baru per perusahaan (5 kolom: 2020–2024)
di sebelah kanan DEWA, dengan format, judul, dan **rumus "RATA-RATA POIN PENGUNGKAPAN ESG"**
yang sama seperti DEWA.

### `hasil/BUKTI PENILAIAN - DATA SKRIPSI.xlsx`
- Sheet **RINGKASAN**: skor ESG Disclosure tiap perusahaan & tahun.
- Sheet **DETAIL**: setiap baris item, poin yang diberikan, dan **alasannya**, contoh:
  - `Indeks GRI hal. 34` → kode tercantum di tabel indeks GRI dengan rujukan halaman 34.
  - `Nomor item tertulis di laporan hal. PDF 49, 50` → nomor item (mis. "102-5") tertulis di isi laporan.
  - `Di indeks tanpa halaman, tetapi nomor item tertulis di laporan ...` → poin 1.
  - `Mengikuti item utama 102-7: ...` → sub-item (102-7-a-i, 102-8-d, 103-2-c-vi).
  - `Tercantum di indeks GRI tanpa halaman/lokasi ...` → poin 0.
  - `Nomor item tidak ditemukan` → poin 0.

Warna baris:
- 🟧 **Oranye** – item tercantum di indeks GRI tetapi tanpa halaman/lokasi → poin 0.
- 🟨 **Kuning** – model ML tidak setuju dengan aturan → mohon dicek manual (pada hasil saat ini: tidak ada).

> "hal. PDF" = urutan halaman di file PDF (yang tampil di pembaca PDF), bisa berbeda dengan nomor
> halaman yang tercetak di laporan.

---

## 6. Aturan penilaian yang dipakai

Penilaian **hanya melihat nomor item standar** (mis. 2-1, 102-1, 102-52, 305-1).

| Kondisi | Poin |
|---|---|
| Di tabel indeks GRI, item tercantum **dengan angka halaman/page atau lokasi tertulis** (mis. "Appendix") | 1 |
| Di tabel indeks GRI tanpa angka halaman ("-"/kosong), **tetapi nomor item tertulis** di bagian lain laporan | 1 |
| Tidak ada di tabel indeks GRI, **tetapi nomor item tertulis** di laporan | 1 |
| Di tabel indeks GRI tanpa angka halaman **dan** nomor item tidak tertulis di bagian lain laporan | 0 |
| Tidak ada di tabel indeks GRI dan nomor item tidak tertulis di laporan | 0 |
| Topik dibahas di laporan, tetapi nomor itemnya **tidak** ditulis (mis. membahas siklus pelaporan tanpa "102-52") | 0 |

"Nomor item tertulis di laporan" tidak menghitung halaman tabel indeks GRI itu sendiri, tabel
pemetaan sejenis (tabel SDGs/POJK yang hanya mendaftar kode), maupun daftar nomor item di pembuka
bab (mis. "GRI ▶ 301-1, 302-1, 302-2, …").

**Perbedaan standar GRI per tahun:**
- **2020–2021 (GRI 2016)** – baris governance dinilai **satu per satu** memakai kode kolom D
  (102-1, 102-3, 102-4, 102-5, dst.).
  Sub-item **102-7-a-i, 102-8-d, 103-2-c-vi** mendapat poin 1 bila item utamanya
  (102-7, 102-8, 103-2) diungkapkan, dan 0 bila tidak.
- **2022–2024 (GRI 2021)** – governance dinilai per item **2-x** (kolom C). **Semua baris** di bawah
  item yang sama diberi nilai yang sama (mis. 2-1 diungkapkan → 102-1, 102-3, 102-4, 102-5 semuanya 1).
- Item lingkungan (301–308) dan sosial (401–418) memakai kode yang sama di kedua periode.

**Pengaman otomatis:** bila laporan 2022+ ternyata masih memakai GRI 2016 (tidak ada kode 2-x),
item 2-x dinilai dari kode 102-x pengganti; bila laporan 2020–2021 sudah memakai GRI 2021, baris
102-x dinilai dari item 2-x-nya. Hal ini dicatat di file bukti.

**Skor ESG Disclosure** = rata-rata semua item. Baris governance dalam satu item (mis. empat baris
2-1) **dirata-rata dulu**, baru dirata-rata dengan item lainnya – persis rumus Excel DEWA
(29 item governance + 31 lingkungan + 36 sosial = 96 item).

---

## 7. Cara kerja program (Python & Machine Learning)

```
PDF ──► 1. Baca teks + posisi kata tiap halaman (PyMuPDF)
     ──► 2. Temukan tabel "GRI Content Index" & baca kolom Halaman/Page tiap kode
     ──► 3. Cari nomor item GRI di isi laporan, mis. "102-5", "(102-5)", "[305-1]", "GRI 2-9"
     ──► 4. Terapkan aturan skripsi (bagian 6) ──► isi Excel + file bukti
     ──► 5. Model ML (Logistic Regression) memeriksa ulang setiap poin
```

- **Langkah 2** membaca tata letak tabel (posisi kolom kode dan kolom "Halaman/Page"), sehingga
  bisa membedakan "kode dengan angka halaman" dan "kode tanpa halaman (- / kosong)". Tabel dua
  halaman berdampingan (spread) juga ditangani: angka dari tabel sebelah tidak ikut terbaca.
- **Langkah 5 (ML)**: model **Logistic Regression** dilatih dari penilaian manual DEWA 2020–2024
  dengan fitur: ada angka halaman di indeks, tercantum di indeks tanpa halaman, dan jumlah halaman
  yang menuliskan nomor item. Poin akhir tetap mengikuti aturan skripsi; bila model tidak setuju,
  baris diberi warna kuning di file bukti agar dicek. Model tersimpan di `model/model_esg.joblib`.
- Daftar item **dibaca langsung dari sheet ESGD**, jadi bila Anda menambah/mengubah item di Excel,
  program otomatis mengikutinya.

---

## 8. Menambah perusahaan lain

1. Buat folder baru dengan nama kode perusahaan, mis. `SKRIPSI/LAPORAN KEBERLANJUTAN/ADRO/`.
2. Masukkan PDF-nya: `2020.pdf`, `2021.pdf`, … `2024.pdf`.
3. Jalankan lagi:

```bash
python3 esg.py nilai
```

Perusahaan baru otomatis ditambahkan sebagai blok kolom baru. Agar perusahaan berikutnya ikut
dinilai di file yang sama, pakai file hasil sebelumnya sebagai input:

```bash
python3 esg.py nilai --excel "hasil/DATA SKRIPSI - HASIL.xlsx" --output "hasil/DATA SKRIPSI - HASIL 2.xlsx"
```

---

## 9. Melatih ulang & menguji model

Model bawaan sudah dilatih dari **DEWA 2020–2024** (5 laporan, 520 data). Bila Anda menambah atau
mengoreksi penilaian manual, latih ulang dengan:

```bash
python3 esg.py latih --perusahaan DEWA
```

Untuk melihat seberapa mirip hasil program dengan penilaian manual (baris yang berbeda ditampilkan):

```bash
python3 esg.py uji --perusahaan DEWA
```

Contoh keluaran:

```
== DEWA 2021
      cocok 117/118 baris | skor program 0.5391 vs manual 0.5495
        baris 112 405-1    program=0 manual=1 | Nomor item tidak ditemukan
Akurasi keseluruhan: 586/590 = 99.3%
```

Setiap kali Anda selesai mengoreksi hasil sebuah perusahaan secara manual di Excel, perusahaan itu
bisa dipakai juga sebagai data latih: `python3 esg.py latih --perusahaan DEWA ITMG`.

---

## 10. Masalah yang sering terjadi

| Pesan / masalah | Solusi |
|---|---|
| `File Excel tidak ditemukan` | Periksa nama file (`DATA SKRIPSI.xlsx`) atau tulis lokasinya dengan `--excel "..."` |
| `folder kosong (belum ada PDF)` | Masukkan PDF ke folder perusahaan tersebut |
| `Tabel indeks GRI tidak terdeteksi` | Laporan tanpa indeks GRI; penilaian hanya dari nomor item yang tertulis di laporan – cek manual file bukti |
| `kemungkinan PDF hasil scan` | PDF berupa gambar, teks tidak bisa dibaca; cari versi PDF lain dari situs perusahaan/BEI |
| `#DIV/0!` di baris rata-rata | Tahun tersebut belum ada PDF-nya (kolom kosong) |
| `python3` tidak dikenal (Windows) | Pakai `python` atau `py` sebagai gantinya |

---

## 11. Program B: Rasio Keuangan (Cost of Debt & Vab. X)

Program ini membaca **laporan posisi keuangan (neraca)** dan **laporan laba rugi** konsolidasian di
dalam laporan tahunan, lalu mengisi sheet **CoD** dan **Vab. X** pada *RATIO DATA SKRIPSI.xlsx*.

### 11.1 Hasil saat ini

| File | Isi |
|---|---|
| `hasil/RATIO DATA SKRIPSI - HASIL.xlsx` | Excel RATIO DATA SKRIPSI dengan sheet CoD & Vab. X terisi untuk DOID, DSSA, ELSA, INDY, ITMG (DEWA tetap seperti aslinya) |
| `hasil/BUKTI RASIO - RATIO DATA SKRIPSI.xlsx` | Bukti setiap angka: laporan tahunan sumber, halaman PDF, nama pos di laporan; rincian pos utang berbunga yang masuk/tidak masuk; daftar yang perlu dicek |

**Cost of Debt (CoD)** = Beban keuangan ÷ rata-rata utang berbunga (tahun t dan t-1)

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| DOID | 8,27% | 7,44% | 8,25% | 9,37% | 8,67% |
| DSSA | 9,84% | 13,15% | 8,31% | 6,02% | 5,28% |
| ELSA | 8,41% | 11,30% | 8,70% | 10,38% | 10,72% |
| INDY | 6,65% | 8,11% | 7,82% | 8,45% | 6,46% |
| ITMG | 4,61% | 6,59% | 5,62% | 6,43% | 13,82% |

Tahun mengikuti contoh DEWA: **Vab. X 2020–2024** dan **CoD 2021–2025**.

### 11.2 Menjalankan

Taruh PDF di `SKRIPSI/LAPORAN TAHUNAN/<KODE>/<tahun>.pdf` dan Excel di `SKRIPSI/RATIO DATA SKRIPSI.xlsx`, lalu:

```bash
python3 rasio.py isi
```

| Kebutuhan | Perintah |
|---|---|
| Hanya perusahaan tertentu | `python3 rasio.py isi --perusahaan DOID ITMG` |
| Isi ulang perusahaan yang sudah ada | `python3 rasio.py isi --perusahaan ITMG --timpa` |
| Lokasi berbeda | `python3 rasio.py isi --laporan "D:/SKRIPSI/LAPORAN TAHUNAN" --excel "D:/SKRIPSI/RATIO DATA SKRIPSI.xlsx"` |
| Melatih ulang model ML dari contoh DEWA | `python3 rasio.py latih` |
| Membandingkan hasil program dengan contoh DEWA | `python3 rasio.py uji` |

### 11.3 Data yang diambil & aturannya

| Kolom | Diambil dari laporan | Keterangan |
|---|---|---|
| Total Asset | Jumlah aset | |
| Total Asset (ribuan Rupiah) | rumus Excel | dikonversi memakai sheet **kurs** (USD → Rp) dan satuan (ribuan/jutaan) |
| Sales | Pendapatan / pendapatan usaha / pendapatan bersih | |
| Net Income | Laba (rugi) tahun berjalan | sebelum penghasilan komprehensif lain, termasuk kepentingan nonpengendali |
| Total Equity | Jumlah ekuitas | termasuk kepentingan nonpengendali |
| EBIT | **Laba usaha** bila disajikan; bila tidak, **laba bruto** | sama seperti contoh DEWA (2020–2023 laba usaha, 2024 laba bruto) |
| Interest Expense | Beban keuangan / beban bunga / finance cost | |
| Satuan Nominal (kolom O) | judul laporan ("Disajikan dalam …") | mis. *dolar AS*, *ribuan dolar AS*, *jutaan Rupiah* |
| Catatan (kolom P / H) | — | sumber laporan, definisi EBIT, konversi, pos utang yang dijumlahkan |

**Utang berbunga (CoD)** dijumlahkan dari pos-pos neraca (rumus `=a+b+c` seperti contoh DEWA):

- **Masuk:** pinjaman/utang bank (jangka pendek & panjang, termasuk bagian jatuh tempo satu tahun),
  utang sewa pembiayaan, liabilitas sewa / utang aset hak guna, obligasi, *notes*, sukuk, MTN,
  utang jangka panjang, pinjaman lain-lain, dan **utang lain-lain pihak ketiga yang berada di
  liabilitas jangka panjang atau bagian jatuh tempo satu tahun** (seperti DEWA).
- **Tidak masuk:** utang usaha, utang pajak, pendapatan diterima di muka/ditangguhkan, uang muka
  pelanggan, utang/pinjaman pihak berelasi, liabilitas pajak tangguhan, imbalan kerja/pascakerja,
  beban akrual, provisi, derivatif, liabilitas lainnya, utang lain-lain operasional di liabilitas
  jangka pendek.

**Ikuti data terbaru:** nilai tahun Y diambil dari **angka komparatif laporan tahun Y+1** bila ada
(karena bisa memuat koreksi), kalau tidak dari laporan tahun Y. Utang t-1 pada CoD tahun t diambil
dari kolom komparatif laporan tahun t.

**Satuan & mata uang:** dalam satu perusahaan semua angka diseragamkan ke satuan laporan terbaru;
bila ada perbedaan (seperti DEWA: dolar AS → ribuan Rupiah), program mengonversi otomatis
(memakai sheet *kurs*) dan menulis catatan. Kelima perusahaan ini satuannya sudah sama setiap tahun.

### 11.4 Cara kerja & Machine Learning

```
PDF ──► 1. Cari halaman neraca & laba rugi konsolidasian (bagian laporan keuangan auditan)
     ──► 2. Baca setiap baris: nama pos + angka tahun berjalan + angka tahun lalu (posisi kolom)
     ──► 3. Tentukan pos neraca: aset / liabilitas jangka pendek / jangka panjang / ekuitas
     ──► 4. Klasifikasi pos liabilitas: utang berbunga atau bukan (aturan + model ML)
     ──► 5. Pilih data terbaru, seragamkan satuan ──► isi Excel + file bukti
```

- **Model ML** (TF-IDF + Logistic Regression) dilatih dari contoh label (`rasio_keuangan/data/contoh_label.csv`)
  dan dari **pos-pos neraca DEWA yang dipakai di rumus contoh CoD** (`python3 rasio.py latih`).
  Model dipakai untuk pos liabilitas yang namanya tidak dikenali aturan; keputusan ML selalu dicatat
  di sheet *CEK MANUAL* file bukti.
- **Pemeriksaan otomatis:** untuk setiap laporan, jumlah semua pos liabilitas yang terbaca harus sama
  dengan "Jumlah liabilitas", dan total aset = total liabilitas + total ekuitas. Seluruh 36 laporan
  (6 perusahaan × 6 tahun) lolos kedua pemeriksaan ini.

### 11.5 Hasil uji terhadap contoh DEWA

`python3 rasio.py uji` membandingkan hasil program dengan isi manual DEWA: **29 dari 36 angka sama**.
Perbedaannya bukan salah baca program, melainkan:

| Bagian | Contoh DEWA | Program | Penyebab |
|---|---|---|---|
| Vab. X 2021 (aset, laba, ekuitas, EBIT) & utang 2021 | dari LT 2021 | dari LT 2022 (komparatif) | aturan "ikuti data terbaru"; LT 2022 menyajikan kembali angka 2021 |
| Utang berbunga 2023 | 1.555.419.659 | 1.410.840.712 | contoh ikut menjumlahkan *liabilitas imbalan pascakerja* 144.578.947 (seharusnya tidak masuk) |
| Utang berbunga 2024 | 2.528.428.564 | 2.555.428.564 | salah ketik di contoh: 103.045.040, di laporan 130.045.040 |

Blok DEWA di Excel hasil **tidak diubah**; silakan koreksi manual bila setuju.

### 11.6 Hal yang perlu Anda ketahui

- **EBIT:** DSSA menyajikan *laba usaha* → EBIT = laba usaha. DOID, ELSA, INDY, ITMG tidak menyajikan
  laba usaha → EBIT = laba bruto. Tertulis di kolom Catatan.
- **INDY 2020** memakai angka yang disajikan kembali di LT 2021 (operasi yang dihentikan), sehingga
  pendapatan 2020 = 1.813.826.560 (bukan 2.077.212.345 seperti di LT 2020).
- **DSSA 2022** memakai angka yang disajikan kembali di LT 2023 (total aset 6.497.181.277).
- Utang lain-lain pihak ketiga yang berada di **liabilitas jangka pendek biasa** (DOID, DSSA, INDY) dianggap
  utang operasional (tidak berbunga). Bila menurut Anda harus masuk, ubah aturan di
  `rasio_keuangan/classify.py` lalu jalankan ulang.
- Pinjaman dari **pihak berelasi** (INDY) tidak dimasukkan sesuai aturan "utang pihak berelasi tidak termasuk".

## Struktur kode

```
esg.py                      <- program utama (python3 esg.py ...)
esg_disclosure/
  cli.py                    <- perintah nilai / latih / uji
  pdf_reader.py             <- membaca PDF (teks + posisi kata)
  gri_index.py              <- membaca tabel GRI Content Index
  body_tags.py              <- mencari nomor item GRI di isi laporan
  model.py                  <- melatih/memuat model Logistic Regression
  scorer.py                 <- aturan penilaian 0/1 & skor
  template.py               <- membaca struktur sheet ESGD
  excel_writer.py           <- menulis blok perusahaan ke Excel (format seperti DEWA)
model/model_esg.joblib      <- model ML terlatih (program A)
rasio.py                    <- program rasio keuangan (python3 rasio.py ...)
rasio_keuangan/
  cli.py                    <- perintah isi / latih / uji
  locate.py                 <- mencari halaman neraca & laba rugi
  parser.py                 <- membaca baris tabel laporan keuangan (label + angka)
  extract.py                <- mengambil total aset, pendapatan, laba, ekuitas, EBIT, beban keuangan, pos liabilitas
  classify.py               <- aturan + model ML utang berbunga
  dataset.py                <- aturan "data terbaru" & penyeragaman satuan/kurs
  units.py                  <- deteksi satuan (dolar AS, ribuan/jutaan Rupiah, ...)
  excel.py                  <- menulis sheet CoD & Vab. X
  data/contoh_label.csv     <- contoh label pos utang berbunga / bukan (boleh ditambah)
model/model_utang_berbunga.joblib <- model ML utang berbunga (program B)
tests/                      <- tes otomatis (python3 -m pytest)
```
