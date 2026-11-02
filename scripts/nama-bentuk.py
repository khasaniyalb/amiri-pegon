#!/usr/bin/env python3
"""Prints the glyph name chosen for every letter of a word.

  python3 scripts/nama-bentuk.py "مُحَمَّد" [fonts/AmiriPegon-Regular.ttf]

Needs: pip install uharfbuzz fonttools
"""
import os, sys
try:
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("Pasang dulu:  pip install uharfbuzz fonttools")

word = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "AmiriPegon-Regular.ttf")
order = TTFont(path).getGlyphOrder()
font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
buf = hb.Buffer(); buf.add_str(word); buf.guess_segment_properties(); hb.shape(font, buf)
names = [order[i.codepoint] for i in buf.glyph_infos][::-1]       # urutan mengetik (kanan ke kiri)
print(" ".join(names))
for n in names:
    print("  ", n)
