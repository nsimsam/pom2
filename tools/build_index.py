# -*- coding: utf-8 -*-
"""Regenerate index.html so the block cards always state the real counts."""

import io, json, re

BLOCKS = [
    ("endo",  1, u"Endocrinology",   u"1–3"),
    ("repro", 2, u"Reproduction",    u"4–6"),
    ("msk",   3, u"Musculoskeletal", u"7–11"),
    ("neuro", 4, u"Neurology",       u"12–16"),
    ("psych", 5, u"Psychiatry",      u"17–20"),
]


def facts(slug):
    page = io.open("%s.html" % slug, encoding="utf-8").read()
    blurb = re.search(r'<p class="lead">\s*(.*?)\s*</p>', page, re.S).group(1)
    hue = re.search(r'--q-accent:(#\w+);', page).group(1)
    qs = json.load(io.open("data/questions/%s.json" % slug, encoding="utf-8"))
    nt = json.load(io.open("data/notes/%s.json" % slug, encoding="utf-8"))
    lects = [l for w in nt["weeks"] for l in w["lectures"]]
    written = len([l for l in lects if l.get("hasNote")])
    return blurb, hue, len(qs), written, len(lects)


def wspan(weeks):
    """how many weeks a block runs, so the year bar can be drawn to scale"""
    a, b = weeks.split(u"–")
    return int(b) - int(a) + 1


YEAR_SEG = (u'<a class="yseg" href="%s.html" style="--hue:%s;--w:%d" '
            u'aria-label="Block %d, %s, weeks %s to %s">%s&ndash;%s</a>')

YEAR = u"""<figure class="year">
<figcaption>The teaching year, twenty weeks</figcaption>
<div class="yearbar">
%s
</div>
</figure>"""

ROW = u"""<li class="brow" style="--hue:%s">
<a href="%s.html">
<span class="bnum">%02d</span>
<span class="bhead"><span class="bname">%s</span><span class="bweeks">weeks %s&ndash;%s</span></span>
<p class="bblurb">%s</p>
<span class="bstats">
<span><b>%d</b> of %d notes</span>
<span><b>%d</b> questions</span>
</span>
</a>
</li>"""


def year():
    """each block's segment is as wide as the number of weeks it runs, so the
       bar is a drawing of the year rather than five equal tiles"""
    segs = []
    for slug, n, name, weeks in BLOCKS:
        first, last = weeks.split(u"–")
        _b, hue, _q, _w, _l = facts(slug)
        segs.append(YEAR_SEG % (slug, hue, wspan(weeks), n, name,
                                first, last, first, last))
    return YEAR % chr(10).join(segs)


def rows():
    """both counts get the same weight - the block is notes AND questions, and
       leading with the question count made it read as a quiz"""
    out = []
    for slug, n, name, weeks in BLOCKS:
        blurb, hue, q, written, lects = facts(slug)
        first, last = weeks.split(u"–")
        out.append(ROW % (hue, slug, n, name, first, last, blurb,
                          written, lects, q))
    return chr(10).join(out)


def totals():
    tq = tw = tl = 0
    for slug, _n, _name, _w in BLOCKS:
        _b, _h, q, w, l = facts(slug)
        tq += q; tw += w; tl += l
    return tq, tw, tl


# the portal ships without analytics; drop your own snippet in here if you want it
CF = ""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600'
         '&display=swap" rel="stylesheet">')

# room for a nav back to whatever site you hang the portal off
PILLNAV = ""

TEMPLATE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PoM 2</title>
<meta name="description" content="Notes and practice questions for the five blocks of Schulich's second Principles of Medicine year.">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%2384223b'/><text x='16' y='23' font-family='Georgia,serif' font-size='17' font-weight='600' fill='%23ffffff' text-anchor='middle'>P2</text></svg>">

