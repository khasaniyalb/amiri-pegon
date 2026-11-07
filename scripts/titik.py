# Amiri Pegon: geser titik huruf sesuai sources/titik-posisi.txt.
#
# Titik di sumber Amiri adalah KOMPONEN di dalam glyph huruf (mis. beh-ar.init = aBaa.init + dotbelow-ar).
# Skrip ini mengubah offset komponen titik itu pada UFO sebelum font dikompilasi, persis seperti tashkil.py
# mengubah ukuran tashkil. Nilai 0 0 = posisi bawaan Amiri. Tidak ada nilai yang menumpuk: setiap titik
# mendapat paling banyak SATU geseran (lihat keterangan di titik-posisi.txt).
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TXT = os.environ.get("TITIK_TXT", os.path.join(ROOT, "sources", "titik-posisi.txt"))
LOG = os.environ.get("TITIK_LOG")          # (opsional) berkas log JSON, dipakai pratinjau-titik.py

KEYS = ("titik", "atas", "bawah", "satu", "dua", "tiga")
# komponen titik yang dikenali: satu, dua, dan tiga titik (atas/bawah). Sengaja eksplisit agar tidak
# ikut menangkap glyph lain seperti dotvowelbelow-ar.
DOT = re.compile(r"^(dot(?P<s1>above|below)"
                 r"|twodots(?:horizontal|vertical)(?P<s2>above|below)"
                 r"|threedots(?:up|down)(?P<s3>above|below))-ar(\..*)?$")


def die(msg, n=None):
    raise SystemExit("titik-posisi.txt%s: %s" % (":%d" % n if n else "", msg))


def classify(base):
    """-> (jumlah titik: 'satu'|'dua'|'tiga', sisi: 'atas'|'bawah') atau None bila bukan komponen titik"""
    m = DOT.match(base)
    if not m:
        return None
    if m.group("s1"):
        cnt, side = "satu", m.group("s1")
    elif m.group("s2"):
        cnt, side = "dua", m.group("s2")
    else:
        cnt, side = "tiga", m.group("s3")
    return cnt, ("atas" if side == "above" else "bawah")


def parse_values(text, n, what):
    vals, toks, i = {}, text.split(), 0
    while i < len(toks):
        if toks[i] not in KEYS:
            die("%s: tulis salah satu dari %s lalu dx dy (bukan %r)" % (what, " / ".join(KEYS), toks[i]), n)
        try:
            vals[toks[i]] = (int(toks[i + 1]), int(toks[i + 2]))
        except (IndexError, ValueError):
            die("%s: sesudah '%s' harus ada dua ANGKA (dx dy), ditemukan %r" % (what, toks[i], " ".join(toks[i + 1:i + 3])), n)
        i += 3
    if not vals:
        die("%s: tidak ada nilai" % what, n)
    return vals


def parse_pattern(pat, n):
    """Tiga bentuk pola:
         ب^            huruf (+ tanda bentuk ^ ~ $ _)           -> semua varian bentuk itu
         ب^.BaaMemInit huruf + bentuk + NAMA VARIAN (boleh * )  -> hanya varian itu
         beh-ar.init.BaaMemInit   nama glyph (boleh * dan ?)    -> glyph itu saja
    """
    pat = pat.strip()
    if re.fullmatch(r"[A-Za-z0-9_.\-*?]+", pat):                      # nama glyph (ASCII)
        return ("glyph", pat)
    m = re.fullmatch(r"(\[[^\]]+\]|\S)([\^~$_]?)(\.[A-Za-z0-9_.*\-]+)?", pat)
    if not m:
        die("pola %r tidak dikenali. Contoh: ب^   [ن ي]$   ب^.BaaMemInit   beh-ar.init.BaaMemInit  "
            "(titik tidak mengenal konteks huruf tetangga)" % pat, n)
    body, mark, var = m.group(1), m.group(2), (m.group(3) or "")[1:]
    letters = [c for c in (body[1:-1] if body.startswith("[") else body) if not c.isspace()]
    if not letters or not all(ord(c) > 0x600 for c in letters):
        die("pola %r harus berisi huruf Arab (atau nama glyph)" % pat, n)
    return ("huruf", letters, mark, var)


def parse(path):
    entries = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=>" not in line:
            die("tulis: huruf => titik dx dy   (lihat contoh di bagian atas berkas)", n)
        pat, act = line.split("=>", 1)
        reg_txt, _, bold_txt = act.partition("|")
        reg = parse_values(reg_txt, n, "nilai")
        bold = None
        if bold_txt.strip():
            b = bold_txt.strip()
            if not b.lower().startswith("bold"):
                die("sesudah | tulis: Bold titik dx dy", n)
            bold = parse_values(b[4:], n, "nilai Bold")
        entries.append((n, line, parse_pattern(pat, n), reg, bold))
    return entries


def glyph_names(font, pat, cmap, n):
    if pat[0] == "glyph":
        import fnmatch
        return {x for x in font.keys() if fnmatch.fnmatchcase(x, pat[1])}
    _, letters, mark, var = pat
    sfx = {"^": r"\.init", "~": r"\.medi", "$": r"\.fina", "": "", "_": r"(?!\.(init|medi|fina)(\.|$))"}[mark]
    vrx = (r"\." + re.escape(var).replace(r"\*", ".*")) if var else ""
    out = set()
    for c in letters:
        if ord(c) not in cmap:
            die("huruf %r tidak ada di font" % c, n)
        rx = re.compile("^%s%s%s(\\..*)?$" % (re.escape(cmap[ord(c)]), sfx, vrx))
        out |= {x for x in font.keys() if rx.match(x)}
    return out


def apply(font):
    if not os.path.exists(TXT):
        return
    # openFont juga dipakai untuk font Latin (mergeLatin); lewati font yang tidak punya titik Arab
    if "dotabove-ar" not in font and "dotbelow-ar" not in font:
        return
    entries = parse(TXT)
    if not entries:
        return
    from fontTools.misc.transform import Transform
    bold = (font.info.openTypeOS2WeightClass or 400) >= 600
    cmap = {}
    for g in font:
        for u in g.unicodes:
            cmap.setdefault(u, g.name)
    # per glyph: baris yang cocok, urut seperti di berkas
    todo = {}
    for n, line, pat, reg, bld in entries:
        names = glyph_names(font, pat, cmap, n)
        if not names:
            print("peringatan titik-posisi.txt:%d: pola %r tidak cocok dengan glyph apa pun" % (n, line.split("=>")[0].strip()))
        for nm in names:
            todo.setdefault(nm, []).append((n, reg, bld))
    log = []
    for nm, rules in todo.items():
        g = font[nm]
        done = set()                                   # setiap komponen titik hanya sekali
        for n, reg, bld in rules:
            for idx, c in enumerate(g.components):
                if idx in done:
                    continue
                info = classify(c.baseGlyph)
                if not info:
                    continue
                cnt, side = info
                key = next((k for k in list(reg) + [k for k in (bld or {}) if k not in reg]
                            if k == "titik" or k == cnt or k == side), None)
                if key is None:
                    continue
                v = (bld[key] if bold and bld and key in bld else reg.get(key))
                if v is None:
                    continue
                t = tuple(c.transformation)
                c.transformation = Transform(t[0], t[1], t[2], t[3], t[4] + v[0], t[5] + v[1])
                done.add(idx)
                log.append(dict(glyph=nm, dot=c.baseGlyph, line=n, key=key, dx=v[0], dy=v[1]))
    if LOG:
        with open(LOG, "a", encoding="utf-8") as fh:
            for r in log:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
