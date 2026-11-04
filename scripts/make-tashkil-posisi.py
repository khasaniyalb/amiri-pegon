#!/usr/bin/env python3
"""Reads sources/tashkil-posisi.txt and writes sources/tashkil_context.fea.

Each line of the txt file shifts the tashkil of a letter (or of a letter in a context):

    pola => atas dx dy  bawah dx dy  | Bold atas dx dy  bawah dx dy

The shifts are ADDED to the original Amiri position (the anchors are not touched). Values for Medium and
SemiBold are interpolated between Regular and Bold at build time (build.py defines TW_<weight>).
"""
import itertools, os, re, sys, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "sources")
TXT = os.environ.get("TP_TXT", os.path.join(SRC, "tashkil-posisi.txt"))
OUT = os.environ.get("TP_OUT", os.path.join(SRC, "tashkil_context.fea"))
GLYPHS = os.path.join(SRC, "Amiri.glyphspackage", "glyphs")
REMOVE_GLYPHS = "com.schriftgestaltung.customParameter.GSFontMaster.Remove Glyphs"
WEIGHTS = (400, 500, 600, 700)
# names usable instead of atas/bawah: one name covers the mark and its variants (e.g. fatha-ar.small)
MARKNAMES = {
    "fatha": "fatha", "damma": "damma", "kasra": "kasra", "fathatan": "fathatan", "dammatan": "dammatan",
    "kasratan": "kasratan", "shadda": "shadda", "sukun": "sukun", "madda": "madda", "alef": "alefabove",
}


def die(msg, n=None):
    raise SystemExit("tashkil-posisi.txt%s: %s" % (":%d" % n if n else "", msg))


def read_cmap():
    cmap = {}
    for fn in os.listdir(GLYPHS):
        t = open(os.path.join(GLYPHS, fn), encoding="utf-8").read()
        m = re.search(r'glyphname = "?([^";\n]+)"?;', t)
        u = re.search(r'\nunicode = "?([0-9A-Fa-f,]+)"?;', t)
        if m and u:
            for cp in u.group(1).split(","):
                cmap.setdefault(int(cp, 16), m.group(1))
    return cmap


def glyph_universe(ufo_path):
    from ufoLib2 import Font
    f = Font.open(ufo_path, validate=False)
    skip = set(f.lib.get("public.skipExportGlyphs", []))
    rem = f.lib.get(REMOVE_GLYPHS)
    rx = re.compile("(" + "|".join(rem) + ")") if rem else None
    names = [g.name for g in f if g.name not in skip and not (rx and rx.match(g.name))]
    keep = set(names)
    ta = [g.name for g in f if g.name in keep and any(a.name == "_TashkilAbove" for a in g.anchors)]
    tb = [g.name for g in f if g.name in keep and any(a.name == "_TashkilBelow" for a in g.anchors)]
    return names, ta, tb


def is_letter(c):
    return ord(c) > 0x600 and unicodedata.category(c).startswith("L")


def parse_values(text, n, what):
    vals = {}
    toks = text.split()
    i = 0
    while i < len(toks):
        if toks[i] not in ("atas", "bawah") and toks[i] not in MARKNAMES:
            die("%s: tulis atas / bawah / nama tanda (%s) lalu dx dy (bukan %r)" % (what, " ".join(MARKNAMES), toks[i]), n)
        side = toks[i]
        try:
            vals[side] = (int(toks[i + 1]), int(toks[i + 2]))
        except (IndexError, ValueError):
            die("%s: sesudah '%s' harus ada dua angka (dx dy)" % (what, side), n)
        i += 3
    if not vals:
        die("%s: tidak ada nilai" % what, n)
    return vals


def parse_line(line, n):
    if "=>" not in line:
        die("tulis: huruf => atas dx dy   (lihat contoh di bagian atas berkas)", n)
    pat, act = line.split("=>", 1)
    reg_txt, _, bold_txt = act.partition("|")
    reg = parse_values(reg_txt, n, "nilai")
    bold = None
    if bold_txt.strip():
        b = bold_txt.strip()
        if not b.lower().startswith("bold"):
            die("sesudah | tulis: Bold atas dx dy", n)
        bold = parse_values(b[4:], n, "nilai Bold")
    if pat.strip() == "*":
        return [(None, "")], 0, reg, bold
    toks = re.findall(r"\[[^\]]+\][\^~$_]?\*?|[^\s\[\]]+", pat.strip())
    slots, target = [], None
    for t in toks:
        star = t.endswith("*")
        if star:
            t = t[:-1]
        mark = ""
        if t and t[-1] in "^~$_":
            mark, t = t[-1], t[:-1]
        letters = t[1:-1] if t.startswith("[") else t
        letters = [c for c in letters if not c.isspace()]
        if not letters or not all(is_letter(c) for c in letters):
            die("pola harus berisi huruf Arab saja (token %r)" % t, n)
        if star:
            if target is not None:
                die("hanya satu huruf yang boleh diberi *", n)
            target = len(slots)
        slots.append((letters, mark))
    if not slots:
        die("pola kosong", n)
    return slots, 0 if target is None else target, reg, bold


def letter_class(letters, mark, names, cmap, n):
    pos = {"^": r"\.init", "~": r"\.medi", "$": r"\.fina", "": "", "_": r"(?!\.(init|medi|fina)(\.|$))"}[mark]
    out = []
    for c in letters:
        if ord(c) not in cmap:
            die("huruf %r tidak ada di font" % c, n)
        rx = re.compile("^%s%s(\\..*)?$" % (re.escape(cmap[ord(c)]), pos))   # "_" = isolated: no init/medi/fina suffix
        out += [x for x in names if rx.match(x) and x not in out]
    return out


