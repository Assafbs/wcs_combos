#!/usr/bin/env python3
"""
Add one West Coast Swing combo to the wall.

It cuts a segment out of a video, turns it into a small muted looping mp4,
drops it in clips/, and appends an entry to combos.json. Refresh the page
(or push to GitHub) and the combo appears.

Example:
    python3 add_combo.py \\
        --video ~/Downloads/lesson3.mp4 \\
        --start 12:30 --end 12:38 \\
        --title "Whip with left side tuck" \\
        --url "https://drive.google.com/file/d/XXXXXXXX/view" \\
        --tags whip intermediate \\
        --publish
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))


def die(msg):
    print(f"\n  ✗ {msg}\n", file=sys.stderr)
    sys.exit(1)


def parse_time(t):
    """Accept seconds (75, 12.5) or clock (mm:ss, hh:mm:ss). Returns float seconds."""
    t = str(t).strip()
    if ":" in t:
        parts = t.split(":")
        if len(parts) > 3:
            die(f"Bad time '{t}'")
        secs = 0.0
        for p in parts:
            secs = secs * 60 + float(p)
        return secs
    return float(t)


def fmt_clock(secs):
    secs = int(round(secs))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def slugify(text):
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:48] or "combo"


def main():
    ap = argparse.ArgumentParser(description="Add a combo clip to the wall.")
    ap.add_argument("--video", required=True, help="Path to the source video file")
    ap.add_argument("--start", required=True, help="Start time (e.g. 12:30 or 750)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--end", help="End time (e.g. 12:38)")
    g.add_argument("--duration", help="Clip length in seconds instead of --end")
    ap.add_argument("--title", required=True, help="Short name shown on the card")
    ap.add_argument("--url", required=True, help="Link to the source video (e.g. Google Drive)")
    ap.add_argument("--tags", nargs="*", default=[], help="Optional tags, space-separated")
    ap.add_argument("--label", help="Override the 'source · time' caption")
    ap.add_argument("--width", type=int, default=540, help="Clip width in px (default 540)")
    ap.add_argument("--crf", type=int, default=26, help="Quality, lower=better/bigger (default 26)")
    ap.add_argument("--keep-audio", action="store_true", help="Keep audio (default: muted)")
    ap.add_argument("--json", default=os.path.join(HERE, "combos.json"))
    ap.add_argument("--clips-dir", default=os.path.join(HERE, "clips"))
    ap.add_argument("--publish", action="store_true", help="git add/commit/push after adding")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        die("ffmpeg not found. Install it first (e.g. `brew install ffmpeg`).")
    if not os.path.isfile(args.video):
        die(f"Video not found: {args.video}")

    start = parse_time(args.start)
    if args.duration is not None:
        dur = float(args.duration)
        end = start + dur
    else:
        end = parse_time(args.end)
        dur = end - start
    if dur <= 0:
        die("End must be after start.")
    if dur > 60:
        print(f"  ! Heads up: {dur:.0f}s is a long loop; combos usually read best under ~12s.")

    os.makedirs(args.clips_dir, exist_ok=True)
    slug = f"{slugify(args.title)}-{uuid.uuid4().hex[:4]}"
    out_path = os.path.join(args.clips_dir, slug + ".mp4")
    rel_file = os.path.relpath(out_path, HERE).replace(os.sep, "/")

    vf = f"scale='min({args.width},iw)':-2"
    cmd = [
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", args.video, "-t", f"{dur:.3f}",
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    cmd += (["-c:a", "aac", "-b:a", "96k"] if args.keep_audio else ["-an"])
    cmd += [out_path]

    print(f"\n  Clipping {fmt_clock(start)}–{fmt_clock(end)} ({dur:.1f}s) → {rel_file}")
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode(errors="replace")[-1500:])
        die("ffmpeg failed (see message above).")

    size_kb = os.path.getsize(out_path) / 1024
    label = args.label or f"{os.path.splitext(os.path.basename(args.video))[0]} · {fmt_clock(start)}"

    entry = {
        "id": slug,
        "title": args.title,
        "file": rel_file,
        "video_url": args.url,
        "source_label": label,
        "tags": args.tags,
        "added": date.today().isoformat(),
    }

    data = []
    if os.path.isfile(args.json):
        try:
            with open(args.json) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            die(f"{args.json} is not valid JSON. Fix or delete it and retry.")
    data.append(entry)
    with open(args.json, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  ✓ Added “{args.title}”  ({size_kb:.0f} KB) — {len(data)} combos total")

    if args.publish:
        publish(out_path, args.json, args.title)
    else:
        print("  → Preview locally:  python3 -m http.server   (then open localhost:8000)")
        print("  → When happy, publish with:  git add -A && git commit -m \"add combo\" && git push\n")


def publish(clip_path, json_path, title):
    if not shutil.which("git"):
        die("git not found, so --publish can't run.")
    try:
        subprocess.run(["git", "add", "-A"], cwd=HERE, check=True)
        subprocess.run(["git", "commit", "-m", f"add combo: {title}"], cwd=HERE, check=True)
        subprocess.run(["git", "push"], cwd=HERE, check=True)
        print("  ✓ Pushed to GitHub — your phone will see it in a moment.\n")
    except subprocess.CalledProcessError:
        die("git push failed. Is this folder a git repo with a remote set up? See README.")


if __name__ == "__main__":
    main()
