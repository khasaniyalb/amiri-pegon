#!/bin/sh
# Membangun SEMUA font AmiriPegon sekaligus: make + ganti nama + Medium/SemiBold.
# Jalankan dari folder repo dengan environment Python aktif:   sh scripts/bangun-semua.sh
# Font lama dihapus dulu supaya pasti dibangun ulang (tidak ada yang "terlewat" karena dianggap masih baru).
set -e
VERSION=${VERSION:-1.001}
rm -f fonts/Amiri-Regular.ttf fonts/Amiri-Bold.ttf fonts/Amiri-Italic.ttf fonts/Amiri-BoldItalic.ttf
make VERSION="$VERSION"
for f in Regular Bold Italic BoldItalic; do
  if [ ! -f "fonts/Amiri-$f.ttf" ]; then
    echo "GAGAL: fonts/Amiri-$f.ttf tidak terbentuk. Lihat pesan error di atas." >&2
    exit 1
  fi
done
python3 scripts/rename.py fonts/Amiri-Regular.ttf fonts/Amiri-Bold.ttf fonts/Amiri-Italic.ttf fonts/Amiri-BoldItalic.ttf
sh scripts/make-weights.sh
echo
echo "Hasil (jamnya harus baru semua):"
ls -la --time-style=long-iso fonts/AmiriPegon-*.ttf
