# -*- coding: utf-8 -*-
"""Regenerate the five PoM 2 block pages.

Every page is the same shell, so it is generated rather than hand-copied: the
block's name, blurb, accent and two counts are the only things that differ.
Blurbs and accents are read back out of the pages being replaced so nothing
written by hand is lost.
"""

import io, json, os, re

BLOCKS = [
    # slug,  n, name,             weeks
    ("endo",  1, u"Endocrinology",   u"1–3"),
    ("repro", 2, u"Reproduction",    u"4–6"),
    ("msk",   3, u"Musculoskeletal", u"7–11"),
    ("neuro", 4, u"Neurology",       u"12–16"),
    ("psych", 5, u"Psychiatry",      u"17–20"),
]

# the portal ships without analytics; drop your own snippet in here if you want it
CF = ""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;'
         '9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

# room for a nav back to whatever site you hang the portal off
PILLNAV = ""

FOOTER = ("<footer>\nGrown by Noor &#127793; &middot; "
          "<a href=\"https://github.com/nsimsam/pom2\" target=\"_blank\" rel=\"noopener noreferrer\">"
          "Source on GitHub</a>\n</footer>")

# said once here, rendered into every block page
HOWTO = """<details class="howto">
<summary>You can save your progress</summary>
<div class="body">
<p><strong>On this device, and nowhere else.</strong> What you have answered is written to
your browser&rsquo;s local storage. It is never sent to this site, never stored in its
repository, and nobody else can see it, not even me.</p>
<p>That also means it does not follow you. A different browser, a different laptop, or
clearing your site data all start from zero.</p>
<p><strong>To carry it with you:</strong> press <strong>Download my progress</strong> in the
panel on the left and keep the JSON file it writes. On the other machine, open this same page
and press <strong>Restore from a file</strong> to pick up where you left off. Doing that now
and then is also the only backup there is.</p>
</div>
</details>"""


def existing(slug):
    """pull the blurb and accent trio out of the page we are about to replace"""
    p = "%s.html" % slug
    s = io.open(p, encoding="utf-8").read()
    lead = re.search(r'<p class="lead">\s*(.*?)\s*</p>', s, re.S).group(1)
    desc = re.search(r'<meta name="description" content="(.*?)">', s, re.S).group(1)
    accent = re.search(r'(--q-accent:.*?;--q-accent-soft:.*?;--q-accent-ink:.*?;)', s).group(1)
    return lead, desc, accent


def counts(slug):
    qs = json.load(io.open("data/questions/%s.json" % slug, encoding="utf-8"))
    nt = json.load(io.open("data/notes/%s.json" % slug, encoding="utf-8"))
    lects = [l for w in nt["weeks"] for l in w["lectures"]]
    written = len([l for l in lects if l.get("hasNote")])
    return len(qs), written, len(lects)


def blocknav(active):
    rows = ['<a class="home" href="index.html">All blocks</a>']
    for slug, n, name, _w in BLOCKS:
        cls = ' class="here"' if slug == active else ''
        rows.append('<a href="%s.html"%s>%d &middot; %s</a>' % (slug, cls, n, name))
    return "\n".join(rows)


PAGE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} &middot; PoM 2</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%2384223b'/><text x='16' y='23' font-family='Georgia,serif' font-size='17' font-weight='600' fill='%23ffffff' text-anchor='middle'>P2</text></svg>">

{fonts}
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="pom2.css">
<style>
:root{{{accent}}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

{pillnav}
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
<div class="score"><b id="sc-first">&ndash;</b><span>First try</span></div>
<div class="score is-bad"><b id="sc-wrong">0</b><span>Wrong now</span></div>
<div class="score is-star"><b id="sc-star">0</b><span>Starred</span></div>
</div>
</header>

<div class="tabs" role="tablist" aria-label="Notes or questions">
<button type="button" id="tab-notes" role="tab" aria-selected="true" aria-controls="panel-notes">Notes <span class="tc" id="tc-notes">{written}/{lectures}</span></button>
<button type="button" id="tab-questions" role="tab" aria-selected="false" aria-controls="panel-questions">Practice questions <span class="tc">{questions}</span></button>
</div>

<div class="q-shell" id="panel-notes" role="tabpanel" aria-labelledby="tab-notes">
<aside class="rail">

<section>
<p class="panel-h">Coverage</p>
<div class="chips" id="cov-chips"></div>
</section>

<section>
<p class="panel-h">Save as PDF</p>
<button class="print-cta" id="print-all" type="button" disabled>Save every note as one PDF</button>
<p class="railnote">Each note has its own <strong>PDF</strong> button, and each week can be
saved in one go. Print it, annotate it, keep it.</p>
</section>

<section>
<p class="panel-h">What these are</p>
<p class="railnote">One note per lecture, built to tell things apart rather than to cover
everything. <strong>Bold marks the fact that decides between two answers</strong>.
Every lecture in the block is listed, so the ones with nothing under them yet are the ones
still to write.</p>
</section>

</aside>

<main class="stream" id="note-stream">
<div class="q-loading">Loading notes&hellip;</div>
</main>
</div>

<div class="q-shell" id="panel-questions" role="tabpanel" aria-labelledby="tab-questions" hidden>

{howto}

<aside class="rail">

<button class="review-cta" id="review-wrong" type="button" disabled>Review wrong only <span class="n" id="review-n">0</span></button>

<section>
<p class="panel-h">Question set</p>
<div class="fams" id="fam-btns"></div>
</section>

<section>
<p class="panel-h">Status</p>
<div class="chips" id="status-chips"></div>
</section>

<section>
<p class="panel-h">Progress</p>
<p class="storenote" id="storenote" hidden></p>
<div class="resets">
<button class="backup-btn" id="export-progress" type="button">Download my progress</button>
<button class="backup-btn" id="import-progress" type="button">Restore from a file</button>
<input type="file" id="import-file" accept="application/json,.json" hidden>
<button class="danger" id="reset-shown" type="button" disabled>Reset the questions shown (0)</button>
<button class="danger" id="reset-all" type="button">Reset all progress</button>
</div>
</section>

</aside>

<main class="stream" id="stream">
<div class="q-loading">Loading {questions} questions&hellip;</div>
</main>
</div>

<script>
window.QUIZ_BLOCK = {{"slug": "{slug}", "n": {n}, "name": "{name}", "weeks": "{weeks}"}};
</script>
<script src="quiz.js"></script>
<script src="notes.js"></script>
<script src="pom2.js"></script>

{footer}

</div>

</body>
</html>
"""


def main():
    for slug, n, name, weeks in BLOCKS:
        lead, desc, accent = existing(slug)
        q, written, lectures = counts(slug)
        html = PAGE.format(slug=slug, n=n, name=name, weeks=weeks, lead=lead, desc=desc,
                           accent=accent, fonts=FONTS, cf=CF, footer=FOOTER,
                           pillnav=PILLNAV, howto=HOWTO,
                           blocknav=blocknav(slug), questions=q,
                           written=written, lectures=lectures)
        io.open("%s.html" % slug, "w", encoding="utf-8", newline="\n").write(html)
        print("%-6s %2d/%d notes  %3d questions" % (slug, written, lectures, q))


if __name__ == "__main__":
    main()
