#!/usr/bin/env python3
"""Check that every youtube_id in songs/ still resolves to a live video.

YouTube IDs rot: uploads get deleted, made private, or blocked by region. This
asks YouTube's oEmbed endpoint about each one and reports the channel and title
it currently points at, so a swapped or dead video is visible rather than
silently embedding nothing.

    python3 deploy/verify-videos.py

Exits non-zero if any ID fails to resolve, so it can gate a deploy.
"""

import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SONGS = pathlib.Path(__file__).resolve().parent.parent / "songs"
OEMBED = "https://www.youtube.com/oembed"
TIMEOUT = 20


def lookup(video_id):
    """Return (channel, title) for a video id, or None if it does not resolve."""
    query = urllib.parse.urlencode({
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "format": "json",
    })
    try:
        with urllib.request.urlopen(f"{OEMBED}?{query}", timeout=TIMEOUT) as resp:
            data = json.load(resp)
        return data.get("author_name", "?"), data.get("title", "?")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError,
            TimeoutError, OSError):
        return None


def main():
    failures = []
    missing = []

    for path in sorted(SONGS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^youtube_id:\s*(\S+)", text, re.M)
        if not match:
            missing.append(path.stem)
            continue

        video_id = match.group(1)
        result = lookup(video_id)
        if result is None:
            print(f"FAIL  {path.stem:32} {video_id}  does not resolve")
            failures.append((path.stem, video_id))
        else:
            channel, title = result
            print(f"ok    {path.stem:32} {video_id}  {channel[:24]} | {title[:40]}")

    for slug in missing:
        print(f"none  {slug:32} (no youtube_id set)")

    if failures:
        print(f"\n{len(failures)} video(s) need replacing.", file=sys.stderr)
        return 1
    print(f"\nall {len(list(SONGS.glob('*.md'))) - len(missing)} videos resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
