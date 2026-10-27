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
| `sources/tashkil-adjust.json` (baru) | koreksi (dx/dy) per glyph hasil `tashkil_check.py`, boleh diedit manual |
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
