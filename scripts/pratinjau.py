#!/usr/bin/env python3
"""Pratinjau aturan posisi tashkil tanpa mengubah repo.

  python3 scripts/pratinjau.py -a "ح^ م~ => atas 0 40" "حَمْدٌ" "حَمَلَ"
  python3 scripts/pratinjau.py -a "ب => atas 0 30 | Bold atas 0 45" -m Bold "بَكَ"
  python3 scripts/pratinjau.py "لِْحَِمِْدُِ" "لَِخَِيَِرَِ"     # tanpa -a: bandingkan hasil edit langsung di tashkil-posisi.txt
  python3 scripts/pratinjau.py --terima                        # jadikan isi tashkil-posisi.txt sekarang sebagai dasar "sebelum"

Yang dilakukan:
  1. menambahkan baris -a (jika ada) ke salinan sementara tashkil-posisi.txt (berkas asli tidak diubah),
  2. membangun dua font sementara (Regular atau Bold): "sebelum" dan "sesudah".
     "Sesudah" = tashkil-posisi.txt di folder kerja (edit langsung Anda) + baris -a.
     "Sebelum" diambil dari yang pertama tersedia:
       -d berkas.txt  >  dasar tersimpan lewat --terima (build/tashkil-posisi.dasar.txt)  >  hasil `make` terakhir,
  3. menggambar kata-kata Anda: hitam = sesudah aturan, biru = posisi tanda SEBELUM aturan,
     lengkap dengan kisi berangka (1 kotak = 100 unit), dan mencetak daftar pergeseran tiap tanda.

Prasyarat: sudah pernah `make` (folder build/ berisi .ufo).
Pasang sekali:  pip install uharfbuzz matplotlib
"""
import argparse, os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SNAP = os.path.join(ROOT, "build", "tashkil-posisi.dasar.txt")


