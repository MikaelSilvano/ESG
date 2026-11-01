# Penilai Skor ESG Disclosure Otomatis

Program ini **membaca Laporan Keberlanjutan (PDF)** setiap perusahaan, lalu **mengisi poin 0/1**
untuk setiap item GRI Standards di sheet **ESGD** pada Excel **DATA SKRIPSI**, persis seperti
contoh perusahaan **DEWA**. Skor ESG Disclosure tiap tahun langsung terhitung oleh rumus di Excel.

Bisa dipakai untuk **perusahaan mana pun**: cukup tambahkan folder baru berisi PDF laporannya.

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
| DEWA (manual, contoh) | 0,6745 | 0,5495 | 0,7708 | 0,7812 | 0,7812 |
| DOID | 0,3625 | 0,3490 | 0,8229 | 0,8854 | 0,8646 |
| DSSA | 0,3490 | 0,3490 | 0,6250 | 0,6458 | 0,7188 |
| ELSA | 0,3125 | 0,4062 | 0,3958 | 0,7812 | 0,7812 |
| INDY | 0,2757 | 0,8646 | 0,9062 | 0,8438 | 0,9167 |
| ITMG | 0,7448 | 0,7188 | 0,8750 | 1,0000 | 1,0000 |

**Akurasi terhadap penilaian manual DEWA (5 tahun): 586 dari 590 baris sama (99,3%).**
Catatan jujur: model ML juga dilatih dari data DEWA yang sama, jadi angka ini belum membuktikan
akurasi pada perusahaan lain. Karena itu hasil lima perusahaan **mohon dicek sampel**, terutama
baris berwarna oranye di file bukti.

**Hal yang perlu Anda ketahui sebelum memakai hasil:**
- Hasil ini menilai **poin 1 hanya jika** ada rujukan halaman di tabel indeks GRI **atau** paragraf
  bertanda kode GRI. Penjelasan tanpa kode & tanpa indeks **tidak otomatis** diberi 1 (pada
  penilaian DEWA pun kata kunci saja tidak cukup). Pada 262 baris berpoin 0, kata kunci item
  ditemukan di laporan dan ditandai **oranye** di file bukti; periksa dan ubah ke 1 di Excel bila perlu.
  Pada pengujian ini komponen ML tidak memberi poin tambahan satu pun (tidak ada baris kuning).
- Indeks GRI **INDY 2020** susunannya tidak rapi di sumbernya (satu kode dipakai untuk beberapa topik,
  mis. "GRI 301-1" muncul untuk bahan dan energi), jadi skor 0,2757 sebaiknya dicek manual.
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
| Tanpa komponen ML (murni aturan indeks GRI) | `python3 esg.py nilai --tanpa-ml` |
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
  - `Penjelasan bertanda kode di hal. PDF 49, 50` → ada paragraf berlabel kode GRI di isi laporan.
  - `Mengikuti item utama 102-7: ...` → sub-item (102-7-a-i, 102-8-d, 103-2-c-vi).
  - `Tidak ditemukan` → poin 0.

Warna baris yang **perlu Anda cek manual**:
- 🟨 **Kuning** – poin 1 yang diberikan oleh model ML (penjelasan tanpa kode/indeks).
- 🟧 **Oranye** – poin 0, tetapi kata kunci item tersebut muncul di laporan (tertulis halaman PDF-nya).
  Bila menurut Anda isinya memang penjelasan item tersebut, ubah poinnya menjadi 1 di Excel.

> "hal. PDF" = urutan halaman di file PDF (yang tampil di pembaca PDF), bisa berbeda dengan nomor
> halaman yang tercetak di laporan.

---

## 6. Aturan penilaian yang dipakai

| Kondisi | Poin |
|---|---|
| Ada penjelasan di laporan **dan** ada rujukan halaman/lokasi di tabel indeks GRI | 1 |
| Ada penjelasan di laporan, **tidak** ada di tabel indeks GRI | 1 |
| **Tidak** ada penjelasan, tetapi ada rujukan halaman/lokasi di tabel indeks GRI | 1 |
| Tidak ada penjelasan **dan** tidak ada rujukan halaman/lokasi di tabel indeks GRI | 0 |

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
     ──► 3. Cari tanda kode GRI di isi laporan, mis. "(102-5)", "[305-1]", "GRI 2-9"
     ──► 4. Model ML (TF-IDF + Logistic Regression) menilai apakah item dijelaskan
            walaupun tanpa kode
     ──► 5. Terapkan aturan skripsi (bagian 6) ──► isi Excel + file bukti
```

- **Langkah 2** membaca tata letak tabel (posisi kolom kode dan kolom "Halaman/Page"), sehingga
  bisa membedakan "kode dengan nomor halaman" dan "kode tanpa halaman / tidak relevan".
- **Langkah 4 (ML)**: setiap halaman diubah menjadi vektor **TF-IDF**, dibandingkan dengan deskripsi
  item GRI (judul Indonesia/Inggris + kata kunci di `esg_disclosure/data/gri_catalog.json`).
  Fitur-fitur tersebut dimasukkan ke model **Logistic Regression** yang **dilatih dari penilaian
  manual DEWA**, sehingga program meniru cara Anda menilai. Model tersimpan di `model/model_esg.joblib`.
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
        baris 112 405-1    program=0 manual=1 | Tidak ditemukan | CEK MANUAL: kata kunci 'keberagaman' muncul di hal. PDF 106
Akurasi keseluruhan: 117/118 = 99.2%
```

Setiap kali Anda selesai mengoreksi hasil sebuah perusahaan secara manual di Excel, perusahaan itu
bisa dipakai juga sebagai data latih: `python3 esg.py latih --perusahaan DEWA ITMG`.

---

## 10. Masalah yang sering terjadi

| Pesan / masalah | Solusi |
|---|---|
| `File Excel tidak ditemukan` | Periksa nama file (`DATA SKRIPSI.xlsx`) atau tulis lokasinya dengan `--excel "..."` |
| `folder kosong (belum ada PDF)` | Masukkan PDF ke folder perusahaan tersebut |
| `Tabel indeks GRI tidak terdeteksi` | Laporan tanpa indeks GRI; penilaian hanya dari tanda kode & ML – cek manual file bukti |
| `kemungkinan PDF hasil scan` | PDF berupa gambar, teks tidak bisa dibaca; cari versi PDF lain dari situs perusahaan/BEI |
| `#DIV/0!` di baris rata-rata | Tahun tersebut belum ada PDF-nya (kolom kosong) |
| `python3` tidak dikenal (Windows) | Pakai `python` atau `py` sebagai gantinya |

---

## Struktur kode

```
esg.py                      <- program utama (python3 esg.py ...)
esg_disclosure/
  cli.py                    <- perintah nilai / latih / uji
  pdf_reader.py             <- membaca PDF (teks + posisi kata)
  gri_index.py              <- membaca tabel GRI Content Index
  body_tags.py              <- mencari tanda kode GRI di isi laporan
  semantic.py               <- fitur ML (TF-IDF, kata kunci)
  model.py                  <- melatih/memuat model Logistic Regression
  scorer.py                 <- aturan penilaian 0/1 & skor
  template.py               <- membaca struktur sheet ESGD
  excel_writer.py           <- menulis blok perusahaan ke Excel (format seperti DEWA)
  data/gri_catalog.json     <- deskripsi & kata kunci tiap item GRI (boleh ditambah)
model/model_esg.joblib      <- model ML terlatih
tests/                      <- tes otomatis (python3 -m pytest)
```
