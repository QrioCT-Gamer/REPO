# ShrubLibrary unified repository upgrade

This patch upgrades the existing `QrioCT-Gamer/REPO` project without replacing its
` sources.txt ` catalogue.

## Replace these three files

- `build.py`
- `.github/workflows/update.yml`
- `.github/workflows/pages.yml`

Keep the existing `sources.txt` unchanged. It already contains the built-in
repository URLs collected for this project.

## Publish

1. Upload/replace the three files above on the repository's `main` branch.
2. Confirm **Settings → Pages → Build and deployment → Source** is set to
   **GitHub Actions**.
3. Open **Actions → Update unified sideloading repository → Run workflow**.
4. Wait for the workflow to finish, then wait for the Pages deployment.

## Feed URLs

- `https://qrioct-gamer.github.io/REPO/repo.json`
- `https://qrioct-gamer.github.io/REPO/esign.json` (compatibility alias)

The scheduled workflow rebuilds every six hours. The output includes build
statistics and per-source failures under `_build`, so a temporarily unavailable
source does not stop the other feeds from being processed.

Note: the feed can only include apps whose source metadata can be parsed by the
normalizer. ShrubLibrary's own app count is not a guarantee that every listing
will appear in this generated feed. Review `_build.appCount`, `_build.failed`,
and the Actions log after the first run.
