#!/usr/bin/env python3
"""Build the Chrysanthemum static site from the markdown files in songs/.

Output:
    index.html      browsable home page with live search and filters
    about.html      what the project is and how songs are handled
    s/<slug>.html   one page per song
    assets/style.css is hand-written, not generated

Each song file carries a frontmatter block, an optional ## notes section, an
optional ## lines section (blank-line-separated triplets of hanzi / pinyin /
english), and an optional ## vocab section of `word | pinyin | meaning` rows.

Songs marked `rights: copyrighted` must not carry a ## lines section — the build
fails if one is present. Those entries link out and teach vocabulary instead.
"""

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
SONGS_DIR = ROOT / "songs"
SONG_OUT = ROOT / "s"

E = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- parsing

def parse_song(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        sys.exit(f"{path.name}: missing frontmatter block")

    meta = {}
    for line in m.group(1).splitlines():
        if line.strip():
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
        "youtubeId": meta.get("youtube_id", ""),
        "notes": sections.get("notes", ""),
        "lines": [],
        "vocab": [],
    }

    if "lines" in sections:
        if song["rights"] != "public-domain":
            sys.exit(
                f"{path.name}: has a ## lines section but rights is "
                f"'{song['rights']}'. Full text may only be included for "
                f"public-domain works."
            )
        for block in re.split(r"\n\s*\n", sections["lines"]):
            rows = [r.strip() for r in block.strip().splitlines() if r.strip()]
            if len(rows) != 3:
                sys.exit(
                    f"{path.name}: expected a hanzi/pinyin/english triplet, got "
                    f"{len(rows)} line(s): {rows!r}"
                )
            song["lines"].append({"hanzi": rows[0], "pinyin": rows[1], "en": rows[2]})

    for row in sections.get("vocab", "").splitlines():
        if row.strip():
            parts = [p.strip() for p in row.split("|")]
            if len(parts) != 3:
                sys.exit(f"{path.name}: bad vocab row: {row!r}")
            song["vocab"].append({"word": parts[0], "pinyin": parts[1], "en": parts[2]})

    return song


def paras(text):
    """Markdown-lite: blank-line paragraphs with **bold**."""
    out = []
    for block in filter(None, re.split(r"\n\s*\n", text)):
        body = E(block.replace("\n", " "))
        body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
        out.append(f"<p>{body}</p>")
    return "".join(out)


# ---------------------------------------------------------------- chrome

