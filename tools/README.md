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

## Pulling a weekly quiz out of Elentra

Two more scripts, off to the side of the four above. They do not touch `data/`
and are not part of the rebuild. They exist to shorten the trip from a weekly
quiz sat in Elentra to a question note in the vault, which is where the four
scripts pick the work up again.

```bash
python tools/make_bookmarklet.py     # once, then open build/elentra-grab.bookmarklet.html
                                     # and drag the button onto the bookmarks bar
python tools/elentra_quiz.py ~/Downloads/elentra-3007-*.json \
    --topic endo --note "C:/Users/nsims/medwiki/00 - Practice Questions/Weekly Quizzes - Endocrinology.md"
```

**`tools/elentra_grab.js`** is the readable source of the bookmarklet.
`make_bookmarklet.py` strips its comments, percent-encodes it and writes the
`javascript:` URL into `build/`, along with a one-link page to drag from.

Sit the quiz, submit it, then open the **feedback** view,
`exams?section=feedback&progress_id=<n>`, the one showing the correct answers,
and click the bookmark. A panel appears bottom right saying
what it found. If the review paginates, click it on every page: captures
accumulate in `localStorage` under the one exam id and **Download JSON** writes
the merge. Nothing is fetched, clicked or submitted on your behalf, so it cannot
disturb an attempt.

**Probe page first.** The Rise grab in the bookmarks bar never reads a page: Rise
ships a whole course, keys included, as one `runtime-data.js`, so that bookmarklet
just fetches it and `rise_to_bank.py` decodes it. If Elentra's exam player has
anything of that kind, scraping the DOM is the wrong approach. The **Probe page**
button writes a file listing what the page fetched, what globals it is holding and
any inline JSON island, and answers that in one click. It reports; it opens and
fetches nothing.

Failing that, the DOM, read two ways. `elentraScan` knows the shape Schulich's
Elentra renders and reads it exactly: `.exam-question` per question,
`tr.question-answer-view` per option carrying `answer-correct`, and a
`.feedback-report` of `Points` / `Correct Answer` / `Rationale` lines. The key is
stated twice there and the prose line wins, since a class name is a theme's
business and can be restyled out from under this.

Anything that shape misses falls through to a structural reader: a group of radios
or checkboxes sharing a `name` is one question, its container is the smallest
ancestor holding that group alone, and the answer is guessed from surrounding
classes and icons. Both paths write every signal they saw into the file beside the
verdict, and keep each question's own `outerHTML`. That is not decoration. The
first version of this was pure guesswork, and one real capture showed that
matching `right` in a class name also matches Bootstrap's `space-right`, which
marked every option correct on all ten questions. The signals are what turned that
into a one-line fix. `--inspect` prints them. A page that parses to nothing has its
whole body kept in the file for the same reason.

**`tools/embed_image.py`** resolves a vault image, re-compresses it and prints the
`<img>` tag to paste into a question. Pictures ship *inside* the question as a
`data:` URI in the stem HTML. There is no image field and no assets directory,
because `quiz.js` renders the stem as HTML and the browser does the rest.

```bash
python tools/embed_image.py '![[incretin effect - oral vs IV glucose.png|600]]'
# incretin effect - oral vs IV glucose.png -> 78.1 KB encoded, 900px wide, q75
# <img loading="lazy" src="data:image/jpeg;base64,...">
```

It takes a bare filename, a whole `![[embed|600]]`, or a path, and looks in the
vault's `Attachments/` (override with `POM2_ATTACHMENTS`). It spends JPEG quality
before it drops pixels, since a keyed radiology or anatomy image is often keyed on
detail, and it walks both down until the encoded bytes fit `--max-kb` (100 by
default). A picture that will not fit warns rather than shipping quietly: the
question's stem still reads as though the image were there, so a picture too big is
the one failure that hides itself. Unlike the four rebuild scripts this one needs
**Pillow**.

**`tools/elentra_quiz.py`** turns that JSON into house-format markdown in
`build/`: a `#### <lecture>` group of `# N` questions with their answer callouts,
sized and numbered to drop into the week's section of
`Weekly Quizzes - <topic>.md`. Pass `--note` and the numbering continues from the
highest `# N` already in the real note, so nothing renumbers.

It writes a fragment rather than the note because the note is a vault file other
sessions edit, and its `## Week N` sections and Coverage callout are hand-kept.
Two things it will not decide on its own:

- **A question with no detected key** gets the `> [!red] No official answer key`
  scaffold rather than a guess.
- **Select-all and short-answer questions** come through in their original shape
  with the rewrite flagged, since the house rule that every banked question is
  MCQ or true/false is a writing job, not a parsing one.

Both are reported on stdout at the end of a run, with the qid range the fragment
claims.
