#!/usr/bin/env python3
"""Build intermediate weights (Medium, SemiBold) of Amiri Pegon.

Glyphs whose Regular and Bold masters are structurally compatible are
interpolated.  The ~10% of glyphs that are not compatible are produced by
dilating the Regular outline until its area equals the area an interpolated
glyph would have.  Dot/mark positions are always interpolated.
"""
import argparse, copy, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import build
import pathops
from pathops import Path, PathOp, LineCap, LineJoin
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.basePen import BasePen


class CubicPen(BasePen):
    """Forward to a segment pen, converting quadratic segments to cubic."""
    def __init__(self, target):
        super().__init__(None)
        self.t = target
    def _moveTo(self, p): self.t.moveTo(p)
    def _lineTo(self, p): self.t.lineTo(p)
    def _curveToOne(self, a, b, c): self.t.curveTo(a, b, c)
    def _closePath(self): self.t.closePath()
    def _endPath(self): self.t.endPath()

stats = {"interp": 0, "dilate": 0, "same": 0}


def sig(c):
    return tuple(p.type for p in c.points)


def area(c):
    from fontTools.pens.areaPen import AreaPen
    pen = AreaPen()
    c.draw(pen)
    return pen.value


def match_contours(cr, cb):
    """Return list of (contourR, contourB, rotation) or None."""
    if len(cr) != len(cb):
        return None
    def key(c):
        b = c.bounds
        return (round((b[0] + b[2]) / 100), round((b[1] + b[3]) / 100)) if b else (0, 0)
    for order in (lambda x: list(x), lambda x: sorted(x, key=key)):
        A, B = order(cr), order(cb)
        out = []
        ok = True
        for a, b in zip(A, B):
            r = rotation(a, b)
            if r is None:
                ok = False
                break
            out.append((a, b, r))
        if ok:
            return out
    return None


def rotation(a, b):
    pa, pb = a.points, b.points
    if len(pa) != len(pb):
        return None
    sa, sb = sig(a), sig(b)
    if (area(a) > 0) != (area(b) > 0):
        return None
    if any(t == "move" for t in sa) or any(t == "move" for t in sb):
        return 0 if sa == sb else None
    n = len(pa)
    best = None
    for k in range(n):
        if all(sa[i] == sb[(i + k) % n] for i in range(n)):
            d = sum((pa[i].x - pb[(i + k) % n].x) ** 2 + (pa[i].y - pb[(i + k) % n].y) ** 2 for i in range(n))
            if best is None or d < best[0]:
                best = (d, k)
    return None if best is None else best[1]


def comps_key(c):
    return (c.baseGlyph, round(c.transformation[4]), round(c.transformation[5]))


def compatible(gr, gb):
    if sorted(c.baseGlyph for c in gr.components) != sorted(c.baseGlyph for c in gb.components):
        return None
    m = match_contours(list(gr.contours), list(gb.contours))
    if m is None:
        return None
    return m


def lerp(a, b, t):
    return a + (b - a) * t


def to_path(font, glyph):
    p = Path()
    glyph.draw(p.getPen(glyphSet=font))
    p.simplify(fix_winding=True)
    return p


def path_area(p):
    pen = AreaPen()
    p.draw(pen)
    return abs(pen.value)


def dilate(p, d):
    if d <= 0:
        return Path(p)
    s = Path(p)
    s.stroke(2 * d, LineCap.ROUND_CAP, LineJoin.ROUND_JOIN, 4)
    s.convertConicsToQuads(0.25)
    out = pathops.op(p, s, PathOp.UNION, fix_winding=True)
    return out


def dilated_outline(reg, bld, name, t):
    pr = to_path(reg, reg[name])
    pb = to_path(bld, bld[name])
    ar, ab = path_area(pr), path_area(pb)
    target = ar + (ab - ar) * t
    if target <= ar or ar == 0:
        return pr
    lo, hi = 0.0, 80.0
    for _ in range(14):
        mid = (lo + hi) / 2
        if path_area(dilate(pr, mid)) < target:
            lo = mid
        else:
            hi = mid
    return dilate(pr, (lo + hi) / 2)


def set_outline(glyph, path):
    glyph.clearContours()
    glyph.clearComponents()
    pen = glyph.getPen()
    path.draw(CubicPen(pen))