def weight_value(reg, bold, side, w):
    r = reg.get(side, (0, 0))
    b = bold[side] if (bold is not None and side in bold) else r   # Bold inherits Regular for a side it does not mention
    t = (w - 400) / 300.0
    return tuple(int(round(r[k] + (b[k] - r[k]) * t)) for k in (0, 1))


def main():
    ufo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "Amiri-Regular.ufo")
    cmap = read_cmap()
    entries = []
    if not os.path.exists(TXT):
        die("berkas tidak ditemukan")
    for n, line in enumerate(open(TXT, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append((n, line) + parse_line(line, n))
    L = ["# Generated by scripts/make-tashkil-posisi.py from sources/tashkil-posisi.txt -- do not edit by hand.", ""]
    if not entries:
        L.append("# (tidak ada aturan: posisi tashkil sama dengan Amiri asli)")
        open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print("tashkil_context.fea: 0 aturan (posisi asli Amiri)")
        return
    names, ta, tb = glyph_universe(ufo)
    bold_ufo = ufo.replace("Regular", "Bold")
    if bold_ufo != ufo and os.path.exists(bold_ufo):          # use only glyphs that exist in BOTH masters
        bn, _, _ = glyph_universe(bold_ufo)
        keep = set(bn)
        names = [x for x in names if x in keep]
        ta = [x for x in ta if x in keep]
        tb = [x for x in tb if x in keep]
    mrx = {k: re.compile(r"^%s-ar(\..*)?$" % v) for k, v in MARKNAMES.items()}
    extra = [x for x in names if x not in set(ta + tb) and any(r.match(x) for r in mrx.values())]
    allmarks = ta + tb + extra
    mset = set(allmarks)
    cls = lambda nm, g: L.append("@%s = [%s];" % (nm, " ".join(g)))
    cls("TP_ABOVE", ta); cls("TP_BELOW", tb); cls("TP_ALL", allmarks)
    cls("TP_BASE", [x for x in names if x not in mset])
    lookups = {w: [] for w in WEIGHTS}
    rules = []
    # specific (longer) patterns first: in one lookup the first matching rule wins
    order = sorted(range(len(entries)), key=lambda i: (-len(entries[i][2]), i))
    for i in order:
        n, line, slots, tgt, reg, bold = entries[i]
        classes = []
        ok = True
        for k, (letters, mark) in enumerate(slots):
            g = [x for x in names if x not in mset] if letters is None else letter_class(letters, mark, names, cmap, n)
            if not g:
                print("peringatan baris %d: pola %r tidak cocok dengan glyph apa pun, baris dilewati" % (n, line.split("=>")[0].strip()))
                ok = False
                break
            nm = "TP_BASE" if letters is None else "TP_%d_%d" % (i, k)
            if letters is not None:
                cls(nm, g)
            classes.append(nm)
        if not ok:
            continue
        keys = [k for k in list(reg) + [k for k in (bold or {}) if k not in reg]]
        for j, key in enumerate(keys):
            vals = {w: weight_value(reg, bold, key, w) for w in WEIGHTS}
            if all(v == (0, 0) for v in vals.values()):
                continue
            if key == "atas":
                T, Tn = "@TP_ABOVE", ta
            elif key == "bawah":
                T, Tn = "@TP_BELOW", tb
            else:
                Tn = [x for x in names if mrx[key].match(x)]
                if not Tn:
                    print("peringatan baris %d: tanda %r tidak ada di font, dilewati" % (n, key))
                    continue
                cls("TP_%d_%d_T" % (i, j), Tn)
                T = "@TP_%d_%d_T" % (i, j)
            lk = "TP_L%d_%d" % (i, j)
            for w in WEIGHTS:
                lookups[w].append("lookup %s { pos %s <%d %d 0 0>; } %s;" % (lk, T, vals[w][0], vals[w][1], lk))
            other = "TP_%d_%d_O" % (i, j)
            cls(other, [x for x in allmarks if x not in set(Tn)])
            seqs = [s for ln in (1, 2, 3) for s in itertools.product("TO", repeat=ln) if "T" in s]
            rules.append("    # baris %d (%s): %s" % (n, key, line.split("=>")[0].strip()))
            pre_opts = [[], ["@TP_ALL"], ["@TP_ALL", "@TP_ALL"]]
            for pre_marks in itertools.product(range(3), repeat=tgt):
                pre = []
                for k in range(tgt):
                    pre += ["@" + classes[k]] + pre_opts[pre_marks[k]]
                for s in seqs:
                    first, last = s.index("T"), len(s) - 1 - s[::-1].index("T")
                    back = pre + ["@" + classes[tgt]] + ["@" + other for _ in s[:first]]
                    inp = ["%s' lookup %s" % (T, lk) if s[j2] == "T" else "@%s'" % other for j2 in range(first, last + 1)]
                    fwd = ["@" + other for _ in s[last + 1:]]
                    tail = ["@" + c for c in classes[tgt + 1:]]
                    rules.append("    pos %s;" % " ".join(back + inp + fwd + tail))
    if not rules:
        open(OUT, "w", encoding="utf-8").write("\n".join(L[:2] + ["# (tidak ada baris yang berlaku)"]) + "\n")
        print("tashkil_context.fea: tidak ada aturan yang berlaku")
        return
    L.append("")
    L.append("#if defined(TW_700)")
    L += lookups[700]
    L.append("#elif defined(TW_600)")
    L += lookups[600]
    L.append("#elif defined(TW_500)")
    L += lookups[500]
    L.append("#else")
    L += lookups[400]
    L.append("#endif")
    L += ["", "feature mark {"] + rules + ["} mark;", ""]
    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("tashkil_context.fea: %d baris aturan" % len(rules))


if __name__ == "__main__":
    main()