def page(base, title, body, nav, extra_script=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="Chinese songs line by line — characters, pinyin and English — for learners.">
<link rel="stylesheet" href="{base}assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>%E2%9C%BD</text></svg>">
</head>
<body>
<header class="site-head"><div class="wrap">
  <a class="brand" href="{base}index.html"><span class="bloom">&#10045;</span> Chrysanthemum</a>
  <nav class="site-nav">
    <a href="{base}index.html"{' aria-current="page"' if nav == 'home' else ''}>Songs</a>
    <a href="{base}about.html"{' aria-current="page"' if nav == 'about' else ''}>About</a>
    <button class="icon-btn" id="t-theme" title="Toggle light / dark">&#9681;</button>
  </nav>
</div></header>

<main class="wrap">
{body}
</main>

<footer class="site-foot"><div class="wrap">
  <p>Full text appears only for songs in the <strong>public domain</strong> — classical
     poems and traditional folk songs. Songs still under copyright are listed with a
     link and a vocabulary sheet instead; open them on a licensed service to read along.</p>
  <p>English translations are original to this project.
     <a href="https://github.com/danielluzhu/chrysanthemum">Source on GitHub</a></p>
</div></footer>

<script>
document.getElementById('t-theme').addEventListener('click', () => {{
  const root = document.documentElement;
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const cur = root.dataset.theme || (dark ? 'dark' : 'light');
  root.dataset.theme = cur === 'dark' ? 'light' : 'dark';
  try {{ localStorage.setItem('theme', root.dataset.theme); }} catch (e) {{}}
}});
try {{
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.dataset.theme = saved;
}} catch (e) {{}}
{extra_script}
</script>
</body>
</html>
"""


def badges(song, extra_class=""):
    pd = song["rights"] == "public-domain"
    tag = ('<span class="badge pd">Full text</span>' if pd
           else '<span class="badge">Vocabulary only</span>')
    lvl = f'<span class="badge">{E(song["level"])}</span>' if song["level"] else ""
    return f'<div class="badges{extra_class}">{tag}{lvl}</div>'


# ---------------------------------------------------------------- pages

def build_home(songs):
    cards = json.dumps([
        {
            "slug": s["slug"], "title": s["title"], "pinyinTitle": s["pinyinTitle"],
            "titleEn": s["titleEn"], "artist": s["artist"], "era": s["era"],
            "rights": s["rights"], "level": s["level"],
            "youtubeId": s["youtubeId"],
            "lines": len(s["lines"]), "vocab": len(s["vocab"]),
            "hay": " ".join([
                s["title"], s["pinyinTitle"], s["titleEn"], s["artist"], s["era"], s["level"]
            ]).lower(),
        }
        for s in songs
    ], ensure_ascii=False)

    body = """
<section class="hero">
  <div class="bloom">&#10045;</div>
  <h1>Chrysanthemum</h1>
  <p>Chinese songs, line by line — characters, pinyin and English together.
     Put the recording on, follow along, and pick up some Chinese as you listen.</p>
</section>

<section class="toolbar">
  <input class="search" id="q" type="search" autocomplete="off"
         placeholder="Search by title, pinyin, artist&hellip;" aria-label="Search songs">
  <div class="filters">
    <span class="label">Show</span>
    <button data-f="rights" data-v="all" aria-pressed="true">All</button>
    <button data-f="rights" data-v="public-domain" aria-pressed="false">Full text</button>
    <button data-f="rights" data-v="copyrighted" aria-pressed="false">Vocabulary</button>
    <span class="label" style="margin-left:.75rem">Level</span>
    <button data-f="level" data-v="all" aria-pressed="true">Any</button>
    <button data-f="level" data-v="beginner" aria-pressed="false">Beginner</button>
    <button data-f="level" data-v="intermediate" aria-pressed="false">Intermediate</button>
    <button data-f="level" data-v="advanced" aria-pressed="false">Advanced</button>
  </div>
  <p class="count" id="count"></p>
</section>

<section class="grid" id="grid"></section>
"""

    script = """
const SONGS = __CARDS__;
const state = { q: '', rights: 'all', level: 'all' };
const grid = document.getElementById('grid');
const countEl = document.getElementById('count');
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function render() {
  const hits = SONGS.filter(s =>
    (state.rights === 'all' || s.rights === state.rights) &&
    (state.level === 'all' || s.level === state.level) &&
    (!state.q || s.hay.includes(state.q)));

  countEl.textContent = hits.length === SONGS.length
    ? SONGS.length + ' songs'
    : hits.length + ' of ' + SONGS.length + ' songs';

  grid.innerHTML = hits.length ? hits.map(s => `
    <a class="card" href="s/${esc(s.slug)}.html">
      ${s.youtubeId ? `<div class="cover">
        <img src="https://i.ytimg.com/vi/${esc(s.youtubeId)}/hqdefault.jpg"
             alt="" loading="lazy" decoding="async">
      </div>` : `<div class="cover cover-blank" aria-hidden="true">&#10045;</div>`}
      <div class="card-body">
      <div class="hz">${esc(s.title)}</div>
      <div class="py">${esc(s.pinyinTitle)}</div>
      <div class="en">${esc(s.titleEn)}</div>
      <div class="meta">${esc(s.artist)}${s.era ? ' &middot; ' + esc(s.era) : ''}</div>
      <div class="badges">
        ${s.rights === 'public-domain'
          ? '<span class="badge pd">' + s.lines + ' lines</span>'
          : '<span class="badge">Vocabulary only</span>'}
        ${s.level ? '<span class="badge">' + esc(s.level) + '</span>' : ''}
      </div>
      </div>
    </a>`).join('')
    : '<p class="empty">No songs match that. Try a different search.</p>';
}

document.getElementById('q').addEventListener('input', e => {
  state.q = e.target.value.trim().toLowerCase();
  render();
});

document.querySelectorAll('.filters button').forEach(btn => {
  btn.addEventListener('click', () => {
    const f = btn.dataset.f;
    state[f] = btn.dataset.v;
    document.querySelectorAll(`.filters button[data-f="${f}"]`).forEach(b =>
      b.setAttribute('aria-pressed', String(b === btn)));
    render();
  });
});

render();
"""
    return page("", "Chrysanthemum — Chinese songs line by line", body, "home",
                script.replace("__CARDS__", cards))


def build_song(song, prev, nxt):
    lines = ""
    if song["lines"]:
        lines = f"""
<div class="section-head">
  <h2>Line by line</h2>
  <div class="toggles">
    <button id="t-pinyin" aria-pressed="true">Pinyin</button>
    <button id="t-english" aria-pressed="true">English</button>
  </div>
</div>
<div class="lines">""" + "".join(
            f"""<div class="line">
  <div class="hanzi">{E(l['hanzi'])}</div>
  <div class="py">{E(l['pinyin'])}</div>
  <div class="en">{E(l['en'])}</div>
</div>""" for l in song["lines"]
        ) + "</div>"

    vocab = ""
    if song["vocab"]:
        rows = "".join(
            f"""<tr><td class="v-word">{E(v['word'])}</td>"""
            f"""<td class="v-py">{E(v['pinyin'])}</td>"""
            f"""<td class="v-en">{E(v['en'])}</td></tr>""" for v in song["vocab"]
        )
        vocab = (f'<div class="section-head"><h2>Vocabulary</h2></div>'
                 f'<div class="v-scroll"><table>{rows}</table></div>')

    pager = ""
    if prev or nxt:
        left = (f'<a class="prev" href="{E(prev["slug"])}.html">'
                f'<div class="dir">&larr; Previous</div>'
                f'<div class="nm">{E(prev["title"])}</div></a>') if prev else "<span></span>"
        right = (f'<a class="next" href="{E(nxt["slug"])}.html">'
                 f'<div class="dir">Next &rarr;</div>'
                 f'<div class="nm">{E(nxt["title"])}</div></a>') if nxt else "<span></span>"
        pager = f'<nav class="pager">{left}{right}</nav>'

    # Click-to-play facade: only a thumbnail loads up front. The player itself
    # is injected on click, so nothing is requested from YouTube until the
    # visitor asks for it.
    if song["youtubeId"]:
        vid = E(song["youtubeId"])
        listen = f"""
<div class="video">
  <button class="video-facade" data-id="{vid}"
          aria-label="Play {E(song['title'])} on YouTube"
          style="background-image:url('https://i.ytimg.com/vi/{vid}/hqdefault.jpg')">
    <span class="play" aria-hidden="true"></span>
  </button>
  <p class="video-note">
    Plays from YouTube &middot;
    <a href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">open there instead</a>
  </p>
</div>"""
    elif song["youtube"]:
        listen = (f'<a class="listen" href="{E(song["youtube"])}" target="_blank" '
                  f'rel="noopener">&#9654; Find it on YouTube</a>')
    else:
        listen = ""

    body = f"""
<article class="song-page">
  <a class="back" href="../index.html">&larr; All songs</a>
  <h1 class="song-title">{E(song['title'])}</h1>
  <p class="song-py">{E(song['pinyinTitle'])}</p>
  <p class="song-en">{E(song['titleEn'])}</p>
  <p class="song-meta">{E(song['artist'])}{' &middot; ' + E(song['era']) if song['era'] else ''}</p>
  {badges(song, " song-head-badges")}
  {f'<div class="notes">{paras(song["notes"])}</div>' if song["notes"] else ""}
  {listen}
  {lines}
  {vocab}
  {pager}
</article>
"""

    script = """
const toggle = (id, cls) => {
  const b = document.getElementById(id);
  if (!b) return;
  b.addEventListener('click', () => {
    const on = b.getAttribute('aria-pressed') === 'true';
    b.setAttribute('aria-pressed', String(!on));
    document.body.classList.toggle(cls, on);
  });
};
toggle('t-pinyin', 'hide-pinyin');
toggle('t-english', 'hide-english');

// Swap the thumbnail for the real player only once the visitor clicks.
document.querySelectorAll('.video-facade').forEach(el => {
  el.addEventListener('click', () => {
    const frame = document.createElement('iframe');
    frame.src = 'https://www.youtube-nocookie.com/embed/' + el.dataset.id +
                '?autoplay=1&rel=0';
    frame.title = 'YouTube video player';
    frame.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture; fullscreen';
    frame.allowFullscreen = true;
    frame.loading = 'lazy';
    el.replaceWith(frame);
  }, { once: true });
});
"""
    title = f"{song['title']} {song['titleEn']} — Chrysanthemum"
    return page("../", title, body, "", script)


def build_about(songs):
    pd = sum(1 for s in songs if s["lines"])
    body = f"""
<section class="prose">
  <h1>About</h1>
  <p>Chrysanthemum presents Chinese songs line by line — simplified characters,
     pinyin, and an English translation stacked together — so you can put a
     recording on, follow along, and pick up some Chinese while you listen.</p>
  <p>It is named for the chrysanthemum, the flower that travelled from China to
     British gardens and from there to the rest of the world.</p>

  <h2>How to use it</h2>
  <ul>
    <li>Find a song, open it, and hit the listening link.</li>
    <li>Read through the vocabulary first — arriving at a song already knowing
        the words beats scanning a translation while it plays.</li>
    <li>On a song page, switch off <strong>Pinyin</strong> or <strong>English</strong>
        to test how much you can carry on your own.</li>
  </ul>

  <h2>Two kinds of entry</h2>
  <p><strong>Public domain — full text.</strong> Classical poems and traditional folk
     songs whose copyright expired long ago. These get the complete line-by-line
     treatment. There are {pd} of them at the moment, from Tang and Song dynasty
     poetry through to an early twentieth-century school song.</p>
  <p><strong>Still in copyright — link and vocabulary.</strong> Modern songs are
     somebody's living work, and reproducing a full set of lyrics is not ours to
     do, whether or not pinyin and a translation sit underneath. Those entries
     carry a listening link, background on the song, and a vocabulary sheet to
     study before you press play. Read the lyrics on QQ&#38899;&#20048;, Apple Music,
     Spotify, or YouTube's own captions.</p>
  <p>The build enforces this: a song marked <code>rights: copyrighted</code> that
     carries a <code>## lines</code> section fails the build outright.</p>

  <h2>Translations</h2>
  <p>The English here is original to this project. It aims to be useful to a
     learner first and literary second — where a choice had to be made, it follows
     the structure of the Chinese line rather than reaching for an elegant
     paraphrase.</p>

  <h2>Adding a song</h2>
  <p>Drop a markdown file into <code>songs/</code> and run <code>python3 build.py</code>.
     The format is documented in the project readme.</p>
</section>
"""
    return page("", "About — Chrysanthemum", body, "about")


# ---------------------------------------------------------------- main

def main():
    songs = sorted(
        (parse_song(p) for p in SONGS_DIR.glob("*.md")),
        key=lambda s: (s["rights"] != "public-domain", s["pinyinTitle"]),
    )
    if not songs:
        sys.exit("no songs found in songs/")

    SONG_OUT.mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(build_home(songs), encoding="utf-8")
    (ROOT / "about.html").write_text(build_about(songs), encoding="utf-8")

    for i, song in enumerate(songs):
        prev = songs[i - 1] if i else None
        nxt = songs[i + 1] if i + 1 < len(songs) else None
        (SONG_OUT / f"{song['slug']}.html").write_text(
            build_song(song, prev, nxt), encoding="utf-8")

    full = sum(1 for s in songs if s["lines"])
    print(f"built {len(songs) + 2} pages: index, about, and {len(songs)} songs "
          f"({full} with full text)")


if __name__ == "__main__":
    main()
