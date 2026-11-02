# Amiri Pegon: shrink tashkil glyphs (80%, maddah 60%).
import re
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen

BASES = ["fatha", "damma", "kasra", "fathatan", "dammatan", "kasratan",
         "shadda", "sukun", "openfathatan", "opendammatan", "openkasratan"]
SCALE = 0.8
MADDA = 0.6
PIVOTS = ["_TashkilAbove", "_TashkilBelow", "_TashkilTashkilAbove",
          "_TashkilTashkilBelow", "_MarkAbove", "_MarkBelow"]


def targets(font):
    out = {}
    for name in font.keys():
        m = re.match(r"([a-z]+)-ar(\..*)?$", name)
        if not m:
            continue
        if m.group(1) in BASES:
            out[name] = SCALE
        elif m.group(1) == "madda":
            out[name] = MADDA
    return out


def apply(font):
    tg = targets(font)
    if not tg:
        return
    # 1. keep an untouched copy for glyphs that use a tashkil as a component
    #    (precomposed letters, U+FDFD ...): they must not change.
    users = {}
    for g in font:
        if g.name in tg:
            continue
        for c in g.components:
            if c.baseGlyph in tg:
                if c.baseGlyph == "madda-ar" and g.name.startswith("alefMadda-ar"):
                    continue  # alef-madda letters follow the scaled maddah
                users.setdefault(c.baseGlyph, []).append(c)
    # 2. decompose target glyphs against ORIGINAL geometry
    rec = {}
    for name in tg:
        pen = DecomposingRecordingPen(font)
        font[name].draw(pen)
        rec[name] = pen
    for base, comps in users.items():
        alias = base + ".noscale"
        if alias not in font:
            g = font.newGlyph(alias)
            g.width = font[base].width
            rec[base].replay(g.getPen())
            for a in font[base].anchors:
                g.appendAnchor(dict(name=a.name, x=a.x, y=a.y))
            skip = font.lib.get("public.skipExportGlyphs")
            if skip is not None:
                skip.append(alias)
        for c in comps:
            c.baseGlyph = alias
    # 3. scale about the attachment anchor
    for name, s in tg.items():
        g = font[name]
        anchors = {a.name: (a.x, a.y) for a in g.anchors}
        px, py = 0, 0
        for p in PIVOTS:
            if p in anchors:
                px, py = anchors[p]
                break
        t = (s, 0, 0, s, px * (1 - s), py * (1 - s))
        g.clearContours()
        g.clearComponents()
        rec[name].replay(TransformPen(g.getPen(), t))
        for a in g.anchors:
            if not a.name.startswith("_"):
                a.x = px + (a.x - px) * s
                a.y = py + (a.y - py) * s
