#!/usr/bin/env python3
"""Rename built Amiri fonts to "Amiri Pegon" (family + PostScript names).

Usage: python3 scripts/rename.py [--family "Amiri Pegon"] fonts/Amiri-Regular.ttf ...
Writes <Family-without-spaces>-<Style>.ttf next to each input; the input is untouched.
"""
import argparse, os
from fontTools.ttLib import TTFont

ap = argparse.ArgumentParser()
ap.add_argument("--family", default="Amiri Pegon")
ap.add_argument("fonts", nargs="+")
a = ap.parse_args()
fam, ps = a.family, a.family.replace(" ", "")

for path in a.fonts:
    f = TTFont(path)
    for r in f["name"].names:
        s = r.toUnicode()
        if r.nameID in (1, 4, 16, 21):
            s = s.replace("Amiri", fam, 1)
        elif r.nameID in (3, 6):
            s = s.replace("Amiri", ps, 1)
        r.string = s
    style = os.path.basename(path).split("-", 1)[-1]
    out = os.path.join(os.path.dirname(path), f"{ps}-{style}")
    f.save(out)
    print(out)
