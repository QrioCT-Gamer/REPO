#!/usr/bin/env python3
"""Build a merged AltStore/ESign/Feather-compatible source from sources.txt."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "sources.txt"
OUTPUTS = (ROOT / "esign.json", ROOT / "repo.json")
UA = "ShrubLibrary-Merged-Repo/2.0 (+https://github.com/QrioCT-Gamer/REPO)"
TIMEOUT = 35


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8-sig"))


def first(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default
    for key in keys:
        value = obj.get(key)
        if value not in (None, ""):
            return value
    return default


def as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def normalize_date(value):
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)


def absolute_url(value, source_url):
    if not value:
        return ""
    value = str(value).strip()
    if value.startswith("//"):
        return "https:" + value
    if re.match(r"^https?://", value, re.I):
        return value
    return urljoin(source_url, value)


def app_versions(app):
    versions = as_list(first(app, "versions", "releases", default=[]))
    if not versions:
        return [app]
    merged = []
    for version in versions:
        if isinstance(version, dict):
            merged.append({**app, **version})
    return merged or [app]


def normalize_app(app, source_url):
    if not isinstance(app, dict):
        return None

    bundle = first(app, "bundleIdentifier", "bundleId", "identifier", "packageName")
    name = first(app, "name", "title", "appName")
    if not (bundle and name):
        return None

    versions = app_versions(app)
    release = next((v for v in versions if first(
        v, "downloadURL", "downloadUrl", "ipa", "url", "download", "assetURL"
    )), versions[0])

    download = first(release, "downloadURL", "downloadUrl", "ipa", "url", "download", "assetURL")
    if not download:
        return None

    version = first(release, "version", "versionString", "shortVersion", default=first(
        app, "version", "versionString", "shortVersion", default=""
    ))
    date = normalize_date(first(release, "versionDate", "date", "published", "updated",
                                default=first(app, "versionDate", "date", "published", "updated")))
    icon = first(app, "iconURL", "iconUrl", "icon", "image", "artwork")
    description = first(app, "localizedDescription", "description", "subtitle", "summary", default="")

    result = {
        "name": str(name),
        "bundleIdentifier": str(bundle),
        "developerName": str(first(app, "developerName", "developer", "author", "artist", default="")),
        "version": str(version or ""),
        "versionDate": date,
        "downloadURL": absolute_url(download, source_url),
        "localizedDescription": str(description or ""),
    }
    if icon:
        result["iconURL"] = absolute_url(icon, source_url)

    tint = first(app, "tintColor", "tint")
    if tint:
        result["tintColor"] = tint

    size = first(release, "size", "downloadSize", default=first(app, "size", "downloadSize"))
    if size is not None:
        try:
            result["size"] = int(size)
        except (TypeError, ValueError):
            pass

    screenshots = first(app, "screenshotURLs", "screenshots")
    if screenshots:
        result["screenshotURLs"] = [
            absolute_url(item, source_url) for item in screenshots
        ] if isinstance(screenshots, list) else screenshots

    return result


def extract_apps(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("apps", "applications", "items", "data"):
        value = data.get(key)
        if isinstance(value, (list, dict)):
            return as_list(value)
    if first(data, "bundleIdentifier", "bundleId", "identifier"):
        return [data]
    return []


def main():
    urls = [
        line.strip() for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    apps_by_key = {}
    loaded, failed = [], []

    for url in urls:
        try:
            data = fetch_json(url)
            source_name = str(first(data, "name", "title", "sourceName", default="")) if isinstance(data, dict) else ""
            count = 0
            for raw_app in extract_apps(data):
                app = normalize_app(raw_app, url)
                if not app:
                    continue
                key = (app["bundleIdentifier"], app["version"], app["downloadURL"])
                if key not in apps_by_key:
                    apps_by_key[key] = app
                    count += 1
            loaded.append({"url": url, "name": source_name, "apps": count})
            print(f"OK   {url} ({count} apps)")
        except Exception as exc:
            failed.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL {url} ({exc})", file=sys.stderr)

    apps = sorted(apps_by_key.values(), key=lambda app: (
        app["name"].casefold(), app["bundleIdentifier"].casefold(),
        app.get("versionDate", "")
    ))

    output = {
        "name": "ShrubLibrary — Unified Repository",
        "identifier": "com.qrioctgamer.shrublibrary.unified",
        "subtitle": f"Unified sideloading repository — {len(apps):,} app builds",
        "website": "https://shrublibrary.pages.dev/",
        "sourceURL": "https://qrioct-gamer.github.io/REPO/repo.json",
        "apps": apps,
        "_build": {
            "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sourceCount": len(urls),
            "successfulSources": len(loaded),
            "failedSources": len(failed),
            "appCount": len(apps),
            "loaded": loaded,
            "failed": failed,
        },
    }

    serialized = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    for path in OUTPUTS:
        path.write_text(serialized, encoding="utf-8")
    print(f"\nWrote esign.json and repo.json: {len(apps):,} app builds from {len(loaded)}/{len(urls)} sources.")


if __name__ == "__main__":
    main()
