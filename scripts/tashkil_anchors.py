# Amiri Pegon: contour-aware tashkil anchors.
#
# Amiri puts TashkilAbove/TashkilBelow at one fixed height for nearly every
# glyph. Here every base glyph (isol/init/medi/fina, ligatures and the
# contextual alternates, which are all single glyphs) gets its anchors
# recomputed from its own outline, in the way Scheherazade New does it:
#
#   mark bottom = max(FLOOR, top of the letter under the mark + gap)
#   mark top    = min(CEIL,  bottom of the letter under the mark - gap)
#
# "under the mark" is the outline inside the horizontal footprint of the mark.
# Dots get a slightly bigger gap than the letter body. All numbers are in
# units of 1000 em and are scaled by UPM. Per-glyph manual / collision
# corrections live in sources/tashkil-adjust.json ({master: {glyph: {dyA,dxA,
# dyB,dxB}}}) and are added on top.
import json, math, os, re
from fontTools.pens.recordingPen import DecomposingRecordingPen

P = dict(
    HALF=95,         # half footprint width of a mark
    GAP_A=85,        # clearance above letter body
    GAP_A_DOT=120,   # clearance above dots
    FLOOR_A=530,     # lowest allowed mark bottom (above baseline); Scheherazade/Noto use ~480-590
    ASC_MIN=600,     # body points above this height form an "ascender" (alef, lam, tah, kaf...)
    GAP_STEM=105,    # clearance between mark and the top of the ascender
    STEM_REACH=340,  # ascender counts for the mark if its tip is at most this far (x) from the anchor
    KAF_LEFT=145,    # kaf family: mark sits this far left of the stroke tip (Scheherazade: ~240)
    STEM_SPAN=300,   # tip narrower than this: anchor x is centred on it (ا ل ط ظ ك)
    GAP_B=75,        # clearance below dots/body that already hang under baseline
    GAP_B_BASE=105,  # clearance below the baseline for flat-bottom letters
    CEIL_B=-105,     # highest allowed mark top (below baseline)
)
DOT_RE = re.compile(r"^(dot|twodots|threedots|fourdots|ring|vabove|vbelow|"
                    r"dotbelow|dotabove|twodotsbelow|twodotsabove|hamza)")
KAF = ("kaf", "keheh", "gaf")
ABOVE_REF = ["fatha-ar", "damma-ar", "sukun-ar", "shadda-ar", "fathatan-ar", "dammatan-ar"]
BELOW_REF = ["kasra-ar", "kasratan-ar"]


def _flatten(pen_value, step=10.0):
    pts, cur, start = [], None, None

    def line(a, b):
        n = max(1, int(math.hypot(b[0]-a[0], b[1]-a[1]) / step))
        for i in range(1, n+1):
            t = i/n
            pts.append((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t))

    for op, args in pen_value:
        if op == "moveTo":
            cur = start = args[0]; pts.append(cur)
        elif op == "lineTo":
            line(cur, args[0]); cur = args[0]
        elif op == "curveTo":
            p = [cur] + list(args)
            for i in range(1, 25):
                t = i/24; u = 1-t
                pts.append((u**3*p[0][0]+3*u*u*t*p[1][0]+3*u*t*t*p[2][0]+t**3*p[3][0],
                            u**3*p[0][1]+3*u*u*t*p[1][1]+3*u*t*t*p[2][1]+t**3*p[3][1]))
            cur = args[-1]
        elif op == "qCurveTo":
            offs, end = list(args[:-1]), args[-1]
            p0 = cur
            for i, o in enumerate(offs):
                nxt = ((o[0]+offs[i+1][0])/2, (o[1]+offs[i+1][1])/2) if i < len(offs)-1 else end
                for k in range(1, 13):
                    t = k/12; u = 1-t
                    pts.append((u*u*p0[0]+2*u*t*o[0]+t*t*nxt[0], u*u*p0[1]+2*u*t*o[1]+t*t*nxt[1]))
                p0 = nxt
            cur = end
        elif op in ("closePath", "endPath"):
            if cur and start and cur != start:
                line(cur, start)
            cur = start
    return pts


def outline(font, glyph, dots_only=None):
    """Sampled outline. dots_only=True: only dot-like components, False: all
    except those, None: everything."""
    pts = []
    if glyph.contours:
        pen = DecomposingRecordingPen(font)
        # own contours only
        for c in glyph.contours:
            c.draw(pen)
        if dots_only in (None, False):
            pts += _flatten(pen.value)
    for comp in glyph.components:
        isdot = bool(DOT_RE.match(comp.baseGlyph))
        if dots_only is not None and isdot != dots_only:
            continue
        pen = DecomposingRecordingPen(font)
        comp.draw(pen)
        pts += _flatten(pen.value)
    return pts


def _window(pts, x0, x1, side):
    ys = [y for x, y in pts if x0 <= x <= x1]
    if not ys:
        return None
    return max(ys) if side == "A" else min(ys)


def ascender(body, ax, p):
    """Nearest ascender tip to x=ax: (top, centre_x, width) or None."""
    hi = sorted(x for x, y in body if y >= p["ASC_MIN"])
    if not hi:
        return None
    clusters, cur = [], [hi[0]]
    for x in hi[1:]:
        if x - cur[-1] > 120: clusters.append(cur); cur = []
        cur.append(x)
    clusters.append(cur)
    best = None
    for c in clusters:
        lo, up = c[0], c[-1]
        top = max(y for x, y in body if lo <= x <= up)
        tip = [x for x, y in body if lo <= x <= up and y >= top - 80]
        cx, w = (min(tip) + max(tip)) / 2, max(tip) - min(tip)
        d = abs(cx - ax)
        if best is None or d < best[0]:
            best = (d, top, cx, w)
    d, top, cx, w = best
    return (top, cx, w) if d <= p["STEM_REACH"] else None


