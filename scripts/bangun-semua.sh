#!/bin/sh
# Membangun SEMUA font AmiriPegon sekaligus: make + ganti nama + Medium/SemiBold.
# Jalankan dari folder repo dengan environment Python aktif:   sh scripts/bangun-semua.sh
set -e
VERSION=${VERSION:-1.001}
make VERSION="$VERSION"
python3 scripts/rename.py fonts/Amiri-Regular.ttf fonts/Amiri-Bold.ttf fonts/Amiri-Italic.ttf fonts/Amiri-BoldItalic.ttf
sh scripts/make-weights.sh
echo
ls -la --time-style=long-iso fonts/AmiriPegon-*.ttf
