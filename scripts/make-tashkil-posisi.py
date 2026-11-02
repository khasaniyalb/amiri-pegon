#!/usr/bin/env python3
"""Reads sources/tashkil-posisi.txt and writes

  sources/tashkil-manual.json   per-glyph anchor corrections (read by tashkil_anchors.py)
  sources/tashkil_context.fea   context-dependent shifts (a mark moves when a certain letter follows)

Usage:  make-tashkil-posisi.py manual                    -> only the JSON
        make-tashkil-posisi.py context [build/Amiri-Regular.ufo]   -> only the .fea
        make-tashkil-posisi.py                           -> both
"""
import itertools, json, os, re, sys, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "sources")
TXT = os.environ.get("TP_TXT", os.path.join(SRC, "tashkil-posisi.txt"))
GLYPHS = os.path.join(SRC, "Amiri.glyphspackage", "glyphs")
POS = {"awal": "init", "tengah": "medi", "akhir": "fina", "sendiri": ""}
REMOVE_GLYPHS = "com.schriftgestaltung.customParameter.GSFontMaster.Remove Glyphs"


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


def read_sections():
    sec, out = None, {}
    if not os.path.exists(TXT):
        die("berkas tidak ditemukan")
    for n, line in enumerate(open(TXT, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"\s*\[([^\]]+)\]\s*$", line)
        if m and m.group(1).split()[0] in ("Bentuk", "Kelompok", "Konteks"):
            sec = m.group(1).strip()
            out.setdefault(sec, [])
            continue
        if sec is None:
            die("baris di luar bagian [..]", n)
        out[sec].append((n, line.strip()))
    return out


# ---------------------------------------------------------------- per-form corrections
def letter_glyph(tok, cmap, n):
    """'ب:awal' -> ('beh-ar.init', False);  'ب:awal*' -> regex of all variants."""
    m = re.match(r"^(.):(awal|tengah|akhir|sendiri)(\*?)$", tok)
    if not m:
        return None
    c, pos, star = m.groups()
    if ord(c) not in cmap:
        die("huruf %r tidak ada di font" % c, n)
    base = cmap[ord(c)]
    suffix = POS[pos]
    name = base + ("." + suffix if suffix else "")
    if star and suffix:
        return "re:^%s(\\..*)?$" % re.escape(name)
    return name


def parse_forms(lines, cmap):
    res = {}
    for n, line in lines:
        toks = line.split()
        key = letter_glyph(toks[0], cmap, n) or toks[0]
        vals, side = {}, None
        for t in toks[1:]:
            if t in ("atas", "bawah"):
                side = "A" if t == "atas" else "B"
                continue
            m = re.match(r"^([xy])=(-?\d+)$", t)
            if not m or side is None:
                die("bentuk tidak dikenal: %r (contoh: atas x=35 y=120)" % t, n)
            vals["d%s%s" % (m.group(1), side)] = int(m.group(2))
        if not vals:
            die("tidak ada nilai", n)
        res.setdefault(key, {}).update(vals)
    return res


def build_manual(secs, cmap):
    out = {}
    for master in ("Regular", "Bold"):
        d = {}
        for name in ("Bentuk", "Bentuk " + master):
            for k, v in parse_forms(secs.get(name, []), cmap).items():
                d.setdefault(k, {}).update(v)
        out[master] = d
    return out


# ---------------------------------------------------------------- context rules
def glyph_universe(ufo_path):
    from ufoLib2 import Font
    f = Font.open(ufo_path, validate=False)
    skip = set(f.lib.get("public.skipExportGlyphs", []))
    rem = f.lib.get(REMOVE_GLYPHS)
    rx = re.compile("(" + "|".join(rem) + ")") if rem else None
    names = [g.name for g in f if g.name not in skip and not (rx and rx.match(g.name))]
    ta = [g.name for g in f if g.name in set(names) and any(a.name == "_TashkilAbove" for a in g.anchors)]
    tb = [g.name for g in f if g.name in set(names) and any(a.name == "_TashkilBelow" for a in g.anchors)]
    return names, ta, tb


def parse_groups(lines, names, ta, tb):
    groups = {"ATAS": ta, "BAWAH": tb, "TANDA": ta + tb}
    have = set(names)
    for n, line in lines:
        m = re.match(r"^(\w+)\s*=\s*(.+)$", line)
        if not m:
            die("kelompok harus berbentuk NAMA = ...", n)
        name, rhs = m.groups()
        minus = []
        if " - " in rhs:
            rhs, sub = rhs.split(" - ", 1)
            minus = groups[sub.strip()]
        rhs = rhs.strip()
        if rhs.startswith("re:"):
            rx = re.compile(rhs[3:])
            g = [x for x in names if rx.match(x)]
        else:
            g = [x for x in rhs.split() if x in have]
        ms = set(minus)
        groups[name] = [x for x in g if x not in ms]
    return groups


def token_class(tok, groups, names, cmap, n):
    """Return the list of glyph names for one pattern token."""
    if tok.startswith("<") and tok.endswith(">"):
        if tok[1:-1] not in groups:
            die("kelompok %s tidak ada" % tok, n)
        return groups[tok[1:-1]]
    inner = tok.lstrip("[").lstrip()
    if inner and ord(inner[0]) > 0x600 and unicodedata.category(inner[0]).startswith("L"):
        mark = ""
        body = tok
        if body and body[-1] in "^~$":
            mark, body = body[-1], body[:-1]
        if body.startswith("["):
            body = body[1:-1]
        letters = [c for c in body if not c.isspace()]
        pos = {"^": r"\.init", "~": r"\.medi", "$": r"\.fina", "": ""}[mark]
        out = []
        for c in letters:
            if ord(c) not in cmap:
                die("huruf %r tidak ada di font" % c, n)
            rx = re.compile("^%s%s(\\..*)?$" % (re.escape(cmap[ord(c)]), pos))
            out += [x for x in names if rx.match(x) and x not in out]
        return out
    # glyph name(s)
    ns = tok[1:-1].split() if tok.startswith("[") else [tok]
    have = set(names)
    return [x for x in ns if x in have]


def parse_rule(line, n):
    m = re.match(r"^(.*?)=>\s*(.+)$", line)
    if not m:
        die("aturan harus berbentuk: pola => sisi dx dy", n)
    pat, act = m.groups()
    toks = re.findall(r"\[[^\]]*\][\^~$]?\*?|<\w+>\*?|\S+?(?=\s|$)", pat.strip())
    slots = []
    for t in toks:
        star = t.endswith("*")
        t = t[:-1] if star else t
        slots.append((t, star))
    if sum(1 for _, s in slots if s) != 1:
        die("tepat satu token harus diberi * (huruf yang tandanya digeser)", n)
    am = re.match(r"^(atas|bawah|\[[^\]]+\])\s+(-?\d+)\s+(-?\d+)\s*$", act.strip())
    if not am:
        die("sesudah => tulis: atas|bawah|[glyph ...] dx dy", n)
    return slots, am.group(1), int(am.group(2)), int(am.group(3))


def build_context(secs, cmap, ufo):
    names, ta, tb = glyph_universe(ufo)
    groups = parse_groups(secs.get("Kelompok", []), names, ta, tb)
    L = ["# Generated by scripts/make-tashkil-posisi.py from sources/tashkil-posisi.txt -- do not edit by hand.", ""]
    cls = lambda n, g: L.append("@%s = [%s];" % (n, " ".join(g)))
    cls("TP_ABOVE", ta); cls("TP_BELOW", tb); cls("TP_ALL", ta + tb)
    rules, lookups = [], []
    for idx, (n, line) in enumerate(secs.get("Konteks", [])):
        slots, side, dx, dy = parse_rule(line, n)
        classes = []
        for k, (tok, star) in enumerate(slots):
            g = token_class(tok, groups, names, cmap, n)
            if not g:
                print("peringatan baris %d: token %r tidak cocok dengan glyph apa pun, aturan dilewati" % (n, tok))
                classes = None
                break
            cname = "TP_%d_%d" % (idx, k)
            cls(cname, g)
            classes.append(cname)
        if classes is None:
            continue
        if side == "atas": T, Tn = "@TP_ABOVE", ta
        elif side == "bawah": T, Tn = "@TP_BELOW", tb
        else:
            sel = [x for x in side[1:-1].split() if x in set(ta + tb)]
            if not sel:
                die("tanda %s tidak ada di font" % side, n)
            cls("TP_%d_T" % idx, sel); T = "@TP_%d_T" % idx; Tn = sel
        # "other" marks = all marks that are not T
        other = [x for x in ta + tb if x not in set(Tn)]
        cls("TP_%d_O" % idx, other)
        lk = "TP_L%d" % idx
        lookups.append("lookup %s { pos %s <%d %d 0 0>; } %s;" % (lk, T, dx, dy, lk))
        tgt = next(i for i, (_, s) in enumerate(slots) if s)
        pre_opts = [[], ["@TP_ALL"], ["@TP_ALL", "@TP_ALL"]]
        seqs = [s for ln in (1, 2, 3) for s in itertools.product("TO", repeat=ln) if "T" in s]
        rules.append("    # %s" % line.split("=>")[0].strip())
        for pre_marks in itertools.product(range(3), repeat=tgt):
            pre = []
            for k in range(tgt):
                pre += ["@" + classes[k]] + pre_opts[pre_marks[k]]
            for s in seqs:
                first, last = s.index("T"), len(s) - 1 - s[::-1].index("T")
                back = pre + ["@" + classes[tgt]] + [("@TP_%d_O" % idx) for _ in s[:first]]
                inp = []
                for i in range(first, last + 1):
                    if s[i] == "T":
                        inp.append("%s' lookup %s" % (T, lk))
                    else:
                        inp.append("@TP_%d_O'" % idx)
                fwd = [("@TP_%d_O" % idx) for _ in s[last + 1:]]
                tail = ["@" + c for c in classes[tgt + 1:]]
                rules.append("    pos %s;" % " ".join(back + inp + fwd + tail))
    L.append("")
    L += lookups
    L += ["", "feature mark {"] + rules + ["} mark;", ""]
    return "\n".join(L), groups


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    cmap = read_cmap()
    secs = read_sections()
    if mode in ("manual", "all"):
        data = build_manual(secs, cmap)
        with open(os.path.join(SRC, "tashkil-manual.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("tashkil-manual.json:", {m: len(v) for m, v in data.items()})
    if mode in ("context", "all"):
        ufo = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build", "Amiri-Regular.ufo")
        text, groups = build_context(secs, cmap, ufo)
        out = os.environ.get("TP_OUT", os.path.join(SRC, "tashkil_context.fea"))
        open(out, "w", encoding="utf-8").write(text)
        print("tashkil_context.fea: %d baris" % (text.count("\n") + 1))


if __name__ == "__main__":
    main()