def mark_offsets(font):
    """Distance mark-bottom (above) / mark-top (below) to its attach anchor,
    measured on the (already shrunk) mark glyphs."""
    offA, offB, halfA, halfB = [], [], [], []
    for n in ABOVE_REF:
        if n in font:
            g = font[n]; b = g.getBounds(font)
            a = next((a for a in g.anchors if a.name == "_TashkilAbove"), None)
            if b and a:
                offA.append(b.yMin - a.y); halfA.append(max(a.x-b.xMin, b.xMax-a.x))
    for n in BELOW_REF:
        if n in font:
            g = font[n]; b = g.getBounds(font)
            a = next((a for a in g.anchors if a.name == "_TashkilBelow"), None)
            if b and a:
                offB.append(a.y - b.yMax); halfB.append(max(a.x-b.xMin, b.xMax-a.x))
    return (max(offA) if offA else 30, max(offB) if offB else -16,
            max(halfA) if halfA else 100, max(halfB) if halfB else 100)


def center_shift(font):
    """The anchor of fatha/damma/tanwin sits left of the visual centre of the
    mark; return how far, so that the mark looks centred over a stem."""
    d = []
    for n in ("fatha-ar", "damma-ar", "fathatan-ar", "dammatan-ar"):
        if n in font:
            g = font[n]; b = g.getBounds(font)
            a = next((a for a in g.anchors if a.name == "_TashkilAbove"), None)
            if b and a:
                d.append(a.x - (b.xMin + b.xMax) / 2)
    return sum(d) / len(d) if d else 0.0


def load_adjust(master):
    path = os.path.join(os.path.dirname(__file__), "..", "sources", "tashkil-adjust.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f).get(master, {})


def apply(font, master="Regular"):
    s = font.info.unitsPerEm / 1000.0
    p = {k: v*s for k, v in P.items()}
    cats = font.lib.get("public.openTypeCategories", {})
    offA, offB, hA, hB = mark_offsets(font)
    cshift = center_shift(font)
    adjust = load_adjust(master)
    clamp = lambda v, lim: max(-lim, min(lim, v))
    MAXDY, MAXDX = 160, 60     # sanity limits for collision corrections
    log = {}
    for g in font:
        if cats.get(g.name) == "mark" or g.name.startswith(("dot", "twodots", "threedots")):
            continue
        anc = {a.name: a for a in g.anchors}
        ta, tb = anc.get("TashkilAbove"), anc.get("TashkilBelow")
        if not (ta or tb) or (not g.contours and not g.components):
            continue
        body = outline(font, g, dots_only=False)
        dots = outline(font, g, dots_only=True)
        allp = body + dots
        if not allp:
            continue
        adj = adjust.get(g.name, {})
        if ta:
            w = max(hA, p["HALF"])
            x0, x1 = ta.x - w, ta.x + w
            tb_ = _window(body, x0, x1, "A"); td_ = _window(dots, x0, x1, "A")
            cand = [p["FLOOR_A"]]
            if tb_ is not None: cand.append(tb_ + p["GAP_A"])
            if td_ is not None: cand.append(td_ + p["GAP_A_DOT"])
            if tb_ is None and td_ is None:   # anchor outside the outline: use glyph top
                cand.append(max(y for x, y in allp) + p["GAP_A"])
            asc = ascender(body, ta.x, p)
            if asc:                      # tall letters: clear the stem, centre on it if it is a vertical stem
                top, cx, wd = asc
                cand.append(top + p["GAP_STEM"])
                if wd <= p["STEM_SPAN"]:
                    kaf = g.name.startswith(KAF)
                    ta.x = cx + cshift - (p["KAF_LEFT"] if kaf else 0)
                    # kaf: the stroke is diagonal, so clear it where the mark really is
                    # (not the tip, which is further right and higher)
                    ref = _window(body, ta.x - w, ta.x + w, "A") if kaf else top
                    td2 = _window(dots, ta.x - w, ta.x + w, "A")
                    cand = [p["FLOOR_A"], (ref if ref is not None else top) + p["GAP_STEM"]] + \
                           ([td2 + p["GAP_A_DOT"]] if td2 is not None else [])
            ta.y = max(cand) - offA + clamp(adj.get("dyA", 0), MAXDY)
            ta.x += clamp(adj.get("dxA", 0), MAXDX)
        if tb:
            w = max(hB, p["HALF"])
            x0, x1 = tb.x - w, tb.x + w
            bb_ = _window(body, x0, x1, "B"); bd_ = _window(dots, x0, x1, "B")
            cand = [p["CEIL_B"]]
            if bb_ is not None: cand.append(min(bb_, 0) - p["GAP_B_BASE"] if bb_ >= -5 else bb_ - p["GAP_B"])
            if bd_ is not None: cand.append(bd_ - p["GAP_B"])
            if bb_ is None and bd_ is None:
                cand.append(min(y for x, y in allp) - p["GAP_B"])
            tb.y = min(cand) - offB + clamp(adj.get("dyB", 0), MAXDY)
            tb.x += clamp(adj.get("dxB", 0), MAXDX)
    return log
