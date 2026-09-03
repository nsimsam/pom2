# Rebuilding the portal

Four scripts, run from the repo root, in this order. Python 3, no dependencies.

```bash
python tools/rosters_from_vault.py    # every lecture in the block, written up or not
python tools/charts_from_vault.py     # folds the notes that exist on top
python tools/build_pages.py           # the five block pages
python tools/build_index.py           # the landing page and its counts
```

The first two read an Obsidian vault of lecture notes. The last two read only
`data/` and the pages already in the repo, so they run anywhere.

**After writing a new note, run the first two and then the last two.** The block
pages and the index both print counts, so they go stale otherwise.

## Pointing them at your vault

`rosters_from_vault.py` and `charts_from_vault.py` default to the author's vault
path. Set `POM2_VAULT` to your own:

```bash
export POM2_VAULT="/path/to/vault/01 - Lectures/99 - PoM 2"   # bash
$env:POM2_VAULT = "C:\path\to\vault\01 - Lectures\99 - PoM 2" # PowerShell
```

Inside that folder the scripts expect one directory per block (`01 - Endocrinology`,
`02 - Repro`, `03 - MSK`, `04 - Neuro`, `05 - Psych`), each holding `Week N`
folders of `.md` files named `NN - Lecture title.md`. The block list and its week
numbers live in `BLOCKS` at the top of both scripts. Edit that and the portal
follows a different course.

## What each one does

**`rosters_from_vault.py`** lists every lecture note in each block's week folders
and writes `data/notes/<slug>.json` with `"hasNote": false` throughout. The roster
is the point: a lecture with no note still appears, so the notes tab reads as a
coverage map. Week headings are borrowed from `data/questions/<slug>.json` so both
tabs name a week the same way.

**A word on vocabulary.** The vault calls these *charts*, since the region at the
top of each lecture note opens `# Overview chart:`, and the site calls them
*notes*. The extractor keeps the vault's word because that is what it reads.
Everything on the site side uses the site's.

**`charts_from_vault.py`** lifts the chart out of the top of each lecture note,
meaning the region between the frontmatter and the first `---`, and folds it into
the roster. It keeps the parts in source order in a `blocks` array, because the
sentence above a table is the reason the table is there. Markdown becomes inline
HTML: `**bold**`, `<u>`, `<br>`, `[[wikilinks]]` as `<span class="wl">`,
`[text](url)` as a real link, and mermaid fences as `{"t": "pathway"}`.

**`build_pages.py`** regenerates the five block pages. Only the name, blurb, accent
and two counts differ between them, so they are generated rather than copied. The
blurb and accent are read back out of the page being replaced, so edit those in the
HTML and they survive the next run.

**`build_index.py`** regenerates `index.html`, taking every count from the data
rather than from prose, so the cards cannot drift.

## Editing by hand

Prose in the block pages and the index is safe to edit **only in the templates**
inside `build_pages.py` and `build_index.py`. The next run overwrites the HTML. The
two exceptions are the per-block blurb (`<p class="lead">`) and the accent trio in
each page's inline `:root`, which are read back out before the page is rewritten.

`base.css`, `pom2.css`, `quiz.js`, `notes.js` and `pom2.js` are hand-maintained and
never generated. **After editing one of them, re-run `build_pages.py` and
`build_index.py` anyway.** The pages link these assets as `base.css?v=<hash of its
contents>`, and the hash is read off the file at build time. GitHub Pages serves
them with `Cache-Control: max-age=600`, so without a fresh hash a browser will keep
last deploy's stylesheet for ten minutes and paint the new markup with the old
rules. Skipping the rebuild is not harmful, since the server ignores the query
string, but it stops the cache from being busted.

Two constants at the top of `build_pages.py` and `build_index.py` are deliberately
empty: `CF`, for an analytics snippet, and `PILLNAV`, for a nav bar back to a
parent site. Fill either in and every generated page picks it up.

## Not regenerated

`data/questions/*.json` is not produced by anything here. If you are bringing your
own questions, write that JSON yourself. One object per question, in a flat list.
The fields the front end reads are documented in the main [README](../README.md).
