#!/bin/sh
# Menghapus berkas sistem tashkil lama yang sudah tidak dipakai. Jalankan dari folder repo.
git rm -q --ignore-unmatch scripts/make-tashkil-context.py scripts/tashkil_anchors.py scripts/tashkil_check.py \
  scripts/nama-bentuk.py sources/tashkil-adjust.json sources/tashkil-manual.json
rm -f scripts/make-tashkil-context.py scripts/tashkil_anchors.py scripts/tashkil_check.py scripts/nama-bentuk.py \
  sources/tashkil-adjust.json sources/tashkil-manual.json
echo "selesai"
