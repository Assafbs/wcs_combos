# The Slot — a personal WCS combo wall

A tiny, no-server web app: a grid of looping dance-combo clips. Tap one to enlarge it
and jump to the full lesson video in Google Drive. Adding combos in bulk is one command.

```
the-slot/
├── index.html       the whole app (open in a browser)
├── combos.txt       your list: one  URL  START  END  per line
├── add_combo.py     reads combos.txt, clips everything, updates the wall
├── combos.json      the wall's data (auto-written by the script)
└── clips/           the generated mp4 clips
```

---

## One-time setup

**1. Install the tools**
- ffmpeg (cuts the clips): macOS `brew install ffmpeg` · Windows `winget install ffmpeg` · Linux `sudo apt install ffmpeg`
- yt-dlp (downloads from your Drive links): `pip install -U yt-dlp`

**2. Put this folder on GitHub Pages** (so you can open it on your phone)
```
git init && git add -A && git commit -m "combo wall"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```
Then on GitHub: **Settings → Pages → Deploy from a branch → main / root → Save.**
Your wall goes live at `https://YOUR_NAME.github.io/YOUR_REPO/`. Open it on your phone
and use **Share → Add to Home Screen** for an app icon.

> Free GitHub Pages is reachable by anyone with the URL (obscure, but not password
> protected). Your Drive videos still need Drive permission to watch, so only the short
> clips would be visible. Want it fully private? Ask and I'll switch the hosting.

---

## Adding combos (the bulk way)

You only provide a **URL and a time range**. Everything else is automatic.

1. Get each lesson's link in Drive: **right-click → Share → Copy link.**
2. Open `combos.txt` and add a line per combo:
   ```
   https://drive.google.com/file/d/FILE_ID/view   12:30   12:38
   https://drive.google.com/file/d/FILE_ID/view   14:02   14:11   Left side pass | pass, whip
   ```
   Times are `mm:ss`, `h:mm:ss`, or seconds. Title and `| tags` are optional —
   leave them off and the clip is named after the lesson + timestamp.
3. Run it:
   ```
   python3 add_combo.py --batch combos.txt --publish
   ```

What happens: it downloads each lesson **once** (cached, so ten combos from one lesson
= one download), clips every range into a small mp4, writes them to the wall, and pushes
to GitHub. Re-running is safe — anything already added is **skipped**, so you can keep
appending lines to `combos.txt` and re-run anytime. Drop `--publish` to preview first.

### About the Drive download
Your lessons are private, so yt-dlp borrows your browser's Google login. By default it
reads Chrome; use `--browser firefox` (or safari/edge/brave) for another. If it says the
cookie database is locked, close the browser and re-run. Alternatively set a file to
"Anyone with the link" in Drive and add `--no-cookies`.

Downloaded lessons are kept in `.cache/` and are **not** uploaded to GitHub (only the
short clips are). Delete `.cache/` anytime to reclaim space.

## One-off without the list
```
python3 add_combo.py --url "https://drive.google.com/file/d/FILE_ID/view" \
  --start 12:30 --end 12:38 --title "Whip with tuck" --tags whip
```
Have the file locally already? Use `--video path/to/lesson.mp4` instead of `--url`.

## Other bits
- **Preview locally:** `python3 -m http.server` then open `localhost:8000`
  (don't open index.html as a file — browsers block it from reading combos.json).
- **Edit / remove:** edit `combos.json`, or delete an entry plus its file in `clips/`.
- **Rename the wall:** the wordmark is in the `<header>` of index.html; the subtitle is
  in the `CONFIG` block just below.
- **Sharper or longer clips:** `--width 720`, or `--keep-audio` to keep sound.
