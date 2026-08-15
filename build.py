#!/usr/bin/env python3
"""Build index.html from the markdown files in songs/.

Each song file has a frontmatter block, an optional ## notes section, an optional
## lines section (blank-line-separated triplets of hanzi / pinyin / english), and
an optional ## vocab section of `word | pinyin | meaning` rows.

Songs marked `rights: copyrighted` must not carry a ## lines section — the build
fails if one is present. Those entries link out and teach vocabulary instead.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
SONGS_DIR = ROOT / "songs"
OUT = ROOT / "index.html"


def parse_song(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        sys.exit(f"{path.name}: missing frontmatter block")

    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    sections = {}
    for chunk in re.split(r"^## ", m.group(2), flags=re.M)[1:]:
        name, _, body = chunk.partition("\n")
        sections[name.strip()] = body.strip()

    song = {
        "slug": meta.get("slug", path.stem),
        "title": meta.get("title", ""),
        "pinyinTitle": meta.get("pinyin_title", ""),
        "titleEn": meta.get("title_en", ""),
        "artist": meta.get("artist", ""),
        "era": meta.get("era", ""),
        "rights": meta.get("rights", "copyrighted"),
        "level": meta.get("level", ""),
        "youtube": meta.get("youtube", ""),
        "notes": sections.get("notes", ""),
        "lines": [],
        "vocab": [],
    }

    if "lines" in sections:
        if song["rights"] != "public-domain":
            sys.exit(
                f"{path.name}: has a ## lines section but rights is "
                f"'{song['rights']}'. Full lyrics may only be included for "
                f"public-domain works."
            )
        for block in re.split(r"\n\s*\n", sections["lines"]):
            rows = [r.strip() for r in block.strip().splitlines() if r.strip()]
            if len(rows) != 3:
                sys.exit(
                    f"{path.name}: expected hanzi/pinyin/english triplet, got "
                    f"{len(rows)} line(s): {rows!r}"
                )
            song["lines"].append({"hanzi": rows[0], "pinyin": rows[1], "en": rows[2]})

    for row in sections.get("vocab", "").splitlines():
        if not row.strip():
            continue
        parts = [p.strip() for p in row.split("|")]
        if len(parts) != 3:
            sys.exit(f"{path.name}: bad vocab row: {row!r}")
        song["vocab"].append({"word": parts[0], "pinyin": parts[1], "en": parts[2]})

    return song


def main():
    songs = sorted(
        (parse_song(p) for p in SONGS_DIR.glob("*.md")),
        key=lambda s: (s["rights"] != "public-domain", s["title"]),
    )
    if not songs:
        sys.exit("no songs found in songs/")

    template = (ROOT / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(songs, ensure_ascii=False, indent=1)
    OUT.write_text(template.replace("/*__SONGS__*/[]", payload), encoding="utf-8")

    full = sum(1 for s in songs if s["lines"])
    print(f"built {OUT.name}: {len(songs)} songs ({full} with full text)")


if __name__ == "__main__":
    main()
