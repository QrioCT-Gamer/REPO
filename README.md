# ShrubLibrary merged ESign repo

This repository builds one ESign/AltStore-compatible JSON feed from the repositories listed in `sources.txt`.

## Files

- `sources.txt` — ShrubLibrary's built-in repository URLs.
- `build.py` — downloads and normalizes the sources.
- `esign.json` — generated merged feed.
- `.github/workflows/update.yml` — rebuilds every 6 hours and on demand.
- `.github/workflows/pages.yml` — publishes `esign.json` through GitHub Pages.

## One-time setup

1. Upload these files to `QrioCT-Gamer/REPO`.
2. In GitHub: **Settings → Pages → Source → GitHub Actions**.
3. Run **Actions → Update merged ESign repo → Run workflow** once.
4. After Pages deployment, your feed will be:

`https://QrioCT-Gamer.github.io/REPO/esign.json`

Use that URL in ESign.

The builder skips sources that are temporarily unavailable and records failures in the `_build.failed` section of the generated JSON.
