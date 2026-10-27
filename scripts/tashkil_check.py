#!/usr/bin/env python
# Amiri Pegon: collision check / auto-adjust for tashkil.
#
#   python scripts/tashkil_check.py fonts/Amiri-Regular.ttf --master Regular \
#          [--words 6000] [--rounds 1] [--write]
#
# Shapes random words with tashkil, finds marks that come closer than MIN units
# to a neighbouring letter/mark, and searches, per base glyph, the smallest
# (dx, dy) shift of its anchor that clears every context seen. With --write the
# cumulative shifts go to sources/tashkil-adjust.json (read by tashkil_anchors).
import argparse, json, os, random, sys, collections
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity

sys.path.insert(0, os.path.dirname(__file__))
from tashkil_anchors import _flatten

LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهويةءؤئأإ") + \
    ["\u06A0", "\u06A4", "\u0686", "\u0762", "\u08B4", "\u088B", "\u06BD", "\u06D1", "\u06A9", "\u06CC"]
HARAKAT = ["\u064E", "\u064F", "\u0650", "\u064B", "\u064C", "\u064D", "\u0652"]
SHADDA = "\u0651"
MAXDY = 160   # cap on a single round; total is clamped again in tashkil_anchors
ADJ = os.path.join(os.path.dirname(__file__), "..", "sources", "tashkil-adjust.json")


TOOTH = list("بتثنيئ") + ["\u06BD", "\u06D1", "\u06CC", "\u06A4"]
CALT = list("سشحجخمهكلرا") + ["\u0686", "\u0762", "\u08B4", "\u088B", "\u06A0"]


def all_letters(path):
    import unicodedata
    cmap = TTFont(path).getBestCmap()
    return [chr(c) for c in sorted(cmap) if unicodedata.category(chr(c)) == "Lo" and
            (0x620 <= c <= 0x6FF or 0x750 <= c <= 0x77F or 0x8A0 <= c <= 0x8FF) and c != 0x640]


def make_words(n, seed=1, letters=None):
    letters = letters or LETTERS
    r = random.Random(seed); out = []
    for _ in range(n):
        w = ""
        for _ in range(r.randint(3, 7)):
            x0 = r.random()
            w += r.choice(TOOTH) if x0 < .20 else (r.choice(CALT) if x0 < .40 else r.choice(letters))
            x = r.random()
            if x < .15: w += SHADDA + r.choice(HARAKAT)
            elif x < .25: w += SHADDA
            elif x < .80: w += r.choice(HARAKAT)
        out.append(w)
    return out


class Geo:
    def __init__(self, path):
        self.tt = TTFont(path); self.gs = self.tt.getGlyphSet(); self.order = self.tt.getGlyphOrder()
        self.hbf = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
        cd = self.tt["GDEF"].table.GlyphClassDef.classDefs
        self.marks = {g for g, c in cd.items() if c == 3}
        self.cache = {}

    def poly(self, name):
        if name in self.cache: return self.cache[name]
        pen = RecordingPen(); self.gs[name].draw(pen)
        flat, sub = [], []
        for op, a in pen.value:
            sub.append((op, a))
            if op in ("closePath", "endPath"):
                pts = _flatten(sub); 
                if len(pts) > 2: flat.append(pts)
                sub = []
        outers, holes = [], []
        for pts in flat:
            pg = Polygon(pts)
            if not pg.is_valid: pg = pg.buffer(0)
            if pg.is_empty: continue
            area = sum((pts[i][0]*pts[(i+1) % len(pts)][1]-pts[(i+1) % len(pts)][0]*pts[i][1]) for i in range(len(pts)))
            (outers if area < 0 else holes).append(pg)   # TrueType: clockwise = filled
        g = unary_union(outers) if outers else Polygon()
        if holes: g = g.difference(unary_union(holes))
        self.cache[name] = g
        return g

    def shape(self, text):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
        buf.direction = "rtl"; buf.script = "Arab"
        hb.shape(self.hbf, buf, {})
        x = 0; out = []
        for i, p in zip(buf.glyph_infos, buf.glyph_positions):
            n = self.order[i.codepoint]
            out.append(dict(name=n, cl=i.cluster, x=x+p.x_offset, y=p.y_offset, mark=n in self.marks))
            x += p.x_advance
        return out

    def placed(self, it):
        return affinity.translate(self.poly(it["name"]), it["x"], it["y"])


