#!/usr/bin/env python3
"""Re-pick videos for songs whose match looks wrong.

The original import took the top YouTube search result, which is sometimes an
obscure re-upload rather than the real thing. A well-known song sitting on a
few thousand views is the tell.

This re-searches those songs, checks the view count of several candidates, and
keeps the most-watched one — a far better proxy for "the canonical upload" than
search position. Notes, vocabulary and everything else are left untouched.

    python3 deploy/refix_videos.py [--below N] [--candidates N] [--dry-run]
"""

import argparse
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
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


def search_ids(query, limit):
    html = get("https://www.youtube.com/results?search_query="
               + urllib.parse.quote(query))
    seen, out = set(), []
    for vid in re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html):
        if vid not in seen:
            seen.add(vid)
            out.append(vid)
        if len(out) >= limit:
            break
    return out


def views_of(video_id):
    m = re.search(r'"viewCount":"(\d+)"',
                  get(f"https://www.youtube.com/watch?v={video_id}"))
    return int(m.group(1)) if m else 0


def best_thumb(video_id):
    if get(f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", head=True) == 200:
        return "maxresdefault"
    return "mqdefault"


def field(text, key):
    m = re.search(rf"^{key}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def set_field(text, key, value):
    return re.sub(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--below", type=int, default=200_000,
                    help="only re-pick songs under this view count")
    ap.add_argument("--candidates", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fixed = kept = 0

    for path in sorted(SONGS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if field(text, "rights") == "public-domain":
            continue                       # low counts are expected there

        current = field(text, "views")
        if not current.isdigit() or int(current) >= args.below:
            continue

        title = field(text, "title")
        artist = field(text, "artist")
        query = f"{title} {artist}"

        best_id, best_views = field(text, "youtube_id"), int(current)
        for vid in search_ids(query, args.candidates):
            if vid == best_id:
                continue
            v = views_of(vid)
            time.sleep(0.4)
            if v > best_views:
                best_id, best_views = vid, v

        if best_id != field(text, "youtube_id"):
            thumb = best_thumb(best_id)
            text = set_field(text, "youtube_id", best_id)
            text = set_field(text, "views", best_views)
            text = set_field(text, "thumb", thumb)
            if not args.dry_run:
                path.write_text(text, encoding="utf-8")
            print(f"fix   {path.stem:30} {int(current):>10,} -> {best_views:>12,}  {best_id}")
            fixed += 1
        else:
            print(f"keep  {path.stem:30} {int(current):>10,} (no better candidate)")
            kept += 1

    print(f"\nre-picked {fixed}, kept {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
