#!/usr/bin/env python3
"""
Build a single ESign/AltStore-compatible source from the repositories listed in sources.txt.

The script is deliberately tolerant: one dead/broken repository does not stop the
whole build. It accepts common AltStore/ESign/Feather/SideStore-like schemas and
normalizes their app records into one ESign-style JSON file.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "sources.txt"
OUTPUT_FILE = ROOT / "esign.json"

UA = "ShrubLibrary-Merged-ESign-Repo/1.0 (+https://github.com/QrioCT-Gamer/REPO)"
TIMEOUT = 30


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
    return json.loads(data.decode("utf-8-sig"))


def first(d, *keys, default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.values())
    return []


def normalize_date(v):
    if not v:
        return ""
    if isinstance(v, (int, float)):
        # Unix timestamps are common in feeds.
        try:
            return datetime.utcfromtimestamp(v).isoformat() + "Z"
        except Exception:
            return str(v)
    return str(v)


def normalize_app(app, source_url):
    if not isinstance(app, dict):
        return None

    bundle = first(app, "bundleIdentifier", "bundleId", "identifier", "id")
    name = first(app, "name", "title", "appName")
    download = first(app, "downloadURL", "downloadUrl", "ipa", "url", "download")
    version = first(app, "version", "versionString", "shortVersion")
    date = normalize_date(first(app, "versionDate", "date", "published", "updated"))

    # Some feeds put versions/releases under a nested list.
    if not download:
        versions = as_list(first(app, "versions", "releases", default=[]))
        if versions:
            latest = versions[0]
            if isinstance(latest, dict):
                download = first(latest, "downloadURL", "downloadUrl", "url", "ipa")
                version = version or first(latest, "version", "versionString")
                date = date or normalize_date(first(latest, "date", "versionDate"))

    if not (bundle and name and download):
        return None

    download = urljoin(source_url, str(download))

    out = {
        "name": str(name),
        "bundleIdentifier": str(bundle),
        "developerName": str(first(app, "developerName", "developer", "author", default="")),
        "version": str(version or ""),
        "versionDate": date,
        "downloadURL": download,
        "localizedDescription": str(first(app, "localizedDescription", "description", "subtitle", default="")),
        "iconURL": str(first(app, "iconURL", "iconUrl", "icon", default="")),
    }

    for key in ("tintColor", "size", "screenshotURLs", "screenshots", "permissions"):
        if key in app and app[key] not in (None, ""):
            if key == "screenshots":
                out["screenshotURLs"] = app[key]
            else:
                out[key] = app[key]

    if "size" in out:
        try:
            out["size"] = int(out["size"])
        except Exception:
            out.pop("size", None)

    return out


def extract_apps(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    # Most known source formats use one of these keys.
    for key in ("apps", "applications", "items", "data"):
        value = data.get(key)
        if isinstance(value, list):
            return value

    # A few sources expose a single app object.
    if first(data, "bundleIdentifier", "bundleId", "identifier"):
        return [data]

    return []


def source_metadata(data, url):
    if isinstance(data, dict):
        name = first(data, "name", "title", "sourceName", default="")
        identifier = first(data, "identifier", "id", default="")
        subtitle = first(data, "subtitle", "description", default="")
        icon = first(data, "iconURL", "iconUrl", "icon", default="")
        website = first(data, "website", "websiteURL", "homepage", default="")
        return name, identifier, subtitle, icon, website
    return "", "", "", "", ""


def main():
    urls = [x.strip() for x in SOURCES_FILE.read_text().splitlines()
            if x.strip() and not x.lstrip().startswith("#")]

    apps_by_key = {}
    loaded = []
    failed = []

    for url in urls:
        try:
            data = fetch_json(url)
            src_name, _, _, _, _ = source_metadata(data, url)
            count = 0
            for raw in extract_apps(data):
                app = normalize_app(raw, url)
                if not app:
                    continue
                # Keep distinct versions/downloads. Exact duplicates are removed.
                key = (
                    app["bundleIdentifier"],
                    app["version"],
                    app["downloadURL"],
                )
                if key not in apps_by_key:
                    apps_by_key[key] = app
                    count += 1
            loaded.append({"url": url, "name": src_name, "apps": count})
            print(f"OK   {url}  ({count} apps)")
        except Exception as e:
            failed.append({"url": url, "error": str(e)})
            print(f"FAIL {url}  ({e})", file=sys.stderr)

    apps = list(apps_by_key.values())
    apps.sort(key=lambda a: (
        a.get("name", "").lower(),
        a.get("bundleIdentifier", "").lower(),
        a.get("versionDate", ""),
    ))

    output = {
        "name": "ShrubLibrary — Merged ESign Repo",
        "identifier": "com.qrioctgamer.shrublibrary.merged",
        "subtitle": f"ShrubLibrary merged repository ({len(apps)} apps)",
        "website": "https://shrublibrary.pages.dev/",
        "sourceURL": "https://qri...github.io/REPO/esign.json",
        "apps": apps,
        "_build": {
            "sourceCount": len(urls),
            "successfulSources": len(loaded),
            "failedSources": len(failed),
            "appCount": len(apps),
            "failed": failed,
        },
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"\nWrote {OUTPUT_FILE} with {len(apps)} apps from {len(loaded)}/{len(urls)} sources.")


if __name__ == "__main__":
    main()
