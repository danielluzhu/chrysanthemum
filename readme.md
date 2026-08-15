# Chrysanthemum ✽

Chinese songs presented line by line — simplified characters, pinyin, and English
together — so you can put a recording on, follow along, and pick up some Chinese
while you listen.

Named for the chrysanthemum, the flower that travelled from China to British gardens
and then to the rest of the world.

## Try it

```sh
python3 build.py && open index.html
```

No dependencies, no build tooling — `build.py` reads `songs/*.md` and writes a
single self-contained `index.html`. On the page you can hide the pinyin or the
English to test yourself, and switch between light and dark.

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

## A note on the YouTube links

Each song links to a YouTube **search** for its title and artist rather than a
specific video ID. Individual uploads get taken down or re-uploaded constantly,
and a search link keeps working. If you want to pin a particular official
recording, replace the URL in the song's frontmatter.

## Translations

The English translations here are original to this project. They aim to be useful
to a learner first and literary second: where a choice had to be made, they follow
the Chinese line structure rather than reaching for an elegant paraphrase.