def interpolate_fonts(reg, bld, t):
    inst = copy.deepcopy(reg)
    for g in inst:
        name = g.name
        if name not in bld:
            continue
        gr, gb = reg[name], bld[name]
        g.width = round(lerp(gr.width, gb.width, t))
        # anchors
        banch = {a.name: a for a in gb.anchors}
        for a in g.anchors:
            if a.name in banch:
                a.x = round(lerp(a.x, banch[a.name].x, t))
                a.y = round(lerp(a.y, banch[a.name].y, t))
        m = compatible(gr, gb)
        if m is None:
            # not compatible
            if not gr.contours and not gr.components:
                continue
            set_outline(g, dilated_outline(reg, bld, name, t))
            stats["dilate"] += 1
            continue
        # contours
        # build lookup from reg contour object to index in glyph
        idx = {id(c): i for i, c in enumerate(gr.contours)}
        for a, b, k in m:
            c = g.contours[idx[id(a)]]
            n = len(a.points)
            for i, p in enumerate(c.points):
                q = b.points[(i + k) % n]
                p.x = round(lerp(a.points[i].x, q.x, t), 2)
                p.y = round(lerp(a.points[i].y, q.y, t), 2)
        # components
        sr = sorted(range(len(gr.components)), key=lambda i: comps_key(gr.components[i]))
        sb = sorted(range(len(gb.components)), key=lambda i: gb.components[i].baseGlyph)
        sr = sorted(range(len(gr.components)), key=lambda i: gr.components[i].baseGlyph)
        for i, j in zip(sr, sb):
            ca, cb = gr.components[i], gb.components[j]
            g.components[i].transformation = tuple(lerp(x, y, t) for x, y in zip(ca.transformation, cb.transformation))
        stats["interp"] += 1
    validate(reg, bld, inst, t)
    return inst


def glyph_area(font, name):
    try:
        return path_area(to_path(font, font[name]))
    except Exception:
        return None


def validate(reg, bld, inst, t, tol=0.12):
    """Interpolated glyphs whose area is far from the expected value (contours
    paired wrongly) fall back to the dilated outline."""
    done = set()
    for _ in range(2):
        fixed = 0
        for g in inst:
            name = g.name
            if name in done:
                continue
            if name not in bld or not (g.contours or g.components):
                continue
            ar, ab = glyph_area(reg, name), glyph_area(bld, name)
            ai = glyph_area(inst, name)
            if None in (ar, ab, ai):
                continue
            exp = ar + (ab - ar) * t
            lo, hi = min(ar, ab), max(ar, ab)
            if abs(ai - exp) > tol * max(exp, 1) + 150 or ai < lo * 0.9 - 150 or ai > hi * 1.1 + 150:
                set_outline(g, dilated_outline(reg, bld, name, t))
                stats["dilate"] += 1
                stats["interp"] -= 1
                fixed += 1
                done.add(name)
                a2 = glyph_area(inst, name)
                if a2 is None or abs(a2 - exp) > tol * max(exp, 1) + 150:
                    src = reg if t < 0.5 else bld
                    set_outline(g, to_path(src, src[name]))
                    print("  nearest master used:", name)
        if not fixed:
            break


def load(path):
    font = build.openFont(path)
    build.cleanAnchors(font)
    return font


def merge_latin(font, latin):
    for glyph in latin:
        try:
            font.addGlyph(glyph)
        except KeyError:
            pass
    font.glyphOrder += latin.glyphOrder
    font.lib["public.openTypeCategories"].update(latin.lib["public.openTypeCategories"])
    font.groups.update(latin.groups)
    font.kerning.update(latin.kerning)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regular", required=True)
    ap.add_argument("--bold", required=True)
    ap.add_argument("--latin-regular", required=True)
    ap.add_argument("--latin-bold", required=True)
    ap.add_argument("--weight", type=int, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--features", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    t = (a.weight - 400) / 300.0

    reg, bld = load(a.regular), load(a.bold)
    lreg, lbld = build.openFont(a.latin_regular), build.openFont(a.latin_bold)
    font = interpolate_fonts(reg, bld, t)
    latin = interpolate_fonts(lreg, lbld, t)
    merge_latin(font, latin)
    print("interpolated %d, dilated %d" % (stats["interp"], stats["dilate"]))

    info = font.info
    info.styleName = a.name
    info.postscriptFontName = "Amiri-" + a.name
    info.postscriptFullName = "Amiri " + a.name
    info.styleMapFamilyName = "Amiri " + a.name
    info.styleMapStyleName = "regular"
    info.openTypeNamePreferredFamilyName = "Amiri"
    info.openTypeNamePreferredSubfamilyName = a.name
    info.openTypeOS2WeightClass = a.weight

    build.makeOverLine(font, posGlyph="overlinecomb")

    class O: pass
    o = O()
    o.features, o.version, o.license, o.output, o.quran, o.slant = a.features, a.version, a.license, a.output, False, None
    otf = build.generateFont(o, font)
    otf.save(a.output)


if __name__ == "__main__":
    main()
