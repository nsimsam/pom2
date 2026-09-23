# -*- coding: utf-8 -*-
"""Regenerate every course's block pages from one template.

Purpose: build one page per block, for every course in the portal, so the four
         courses cannot drift into four layouts.
Author:  Noor Sims
Date:    2026-09-21
Input:   tools/portal.py (the course roster), each course's data/, and the page
         being replaced (for its blurb and accent, so hand edits survive)
Output:  <course>/<block>.html

Run from the repo root. A course with no blocks yet is skipped; its landing page
still renders from build_index.py, saying it is empty.
"""

import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal

HOWTO = """<details class="howto">
<summary>You can save your progress</summary>
<div class="body">
<p><strong>On this device, and nowhere else.</strong> What you have answered is written to
your browser&rsquo;s local storage. It is never sent to this site, never stored in its
repository, and nobody else can see it, not even me.</p>
<p>That also means it does not follow you. A different browser, a different laptop, or
clearing your site data all start from zero.</p>
<p><strong>To carry it with you:</strong> press <strong>Download all my progress</strong> in
the panel on the left and keep the JSON file it writes. One file holds every block of this
course, and it can be pressed from any of them. On the other machine, open any block and
press <strong>Restore from a file</strong> to put all of it back at once. A restore only ever
adds and updates, so an out of date file cannot wipe out newer answers. Doing that now and
then is also the only backup there is.</p>
</div>
</details>"""

# Used only when a page does not exist yet. After that the page itself is the
# source of truth for these three, so anything reworded by hand survives.
SEED = {}

FAVICON = {"pom2": ("P2", "84223b")}


def existing(course, slug):
    p = os.path.join(portal.cdir(course), "%s.html" % slug)
    if not os.path.exists(p):
        return SEED[(course["slug"], slug)]
    s = io.open(p, encoding="utf-8").read()
    lead = re.search(r'<p class="lead">\s*(.*?)\s*</p>', s, re.S).group(1)
    desc = re.search(r'<meta name="description" content="(.*?)">', s, re.S).group(1)
    accent = re.search(r'(--q-accent:.*?;--q-accent-soft:.*?;--q-accent-ink:.*?;)', s).group(1)
    return lead, desc, accent


def block_counts(course, slug):
    d = portal.cdir(course)
    qs = json.load(io.open(os.path.join(d, "data", "questions", "%s.json" % slug),
                           encoding="utf-8"))
    nt = json.load(io.open(os.path.join(d, "data", "notes", "%s.json" % slug),
                           encoding="utf-8"))
    lects = [l for w in nt["weeks"] for l in w["lectures"]]
    return len(qs), len([l for l in lects if l.get("hasNote")]), len(lects)


def blocknav(course, active):
    rows = ['<a class="home" href="%s">All courses</a>' % portal.HUB_URL]
    for slug, n, name, _w in course["blocks"]:
        cls = ' class="here"' if slug == active else ''
        rows.append('<a href="%s.html"%s>%d &middot; %s</a>' % (slug, cls, n, name))
    return "\n".join(rows)


PAGE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} &middot; {course}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
{favicon}

