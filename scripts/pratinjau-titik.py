#!/usr/bin/env python3
"""Pratinjau aturan posisi titik tanpa mengubah repo.

  python3 scripts/pratinjau-titik.py -a "ب^.BaaMemInit => bawah 0 -40" "بما" "بم"
  python3 scripts/pratinjau-titik.py -a "ث => tiga 0 40 | Bold tiga 0 55" -m Bold "ثمر"
  python3 scripts/pratinjau-titik.py "بما" "بم" "ثمر"        # tanpa -a: bandingkan hasil edit langsung di titik-posisi.txt
  python3 scripts/pratinjau-titik.py --terima                # jadikan isi titik-posisi.txt sekarang sebagai dasar "sebelum"

Yang dilakukan:
  1. menambahkan baris -a (jika ada) ke salinan sementara titik-posisi.txt (berkas asli tidak diubah),
  2. membangun font sementara (Regular atau Bold): "sebelum" dan "sesudah".
     "Sesudah" = titik-posisi.txt di folder kerja (edit langsung Anda) + baris -a.
     "Sebelum" diambil dari yang pertama tersedia:
       -s font.ttf  >  -d berkas.txt  >  dasar tersimpan lewat --terima (build/titik-posisi.dasar.txt)
       >  font hasil `make` terakhir (fonts/Amiri-*.ttf atau fonts/AmiriPegon-*.ttf, yang terbaru),
  3. menggambar kata-kata Anda: hitam = sesudah aturan, biru = posisi titik SEBELUM aturan,
     lengkap dengan kisi berangka (1 kotak = 100 unit), dan mencetak daftar pergeseran titik tiap glyph
     beserta nama glyph yang dipakai kata itu (berguna untuk menunjuk varian: ب^.BaaMemInit).

Prasyarat: sudah pernah `make` (folder build/ berisi .ufo).
Pasang sekali:  pip install uharfbuzz matplotlib
"""
import argparse, collections, contextlib, io, os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SNAP = os.path.join(ROOT, "build", "titik-posisi.dasar.txt")
TXT = os.path.join(ROOT, "sources", "titik-posisi.txt")


def need(mod, pip):
    try:
        return __import__(mod, fromlist=["x"])
    except ImportError:
        sys.exit("Pasang dulu:  pip install %s" % pip)