def need(mod, pip):
    try:
        return __import__(mod, fromlist=["x"])
    except ImportError:
        sys.exit("Pasang dulu:  pip install %s" % pip)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-a", "--aturan", action="append", default=[], help="satu baris aturan (boleh diulang)")
    ap.add_argument("-m", "--master", default="Regular", choices=["Regular", "Bold"])
    ap.add_argument("-o", "--keluar", default="pratinjau.png")
    ap.add_argument("-s", "--sebelum", help="font pembanding siap pakai (mempercepat; bawaan: dibangun otomatis)")
    ap.add_argument("-d", "--dasar", help="berkas tashkil-posisi.txt pembanding untuk 'sebelum'")
    ap.add_argument("--terima", action="store_true",
                    help="simpan tashkil-posisi.txt sekarang sebagai dasar 'sebelum' berikutnya, lalu selesai")
    ap.add_argument("kata", nargs="*", help="kata contoh (lengkap dengan harakat)")
    a = ap.parse_args()
    if a.terima:
        return terima(a)
    if not a.kata:
        ap.error("tulis minimal satu kata contoh")

    uh = need("uharfbuzz", "uharfbuzz")
    need("matplotlib", "matplotlib")
    from fontTools.ttLib import TTFont

    ufo = os.path.join(ROOT, "build", "Amiri-%s.ufo" % a.master)
    if not os.path.exists(ufo):
        sys.exit("Belum ada %s. Jalankan `make` sekali dulu." % ufo)
    tmp = tempfile.mkdtemp(prefix="pratinjau-")
    try:
        os.makedirs(os.path.join(tmp, "sources"))
        # 1. temporary position file = original + the user's lines
        text = open(os.path.join(ROOT, "sources", "tashkil-posisi.txt"), encoding="utf-8").read()
        text += "\n" + "\n".join(a.aturan) + "\n"
        posisi = os.path.join(tmp, "tashkil-posisi.txt")
        open(posisi, "w", encoding="utf-8").write(text)
        env = dict(os.environ, TP_TXT=posisi, TP_OUT=os.path.join(tmp, "sources", "tashkil_context.fea"))
        gen = os.path.join(ROOT, "scripts", "make-tashkil-posisi.py")
        r = subprocess.run([sys.executable, gen, ufo], cwd=ROOT, env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit("[sesudah] " + (r.stderr.strip() or r.stdout.strip()))
        for ln in r.stdout.splitlines():
            if ln.startswith("peringatan"):
                print("!!", ln)
        # 2. feature files: copies, with the generated context file swapped in
        for fn in os.listdir(os.path.join(ROOT, "sources")):
            if fn.endswith(".fea") and fn != "tashkil_context.fea":
                shutil.copy(os.path.join(ROOT, "sources", fn), os.path.join(tmp, "sources", fn))
        # 3. build two fonts: baseline (current repo state) and with your lines
        def build(feat, out):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py"), "--input", ufo, "--output", out,
                                "--features", feat, "--version", "0.0", "--license", os.path.join(ROOT, "OFL.txt")],
                               cwd=ROOT, env=env, capture_output=True, text=True)
            if r.returncode or not os.path.exists(out):
                sys.exit("Build gagal:\n" + (r.stderr or r.stdout)[-1500:])
        before = a.sebelum or os.path.join(tmp, "sebelum.ttf")
        after = os.path.join(tmp, "sesudah.ttf")
        print("Membangun dua font sementara (%s): sebelum dan sesudah, sekitar 2-3 menit ..." % a.master)
        if not a.sebelum:
            base_txt = None
            if a.dasar:
                base_txt = os.path.abspath(a.dasar)
                if not os.path.exists(base_txt):
                    sys.exit("Berkas tidak ditemukan: %s" % base_txt)
                asal = "berkas -d (%s)" % a.dasar
            elif os.path.exists(SNAP):
                base_txt = SNAP
                asal = "dasar tersimpan lewat --terima"
            if base_txt:
                # "sebelum" dibangkitkan ULANG dari berkas dasar itu
                bdir = os.path.join(tmp, "sources_sebelum")
                os.makedirs(bdir)
                for fn in os.listdir(os.path.join(ROOT, "sources")):
                    if fn.endswith(".fea") and fn != "tashkil_context.fea":
                        shutil.copy(os.path.join(ROOT, "sources", fn), os.path.join(bdir, fn))
                env_b = dict(os.environ, TP_TXT=base_txt, TP_OUT=os.path.join(bdir, "tashkil_context.fea"))
                rb = subprocess.run([sys.executable, gen, ufo], cwd=ROOT, env=env_b, capture_output=True, text=True)
                if rb.returncode:
                    sys.exit("[sebelum: %s] %s" % (asal, rb.stderr.strip() or rb.stdout.strip()))
                print("Pembanding 'sebelum': %s" % asal)
                build(os.path.join(bdir, "Amiri.fea"), before)
            else:
                if not os.path.exists(os.path.join(ROOT, "sources", "tashkil_context.fea")):
                    sys.exit("Belum ada sources/tashkil_context.fea. Jalankan `make` sekali dulu.")
                print("Pembanding 'sebelum': hasil `make` terakhir (sources/tashkil_context.fea)")
                build(os.path.join(ROOT, "sources", "Amiri.fea"), before)
        build(os.path.join(tmp, "sources", "Amiri.fea"), after)
        render(a, before, after, uh, TTFont)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def terima(a):
    ufo = os.path.join(ROOT, "build", "Amiri-%s.ufo" % a.master)
    if not os.path.exists(ufo):
        sys.exit("Belum ada %s. Jalankan `make` sekali dulu." % ufo)
    src = os.path.join(ROOT, "sources", "tashkil-posisi.txt")
    tmp = tempfile.mkdtemp(prefix="pratinjau-")
    try:
        env = dict(os.environ, TP_TXT=src, TP_OUT=os.path.join(tmp, "uji.fea"))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make-tashkil-posisi.py"), ufo],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit("Tidak disimpan, tashkil-posisi.txt sekarang belum valid:\n" + (r.stderr.strip() or r.stdout.strip()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.copy(src, SNAP)
    print("Tersimpan: %s\nPratinjau berikutnya akan membandingkan edit Anda dengan isi ini." % SNAP)


