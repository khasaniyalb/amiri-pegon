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

## Catatan

- Posisi titik bawah memakai hasil pengukuran otomatis terhadap kombinasi huruf Arab dan Pegon umum.
  Kombinasi yang jarang dipakai bisa saja masih perlu penyesuaian manual.
- Jika huruf tetangga sendiri sudah menabrak badan kaf (misalnya ra sebelum kaf), itu tidak bisa
  diperbaiki lewat posisi titik.
- Untuk mengubah posisi titik satu varian, edit transform komponen `dotbelow-ar` (atau `dotabove-ar`
  pada glyph khah) di berkas `.glyph` terkait, pada kedua master (Regular dan Bold).
