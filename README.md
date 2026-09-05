# PoM 2 portal

A static study portal for a medical school course, built around one page per
block. Each page has two tabs: **notes**, a coverage map of every lecture in the
block whether or not it has been written up, and **practice questions**, a quiz
runner that keeps score.

No build step, no framework, no server. Six HTML files, three JS files, two
stylesheets and a folder of JSON. Open `index.html` and it works.

It was written for the five blocks of the second Principles of Medicine year at
Schulich (endocrinology, reproduction, MSK, neurology, psychiatry), but nothing
about the code knows that. Swap the JSON and it is your course.

Live at **<https://noorsimsam.com/pom2/>**.

## Run it yourself

```bash
git clone https://github.com/nsimsam/pom2
cd pom2
python -m http.server 8000
```

Then open <http://localhost:8000>. A plain `file://` open works too, except that
browsers block `fetch` of local JSON, so the tabs come up empty. Use the server.

## What is in here

```
index.html              the landing page, five block cards
endo|repro|msk|neuro|psych.html    one page per block
base.css                design tokens, the reset, the page frame
pom2.css                everything the portal draws
pom2.js                 tab switching, shared helpers
notes.js                the notes tab, including the PDF printing
quiz.js                 the question runner and the progress store
data/notes/*.json       lecture rosters, with a written note folded in where one exists
data/questions/*.json   the question bank
tools/                  the four scripts that regenerate all of the above
```

`tools/` is only needed if you keep your source material in an Obsidian vault and
want it extracted automatically. See [tools/README.md](tools/README.md). If you
are hand-writing the JSON, ignore the whole folder.

## Progress stays on the device

Answers, stars and per-lecture accuracy are written to the browser's
`localStorage`. Nothing is sent anywhere, there is no backend, and nobody running
a copy of this can see anyone else's progress. The flip side is that it does not
follow you between browsers or machines, so the questions tab has **Download all my
progress** and **Restore from a file** buttons that move a JSON file by hand. One file holds
every block and can be written or read from any of them, and a restore only adds and updates,
so an out of date file cannot overwrite newer answers.

## Bringing your own content

### Questions

`data/questions/<block>.json` is a flat list of question objects. Every question
carries the same fields:

| field | what it holds |
| --- | --- |
| `qid` | unique id, and the key progress is stored against |
| `num`, `week`, `weekLabel` | position in the course, used for grouping |
| `lecture`, `lectureMeta` | which lecture it hangs off, and a note about the source |
| `source`, `sourceLabel`, `family` | which bank it came from, shown as a filter |
| `stem`, `preamble` | the question itself as HTML, and any shared setup above it |
| `kind` | `mcq`, `short`, `matching`, or `broken` |
| `options` | `[{"letter": "A", "html": "..."}]` |
| `correct`, `multi` | the answer letters, and whether more than one is expected |
| `answer`, `answerTitle` | the explanation shown after answering |
| `keyed`, `free`, `unscorable`, `retired` | whether it has a real key, is ungraded, cannot be scored, or is hidden |
| `flags` | `[{"type": "warning", "title": "...", "html": "..."}]`, printed on the question |

`keyed: false` and `unscorable: true` matter. Question banks handed down between
years are often missing an answer key or contain a question with no defensible
answer. Rather than inventing a letter, the portal says so on the question's face
and leaves it out of the score.

### Notes

`data/notes/<block>.json` is one object per block, holding `weeks`, holding
`lectures`. A lecture with `hasNote: false` still renders, greyed, so the tab
reads as a coverage map rather than a list of what happens to be done. A lecture
with a note adds `title`, `framing`, `keypoints` and `blocks`, where `blocks` is
an ordered list of `{"t": "table" | "note" | "callout" | "list" | "pathway"}`
parts. Order is preserved on purpose, since the sentence above a table is usually
the reason the table is there.

## Making it yours

- **Colours.** The palette is nine custom properties at the top of `base.css`.
  Each block page then sets its own `--q-accent`, `--q-accent-soft` and
  `--q-accent-ink` in an inline `:root`, which is also what the landing page card
  reads for its `--hue`.
- **Blocks.** The block list lives in `BLOCKS` at the top of each script in
  `tools/`. Five is not special.
- **Fonts.** Fraunces and Inter, pulled from Google Fonts in each page head. Both
  have local fallbacks in `base.css`.
- **Search engines.** Every page ships with `<meta name="robots"
  content="noindex, nofollow">`, because the original is meant to be unlisted.
  Delete that line if you want yours found.
- **Analytics and a parent nav.** `CF` and `PILLNAV` in `build_pages.py` and
  `build_index.py` sit in the right spot in the template. `CF` is empty.
  `PILLNAV` holds the nav bar of the site this copy hangs off, styled by
  `.pill-nav` in `base.css`; blank it and the pages lose the bar cleanly.

## Licence and content

The code is MIT, see [LICENSE](LICENSE).

The study content under `data/` has its own history. The 700 practice questions
came out of shared course material: a student-written workbook handed down through
the Schulich classes of 2015 to 2025, Elentra module knowledge checks, weekly
quizzes, slide concept checks and questions written from the case and small-group
sessions.

**They are here on purpose.** These are resources students already pass between
years, and putting them somewhere public is the reason this
repository exists, not an accident of packaging. Use them, fork them, correct them,
add to them. Where a question came out of a peer-written bank its errors are flagged
on the question itself rather than quietly patched, so you can see what you are
trusting before you trust it.