def render(a, before, after, uh, TTFont):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    from fontTools.pens.basePen import BasePen

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
        font = uh.Font(uh.Face(uh.Blob.from_file_path(p)))
        marks = {n for n, c in tt["GDEF"].table.GlyphClassDef.classDefs.items() if c == 3}
        return tt, font, marks

    def shape(tt, font, word):
        order = tt.getGlyphOrder()
        buf = uh.Buffer(); buf.add_str(word); buf.guess_segment_properties(); uh.shape(font, buf)
        out, x = [], 0
        for i, p in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((order[i.codepoint], x + p.x_offset, p.y_offset)); x += p.x_advance
        return out, x

    TB, FB, MB = load(before)
    TA, FA, MA = load(after)
    n = len(a.kata)
    fig, axes = plt.subplots(n, 1, figsize=(11, 3.4 * n))
    axes = np.atleast_1d(axes)
    any_change = False
    for ax, word in zip(axes, a.kata):
        sb, wb = shape(TB, FB, word); sa, wa = shape(TA, FA, word)
        gsA, gsB = TA.getGlyphSet(), TB.getGlyphSet()
        def draw(gs, items, only_marks, marks, **kw):
            for name, x, y in items:
                if only_marks and name not in marks:
                    continue
                pen = MP(gs); gs[name].draw(pen)
                if pen.v:
                    v = np.array(pen.v, float); v[:, 0] += x; v[:, 1] += y
                    ax.add_patch(PathPatch(Path(v, pen.c), **kw))
        draw(gsB, sb, True, MB, fc="#2a6fdb", ec="none", alpha=0.45)   # bayangan: tanda sebelum aturan
        draw(gsA, sa, False, MA, fc="k", ec="none")                      # hitam di atasnya: sesudah aturan
        ax.set_xlim(-60, max(wa, wb) + 60); ax.set_ylim(-520, 1100); ax.set_aspect("equal")
        ax.set_xticks(range(0, int(max(wa, wb)) + 60, 100)); ax.set_yticks(range(-500, 1101, 100))
        ax.tick_params(labelsize=6); ax.grid(lw=0.3)
        # numeric report
        marks_b = [(nm, x, y) for nm, x, y in sb if nm in MB]; marks_a = [(nm, x, y) for nm, x, y in sa if nm in MA]
        lines = []
        if [m[0] for m in marks_b] == [m[0] for m in marks_a]:
            for (nm, xb, yb), (_, xa, ya) in zip(marks_b, marks_a):
                if round(xa - xb) or round(ya - yb):
                    lines.append("  %-22s geser x %+d  y %+d" % (nm, round(xa - xb), round(ya - yb)))
        else:
            lines.append("  urutan/jenis glyph berubah (aturan memengaruhi pemilihan bentuk)")
        ttl = "%s   ->   %s" % (word, "berubah" if lines else "TIDAK ADA perubahan (aturan tidak mengenai kata ini)")
        ax.set_title(ttl, fontsize=9, loc="left")
        print(ttl); [print(l) for l in lines]
        any_change |= bool(lines)
    fig.suptitle("hitam = sesudah aturan, bayangan biru = posisi tanda sebelum aturan (tanda yang tak bergeser tertutup hitam). 1 kotak = 100 unit", fontsize=8)
    fig.tight_layout(); fig.savefig(a.keluar, dpi=90)
    print("\nGambar: %s%s" % (os.path.abspath(a.keluar), "" if any_change else "  (tidak ada tanda yang bergeser)"))


if __name__ == "__main__":
    main()
