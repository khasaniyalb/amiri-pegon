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
- Madda di dalam آ dan komponen U+FDFD tidak diubah.

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
| `scripts/tashkil_anchors.py` (baru) | posisi tashkil mengikuti kontur huruf (anchor `TashkilAbove`/`TashkilBelow` dihitung ulang per glyph saat build) |
| `scripts/tashkil_check.py` (baru) | deteksi tabrakan tashkil dan penghitung koreksi otomatis |
| `sources/tashkil-adjust.json` (baru) | koreksi (dx/dy) per glyph hasil `tashkil_check.py` |
| `scripts/rename.py` (baru) | ganti nama font setelah build |

## Build

Kebutuhan sama dengan Amiri asli (lihat `requirements.txt`).

```sh
pip install -r requirements.txt
make VERSION=1.001
```

Hasil ada di `fonts/`. Pengecilan tashkil berjalan otomatis lewat `scripts/build.py`.

## Mengganti nama font

Nama font Amiri asli dipakai oleh `NAME=Amiri` di `Makefile` dan `fontinfo.plist`. Mengubah keduanya
akan memengaruhi seluruh jalur build, jadi cara paling aman adalah mengganti nama setelah build:

```sh
python3 scripts/rename.py fonts/Amiri-Regular.ttf fonts/Amiri-Bold.ttf \
    fonts/Amiri-Italic.ttf fonts/Amiri-BoldItalic.ttf
```

Skrip ini menulis `AmiriPegon-Regular.ttf` dan seterusnya (family "Amiri Pegon"; nama PostScript
`AmiriPegon-*`), dan tidak menyentuh berkas asli. Untuk nama lain: `--family "Nama Lain"`.

## Posisi tashkil mengikuti badan huruf

Amiri asli meletakkan hampir semua tashkil pada satu ketinggian tetap (y=801 atas, y=-327 bawah).
`scripts/tashkil_anchors.py` menghitung ulang anchor untuk setiap glyph (isol/init/medi/fina, ligatur,
dan semua varian kontekstual/calt, karena semuanya glyph tunggal) dari kontur glyph itu sendiri,
mengikuti pola Scheherazade New:

- Huruf berbatang tinggi (ا ل ط ظ ك dan variannya): tanda diletakkan relatif pada *puncak batang* (celah `GAP_STEM`). Anchor x dipindah ke puncak batang/goresan (ل ط ظ ك) dan digeser sekitar 14 unit agar *pusat visual* tanda (bukan titik anchor-nya, yang berada di kiri pusat pada fatha/damma/tanwin) tepat di atas batang. Khusus keluarga ك (kaf, keheh, gaf), tanda digeser `KAF_LEFT` (145 unit) ke kiri dari ujung goresan atas dan tingginya dihitung dari kontur goresan di posisi itu, mirip Scheherazade yang menaruh tanda ك lebih ke kiri lagi.
- Atas: dasar tanda = max(lantai 530, puncak huruf di bawah tanda + celah). Titik di atas huruf diberi
  celah lebih besar daripada badan huruf. Huruf rendah (ba, sin, mim) mendapat tanda rendah,
  huruf tinggi (alif, lam, tha) mendapat tanda tinggi.
- Bawah: puncak tanda = min(batas bawah garis dasar, dasar huruf/titik bawah - celah).
- Semua angka ada di `P` pada awal `tashkil_anchors.py` (satuan per 1000 em) dan mudah diubah.
- Quran tidak ikut diubah.

Tabrakan dengan huruf/tanda tetangga diukur dan dikoreksi per glyph:

```sh
python scripts/tashkil_check.py fonts/Amiri-Regular.ttf --master Regular --words 14000 --seed 11 --write
make VERSION=1.001 fonts/Amiri-Regular.ttf     # ulangi 2-3 putaran dengan seed berbeda
```

Koreksi disimpan di `sources/tashkil-adjust.json` ({master: {glyph: {dxA, dyA, dxB, dyB}}}),
dibatasi maksimum 160 unit vertikal dan 60 unit horizontal. Pada 9.000 kata acak (seed 2026) yang
tidak dipakai untuk melatih koreksi, tanda yang berjarak < 22 unit dari huruf/tanda tetangga turun dari
3,03% menjadi 0,42% (Regular) dan 3,89% menjadi 0,78% (Bold).

### Satu berkas untuk semua pengaturan posisi: `sources/tashkil-posisi.txt`

Semua koreksi manual posisi tashkil ada di satu berkas teks yang mudah dibaca. Isinya tiga bagian
(penjelasan lengkap ada di bagian atas berkas itu):

