#!/usr/bin/env python3
"""Generate song entries from deploy/tracks.tsv.

For each track: search YouTube, take the top result, confirm it resolves via
oEmbed, and write songs/<slug>.md.

Every entry produced here is marked `rights: copyrighted`, which means build.py
will refuse to let it carry a `## lines` section. These entries hold a video,
notes and vocabulary — never lyrics.

    python3 deploy/import_tracks.py [--limit N] [--force]

Existing files are left alone unless --force is passed, so hand-written notes
and vocabulary added later are never overwritten by a re-run.
"""

import argparse
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKS = ROOT / "deploy" / "tracks.tsv"
SONGS = ROOT / "songs"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def slugify(pinyin, title, artist):
    """ASCII slug, preferring the romanised title."""
    base = title if pinyin in ("—", "") else pinyin
    base = unicodedata.normalize("NFKD", base)
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if not base:  # title had no romanisable content
        base = re.sub(r"[^a-z0-9]+", "-", artist.lower()).strip("-") or "track"
    return base[:48]


def search_video(query):
    """Return the top YouTube video id for a query, or None."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    try:
        html = fetch(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    return ids[0] if ids else None


def verify(video_id):
    """Return (channel, title) if the id resolves, else None."""
    query = urllib.parse.urlencode({
        "url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})
    try:
        data = json.loads(fetch(f"https://www.youtube.com/oembed?{query}", timeout=20))
        return data.get("author_name", "?"), data.get("title", "?")
    except Exception:
        return None


TEMPLATE = """---
slug: {slug}
title: {title}
pinyin_title: {pinyin}
title_en: {english}
artist: {artist}
era: contemporary
rights: copyrighted
level: {level}
youtube: {search_url}
youtube_id: {video_id}
---

## notes

Imported from the source playlist. **Under copyright, so no lyrics here** — use
the video, and read the words on a licensed service such as QQ&#38899;&#20048;,
Apple Music, Spotify or YouTube's own captions.

Notes, a listening guide and vocabulary for this song are still to be written.

## vocab

"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tracks", default=str(TRACKS),
                    help="TSV to import (defaults to deploy/tracks.tsv)")
    args = ap.parse_args()

    rows = []
    for line in pathlib.Path(args.tracks).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 5:
            print(f"skip malformed row: {line[:60]!r}", file=sys.stderr)
            continue
        rows.append(parts)

    if args.limit:
        rows = rows[:args.limit]

    made = skipped = failed = 0
    seen = set()

    for title, artist, pinyin, english, level in rows:
        slug = slugify(pinyin, title, artist)
        while slug in seen:                       # collision guard
            slug += "-2"
        seen.add(slug)

        path = SONGS / f"{slug}.md"
        if path.exists() and not args.force:
            skipped += 1
            continue

        query = f"{title} {artist}"
        video_id = search_video(query)
        checked = verify(video_id) if video_id else None
        if not checked:
            print(f"FAIL  {title} — no usable video")
            failed += 1
            continue

        path.write_text(TEMPLATE.format(
            slug=slug, title=title, pinyin="" if pinyin == "—" else pinyin,
            english=english, artist=artist, level=level, video_id=video_id,
            search_url="https://www.youtube.com/results?search_query="
                       + urllib.parse.quote(query),
        ), encoding="utf-8")

        print(f"ok    {slug:34} {video_id}  {checked[0][:22]}")
        made += 1
        time.sleep(0.4)          # be gentle with YouTube

    print(f"\ncreated {made}, skipped {skipped} (already present), failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