def validate(txt, ufo, label):
    """Periksa penulisan DAN kecocokan huruf/glyph pada UFO tanpa mengompilasi font (beberapa detik).
    Mengembalikan peringatan (mis. pola yang tidak cocok dengan glyph apa pun); galat dihentikan di sini."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import titik
    from ufoLib2 import Font
    titik.TXT, titik.LOG = txt, None
    font = Font.open(ufo, validate=False)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            titik.apply(font)
    except SystemExit as e:
        sys.exit("[%s] %s" % (label, e))
    return [ln for ln in buf.getvalue().splitlines() if ln.startswith("peringatan")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-a", "--aturan", action="append", default=[], help="satu baris aturan (boleh diulang)")
    ap.add_argument("-m", "--master", default="Regular", choices=["Regular", "Bold"])
    ap.add_argument("-o", "--keluar", default="pratinjau-titik.png")
    ap.add_argument("-s", "--sebelum", help="font pembanding siap pakai (mempercepat; bawaan: lihat urutan di atas)")
    ap.add_argument("-d", "--dasar", help="berkas titik-posisi.txt pembanding untuk 'sebelum'")
    ap.add_argument("--terima", action="store_true",
                    help="simpan titik-posisi.txt sekarang sebagai dasar 'sebelum' berikutnya, lalu selesai")
    ap.add_argument("kata", nargs="*", help="kata contoh (lengkap dengan harakat)")
    a = ap.parse_args()
    ufo = os.path.join(ROOT, "build", "Amiri-%s.ufo" % a.master)
    if not os.path.exists(ufo):
        sys.exit("Belum ada %s. Jalankan `make` sekali dulu." % ufo)
    if a.terima:
        return terima(a, ufo)
    if not a.kata:
        ap.error("tulis minimal satu kata contoh")

    uh = need("uharfbuzz", "uharfbuzz")
    need("matplotlib", "matplotlib")
    from fontTools.ttLib import TTFont

    tmp = tempfile.mkdtemp(prefix="pratinjau-titik-")
    try:
        # 1. berkas sesudah = isi titik-posisi.txt sekarang + baris -a
        teks = open(TXT, encoding="utf-8").read() if os.path.exists(TXT) else ""
        sesudah_txt = os.path.join(tmp, "sesudah.txt")
        open(sesudah_txt, "w", encoding="utf-8").write(teks + "\n" + "\n".join(a.aturan) + "\n")
        for ln in validate(sesudah_txt, ufo, "sesudah"):
            print("!!", ln)

        # 2. tentukan pembanding "sebelum"
        before, base_txt, asal = None, None, None
        if a.sebelum:
            before, asal = os.path.abspath(a.sebelum), "font -s (%s)" % a.sebelum
            if not os.path.exists(before):
                sys.exit("Berkas tidak ditemukan: %s" % before)
        elif a.dasar:
            base_txt, asal = os.path.abspath(a.dasar), "berkas -d (%s)" % a.dasar
            if not os.path.exists(base_txt):
                sys.exit("Berkas tidak ditemukan: %s" % base_txt)
        elif os.path.exists(SNAP):
            base_txt, asal = SNAP, "dasar tersimpan lewat --terima"
        else:
            cand = [os.path.join(ROOT, "fonts", "%s-%s.ttf" % (fam, a.master)) for fam in ("Amiri", "AmiriPegon")]
            cand = [c for c in cand if os.path.exists(c)]
            if not cand:
                sys.exit("Tidak ada pembanding 'sebelum'. Jalankan `make` sekali, atau simpan dasar dengan "
                         "`python3 scripts/pratinjau-titik.py --terima`, atau pakai -d / -s.")
            before = max(cand, key=os.path.getmtime)
            asal = "font hasil `make` terakhir (%s)" % os.path.relpath(before, ROOT)
        if base_txt:
            validate(base_txt, ufo, "sebelum: " + asal)
        print("Pembanding 'sebelum': %s" % asal)

        # 3. bangun font (paralel)
        def start(txt, out):
            env = dict(os.environ, TITIK_TXT=txt, PYTHONPATH=os.path.join(ROOT, "scripts"))
            env.pop("TITIK_LOG", None)
            return subprocess.Popen(
                [sys.executable, os.path.join(ROOT, "scripts", "build.py"), "--input", ufo, "--output", out,
                 "--features", os.path.join(ROOT, "sources", "Amiri.fea"), "--version", "0.0",
                 "--license", os.path.join(ROOT, "OFL.txt")],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        after = os.path.join(tmp, "sesudah.ttf")
        jobs = {"sesudah": (start(sesudah_txt, after), after)}
        if base_txt:
            before = os.path.join(tmp, "sebelum.ttf")
            jobs["sebelum"] = (start(base_txt, before), before)
        print("Membangun %d font sementara (%s), sekitar 1-2 menit ..." % (len(jobs), a.master))
        for nm, (p, out) in jobs.items():
            log = p.communicate()[0]
            if p.returncode or not os.path.exists(out):
                sys.exit("Build gagal (%s):\n%s" % (nm, log[-1500:]))
        render(a, before, after, uh, TTFont)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def terima(a, ufo):
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    if os.path.exists(TXT):
        for ln in validate(TXT, ufo, "titik-posisi.txt sekarang belum valid, tidak disimpan"):
            print("!!", ln)
        shutil.copy(TXT, SNAP)
    else:
        open(SNAP, "w", encoding="utf-8").write("")
    print("Tersimpan: %s\nPratinjau berikutnya akan membandingkan edit Anda dengan isi ini." % SNAP)


def render(a, before, after, uh, TTFont):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    from fontTools.pens.basePen import BasePen
    from fontTools.pens.recordingPen import DecomposingRecordingPen

    class MP(BasePen):
        def __init__(s, gs):
            super().__init__(gs); s.v = []; s.c = []
        def _moveTo(s, p): s.v.append(p); s.c.append(Path.MOVETO)
        def _lineTo(s, p): s.v.append(p); s.c.append(Path.LINETO)
        def _curveToOne(s, p1, p2, p3): s.v += [p1, p2, p3]; s.c += [Path.CURVE4] * 3
        def _qCurveToOne(s, p1, p2): s.v += [p1, p2]; s.c += [Path.CURVE3] * 2
        def _closePath(s): s.v.append((0, 0)); s.c.append(Path.CLOSEPOLY)

    def load(p):
        tt = TTFont(p)
        return tt, uh.Font(uh.Face(uh.Blob.from_file_path(p)))

    def shape(tt, font, word):
        order = tt.getGlyphOrder()
        buf = uh.Buffer(); buf.add_str(word); buf.guess_segment_properties(); uh.shape(font, buf)
        out, x = [], 0
        for i, p in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((order[i.codepoint], x + p.x_offset, p.y_offset)); x += p.x_advance
        return out, x

    def points(gs, name):
        pen = DecomposingRecordingPen(gs); gs[name].draw(pen)
        return [pt for _, args in pen.value for pt in args]

    TB, FB = load(before)
    TA, FA = load(after)
    gsA, gsB = TA.getGlyphSet(), TB.getGlyphSet()
    n = len(a.kata)
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.4 * n))
    axes = np.atleast_1d(axes)
    any_change = False
    marknames = ("fatha", "damma", "kasra", "shadda", "sukun", "madda", "alefabove", "openf", "opend", "openk")
    for ax, word in zip(axes, a.kata):
        sb, wb = shape(TB, FB, word); sa, wa = shape(TA, FA, word)

        def draw(gs, items, **kw):
            for name, x, y in items:
                pen = MP(gs); gs[name].draw(pen)
                if pen.v:
                    v = np.array(pen.v, float); v[:, 0] += x; v[:, 1] += y
                    ax.add_patch(PathPatch(Path(v, pen.c), **kw))
        draw(gsB, sb, fc="#2a6fdb", ec="none", alpha=0.55)      # biru: sebelum
        draw(gsA, sa, fc="k", ec="none", alpha=0.85)            # hitam: sesudah (biru tampak di tempat titik lama)
        ax.set_xlim(-60, max(wa, wb) + 60); ax.set_ylim(-520, 1100); ax.set_aspect("equal")
        ax.set_xticks(range(0, int(max(wa, wb)) + 60, 100)); ax.set_yticks(range(-500, 1101, 100))
        ax.tick_params(labelsize=6); ax.grid(lw=0.3)
        lines = []
        if [g[0] for g in sa] != [g[0] for g in sb]:
            lines.append("  urutan/jenis glyph berubah (pembanding dibangun dengan sumber yang berbeda)")
        else:
            for nm, _, _ in sa:
                A, B = points(gsA, nm), points(gsB, nm)
                if A == B:
                    continue
                if len(A) != len(B):
                    lines.append("  %-40s bentuk glyph berubah" % nm); continue
                dl = collections.Counter((round(p[0] - q[0]), round(p[1] - q[1])) for p, q in zip(A, B))
                dl.pop((0, 0), None)
                for (dx, dy), c in dl.most_common():
                    lines.append("  %-40s titik geser x %+d  y %+d  (%d titik kontur)" % (nm, dx, dy, c))
        names = [nm for nm, _, _ in reversed(sa) if not nm.startswith(marknames)]
        ttl = "%s   ->   %s" % (word, "berubah" if lines else "TIDAK ADA perubahan (aturan tidak mengenai kata ini)")
        ax.set_title(ttl, fontsize=9, loc="left")
        print(ttl); [print(l) for l in lines]
        print("  glyph: " + " ".join(names))
        any_change |= bool(lines)
    fig.suptitle("hitam = sesudah aturan, biru = posisi sebelum aturan (tampak di tempat titik lama). 1 kotak = 100 unit", fontsize=8)
    fig.tight_layout(); fig.savefig(a.keluar, dpi=90)
    print("\nGambar: %s%s" % (os.path.abspath(a.keluar), "" if any_change else "  (tidak ada yang bergeser)"))


if __name__ == "__main__":
    main()
