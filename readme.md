# Chrysanthemum ✽

Chinese songs presented line by line — simplified characters, pinyin, and English
together — so you can put a recording on, follow along, and pick up some Chinese
while you listen.

Named for the chrysanthemum, the flower that travelled from China to British gardens
and then to the rest of the world.

**Live site: <https://danielluzhu.github.io/chrysanthemum/>**

## Try it

```sh
python3 build.py && python3 -m http.server 8000
```

No dependencies and no build tooling — `build.py` reads `songs/*.md` and writes
plain HTML:

```
index.html      home: card grid with live search and filters
about.html      what the project is, and how songs are handled
s/<slug>.html   one page per song
assets/style.css  hand-written, not generated
```

The home page searches titles, pinyin, artists and eras as you type, and filters
by full-text/vocabulary and by difficulty. On a song page you can switch off the
pinyin or the English to test yourself, and page straight to the next song. Light
and dark both supported; your choice is remembered.

## Self-hosting with Bun + systemd

The generated site is plain static files, so GitHub Pages serves it fine. To run
it on your own box instead, there is a small Bun server and a systemd unit.

```sh
PORT=8787 bun run server.ts          # foreground, for a quick look
```

`server.ts` has no dependencies. It serves the built pages, resolves
extension-less URLs (`/about`, `/s/mo-li-hua`), returns a styled 404, refuses
anything that isn't GET/HEAD, and rejects paths that try to escape the project
directory.

To install it as a service:

```sh
sudo cp deploy/chrysanthemum.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chrysanthemum
```

```sh
systemctl status chrysanthemum
journalctl -u chrysanthemum -f
sudo systemctl restart chrysanthemum   # also rebuilds the site
```

Two things worth knowing about the unit:

**It rebuilds before serving.** `ExecStartPre` runs `build.py`, so a restart always
picks up edits to `songs/`. If a song breaks the copyright rule below, the build
fails and *the service refuses to start* — better to serve nothing than to serve
text that shouldn't be there.

**It binds to `127.0.0.1` only.** Nothing reaches it from outside the machine as
shipped. Put a reverse proxy in front of it for real traffic, and let that
terminate TLS — or set `HOST=0.0.0.0` in the unit if you genuinely want it
exposed directly.

The unit runs as `ubuntu` with the usual hardening (`ProtectSystem=strict`,
`ProtectHome=read-only`, a syscall filter, `/workspace` the only writable path).
Note `MemoryDenyWriteExecute=false` is deliberate — Bun's JIT needs
write-execute pages and the service will not start without it.

## How songs are handled

Songs come in two kinds, and the difference is about copyright.

**Public domain — full text.** Classical poems and traditional folk songs whose
copyright has long expired. These get the complete line-by-line treatment: hanzi,
pinyin, English. Currently five of them, from Li Bai and Su Shi through to a
much-loved 1915 school song.

**Still in copyright — link and vocabulary.** Modern songs are somebody's living
work, and reproducing a whole set of lyrics is not ours to do, whether or not
pinyin and a translation are stacked underneath. So these entries carry a listening
link, background on the song, and a vocabulary sheet of individual words to learn
before you press play. Open the lyrics on QQ音乐, Apple Music, Spotify, or YouTube's
captions and read along there.

Studying the vocabulary first is, for what it's worth, a better way to learn than
scanning a translation — you arrive at the song already knowing what to listen for.

`build.py` enforces this: a song marked `rights: copyrighted` that carries a
`## lines` section fails the build.

## Adding a song

Drop a new file in `songs/`:

```markdown
---
slug: my-song
title: 歌名
pinyin_title: Gē Míng
title_en: Song Title
artist: 演唱者
era: 2001
rights: public-domain   # or: copyrighted
level: beginner         # beginner | intermediate | advanced
youtube: https://...
---

## notes

A paragraph or two of context — who wrote it, when, why it matters.

## lines

汉字一行
Hànzì yī háng
One line of characters

## vocab

词 | cí | word
```

The `## lines` section is blank-line-separated triplets: characters, then pinyin,
then English. Omit it entirely for songs under copyright. `## vocab` rows are
`word | pinyin | meaning`. Then run `python3 build.py`.

## Videos

Each song embeds a recording, set by `youtube_id` in its frontmatter. Official
artist, label, VEVO and Topic channels are preferred where they exist, since
those are far less likely to disappear than fan uploads.

Nothing loads from YouTube until you ask it to. The page renders a thumbnail
with a play button, and the player is injected only on click — via
`youtube-nocookie.com`, so no tracking cookie is set for visitors who never
press play.

Video IDs rot: uploads get deleted, made private, or region-blocked. To find
out before your visitors do:

```sh
python3 deploy/verify-videos.py
```

It asks YouTube's oEmbed endpoint about every ID and prints the channel and
title each currently resolves to, exiting non-zero if any fail. Worth running
periodically — a swapped video is otherwise invisible.

The `youtube:` search URL stays in the frontmatter as a fallback: if a song has
no `youtube_id`, the page falls back to a plain search link.

## Translations

The English translations here are original to this project. They aim to be useful
to a learner first and literary second: where a choice had to be made, they follow
the Chinese line structure rather than reaching for an elegant paraphrase.
