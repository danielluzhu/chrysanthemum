#!/usr/bin/env python3
"""Scrape Hit FM 年度百首單曲 annual rankings from the tw-pop-chart archive.

Only chart facts are taken: position, song title and artist. Those are data,
not creative work. Nothing else is copied from the source pages.

The chart ranks international releases alongside Mandopop, so entries whose
title and artist contain no Chinese characters are dropped — a Korean or
English track is no use on a Chinese-learning site.

    python3 deploy/scrape_charts.py --top 10 > /tmp/charts.tsv

Output columns: year, rank, title, artist.
"""

import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.request

SITEMAP = "https://tw-pop-chart.blogspot.com/sitemap.xml?page={}"
POST_RE = re.compile(
    r"https://tw-pop-chart\.blogspot\.com/\d{4}/\d{2}/hit-fm-(\d{4})\.html")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
CJK = re.compile(r"[一-鿿]")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return ""


def find_year_pages():
    found = {}
    for page in (1, 2, 3):
        for m in POST_RE.finditer(fetch(SITEMAP.format(page))):
            found[int(m.group(1))] = m.group(0)
    return dict(sorted(found.items()))


def cells(row):
    out = []
    for c in re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", row):
        text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", c))
        out.append(re.sub(r"\s+", " ", text).strip())
    return out


def parse_year(url, top):
    rows = re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", fetch(url))
    out = []
    for row in rows:
        c = cells(row)
        if len(c) >= 3 and re.fullmatch(r"\d{1,3}", c[0] or ""):
            rank = int(c[0])
            if rank <= top:
                out.append((rank, c[1], c[2]))
    return sorted(out)[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    pages = find_year_pages()
    print(f"# {len(pages)} year pages: {min(pages)}–{max(pages)}", file=sys.stderr)

    kept = dropped = 0
    for year, url in pages.items():
        entries = parse_year(url, args.top)
        if not entries:
            print(f"# {year}: no rows parsed", file=sys.stderr)
            continue
        for rank, title, artist in entries:
            # The TITLE must contain Chinese. Testing the artist instead lets
            # through English-language tracks by Chinese singers, which teach
            # nothing here.
            if not CJK.search(title):
                dropped += 1
                continue
            print(f"{year}\t{rank}\t{title}\t{artist}")
            kept += 1
        time.sleep(0.6)

    print(f"# kept {kept}, dropped {dropped} non-Chinese", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
