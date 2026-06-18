# The Slot — a personal WCS combo wall

A tiny, no-server web app: a grid of looping dance-combo clips. Tap one to enlarge
it and jump to the full lesson video in Google Drive. Adding a combo is one command.

```
the-slot/
├── index.html       the whole app (open in a browser)
├── combos.json      your list of combos (auto-updated by the script)
├── add_combo.py     the "add a combo" tool
└── clips/           the generated mp4 clips live here
```

---

## One-time setup

**1. Install ffmpeg** (the script needs it to cut clips)
- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg`  ·  Linux: `sudo apt install ffmpeg`

**2. Put this folder on GitHub Pages** (so you can open it on your phone)
1. Create a new repository on GitHub (a private repo is fine for the files; see the
   note on visibility below).
2. In this folder:
   ```
   git init
   git add -A
   git commit -m "combo wall"
   git branch -M main
   git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Pages → Source: Deploy from a branch → main / root → Save.**
4. After a minute your wall is live at `https://YOUR_NAME.github.io/YOUR_REPO/`.
   Open that on your phone and use **Share → Add to Home Screen** for an app icon.

> **Visibility note:** on GitHub's free plan, a Pages site is reachable by anyone who
> has the URL (the URL is obscure, but it isn't password-protected). Your Drive videos
> still require Drive permissions to actually watch, so only the short clips would be
> visible. If you want it truly private, tell me and I'll switch the hosting to a
> password-protected option.

---

## Adding a combo

You need the video on your computer (Google Drive desktop app, or just download it).
Then grab the share link from Drive: **right-click the video → Share → Copy link.**

```
python3 add_combo.py \
  --video ~/Downloads/lesson3.mp4 \
  --start 12:30 --end 12:38 \
  --title "Whip with left side tuck" \
  --url "https://drive.google.com/file/d/XXXXXXXX/view" \
  --tags whip intermediate \
  --publish
```

What each part does:
- `--start` / `--end` — clock (`mm:ss`, `h:mm:ss`) or plain seconds. Use `--duration 8`
  instead of `--end` if you prefer.
- `--title` — the name on the card (also searchable).
- `--url` — the Drive link. Drive can't deep-link to a timestamp, so the card shows the
  start time as a label (e.g. `lesson3 · 12:30`) so you know where to scrub.
- `--tags` — optional, space-separated; they're searchable too.
- `--publish` — runs `git add/commit/push` for you so it appears on your phone.
  Leave it off to preview locally first.

Useful extras: `--label "anything you want"` to override the caption,
`--width 720` for a sharper clip, `--keep-audio` to keep sound.

## Previewing locally (optional)

Don't open `index.html` as a file — browsers block it from reading `combos.json`.
Run a quick local server instead:

```
python3 -m http.server
```
then open `http://localhost:8000`. When it looks right, `--publish` (or push) to go live.

## Editing or removing a combo

Open `combos.json` and edit the text, or delete an entry and its file in `clips/`,
then push. The wall shows newest first.

## Renaming the wall

Open `index.html`, find the `CONFIG` block near the bottom, and change `subtitle`.
The "the slot" wordmark is in the `<header>` just above it.