{nocache}
{fonts}
<link rel="stylesheet" href="{base_css}">
<link rel="stylesheet" href="{portal_css}">
<style>
:root{{{accent}}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

<nav class="blocknav">
{blocknav}
</nav>

<header class="q-masthead">
<div>
<p class="eyebrow" id="m-eyebrow"></p>
<h1>{name}</h1>
<p class="lead">{lead}</p>
</div>
<div class="scoreboard" id="sb-notes">
<div class="score"><b><span id="cv-notes">0</span><span class="of" id="cv-of"></span></b><span>Notes written</span></div>
<div class="score"><b><span id="cv-weeks">0</span><span class="of" id="cv-weeks-of"></span></b><span>Weeks covered</span></div>
</div>
<div class="scoreboard" id="sb-questions" hidden>
<div class="score"><b><span id="sc-done">0</span><span class="of" id="sc-of"></span></b><span>Attempted</span></div>
<div class="score"><b id="sc-first">&ndash;</b><span>Correct</span></div>
<div class="score is-bad"><b id="sc-wrong">0</b><span>Wrong</span></div>
<div class="score is-star"><b id="sc-star">0</b><span>Starred</span></div>
</div>
</header>

<div class="tabs" role="tablist" aria-label="Notes, Anki or questions">
<button type="button" id="tab-notes" role="tab" aria-selected="true" aria-controls="panel-notes">Notes <span class="tc" id="tc-notes">{written}/{lectures}</span></button>
<button type="button" id="tab-anki" role="tab" aria-selected="false" aria-controls="panel-anki">Anki</button>
<button type="button" id="tab-questions" role="tab" aria-selected="false" aria-controls="panel-questions">Practice questions <span class="tc">{questions}</span></button>
</div>

<div class="q-shell is-solo" id="panel-anki" role="tabpanel" aria-labelledby="tab-anki" hidden>
<div class="tab-empty">
<h2>The decks are not up yet.</h2>
<p>This is where the {course} Anki cards for weeks {weeks} will live, filed by week and
lecture the way the notes are. Nothing has been uploaded into it yet.</p>
</div>
</div>

<div class="q-shell" id="panel-notes" role="tabpanel" aria-labelledby="tab-notes">
<aside class="rail">

<section>
<p class="panel-h">Week</p>
<div class="chips" id="note-week-chips"></div>
</section>

<section>
<p class="panel-h">Lectures</p>
<nav class="lecindex" id="note-index" aria-label="Jump to a lecture"></nav>
</section>

<section>
<p class="panel-h">Save as PDF</p>
<button class="print-cta" id="print-all" type="button" disabled>Save every note as one PDF</button>
<p class="railnote">Each note has its own <strong>PDF</strong> button, and each week can be
saved in one go. Print it, annotate it, keep it.</p>
</section>

</aside>

<main class="stream" id="note-stream">
<div class="q-loading">Loading notes&hellip;</div>
</main>

<div class="posbar notebar" id="notebar" hidden>
<button class="pb-step pb-top" id="nb-top" type="button" title="Back to the top" aria-label="Back to the top">Top</button>
</div>
</div>

<div class="q-shell" id="panel-questions" role="tabpanel" aria-labelledby="tab-questions" hidden>

{howto}

<aside class="rail" id="q-rail" data-filter-open="false">

<button class="mfilter" id="filter-toggle" type="button" aria-expanded="false" aria-controls="filter-groups">
<svg class="mfilter-glyph" viewBox="0 0 14 14" aria-hidden="true"><line x1="2" x2="12" y1="3.5" y2="3.5"></line><line x1="3.5" x2="10.5" y1="7" y2="7"></line><line x1="5.5" x2="8.5" y1="10.5" y2="10.5"></line></svg>
<span class="mfilter-label">Filter</span>
<span class="mfilter-badge" id="filter-badge" hidden>0</span>
<svg class="mfilter-chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4.5 L6 8.5 L10 4.5"></path></svg>
</button>

<div class="applied" id="applied" hidden></div>

<div class="rail-groups" id="filter-groups">

<button class="review-cta" id="review-wrong" type="button" disabled>Review wrong only <span class="n" id="review-n">0</span></button>

<section>
<p class="panel-h">Question set</p>
<div class="fams" id="fam-btns"></div>
</section>

<section>
<p class="panel-h">Week</p>
<div class="chips" id="week-chips"></div>
</section>

<section id="tag-section" hidden>
<p class="panel-h">Topic</p>
<div class="chips" id="tag-chips"></div>
</section>

<section>
<p class="panel-h">Status</p>
<div class="chips" id="status-chips"></div>
</section>

<section>
<p class="panel-h">Progress</p>
<p class="storenote" id="storenote" hidden></p>
<div class="resets">
<button class="backup-btn" id="export-progress" type="button">Download all my progress</button>
<button class="backup-btn" id="import-progress" type="button">Restore from a file</button>
<input type="file" id="import-file" accept="application/json,.json" hidden>
<button class="danger" id="reset-shown" type="button" disabled>Reset the questions shown (0)</button>
<button class="danger" id="reset-all" type="button">Reset all progress</button>
</div>
</section>

</div>

</aside>

<main class="stream" id="stream">
<div class="q-loading">Loading {questions} questions&hellip;</div>
</main>

<div class="posbar" id="posbar" hidden>
<span class="pb-where" id="pb-where"></span>
<span class="pb-count" id="pb-count"></span>
<span class="pb-steps">
<button class="pb-step pb-top" id="pb-top" type="button" title="Back to the top" aria-label="Back to the top">Top</button>
<button class="pb-step" id="pb-prev" type="button" title="Previous question (k)" aria-label="Previous question">&uarr;</button>
<button class="pb-step" id="pb-next" type="button" title="Next question (j)" aria-label="Next question">&darr;</button>
</span>
<button class="pb-mark" id="pb-mark" type="button" hidden></button>
</div>
</div>

<script>
window.QUIZ_BLOCK = {block_json};
</script>
<script src="{quiz_js}"></script>
<script src="{notes_js}"></script>
<script src="{portal_js}"></script>

{footer}

</div>

</body>
</html>
"""


def main():
    for course in portal.COURSES:
        for slug, n, name, weeks in course["blocks"]:
            lead, desc, accent = existing(course, slug)
            q, written, lectures = block_counts(course, slug)
            d = portal.cdir(course)
            cfg = {
                "slug": slug, "n": n, "name": name, "weeks": weeks,
                "course": course["short"], "store": course["store"],
                "families": course["families"],
                "qv": portal.digest(os.path.join(d, "data", "questions", "%s.json" % slug)),
                "nv": portal.digest(os.path.join(d, "data", "notes", "%s.json" % slug)),
            }
            label, fill = FAVICON[course["slug"]]
            html = PAGE.format(
                base_css=portal.asset("base.css"), portal_css=portal.asset("portal.css"),
                quiz_js=portal.asset("quiz.js"), notes_js=portal.asset("notes.js"),
                portal_js=portal.asset("portal.js"),
                name=name, course=course["short"], weeks=weeks, lead=lead, desc=desc, accent=accent,
                fonts=portal.FONTS, nocache=portal.NOCACHE, cf=portal.CF, footer=portal.footer(), howto=HOWTO, favicon=portal.favicon(label, fill),
                blocknav=blocknav(course, slug), questions=q,
                written=written, lectures=lectures,
                block_json=json.dumps(cfg, ensure_ascii=False))
            io.open(os.path.join(d, "%s.html" % slug), "w",
                    encoding="utf-8", newline="\n").write(html)
            print("%-5s %-6s %2d/%d notes  %4d questions"
                  % (course["slug"], slug, written, lectures, q))


if __name__ == "__main__":
    main()
