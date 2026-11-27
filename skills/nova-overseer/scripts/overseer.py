#!/usr/bin/env python3
"""
nova-overseer — token-cheap screen-recording analysis.

Usage:
  python overseer.py setup [--ocr]              install dependencies into a private venv
  python overseer.py probe   <video>            duration / fps / size as JSON
  python overseer.py analyze <video> [outdir] [--level quick|balanced|deep] [--force]
                             [--step 1] [--gap 4] [--thr 30] [--ocr]
      outdir defaults to <cwd>/docs/video-analysis/<video-name>/ (inside the project).
      balanced (default) = step 1, gap 4, thr 30, OCR on.  quick = step 2, gap 6, thr 40, no OCR.
      deep = step 0.5, gap 2, thr 20, OCR on.  An already-analyzed, unchanged video at the same
      level is skipped (prints status "cached") unless --force is given.
  python overseer.py audio   <video> [outdir]   extract the soundtrack to audio.mp3 (bundled ffmpeg)
  python overseer.py frames  <video> <outdir> [--thr 6] [--maxgap 10]   (fallback: full-frame keyframes)

On first run the script creates ~/.nova-overseer/venv and re-executes itself there
(opencv-python-headless, numpy, pillow; rapidocr-onnxruntime when --ocr / setup --ocr).
No admin rights, no global installs. Set NOVA_OVERSEER_HOME to relocate the venv.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path(os.environ.get("NOVA_OVERSEER_HOME", Path.home() / ".nova-overseer"))
VENV = HOME / "venv"
CORE = ["opencv-python-headless", "numpy", "pillow"]
OCR = ["rapidocr-onnxruntime"]
AUDIO = ["imageio-ffmpeg"]
LEVELS = {"quick": (2.0, 6.0, 40.0, False), "balanced": (1.0, 4.0, 30.0, True), "deep": (0.5, 2.0, 20.0, True)}


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_env(need_ocr: bool, need_audio: bool = False) -> None:
    """Create the venv if needed, install missing packages, then re-exec inside it."""
    if os.environ.get("NOVA_OVERSEER_IN_VENV") == "1":
        return
    py = venv_python()
    if not py.exists():
        HOME.mkdir(parents=True, exist_ok=True)
        print("[overseer] creating venv:", VENV, file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    mods = ["cv2", "numpy", "PIL"] + (["rapidocr_onnxruntime"] if need_ocr else []) + (["imageio_ffmpeg"] if need_audio else [])
    probe = "import importlib.util as u,sys;sys.exit(0 if all(u.find_spec(m) for m in %r) else 1)" % (mods,)
    if subprocess.run([str(py), "-c", probe]).returncode != 0:
        want = CORE + (OCR if need_ocr else []) + (AUDIO if need_audio else [])
        print("[overseer] installing:", " ".join(want), file=sys.stderr)
        subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *want], check=True)
    env = dict(os.environ, NOVA_OVERSEER_IN_VENV="1", PYTHONUTF8="1")
    sys.exit(subprocess.run([str(py), os.path.abspath(__file__), *sys.argv[1:]], env=env).returncode)


def opt(args, name, default):
    """Numeric option value; a missing or non-numeric value exits with a clear message."""
    if name not in args:
        return default
    i = args.index(name)
    try:
        return float(args[i + 1])
    except (IndexError, ValueError):
        sys.exit(f"[overseer] {name} needs a number, e.g. {name} {default:g}")


def default_out(video, out=None):
    return Path(out) if out else Path.cwd() / "docs" / "video-analysis" / Path(video).stem


def fingerprint(video):
    st = os.stat(video)
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def cmd_audio(video, out):
    out = default_out(video, out)
    out.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg
    dst = out / "audio.mp3"
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", video, "-vn", "-ac", "1", "-b:a", "64k", str(dst)],
                       capture_output=True, text=True)
    ok = r.returncode == 0 and dst.exists()
    print(json.dumps({"ok": ok, "audio": str(dst) if ok else None,
                      "error": None if ok else (r.stderr or "")[-300:] + " (no audio track?)"}))
    return 0 if ok else 1


def cmd_probe(video):
    import cv2
    c = cv2.VideoCapture(video)
    if not c.isOpened():
        print(json.dumps({"ok": False, "error": "cannot open video"}))
        return 1
    fps = c.get(5) or 25
    print(json.dumps({"ok": True, "duration_s": round(c.get(7) / fps, 1), "fps": round(fps, 2),
                      "width": int(c.get(3)), "height": int(c.get(4))}))
    return 0


def cmd_analyze(video, out, step, gap, thr, do_ocr, level="custom", force=False):
    """Keep only the screen region that CHANGED, pack the crops into contact sheets,
    and (optionally) OCR every crop into transcript.md. Near-duplicate crops are dropped."""
    import cv2
    import numpy as np
    out = default_out(video, out)
    out.mkdir(parents=True, exist_ok=True)
    meta = out / "analysis.json"
    fp = {**fingerprint(video), "level": level, "ocr": do_ocr, "step": step, "gap": gap, "thr": thr}
    if meta.exists() and not force:
        try:
            old = json.loads(meta.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
        if all(old.get(k) == fp[k] for k in fp):
            print(json.dumps({"ok": True, "status": "cached", "outdir": str(out),
                              "hint": "already analyzed, video unchanged; read index.json / transcript.md, or pass --force"}))
            return 0
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        print(json.dumps({"ok": False, "error": "cannot open video"}))
        return 1
    fps = cap.get(5) or 25
    dur = cap.get(7) / fps
    SW, SH = 480, 270
    ref, last_t, items, t = None, -99.0, [], 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(fr, (SW, SH)), cv2.COLOR_BGR2GRAY)
        if ref is None:
            items.append((t, fr, None))
            last_t, ref = t, g
        else:
            m = (cv2.absdiff(g, ref) > thr).astype(np.uint8)
            m = cv2.dilate(m, np.ones((9, 9), np.uint8), iterations=2)
            if m.sum() > 1200 and t - last_t >= gap:
                ys, xs = np.where(m > 0)
                x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
                area = (x1 - x0) * (y1 - y0) / (SW * SH)
                items.append((t, fr, (x0 / SW, y0 / SH, x1 / SW, y1 / SH, area)))
                last_t, ref = t, g
        t += step
    cap.release()

    crops, sigs, skipped = [], [], 0
    for t, fr, bb in items:
        H, W = fr.shape[:2]
        if bb is None or bb[4] > 0.55:                      # first frame / big change -> whole screen
            im = cv2.resize(fr, (700, int(700 * H / W)))
        else:
            mx, my = 0.03, 0.04
            x0 = max(0, int((bb[0] - mx) * W))
            x1 = min(W, int((bb[2] + mx) * W))
            y0 = max(0, int((bb[1] - my) * H))
            y1 = min(H, int((bb[3] + my) * H))
            if x1 - x0 < 320:
                c = (x0 + x1) // 2
                x0, x1 = max(0, c - 160), min(W, c + 160)
            if y1 - y0 < 120:
                c = (y0 + y1) // 2
                y0, y1 = max(0, c - 60), min(H, c + 60)
            im = fr[y0:y1, x0:x1]
            if im.shape[1] > 700:
                im = cv2.resize(im, (700, int(im.shape[0] * 700 / im.shape[1])))
        sig = cv2.cvtColor(cv2.resize(im, (96, 54)), cv2.COLOR_BGR2GRAY).astype(np.int16)
        if any(np.abs(sig - s).mean() < 1.5 for s in sigs):  # conservative: only near-identical to ANY earlier crop
            skipped += 1
            continue
        sigs.append(sig)
        crops.append((t, im.copy()))

    if do_ocr:
        from rapidocr_onnxruntime import RapidOCR
        eng, seen = RapidOCR(), set()
        with open(out / "transcript.md", "w", encoding="utf-8") as f:
            f.write(f"# OCR transcript - {Path(video).name}\n\n"
                    "New on-screen text per change moment (repeated UI text is printed once).\n\n")
            for t, im in crops:
                r, _ = eng(im)
                lines = []
                for x in (r or []):
                    s = x[1].strip()
                    if s and s not in seen:
                        seen.add(s)
                        lines.append(s)
                f.write(f"## t={t:.0f}s\n" + ("\n".join(f"- {s}" for s in lines) or "- (no new text)") + "\n\n")

    SWd, SHm = 1500, 1500
    state = {"cur": np.full((SHm, SWd, 3), 255, np.uint8), "x": 0, "y": 0, "rowh": 0, "members": []}
    sheets, index = [], []

    def flush():
        if state["y"] + state["rowh"] > 0:
            sheets.append(state["cur"][:state["y"] + state["rowh"]])
            index.append(state["members"])
        state.update(cur=np.full((SHm, SWd, 3), 255, np.uint8), x=0, y=0, rowh=0, members=[])

    for t, im in crops:
        im = im.copy()
        cv2.putText(im, f"{t:.0f}s", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        h, w = im.shape[:2]
        if w > SWd or h > SHm:                              # never exceed one sheet (tall crops, 4K sources)
            k = min(SWd / w, SHm / h)
            im = cv2.resize(im, (max(1, int(w * k)), max(1, int(h * k))))
            h, w = im.shape[:2]
        if state["x"] + w > SWd:
            state["y"] += state["rowh"] + 4
            state["x"], state["rowh"] = 0, 0
        if state["y"] + h > SHm:
            flush()
        state["cur"][state["y"]:state["y"] + h, state["x"]:state["x"] + w] = im
        state["x"] += w + 4
        state["rowh"] = max(state["rowh"], h)
        state["members"].append(round(t))
    flush()
    cdir = out / "crops"                                    # individual key crops for later, finer analysis
    import shutil
    shutil.rmtree(cdir, ignore_errors=True)                 # drop leftovers of a previous run
    for old in list(out.glob("c[0-9][0-9].jpg")) + ([] if do_ocr else [out / "transcript.md"]):
        old.unlink(missing_ok=True)
    cdir.mkdir(exist_ok=True)
    for t, im in crops:
        cv2.imwrite(str(cdir / f"t{int(t):05d}s.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 80])
    for i, s in enumerate(sheets):
        cv2.imwrite(str(out / f"c{i:02d}.jpg"), s, [cv2.IMWRITE_JPEG_QUALITY, 70])
    summary = {"ok": True, "status": "analyzed", "level": level, "outdir": str(out), "duration_s": round(dur), "change_moments": len(items), "dropped_duplicates": skipped,
               "crops": len(crops), "sheets": [{"file": f"c{i:02d}.jpg", "times_s": m} for i, m in enumerate(index)],
               "transcript": str(out / "transcript.md") if do_ocr else None}
    meta.write_text(json.dumps(fp), encoding="utf-8")
    (out / "index.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_frames(video, out, thr, maxgap):
    """Fallback: whole-screen keyframes at scene changes (costs more tokens than analyze)."""
    import cv2
    import numpy as np
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    c = cv2.VideoCapture(video)
    fps = c.get(5) or 25
    dur = c.get(7) / fps
    last, lastt, i, t = None, -99.0, 0, 0.0
    while t < dur:
        c.set(1, int(t * fps))
        ok, f = c.read()
        if not ok:
            break
        h, w = f.shape[:2]
        f = cv2.resize(f, (1280, int(h * 1280 / w)))
        g = cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        d = 99 if last is None else float(np.abs(g - last).mean())
        if (d > thr and t - lastt >= 2.0) or t - lastt >= maxgap:
            cv2.imwrite(str(out / f"{i:03d}_{int(t)}s.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 70])
            i += 1
            last, lastt = g, t
        t += 1.0
    print(json.dumps({"ok": True, "frames": i, "duration_s": round(dur)}))
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, args = argv[1], argv[2:]
    level = args[args.index("--level") + 1] if "--level" in args and args.index("--level") + 1 < len(args) else "balanced"
    if level not in LEVELS:
        sys.exit("[overseer] --level must be quick, balanced or deep")
    lstep, lgap, lthr, locr = LEVELS[level]
    ocr = "--ocr" in args or (cmd == "analyze" and locr and "--no-ocr" not in args)
    ensure_env(need_ocr=ocr, need_audio=(cmd == "audio"))
    if cmd == "setup":
        print(json.dumps({"ok": True, "venv": str(VENV), "ocr": "--ocr" in args}))
        return 0
    if cmd == "probe" and args:
        return cmd_probe(args[0])
    pos = []
    skip = False
    for i, a in enumerate(args):
        if skip:
            skip = False
        elif a in ("--step", "--gap", "--thr", "--level"):
            skip = True
        elif not a.startswith("--"):
            pos.append(a)
    if cmd == "audio" and pos:
        return cmd_audio(pos[0], pos[1] if len(pos) > 1 else None)
    if cmd == "analyze" and pos:
        return cmd_analyze(pos[0], pos[1] if len(pos) > 1 else None, opt(args, "--step", lstep), opt(args, "--gap", lgap),
                           opt(args, "--thr", lthr), ocr, level, "--force" in args)
    if cmd == "frames" and len(args) >= 2:
        return cmd_frames(args[0], args[1], opt(args, "--thr", 6.0), opt(args, "--maxgap", 10.0))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
