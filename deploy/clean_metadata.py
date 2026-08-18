#!/usr/bin/env python3
"""Clear implausible metadata left behind by the MusicBrainz enrichment pass.

MusicBrainz coverage of Mandopop is patchy, so the automatic pass sometimes
matched the wrong artist entirely, or picked a DJ compilation, karaoke disc or
live album as the "earliest release". A filter showing a wrong year is worse
than one showing Unknown, so anything that fails these checks is blanked.

    python3 deploy/clean_metadata.py [--dry-run]
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs"

# Releases that are clearly not the original: compilations, club mixes,
# karaoke discs, live recordings, greatest-hits sets.
BAD_ALBUM = re.compile(
    r"hot mix|dj舞曲|夜店|精選|精选|合輯|合辑|karaoke|卡拉ok|"
    r"live|演唱會|演唱会|珍藏版|超好听|新歌\+|best of|greatest",
    re.I,
)

# Chinese-language pop comes from these places. Anything else is a mismatched
# artist record rather than a genuinely foreign act.
PLAUSIBLE = {"CN", "TW", "HK", "SG", "MY", "US", "CA", "JP", "KR", "GB", "AU"}

# Release years known to be correct, where the automatic pass got it wrong or
# found nothing. Only songs whose history is unambiguous are listed.
KNOWN = {
    "turan-hao-xiang-ni":            ("2008", "後青春期的詩"),
    "yekong-zhong-zui-liang-de-xing": ("2011", "世界"),
    "yiran-ai-ni":                   ("2011", "十八般武藝"),
    "gaobai-qiqiu":                  ("2016", "周杰倫的床邊故事"),
    "xiulian-aiqing":                ("2013", "因你而在"),
    "yihou-bie-zuo-pengyou":         ("2015", "學著愛"),
    "ju-hua-tai":                    ("2006", "依然范特西"),
    "yue-liang-dai-biao-wo-de-xin":  ("1977", "島國之情歌第三集"),
}


def field(text, key):
    m = re.search(rf"^{key}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def set_field(text, key, value):
    if re.search(rf"^{key}:", text, re.M):
        return re.sub(rf"^{key}:.*$", f"{key}: {value}", text, count=1, flags=re.M)
    return re.sub(r"^(youtube_id:.*)$", rf"\1\n{key}: {value}", text,
                  count=1, flags=re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cleared_album = cleared_country = corrected = 0

    for path in sorted(SONGS.glob("*.md")):
        text = original = path.read_text(encoding="utf-8")
        slug = path.stem

        if slug in KNOWN:
            year, album = KNOWN[slug]
            if field(text, "year") != year or field(text, "album") != album:
                text = set_field(set_field(text, "year", year), "album", album)
                print(f"fix   {slug:34} year={year} album={album}")
                corrected += 1
        else:
            album = field(text, "album")
            if album and BAD_ALBUM.search(album):
                text = set_field(set_field(text, "album", ""), "year", "")
                print(f"clear {slug:34} compilation/live: {album[:40]}")
                cleared_album += 1

        country = field(text, "country")
        if country and country not in PLAUSIBLE:
            text = set_field(text, "country", "")
            print(f"clear {slug:34} implausible country: {country}")
            cleared_country += 1

        if text != original and not args.dry_run:
            path.write_text(text, encoding="utf-8")

    print(f"\ncorrected {corrected}, cleared {cleared_album} albums, "
          f"{cleared_country} countries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
