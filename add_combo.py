#!/usr/bin/env python3
"""
Add West Coast Swing combos to the wall — one at a time, or many at once.

BULK (the easy way): list your combos in a text file, then run it.

  Google Photos (and most sources): download each lesson video once, drop it in
  lessons/, and declare it with an "@" line; then list time ranges under it:

      @ lessons/sat-intermediate.mp4 | https://photos.google.com/album/.../photo/...
      2:05  2:10   Sugar push variation | push
      3:40  3:52   Left side pass | pass, beginner

      @ lessons/sunday-advanced.mp4 | https://photos.google.com/album/.../photo/...
      1:10  1:22   Whip with tuck

  Google Drive only: a link can be fetched automatically, one combo per line:

      https://drive.google.com/file/d/XXXX/view   12:30   12:38   Optional title | tag

Then:  python3 add_combo.py --batch combos.txt --publish

The "@" line pairs a local video with the link shown on the card's "Open source
video" button. Time ranges are mm:ss, h:mm:ss, or seconds. Title and "| tags" are
optional — leave them off and the clip is named after the lesson + timestamp.
Re-running is safe: anything already added is skipped.

SINGLE:
    python3 add_combo.py --video lessons/sat.mp4 --start 12:30 --end 12:38 \\
        --url "https://photos.google.com/..." --title "Whip with tuck" --tags whip

Why download first? Google Photos has no API to fetch your existing videos by link
(and yt-dlp doesn't support Photos), so the video has to be local. Drive links can
still be auto-downloaded via yt-dlp, which borrows your browser's Google login.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")


def die(msg):
    print(f"\n  \u2717 {msg}\n", file=sys.stderr)
    sys.exit(1)


def parse_time(t):
    """Seconds (75, 12.5) or clock (mm:ss, h:mm:ss) -> float seconds."""
    t = str(t).strip()
    if ":" in t:
        secs = 0.0
        for p in t.split(":"):
            secs = secs * 60 + float(p)
        return secs
    return float(t)


def fmt_clock(secs):
    secs = int(round(secs))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def slugify(text):
    s = re.sub(r"[^\w\s-]", "", str(text).lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:48] or "combo"


def extract_file_id(url):
    m = re.search(r"/d/([A-Za-z0-9_-]{10,})", url) or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url)
    return m.group(1) if m else None


def normalize_video_url(url):
    """Convert album-context Google Photos URLs to direct photo URLs.

    photos.google.com/album/{albumId}/photo/{photoId}  →  photos.google.com/photo/{photoId}
    The album-context form opens the album (not the video) in the Android app.
    """
    if not url:
        return url
    m = re.search(r"photos\.google\.com/album/[^/]+/photo/([A-Za-z0-9_-]+)", url)
    if m:
        return f"https://photos.google.com/photo/{m.group(1)}"
    return url


def parse_batch(path):
    if not os.path.isfile(path):
        die(f"Batch file not found: {path}")
    jobs = []
    cur_video = cur_url = None
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue

            # "@ lessons/file.mp4 | https://photos.google.com/..."  declares a lesson
            if s.startswith("@"):
                decl = s[1:].strip()
                if "|" in decl:
                    vpart, upart = decl.split("|", 1)
                    cur_video, cur_url = os.path.expanduser(vpart.strip()), (upart.strip() or None)
                else:
                    cur_video, cur_url = os.path.expanduser(decl), None
                continue

            title, tags, left = None, [], s
            if "|" in s:
                left, rest = s.split("|", 1)
                left = left.strip()
                tags = [t.strip() for t in rest.replace("|", ",").split(",") if t.strip()]
            toks = left.split()
            first = toks[0] if toks else ""

            if first.startswith(("http://", "https://")):
                # standalone link line (e.g. a Google Drive auto-download)
                if len(toks) < 3:
                    die(f"Line {n}: need 'URL START END' -> {s!r}")
                if title is None and len(toks) > 3:
                    title = " ".join(toks[3:])
                jobs.append({"url": toks[0], "start": toks[1], "end": toks[2],
                             "title": title, "tags": tags, "line": n})
            else:
                # combo under the current @lesson:  START END [title]
                if not cur_video:
                    die(f"Line {n}: a combo appears before any '@ lesson' line -> {s!r}")
                if len(toks) < 2:
                    die(f"Line {n}: need 'START END [title]' -> {s!r}")
                if title is None and len(toks) > 2:
                    title = " ".join(toks[2:])
                jobs.append({"video": cur_video, "url": cur_url,
                             "start": toks[0], "end": toks[1],
                             "title": title, "tags": tags, "line": n})
    if not jobs:
        die(f"No combos found in {path}.")
    return jobs


def find_cached_media(fid):
    for p in sorted(glob.glob(os.path.join(CACHE, fid + ".*"))):
        if not p.endswith((".info.json", ".part", ".ytdl")):
            return p
    return None


def cached_title(fid):
    j = os.path.join(CACHE, fid + ".info.json")
    if os.path.isfile(j):
        try:
            with open(j, encoding="utf-8") as f:
                return json.load(f).get("title")
        except Exception:
            pass
    return None


def ensure_video(url, browser, use_cookies):
    """Return (local_media_path, human_source_name), downloading once and caching."""
    fid = extract_file_id(url)
    if not fid:
        die(f"Can't auto-download this link: {url}\n"
            "    Only Google Drive links can be fetched automatically. For Google Photos\n"
            "    (or anything else), download the video once and point to the local file\n"
            "    with an '@ lessons/file.mp4 | <link>' line in your batch, or --video.")
    os.makedirs(CACHE, exist_ok=True)
    media = find_cached_media(fid)
    if media:
        return media, (cached_title(fid) or fid)

    if not shutil.which("yt-dlp"):
        die("yt-dlp not found. Install it:  pip install -U yt-dlp")
    print("    downloading source video (first time for this lesson)...")
    cmd = ["yt-dlp", "--no-playlist", "--write-info-json",
           "-o", os.path.join(CACHE, fid + ".%(ext)s")]
    if use_cookies:
        cmd += ["--cookies-from-browser", browser]
    cmd += [url]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        tail = res.stderr.decode(errors="replace")[-1200:]
        sys.stderr.write(tail + "\n")
        die("Download failed. Try a different --browser, close the browser so its "
            "cookies unlock, or set the file to 'Anyone with the link' and use --no-cookies.")
    media = find_cached_media(fid)
    if not media:
        die("Download reported success but no media file appeared in .cache/")
    return media, (cached_title(fid) or fid)


def clean_name(name):
    return re.sub(r"\.(mp4|mov|m4v|webm|avi|mkv)$", "", str(name), flags=re.I).strip()


def make_clip(video, start, dur, width, crf, keep_audio, slug):
    os.makedirs(os.path.join(HERE, "clips"), exist_ok=True)
    out = os.path.join(HERE, "clips", slug + ".mp4")
    cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", video, "-t", f"{dur:.3f}",
           "-vf", f"scale='min({width},iw)':-2", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    cmd += (["-c:a", "aac", "-b:a", "96k"] if keep_audio else ["-an"])
    cmd += [out]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode(errors="replace")[-1200:] + "\n")
        die("ffmpeg failed (see above).")
    if not os.path.isfile(out) or os.path.getsize(out) < 2048:
        if os.path.isfile(out):
            os.remove(out)
        die("Produced an empty clip — the time range is probably past the end of the "
            "video, or start/end are reversed. Double-check the timestamps.")
    return out


def main():
    ap = argparse.ArgumentParser(description="Add WCS combos to the wall.")
    ap.add_argument("--batch", help="Text file: one 'URL START END [title] [| tags]' per line")
    ap.add_argument("--url", help="Drive link (single mode)")
    ap.add_argument("--start", help="Start time, e.g. 12:30")
    ap.add_argument("--end", help="End time, e.g. 12:38")
    ap.add_argument("--duration", help="Length in seconds instead of --end")
    ap.add_argument("--title", help="Optional; auto-derived from the lesson name if omitted")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--video", help="Use a local video file instead of downloading (single mode)")
    ap.add_argument("--browser", default="chrome",
                    help="Browser to borrow the Google login from (chrome/firefox/safari/edge/brave)")
    ap.add_argument("--no-cookies", action="store_true", help="For 'Anyone with the link' files")
    ap.add_argument("--width", type=int, default=540)
    ap.add_argument("--crf", type=int, default=26)
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--force", action="store_true", help="Add even if an identical clip exists")
    ap.add_argument("--json", default=os.path.join(HERE, "combos.json"))
    ap.add_argument("--publish", action="store_true", help="git push once after adding")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        die("ffmpeg not found. Install it first.")

    if args.batch:
        jobs = parse_batch(args.batch)
    elif args.url or args.video:
        if not args.start or not (args.end or args.duration):
            die("Single mode needs --start and (--end or --duration).")
        jobs = [{"url": args.url, "start": args.start, "end": args.end,
                 "title": args.title, "tags": args.tags, "line": 0,
                 "duration": args.duration, "video": args.video}]
    else:
        die("Give me --batch FILE, or --url/--video with --start/--end.")

    data = []
    if os.path.isfile(args.json):
        try:
            with open(args.json, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            die(f"{args.json} isn't valid JSON. Fix or delete it and retry.")
    seen = {(e.get("source_id"), round(e.get("start", -1), 2), round(e.get("end", -1), 2))
            for e in data}

    added = skipped = 0
    for i, job in enumerate(jobs, 1):
        tag = f"[{i}/{len(jobs)}]"
        start = parse_time(job["start"])
        if job.get("duration"):
            end = start + float(job["duration"])
        elif job.get("end"):
            end = parse_time(job["end"])
        else:
            die(f"{tag} missing end/duration")
        if end <= start:
            die(f"{tag} end must be after start")

        local_video = job.get("video")
        fid = extract_file_id(job["url"]) if job.get("url") else None
        source_key = os.path.basename(local_video) if local_video else fid
        key = (source_key, round(start, 2), round(end, 2))
        if not args.force and key in seen:
            print(f"  {tag} skip (already added): {fmt_clock(start)}-{fmt_clock(end)}")
            skipped += 1
            continue

        if local_video:
            if not os.path.isfile(local_video):
                die(f"{tag} video not found: {local_video}")
            source_name = clean_name(os.path.basename(local_video))
        else:
            print(f"  {tag} {fmt_clock(start)}-{fmt_clock(end)}")
            local_video, source_name = ensure_video(job["url"], args.browser, not args.no_cookies)
            source_name = clean_name(source_name)

        title = job.get("title") or f"{source_name} \u00b7 {fmt_clock(start)}"
        slug = f"{slugify(title)}-{uuid.uuid4().hex[:4]}"
        out = make_clip(local_video, start, end - start, args.width, args.crf,
                        args.keep_audio, slug)
        size_kb = os.path.getsize(out) / 1024

        data.append({
            "id": slug,
            "title": title,
            "file": os.path.relpath(out, HERE).replace(os.sep, "/"),
            "video_url": normalize_video_url(job.get("url") or ""),
            "source_label": f"{source_name} \u00b7 {fmt_clock(start)}",
            "tags": job.get("tags", []),
            "source_id": source_key,
            "start": round(start, 2),
            "end": round(end, 2),
            "added": date.today().isoformat(),
        })
        seen.add(key)
        added += 1
        print(f"     \u2713 {title}  ({size_kb:.0f} KB)")

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\n  Done: {added} added, {skipped} skipped, {len(data)} total.")
    if added and args.publish:
        publish(added)
    elif added:
        print("  Preview:  python3 -m http.server   (open localhost:8000)")
        print("  Publish:  git add -A && git commit -m \"add combos\" && git push\n")


def publish(n):
    if not shutil.which("git"):
        die("git not found, so --publish can't run.")
    try:
        subprocess.run(["git", "add", "-A"], cwd=HERE, check=True)
        subprocess.run(["git", "commit", "-m", f"add {n} combo(s)"], cwd=HERE, check=True)
        subprocess.run(["git", "push"], cwd=HERE, check=True)
        print("  \u2713 Pushed to GitHub.\n")
    except subprocess.CalledProcessError:
        die("git push failed. Is this a git repo with a remote? See README.")


if __name__ == "__main__":
    main()
