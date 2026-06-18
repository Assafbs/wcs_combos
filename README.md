# The Slot — a personal WCS combo wall

A tiny, no-server web app: a grid of looping dance-combo clips. Tap one to enlarge it
and jump to the original lesson video. Adding combos is one command.

```
the-slot/
├── index.html       the whole app (open in a browser)
├── combos.txt       your list of combos
├── add_combo.py     reads combos.txt, clips everything, updates the wall
├── combos.json      the wall's data (auto-written)
├── lessons/         downloaded source videos (stay on your computer)
└── clips/           the short generated clips (these get published)
```

---

## How sources work (read this first)

Your lesson videos live in **Google Photos**. Google removed all API access to your
existing Photos in 2025, so no tool can fetch them from a link automatically. The fix
is small: **download each lesson video once**, then the tool does the rest.

In Google Photos (web): open the lesson video → **⋮ menu → Download** (or `Shift+D`).
Save it into the `lessons/` folder. You do this once per lesson, not per combo — one
download covers all the combos you cut from that lesson.

(If a video is ever in Google **Drive** instead, those links *can* be auto-downloaded —
see the Drive note at the bottom.)

---

## One-time setup

**1. Install ffmpeg** (cuts the clips)
- macOS: `brew install ffmpeg` · Windows: `winget install ffmpeg` · Linux: `sudo apt install ffmpeg`
- (yt-dlp is **optional** — only needed if you ever use Google Drive links. On macOS,
  install it with `brew install yt-dlp`, not pip.)

**2. Put this folder on GitHub Pages** (so you can open it on your phone)
```
git init && git add -A && git commit -m "combo wall"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```
Then on GitHub: **Settings → Pages → Deploy from a branch → main / root → Save.**
Live at `https://YOUR_NAME.github.io/YOUR_REPO/`. Open it on your phone and use
**Share → Add to Home Screen** for an app icon. (Your big `lessons/` videos are not
uploaded — only the small clips are.)

> Free GitHub Pages is reachable by anyone with the URL (obscure, not password-protected).
> Want it fully private? Ask and I'll switch the hosting.

---

## Adding combos

1. Download the lesson video(s) from Photos into `lessons/` (see above).
2. In Google Photos, copy the link to each lesson video (open it → Share → Copy link).
3. Open `combos.txt`. For each lesson, add one `@` line, then a line per combo:
   ```
   @ lessons/sat-intermediate.mp4 | https://photos.google.com/album/.../photo/...
   2:05  2:10   Sugar push variation | push
   3:40  3:52   Left side pass | pass, beginner

   @ lessons/sunday-advanced.mp4 | https://photos.google.com/album/.../photo/...
   1:10  1:22
   ```
   The `@` line pairs the local file with the link the card's **Open source video**
   button will use. Times are `mm:ss`, `h:mm:ss`, or seconds. Title and `| tags` are
   optional — omit them and the clip is named after the lesson + timestamp.
4. Run it:
   ```
   python3 add_combo.py --batch combos.txt --publish
   ```
   It clips every range into a small mp4, writes them to the wall, and pushes to GitHub.
   Re-running is safe — anything already added is **skipped**, so keep appending lines
   and re-run anytime. Drop `--publish` to preview locally first.

## One-off without the list
```
python3 add_combo.py --video lessons/sat.mp4 --start 12:30 --end 12:38 \
  --url "https://photos.google.com/album/.../photo/..." --title "Whip with tuck" --tags whip
```

## Other bits
- **Preview locally:** `python3 -m http.server` then open `localhost:8000`
  (don't open index.html as a file — browsers block it from reading combos.json).
- **Edit / remove:** edit `combos.json`, or delete an entry plus its file in `clips/`.
- **Rename the wall:** the wordmark is in the `<header>` of index.html; the subtitle is
  in the `CONFIG` block just below.
- **Sharper or longer clips:** `--width 720`, or `--keep-audio` to keep sound.

### Google Drive (optional auto-download)
If a source is in Drive, you can skip the manual download and put the link inline:
```
https://drive.google.com/file/d/FILE_ID/view   12:30   12:38   Title | tag
```
This uses yt-dlp with your browser login: add `--browser firefox` (or safari/edge) if
you don't use Chrome; close the browser if it says cookies are locked.
