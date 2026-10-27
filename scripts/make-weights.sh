#!/bin/sh
# Build Medium (500) and SemiBold (600) of Amiri Pegon.
# Run from the repository root AFTER `make` (needs build/Amiri-*.ufo).
set -e
VERSION=${VERSION:-1.001}
for W in "500 Medium" "600 SemiBold"; do
  set -- $W
  python3 scripts/weights.py \
    --regular build/Amiri-Regular.ufo --bold build/Amiri-Bold.ufo \
    --latin-regular sources/AmiriLatin-Regular.ufo --latin-bold sources/AmiriLatin-Bold.ufo \
    --weight "$1" --name "$2" --features sources/Amiri.fea \
    --version "$VERSION" --license OFL.txt --output "fonts/Amiri-$2.ttf"
done
python3 scripts/rename.py fonts/Amiri-Medium.ttf fonts/Amiri-SemiBold.ttf
rm -f fonts/Amiri-Medium.ttf fonts/Amiri-SemiBold.ttf