{fonts}
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="pom2.css">
<style>
:root{{--q-accent:#84223b;--q-accent-soft:#f5cdd2;--q-accent-ink:#6d1b31;}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

{pillnav}

<div class="page-hero">
<p class="eyebrow">Principles of Medicine 2</p>
<h1>PoM 2</h1>
<p>
Each block has <strong>notes</strong> and <strong>practice questions</strong>, week by week.
Notes save to PDF if you would rather annotate them yourself.
</p>
</div>

{year}

<ol class="blocks">
{rows}
</ol>

<div class="prose">

<details class="fold">
<summary>Where the practice questions come from</summary>
<div class="body">

<ul>
<li><strong>Course modules.</strong> Elentra knowledge checks, the concept checks in the lecture slides, and the weekly quizzes.</li>
<li><strong>Pre-Clerkship Workbook.</strong> The 2023 student bank handed down through the Schulich classes of 2015&ndash;2025. Peer-written, so its errors are flagged on the question.</li>
<li><strong>Meds 2029.</strong> Questions written from the patient cases in the modules, the DSSGs and the in-class sessions.</li>
<li><strong>Schulich Reviews.</strong> Both the practice questions and the summary content. TBD.</li>
</ul>

<p>
Anything without a real answer key says so on its face, and the handful of questions that
cannot be scored are marked <em>not scored</em> rather than given an invented letter.
</p>

<p>
What they are written to, from the syllabus:
</p>

<blockquote>
<p>
Most of the questions will involve clinical scenarios which will assess clinical decision
making around: <strong>localization, differential diagnosis, ordering appropriate
investigations, or management</strong> of the patient. The questions will not be simple
recall questions, and the student will need to apply foundational knowledge to clinical
scenarios.
</p>
</blockquote>

<p>
And on integrating across blocks:
</p>

<blockquote>
<p>
As outlined in the syllabus, approximately <strong>20% of Progress Test #2</strong> will
consist of <strong>integration questions</strong>. These may require you to draw on
foundational knowledge from <strong>FOM, P1, and the first half of P2</strong> to reason
through a <strong>new MCC-style clinical presentation</strong>. The purpose is not to
re-examine previous blocks, but to assess your ability to <strong>apply previously learned
knowledge in a new clinical context</strong>.
</p>
<p>
When preparing, think broadly about <strong>clinical presentations</strong> rather than
focusing only on the body system currently being taught. You should be able to
<strong>integrate knowledge across systems</strong> and consider appropriate
<strong>differential diagnoses</strong>. Examples include <strong>abdominal pain</strong>,
<strong>shortness of breath</strong>, <strong>cardiac rhythm disturbances</strong>,
<strong>anemia</strong>, <strong>pulmonary embolism</strong>, and <strong>deep vein
thrombosis</strong>.
</p>
</blockquote>

</div>
</details>

<details class="fold">
<summary>Customize it to your own learning</summary>
<div class="body">

<p>
The portal is open source at
<a href="https://github.com/nsimsam/pom2" target="_blank" rel="noopener noreferrer">github.com/nsimsam/pom2</a>.
</p>

<p>
Clone it and point Claude Code at the folder. The JSON is structured enough to build study
tooling on. Anki is one use: the portal records which questions you got wrong, so a skill
can generate cards from those alone, rather than from an inherited deck built around
someone else&rsquo;s gaps. Importing your own course material into the question format is a
similar job.
</p>

</div>
</details>

</div>

<footer>
Grown by Noor &#127793; &middot; <a href="https://github.com/nsimsam/pom2" target="_blank" rel="noopener noreferrer">Source on GitHub</a>
</footer>

</div>

</body>
</html>
"""


def main():
    tq, tw, tl = totals()
    html = TEMPLATE.format(fonts=FONTS, cf=CF, year=year(), rows=rows(),
                           pillnav=PILLNAV)
    io.open("index.html", "w", encoding="utf-8", newline="\n").write(html)
    print("index.html: %d/%d lectures written, %d questions" % (tw, tl, tq))


if __name__ == "__main__":
    main()
