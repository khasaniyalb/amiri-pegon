# Amiri Pegon

Modifikasi font [Amiri](https://github.com/aliftype/amiri) untuk penulisan Pegon.
Lisensi tetap SIL Open Font License 1.1 (lihat `OFL.txt`).

## Perubahan

### 1. Huruf Pegon baru
| Karakter | Unicode | Nama | Basis |
|---|---|---|---|
| ࢴ | U+08B4 | Kaf dengan titik bawah | ك (U+0643) |
| ࢋ | U+088B | Tah dengan titik bawah | ط (U+0637) |

- Tersedia bentuk isol, init, medi, dan fina.
- Seluruh ligatur dan contextual alternate milik kaf (27 varian) dan tah (5 varian) ikut tersedia.
- Posisi titik bawah dihitung terhadap huruf tetangga agar tidak bertabrakan atau ambigu dengan titik huruf sebelahnya, terpisah untuk Regular dan Bold.
- Ligatur kaf + jim/hah/kha: titik kaf berada di dalam kait kaf. Titik kha dipindah ke kiri kait kaf, juga untuk kaf biasa (ك) + kha.
- Font Quran (`AmiriQuran*.ttf`) tidak memuat huruf ini.

### 2. Lam + Kha
Pada ligatur lam + kha, titik kha berada di sisi kiri batang lam (tidak di kiri kha):
`لخ`, `لخخ`, `لخخا`, `لخمم`. Fa + kha tidak berubah.

### 3. Tashkil
- Semua tashkil (fatha, damma, kasra, tanwin, shadda, sukun, dan varian kecilnya) diperkecil menjadi 80%.
- Madda (U+0653) diperkecil menjadi 60%.
- Titik tumpu pengecilan adalah anchor tempel, sehingga posisi tempel pada huruf tetap.
- Madda di dalam آ ikut mengecil (60%); komponen U+FDFD tidak diubah.

## File yang berubah dari Amiri asli

| Berkas | Perubahan |
|---|---|
| `sources/Amiri.glyphspackage/glyphs/kafD_otbelow-ar*.glyph` | 27 glyph baru (kaf titik bawah) |
| `sources/Amiri.glyphspackage/glyphs/tahD_otbelow-ar*.glyph` | 5 glyph baru (tah titik bawah) |
| glyph `khah-ar.*.LamKhah` dan `khah-ar.*.KafKhah` (nama berkas memakai penulisan `L_amK_hah`) | 4 varian kha baru |
| `khah-ar.medi.1LamHaaHaaInit`, `khah-ar.medi.LamHaaMemInit` | titik kha digeser |
| `sources/Amiri.glyphspackage/order.plist` | daftar glyph baru |
| `sources/classes.fea`, `sources/basic.fea` | glyph baru masuk kelas dan substitusi posisi |
| `sources/contextuals.fea` | lookup `LamKhahDot` dan `KafKhahDot` di akhir berkas |
| `scripts/tashkil.py` (baru), `scripts/build.py` | pengecilan tashkil saat build |
| `sources/tashkil-posisi.txt` / `scripts/make-tashkil-posisi.py` / `scripts/pratinjau.py` (baru) | koreksi posisi tashkil per huruf, pembangkit aturan, dan pratinjau (bagian "Posisi tashkil") |
| `scripts/rename.py` (baru) | ganti nama font setelah build |

## Build

Kebutuhan sama dengan Amiri asli (lihat `requirements.txt`).

```sh
pip install -r requirements.txt
make VERSION=1.001
```

Hasil ada di `fonts/`. Pengecilan tashkil berjalan otomatis lewat `scripts/build.py`.

Cara paling mudah membangun semua font (empat font utama + Medium + SemiBold) sekaligus:

```sh
sh scripts/bangun-semua.sh
```

Catatan: `make` hanya membuat `fonts/Amiri-*.ttf`. Berkas `fonts/AmiriPegon-Regular/Bold/Italic/BoldItalic.ttf` baru
dibuat oleh langkah `rename.py` (sudah termasuk di skrip di atas); Medium dan SemiBold dibuat oleh `make-weights.sh`.
Jadi bila hanya menjalankan `make`, berkas `AmiriPegon-Regular/Bold/...` tidak ikut diperbarui.

## Mengganti nama font

Nama font Amiri asli dipakai oleh `NAME=Amiri` di `Makefile` dan `fontinfo.plist`. Mengubah keduanya
akan memengaruhi seluruh jalur build, jadi cara paling aman adalah mengganti nama setelah build:

```sh
python3 scripts/rename.py fonts/Amiri-Regular.ttf fonts/Amiri-Bold.ttf \
    fonts/Amiri-Italic.ttf fonts/Amiri-BoldItalic.ttf
```

Skrip ini menulis `AmiriPegon-Regular.ttf` dan seterusnya (family "Amiri Pegon"; nama PostScript
`AmiriPegon-*`), dan tidak menyentuh berkas asli. Untuk nama lain: `--family "Nama Lain"`.

## Posisi tashkil

Posisi dasar tashkil sama dengan font Amiri asli (anchor di sumber glyph tidak diubah). Yang diubah dari Amiri
hanya ukurannya (bagian "Tashkil" di atas). Koreksi posisi, bila perlu, ditulis di satu berkas teks:
`sources/tashkil-posisi.txt`, satu baris per koreksi:

```
huruf => atas dx dy  bawah dx dy  | Bold atas dx dy  bawah dx dy
```

- **Satu huruf** = huruf itu di mana pun (semua bentuknya). **Dua huruf atau lebih** = konteks (berurutan, dalam
  urutan mengetik, dipisah spasi). Tanda pada huruf yang diberi `*` yang digeser; tanpa `*`, huruf pertama.
- `^`, `~`, `$`, `_` pada sebuah huruf = bentuk awal, tengah, akhir kata, atau berdiri sendiri (isolated); berlaku juga untuk huruf tunggal. `[ح ج خ]` = beberapa huruf pada satu posisi.
- `atas` / `bawah` = tanda di atas / di bawah huruf. `dx dy` = geser ke kanan (+) / kiri (-) dan ke atas (+) / bawah (-),
  dalam 1/1000 tinggi huruf, relatif terhadap posisi asli.
- Bagian `| Bold ...` bersifat opsional. Tanpa itu Bold memakai angka yang sama. Medium dan SemiBold otomatis berada di
  antara Regular dan Bold.
- Bila beberapa baris cocok pada tanda yang sama, baris yang paling spesifik (huruf paling banyak) yang dipakai.

Contoh: `ت ك => atas 0 314` (tanda atas ت yang diikuti ك naik 314), `ل ح* => atas 140 0` (tanda atas ح setelah ل
bergeser ke kanan 140), `ب^ => bawah 0 -30 | Bold bawah 0 -40`.

Setelah mengubah berkas itu, jalankan `make` (aturan dibangkitkan otomatis ke `sources/tashkil_context.fea` oleh
`scripts/make-tashkil-posisi.py`; jangan diedit tangan), lalu `sh scripts/make-weights.sh`.

Untuk melihat hasil sebuah baris sebelum menyimpannya:

```sh
pip install uharfbuzz matplotlib          # sekali saja
python3 scripts/pratinjau.py -a "ب^ ل~* => atas 0 50" "بَلَلَ" "بَلَ"
```

Skrip membangun dua font sementara (sebelum dan sesudah, sekitar 2-3 menit), menggambar kata-kata itu ke
`pratinjau.png` (hitam = sesudah, bayangan biru = posisi tanda sebelumnya, 1 kotak = 100 unit), dan mencetak
pergeseran tiap tanda. Opsi: `-m Bold`, `-o berkas.png`, dan `-a` boleh diulang.

Mekanisme: setiap baris menjadi aturan GPOS kontekstual yang menggeser tanda setelah posisi tanda dari anchor Amiri
dihitung. Nilai per bobot dipilih saat build (`TW_400`, `TW_500`, `TW_600`, `TW_700`).


### Hamzah di إ

Hamzah bawah pada `alefHamzabelow-ar*` (9 glyph) dikecilkan menjadi 80%, dengan cara yang sama seperti hamzah أ:
skala 0,8 pada komponen `hamzabelow-ar`, titik tetapnya di puncak hamzah (sisi yang dekat alif) sehingga jarak ke alif
tidak berubah. `alefWavyhamzabelow-ar*` (huruf lain) tidak diubah.

## Catatan

- Posisi titik bawah memakai hasil pengukuran otomatis terhadap kombinasi huruf Arab dan Pegon umum.
  Kombinasi yang jarang dipakai bisa saja masih perlu penyesuaian manual.
- Jika huruf tetangga sendiri sudah menabrak badan kaf (misalnya ra sebelum kaf), itu tidak bisa
  diperbaiki lewat posisi titik.
- Untuk mengubah posisi titik satu varian, edit transform komponen `dotbelow-ar` (atau `dotabove-ar`
  pada glyph khah) di berkas `.glyph` terkait, pada kedua master (Regular dan Bold).

## Bobot Medium dan SemiBold

Amiri hanya punya dua master (Regular 400 dan Bold 700). Medium (500) dan SemiBold (600)
dibuat oleh `scripts/weights.py` dengan interpolasi antara kedua master:

- Glyph yang strukturnya cocok di kedua master (sekitar 92%) diinterpolasi langsung, termasuk
  posisi titik dan anchor tashkil.
- Glyph yang tidak cocok (sekitar 8%, misalnya alif akhir dan sebagian bentuk ain) dibuat dengan
  menebalkan kontur Regular sampai luasnya sama dengan luas hasil interpolasi.
- Hasil interpolasi yang luasnya menyimpang dari yang diharapkan otomatis diganti dengan cara kedua.

Cara membangun (setelah `make`):

```sh
sh scripts/make-weights.sh
```

Hasilnya `fonts/AmiriPegon-Medium.ttf` dan `fonts/AmiriPegon-SemiBold.ttf`. ExtraBold tidak
tersedia karena membutuhkan ekstrapolasi di luar Bold, yang membuat jarak titik terlalu sempit.

## Pembatalan ligatur saat ada harakat

Daftar pola ada di `sources/batal-ligatur.txt` (satu pola per baris, format dijelaskan di dalam file).
Bila ada harakat di dalam pola, font menyisipkan ZWJ tak terlihat di titik `|`, sehingga ligatur yang
mengharuskan huruf-hurufnya berdekatan tidak terbentuk. Teks tanpa harakat tidak berubah.

Contoh baris: `م ح | م +`
- `|` : tempat ZWJ disisipkan (setelah harakat huruf di kirinya)
- `+` : hanya bila pola disambung ke huruf berikutnya (`-` : hanya bila tidak disambung; tanpa tanda: keduanya)
- `[ح ج خ]` : beberapa pilihan huruf pada satu posisi

Setelah mengubah daftar, jalankan `make` (berkas `sources/batal_ligatur.fea` dibangkitkan otomatis oleh
`scripts/make-batal-ligatur.py`), lalu `sh scripts/make-weights.sh`.
