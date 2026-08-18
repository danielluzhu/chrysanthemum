#!/usr/bin/env python3
"""Fill in year, album and country for songs from MusicBrainz.

Country comes from the artist record, which is reliable. Year and album come
from the recording's releases — and because MusicBrainz returns compilations and
tour editions alongside originals, we take the EARLIEST dated release rather
than whatever comes back first. That approximates the original release.

Fields are only written when found. Anything MusicBrainz does not know is left
blank rather than guessed, and shows as "Unknown" in the site filters.

    python3 deploy/enrich_metadata.py [--limit N] [--force]

MusicBrainz asks for at most one request per second; this honours that, so a
full run over ~96 songs takes several minutes.
"""

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs"
BASE = "https://musicbrainz.org/ws/2"
UA = "chrysanthemum/1.0 (https://github.com/danielluzhu/chrysanthemum)"
DELAY = 1.1  # MusicBrainz rate limit

# Artists whose country MusicBrainz gets wrong or does not list, where the
# scene they belong to is unambiguous.
COUNTRY_HINTS = {
    "Mayday": "TW", "五月天": "TW", "Escape Plan": "CN", "逃跑計劃": "CN",
}


def api(path, params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode({**params, "fmt": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError,
            json.JSONDecodeError, TimeoutError, OSError):
        return {}


def clean_artist(raw):
    """'Eric Chou 周興哲' -> best single search term."""
    raw = re.sub(r"\(.*?\)", "", raw)
    raw = raw.split(",")[0].strip()
    latin = re.sub(r"[^\x00-\x7F]+", " ", raw).strip()
    return latin or raw


def artist_country(name, cache):
    key = clean_artist(name)
    if key in cache:
        return cache[key]
    for hint, code in COUNTRY_HINTS.items():
        if hint in name:
            cache[key] = code
            return code
    data = api("artist", {"query": key, "limit": 3})
    time.sleep(DELAY)
    country = ""
    for artist in data.get("artists", []):
        if artist.get("country"):
            country = artist["country"]
            break
    cache[key] = country
    return country


def earliest_release(title, artist):
    """Return (year, album) from the earliest dated release, or ('', '')."""
    query = f'recording:"{title}"'
    latin = clean_artist(artist)
    if latin:
        query += f' AND artist:"{latin}"'

    data = api("recording", {"query": query, "limit": 25})
    time.sleep(DELAY)
    if not data.get("recordings"):                 # retry without the artist
        data = api("recording", {"query": f'recording:"{title}"', "limit": 25})
        time.sleep(DELAY)

    best = None
    for rec in data.get("recordings", []):
        for rel in rec.get("releases") or []:
            date = rel.get("date") or ""
            m = re.match(r"(\d{4})", date)
            if not m:
                continue
            year = int(m.group(1))
            if best is None or year < best[0]:
                best = (year, rel.get("title", ""))
    return (str(best[0]), best[1]) if best else ("", "")


def set_field(text, key, value):
    """Insert or replace a frontmatter key, keeping it before the closing ---."""
    if re.search(rf"^{key}:", text, re.M):
        return re.sub(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.M)
    return re.sub(r"^(youtube_id:.*)$", rf"\1\n{key}: {value}", text,
                  count=1, flags=re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    paths = sorted(SONGS.glob("*.md"))
    if args.limit:
        paths = paths[:args.limit]

    cache = {}
    filled = skipped = 0

    for path in paths:
        text = path.read_text(encoding="utf-8")

        if re.search(r"^country:", text, re.M) and not args.force:
            skipped += 1
            continue

        # Classical and traditional entries have no album or country to find.
        if re.search(r"^rights: public-domain", text, re.M):
            text = set_field(text, "country", "CN")
            path.write_text(text, encoding="utf-8")
            print(f"pd    {path.stem:34} country=CN (no album/year lookup)")
            filled += 1
            continue

        title = re.search(r"^title: (.*)$", text, re.M).group(1).strip()
        artist = re.search(r"^artist: (.*)$", text, re.M).group(1).strip()

        country = artist_country(artist, cache)
        year, album = earliest_release(title, artist)

        text = set_field(text, "country", country)
        text = set_field(text, "year", year)
        text = set_field(text, "album", album)
        path.write_text(text, encoding="utf-8")

        print(f"ok    {path.stem:34} country={country or '-':3} "
              f"year={year or '-':5} album={(album or '-')[:32]}")
        filled += 1

    print(f"\nfilled {filled}, skipped {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