def instances(geo, text, MIN):
    """yield (base_name, side, group_polygon, obstacles_polygon, violations_now)"""
    items = geo.shape(text)
    for it in items: it["poly"] = geo.placed(it)
    by = collections.defaultdict(list)
    for i, it in enumerate(items): by[it["cl"]].append(i)
    res = []
    for cl, idxs in by.items():
        bases = [i for i in idxs if not items[i]["mark"]]
        if not bases: continue
        b = items[bases[0]]
        for side in ("A", "B"):
            g = [items[i] for i in idxs if items[i]["mark"] and not items[i]["poly"].is_empty and
                 ((items[i]["poly"].centroid.y > 0) == (side == "A"))]
            if not g: continue
            grp = unary_union([m["poly"] for m in g]).simplify(2)
            near = grp.buffer(260).bounds           # only what can matter after a shift
            others = unary_union([it["poly"] for j, it in enumerate(items) if j not in idxs
                                  and not it["poly"].is_empty and _hits(it["poly"], near)]).simplify(3)
            own = b["poly"].simplify(3)
            res.append((b["name"], side, grp, others, own))
    return res


def _hits(poly, bb):
    x0, y0, x1, y1 = poly.bounds
    return not (x1 < bb[0] or x0 > bb[2] or y1 < bb[1] or y0 > bb[3])


def violates(grp, others, own, dx, dy, MIN, MINSELF):
    g = affinity.translate(grp, dx, dy)
    if g.distance(others) < MIN: return 1
    if g.distance(own) < MINSELF: return 1
    return 0


def collect(path, words, MIN):
    geo = Geo(path); cons = collections.defaultdict(list); total = bad = 0
    for w in words:
        for base, side, grp, others, own in instances(geo, w, MIN):
            total += 1
            v = violates(grp, others, own, 0, 0, MIN, 10); bad += v
            lst = cons[(base, side)]
            if v or len(lst) < 8:
                lst.append((grp, others, own))
    return total, bad, dict(cons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("font"); ap.add_argument("--master", default="Regular")
    ap.add_argument("--words", type=int, default=4000); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min", type=float, default=22); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    geo = Geo(a.font)
    cons = collections.defaultdict(list)       # (base, side) -> [(grp,others,own)]
    total = bad = 0
    import multiprocessing as mp
    words = make_words(a.words, a.seed, all_letters(a.font))
    chunks = [words[i::os.cpu_count()] for i in range(os.cpu_count())]
    with mp.Pool(os.cpu_count()) as pool:
        for t, b, c in pool.starmap(collect, [(a.font, ch, a.min) for ch in chunks]):
            total += t; bad += b
            for k, v in c.items():
                cons[k].extend(v)
    for k in cons:   # keep violating contexts first, cap size
        cons[k].sort(key=lambda t: -violates(*t, 0, 0, a.min, 10))
        cons[k] = cons[k][:16]
    print(f"{a.font}: {total} mark groups, {bad} too close (<{a.min}u) = {100*bad/max(total,1):.2f}%; "
          f"{len(set(b for b, s in cons))} distinct base glyphs seen")
    adj = {}
    if os.path.exists(ADJ): adj = json.load(open(ADJ))
    adj.setdefault(a.master, {})
    fixed = unfixed = 0
    for (base, side), lst in cons.items():
        if not any(violates(g, o, w, 0, 0, a.min, 10) for g, o, w in lst): continue
        sgn = 1 if side == "A" else -1
        best = None
        for dy in range(0, MAXDY+1, 20):
            for dx in (0, 25, -25, 50, -50):
                v = sum(violates(g, o, w, dx, sgn*dy, a.min, 10) for g, o, w in lst)
                c = (v * 50 + dy + 0.8*abs(dx), v)       # a violation is worth ~50u of shift
                if best is None or c < best[0]: best = (c, dx, dy)
        (cost, v), dx, dy = best
        if v == 0: fixed += 1
        else: unfixed += 1
        e = adj[a.master].setdefault(base, {})
        e["dy"+side] = round(e.get("dy"+side, 0) + sgn*dy)
        e["dx"+side] = round(e.get("dx"+side, 0) + dx)
        e.setdefault("residual"+side, 0); e["residual"+side] = v
    print(f"glyph/side fully cleared: {fixed}, partly (unavoidable): {unfixed}")
    if a.write:
        for g in adj[a.master].values():
            for k in [k for k in g if k.startswith("residual")]: del g[k]
            for k in g:
                g[k] = max(-160, min(160, g[k])) if k.startswith("dy") else max(-60, min(60, g[k]))
        json.dump(adj, open(ADJ, "w"), indent=1, sort_keys=True); print("wrote", ADJ)


if __name__ == "__main__":
    main()