- `[Bentuk]` : koreksi untuk satu bentuk huruf di mana pun muncul (menggantikan posisi otomatis). Menggantikan
  `tashkil-manual.json` yang sebelumnya diedit tangan.
- `[Kelompok]` : nama untuk sekumpulan glyph, dipakai di aturan konteks.
- `[Konteks]` : tanda sebuah huruf bergeser bila huruf tertentu ada di sebelahnya, ditulis sebagai
  `pola => sisi dx dy`, mis. `ت^* ك~ => atas 0 314`. Menggantikan `make-tashkil-context.py`.

Setelah mengubah berkas itu, cukup `make` (dua berkas turunan dibangkitkan otomatis oleh
`scripts/make-tashkil-posisi.py`: `sources/tashkil-manual.json` dan `sources/tashkil_context.fea`; jangan diedit
tangan), lalu `sh scripts/make-weights.sh`. Untuk melihat nama bentuk huruf pada suatu kata:
`python3 scripts/nama-bentuk.py "مُحَمَّد"` (butuh `pip install uharfbuzz`).

Hal yang tetap ditangani mesin `tashkil_anchors.py`:
- Fa/qaf awal sebelum jim/ha/kha (`init.FaaHaaInit`): tanda diletakkan tepat di atas kepala dan titik fa; tanda huruf
  sesudahnya (`fina.AboveHaaIsol2`, `medi.FaaHaaInit`) dihitung sejajar secara diagonal di kiri-bawah tanda fa (`FEH_*` di `P`).
- Bentuk tengah sebelum yeh akhir/bari (nama konteks memuat `Yaa`/`Bari`): anchor bawah asli Amiri dipertahankan
  bila lebih dalam, supaya kasra tidak tertutup lengkung yeh.

Aturan konteks bawaan (delapan aturan) dan maksudnya:

- teh/noon awal sebelum kaf tengah: tanda atas dinaikkan sampai setinggi tanda theh (di atas ujung goresan kaf);
- beh awal sebelum kaf tengah: tanda atas diturunkan ke bawah ujung goresan kaf, seperti yeh;
- ha/jim/kha di akhir kata sesudah `lam-ar.init.LamHaaInit`: tanda digeser ke kanan;
- meem setelah lam sebelum yeh akhir: kasra diturunkan ke bawah lengkung yeh;
- meem setelah lam sebelum alif akhir: tanda dinaikkan ke atas ujung batang lam dan alif;
- huruf sesudah fa + hah/jim/kha (bentuk tengah): tanda digeser ke kiri agar membentuk tangga diagonal dan tidak
  bertumpuk dengan tanda hah/jim/kha; damma/dammatan milik hah/jim/kha ikut naik dan bergeser sedikit ke kanan.

Tanda yang menumpuk pada satu huruf (shadda + harakat) diposisikan sendiri-sendiri, jadi aturan menggeser semuanya.
Anchor beh/teh/noon awal dibekukan di bagian `[Bentuk]` supaya nilai pergeseran tetap bermakna.

### Hamzah di إ

Hamzah bawah pada `alefHamzabelow-ar*` (9 glyph) dikecilkan menjadi 80%, dengan cara yang sama seperti hamzah أ:
skala 0,8 pada komponen `hamzabelow-ar`, titik tetapnya di puncak hamzah (sisi yang dekat alif) sehingga jarak ke alif
tidak berubah. `alefWavyhamzabelow-ar*` (huruf lain) tidak diubah.

### Catatan tentang pengukur tabrakan

`tashkil_check.py` membaca TTF hasil build, yang glyph hurufnya berupa komponen. Versi awal tidak mendekomposisi
komponen sehingga hanya melihat sebagian geometri, dan angka perbaikan yang dilaporkan waktu itu terlalu optimis.
Sekarang komponen didekomposisi. Dengan 6.000 kata acak (seed 2026), tanda yang berjarak < 22 unit dari tetangganya:
Regular 5,90% (font awal) menjadi 2,91%; Bold 8,69% menjadi 4,51%. Sisanya sebagian besar tabrakan antar-tanda pada
huruf berdampingan yang tidak bisa diselesaikan hanya dengan anchor per glyph.

## Catatan

- Koreksi tabrakan hanya mencakup glyph yang muncul pada kata acak uji (sekitar 3.000 dari 5.000 glyph
  berjangkar); sisanya memakai posisi dasar dari kontur saja.
- Tabrakan sisa umumnya antar tanda pada huruf sempit yang berdampingan (misalnya alif-lam), yang tidak
  bisa diselesaikan hanya dengan anchor per glyph. Perlu aturan GPOS kontekstual bila ingin dihilangkan.
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
