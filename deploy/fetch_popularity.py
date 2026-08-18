#!/usr/bin/env python3
"""Record each song's YouTube view count and best available thumbnail.

Two things at once, since both need a round trip per video:

  views  — pulled from the watch page. Used to order the song grid, so the
           best-known songs land first instead of alphabetically.
  thumb  — which thumbnail size actually exists. maxresdefault is 1280x720
           but is missing for plenty of uploads; mqdefault is 320x180 and
           always present. Recording the winner avoids relying on an onerror
           fallback in the browser, which causes a visible flash.

    python3 deploy/fetch_popularity.py [--limit N] [--force]

View counts are a snapshot, not live data. Re-run occasionally.
"""

import argparse
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def get(url, timeout=25, head=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA},
                                 method="HEAD" if head else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status if head else resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code if head else ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0 if head else ""


def view_count(video_id):
    html = get(f"https://www.youtube.com/watch?v={video_id}")
    m = re.search(r'"viewCount":"(\d+)"', html)
    return int(m.group(1)) if m else None


def best_thumb(video_id):
    """maxresdefault when it exists, otherwise mqdefault (always present)."""
    if get(f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", head=True) == 200:
        return "maxresdefault"
    if get(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg", head=True) == 200:
        return "mqdefault"
    return ""


def set_field(text, key, value):
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

    done = skipped = failed = 0

    for path in paths:
        text = path.read_text(encoding="utf-8")

        if re.search(r"^views:\s*\d", text, re.M) and not args.force:
            skipped += 1
            continue

        m = re.search(r"^youtube_id:\s*(\S+)", text, re.M)
        if not m:
            print(f"skip  {path.stem:34} no youtube_id")
            failed += 1
            continue

        vid = m.group(1)
        views = view_count(vid)
        thumb = best_thumb(vid)

        if views is None:
            print(f"FAIL  {path.stem:34} {vid} no view count")
            failed += 1
        text = set_field(text, "views", views if views is not None else "")
        text = set_field(text, "thumb", thumb)
        path.write_text(text, encoding="utf-8")

        if views is not None:
            print(f"ok    {path.stem:34} {views:>12,}  {thumb}")
            done += 1
        time.sleep(0.5)

    print(f"\nfetched {done}, skipped {skipped}, failed {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
