#!/usr/bin/env python3
"""Reads sources/tashkil-posisi.txt and writes sources/tashkil_context.fea.

SEMANTICS (important):
  * A rule with ONE letter (bentuk dasar) shifts the mark from the original Amiri position.
  * A rule with TWO OR MORE letters (konteks) is ADDED ON TOP of the BASE FORM only, i.e. the one-letter rule of
    the target letter (one level, no chain).  It never inherits from another context rule.  So "0 0" in a
    context rule = exactly the base form; "-100 0" = base form shifted a further 100 to the left.  The base
    value is resolved per glyph (init/medi/fina/isol differ).  A longer line that must keep the shift of a
    shorter context line has to repeat it (a warning is printed when that happens).
  * "atas = dx dy" (an "=" right after atas/bawah/mark name) is ABSOLUTE: relative to the original Amiri
    position, the base form is not added.

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
    # hapus hasil lama: kalau tidak, build berikutnya diam-diam memakai aturan LAMA
    try:
        os.remove(OUT)
    except OSError:
        pass
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
    vals, absk = {}, set()
    toks = text.split()
    i = 0
    while i < len(toks):
        if toks[i] not in ("atas", "bawah") and toks[i] not in MARKNAMES:
            die("%s: tulis atas / bawah / nama tanda (%s) lalu dx dy (bukan %r)" % (what, " ".join(MARKNAMES), toks[i]), n)
        side = toks[i]
        j = i + 1
        if j < len(toks) and toks[j] == "=":          # "atas = dx dy": nilai ABSOLUT (relatif Amiri)
            absk.add(side)
            j += 1
        try:
            vals[side] = (int(toks[j]), int(toks[j + 1]))
        except (IndexError, ValueError):
            die("%s: sesudah '%s' harus ada dua ANGKA (dx dy), ditemukan %r" % (what, side, " ".join(toks[j:j + 2])), n)
        i = j + 2
    if not vals:
        die("%s: tidak ada nilai" % what, n)
    return vals, absk


def parse_line(line, n):
    if "=>" not in line:
        die("tulis: huruf => atas dx dy   (lihat contoh di bagian atas berkas)", n)
    pat, act = line.split("=>", 1)
    reg_txt, _, bold_txt = act.partition("|")
    reg, ra = parse_values(reg_txt, n, "nilai")
    bold, ba = None, set()
    if bold_txt.strip():
        b = bold_txt.strip()
        if not b.lower().startswith("bold"):
            die("sesudah | tulis: Bold atas dx dy", n)
        bold, ba = parse_values(b[4:], n, "nilai Bold")
    ab = ra | ba            # sisi yang ditulis dengan "=" (berlaku untuk semua bobot)
    if pat.strip() == "*":
        return [(None, "")], 0, reg, bold, ab
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
    return slots, 0 if target is None else target, reg, bold, ab


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
    for e in entries:
        if len(e[2]) == 1 and e[6]:
            print("peringatan baris %d: tanda = pada aturan satu huruf tidak berpengaruh (sudah relatif terhadap Amiri)" % e[0])
    seen = {}
    for e in entries:
        key = re.sub(r"\\s+", " ", e[1].split("=>")[0].strip())
        if key in seen:
            print("peringatan baris %d: pola %r sudah ada di baris %d (yang pertama menang, ini tidak berlaku)" % (e[0], key, seen[key]))
        else:
            seen[key] = e[0]
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
    # kashida (mis. kashida-ar.05 yang disisipkan Amiri sesudah khah/hah tertentu, atau tatwil yang diketik)
    # berada di antara huruf dan tashkilnya: perlakukan sebagai "perantara" supaya pola tetap cocok
    kash = [x for x in names if re.match(r"^kashida-ar(\..*)?$", x) and x not in set(ta + tb + extra)]
    # penghalang tak terlihat dari batal-ligatur (zerowidthspace): berada setelah tashkil huruf kiri
    zw = [x for x in names if x == "zerowidthspace" and x not in set(ta + tb + extra + kash)]
    allmarks = ta + tb + extra + kash + zw
    mset = set(allmarks)
    cls = lambda nm, g: L.append("@%s = [%s];" % (nm, " ".join(g)))
    cls("TP_ABOVE", ta); cls("TP_BELOW", tb); cls("TP_ALL", allmarks)
    if zw:
        cls("TP_ZW", zw)
    cls("TP_BASE", [x for x in names if x not in mset])
    lookups = {w: [] for w in WEIGHTS}
    rules = []
    ZERO = tuple((0, 0) for _ in WEIGHTS)

    # ---- pass 1: resolve every line to glyph classes and keys ------------------------------------
    infos = {}
    for i, (n, line, slots, tgt, reg, bold, _ab) in enumerate(entries):
        classes, glyphs, ok = [], [], True
        for k, (letters, mark) in enumerate(slots):
            g = [x for x in names if x not in mset] if letters is None else letter_class(letters, mark, names, cmap, n)
            if not g:
                print("peringatan baris %d: pola %r tidak cocok dengan glyph apa pun, baris dilewati" % (n, line.split("=>")[0].strip()))
                ok = False
                break
            classes.append("TP_BASE" if letters is None else "TP_%d_%d" % (i, k))
            glyphs.append(g)
        if not ok:
            continue
        kinfo = []
        for key in list(reg) + [k for k in (bold or {}) if k not in reg]:
            if key == "atas":
                Tn = ta
            elif key == "bawah":
                Tn = tb
            else:
                Tn = [x for x in names if mrx[key].match(x)]
                if not Tn:
                    print("peringatan baris %d: tanda %r tidak ada di font, dilewati" % (n, key))
                    continue
            vals = tuple(weight_value(reg, bold, key, w) for w in WEIGHTS)
            kinfo.append((key, Tn, vals))
        infos[i] = (classes, glyphs, kinfo)

    # ---- parent table: the one-letter rules, first match wins (same order as before) -------------
    tn_sets = {(i, key): set(Tn) for i in infos for key, Tn, vals in infos[i][2]}
    plist = []          # (set of base glyphs, set of marks, values per weight, entry index)
    for i in sorted(infos):
        if len(entries[i][2]) == 1:
            for key, Tn, vals in infos[i][2]:
                plist.append((set(infos[i][1][0]), set(Tn), vals, i, key))
    by_glyph = {}
    for e in plist:
        for g in e[0]:
            by_glyph.setdefault(g, []).append(e)

    gsets = {i: [set(x) for x in infos[i][1]] for i in infos}
    korder = sorted(infos, key=lambda i: (-len(entries[i][2]), i))      # urutan yang sama dengan aturan di font

    def delta(i, m):
        """geseran baris i pada tanda m (kunci pertama yang mencakup m), per bobot; None bila tidak mencakup"""
        for key, Tn, vals in infos[i][2]:
            if m in tn_sets[(i, key)]:
                return vals
        return None

    def absolute(i, m):
        """True bila baris i menulis sisi yang mencakup tanda m dengan "=" (nilai absolut, tanpa bentuk dasar)"""
        for key, Tn, vals in infos[i][2]:
            if m in tn_sets[(i, key)]:
                return key in entries[i][6]
        return False

    def is_ancestor(P, R, g):
        """Untuk huruf sasaran g: P berlaku di mana pun R berlaku. Pola P adalah potongan berurutan dari pola R
        yang mengandung huruf sasaran; g harus termasuk kelas sasaran P, dan setiap huruf lain di P harus
        mencakup seluruh kelas huruf yang sejajar di R."""
        sp, sr = gsets[P], gsets[R]
        tp, tr = entries[P][3], entries[R][3]
        o = tr - tp
        if P == R or o < 0 or o + len(sp) > len(sr) or g not in sp[tp]:
            return False
        if len(sp) == len(sr) and all(sp[j] == sr[j] for j in range(len(sp))):
            return False
        return all(sr[j + o] <= sp[j] for j in range(len(sp)) if j != tp)

    anc_cache = {}

    def ancestors(R, g):
        k = (R, g)
        if k not in anc_cache:
            # induk = HANYA aturan satu huruf (bentuk dasar); baris konteks tidak mewarisi baris konteks lain
            anc_cache[k] = [P for P in korder if len(entries[P][2]) == 1 and is_ancestor(P, R, g)] if len(entries[R][2]) > 1 else []
        return anc_cache[k]

    memo = {}

    def parent(R, g, m):
        """nilai total (relatif Amiri) bentuk dasar yang mencakup tanda m; nol bila tidak ada atau bila baris R memakai ="""
        if absolute(R, m):
            return ZERO
        for P in ancestors(R, g):
            if delta(P, m) is not None:
                return eff(P, g, m)
        return ZERO

    def eff(R, g, m):
        """posisi total baris R untuk (huruf g, tanda m) relatif terhadap Amiri: geseran sendiri + warisan"""
        k = (R, g, m)
        if k not in memo:
            d = delta(R, m) or ZERO
            par = parent(R, g, m)
            memo[k] = tuple((d[x][0] + par[x][0], d[x][1] + par[x][1]) for x in range(len(WEIGHTS)))
        return memo[k]

    def shadowed_zero_needed(idx):
        gs, ms, vals, _, _ = plist[idx]
        return any(f[0] & gs and f[1] & ms and f[2] != ZERO for f in plist[idx + 1:])

    # ---- peringatan: baris konteks bersarang di baris konteks lain pada tanda yang sama ---------------
    for R in korder:
        if len(entries[R][2]) < 2:
            continue
        tg = infos[R][1][entries[R][3]]
        kr = {k for k, _, _ in infos[R][2] if k not in entries[R][6]}
        for P in korder:
            if P == R or len(entries[P][2]) < 2 or not any(is_ancestor(P, R, x) for x in tg):
                continue
            lost = [k for k, _, vals in infos[P][2] if k in kr and any(v != (0, 0) for v in vals)]
            if lost:
                print("peringatan baris %d: pola %r bersarang di baris %d (%r) pada tanda %s; geseran baris %d TIDAK diwarisi "
                      "(induk hanya bentuk dasar). Tulis ulang geseran itu di baris %d bila perlu, atau pakai = untuk nilai absolut."
                      % (entries[R][0], entries[R][1].split("=>")[0].strip(), entries[P][0],
                         entries[P][1].split("=>")[0].strip(), "/".join(lost), entries[P][0], entries[R][0]))

    # ---- pass 2: emit; longer patterns first (in one lookup the first matching rule wins) ----------
    order = sorted(infos, key=lambda i: (-len(entries[i][2]), i))
    pidx = {(e[3], e[4]): x for x, e in enumerate(plist)}
    for i in order:
        n, line, slots, tgt, reg, bold, _ab = entries[i]
        classes, glyphs, kinfo = infos[i]
        for k, (letters, mark) in enumerate(slots):
            if letters is not None:
                cls(classes[k], glyphs[k])
        child = len(slots) > 1
        for j, (key, Tn, cvals) in enumerate(kinfo):
            if child:
                # base value is resolved per (base glyph, mark): group the pairs that share a parent value
                groups = {}
                for g in glyphs[tgt]:
                    for m in Tn:
                        groups.setdefault((parent(i, g, m), g), []).append(m)
                merged = {}
                for (pv, g), ms in groups.items():
                    merged.setdefault((pv, tuple(ms)), []).append(g)
                parts = [(pv, gl, set(ms)) for (pv, ms), gl in merged.items()]
            else:
                if cvals == ZERO and not shadowed_zero_needed(pidx[(i, key)]):
                    continue                      # nothing to say, and nothing below it to block
                parts = [(ZERO, glyphs[tgt], set(Tn))]
            other = "TP_%d_%d_O" % (i, j)
            cls(other, [x for x in allmarks if x not in set(Tn)])
            rules.append("    # baris %d (%s): %s" % (n, key, line.split("=>")[0].strip()))
            for pn, (pv, gl, ms) in enumerate(parts):
                vals = {w: (cvals[x][0] + pv[x][0], cvals[x][1] + pv[x][1]) for x, w in enumerate(WEIGHTS)}
                cl = list(classes)
                if len(parts) > 1 or child:
                    cl[tgt] = "TP_%d_%d_%d_G" % (i, j, pn)
                    cls(cl[tgt], gl)
                if key == "atas" and ms == set(ta):
                    T = "@TP_ABOVE"
                elif key == "bawah" and ms == set(tb):
                    T = "@TP_BELOW"
                else:
                    cls("TP_%d_%d_%d_T" % (i, j, pn), [m for m in Tn if m in ms])
                    T = "@TP_%d_%d_%d_T" % (i, j, pn)
                lk = "TP_L%d_%d_%d" % (i, j, pn)
                for w in WEIGHTS:
                    lookups[w].append("lookup %s { pos %s <%d %d 0 0>; } %s;" % (lk, T, vals[w][0], vals[w][1], lk))
                seqs = [s_ for ln in (1, 2, 3) for s_ in itertools.product("TO", repeat=ln) if "T" in s_]
                pre_opts = [[], ["@TP_ALL"], ["@TP_ALL"] * 2, ["@TP_ALL"] * 3]
                # huruf sesudah target: tanda milik huruf perantara (0-2) boleh berada di antaranya
                tails = [[]]
                gap0 = [[]] + ([["@TP_ZW"]] if zw else [])          # antara tashkil target dan huruf berikutnya
                for idx, c in enumerate(cl[tgt + 1:]):
                    tails = [t + o + ["@" + c] for t in tails for o in (pre_opts if idx else gap0)]
                for pre_marks in itertools.product(range(len(pre_opts)), repeat=tgt):
                    pre = []
                    for k in range(tgt):
                        pre += ["@" + cl[k]] + pre_opts[pre_marks[k]]
                    for s_ in seqs:
                        first, last = s_.index("T"), len(s_) - 1 - s_[::-1].index("T")
                        back = pre + ["@" + cl[tgt]] + ["@" + other for _ in s_[:first]]
                        inp = ["%s' lookup %s" % (T, lk) if s_[j2] == "T" else "@%s'" % other for j2 in range(first, last + 1)]
                        fwd = ["@" + other for _ in s_[last + 1:]]
                        for tail in tails:
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
