# -*- coding: utf-8 -*-
"""Build the portal's front door: one card per course, with real counts.

Purpose: the root landing page of the pre-clerkship portal.
Author:  Noor Sims
Date:    2026-09-21
Input:   tools/portal.py and each course's data/
Output:  index.html

Run from the repo root, last. A course with nothing in it still gets a card,
greyed and unlinked, saying so - the portal shows the gap rather than hiding it,
which is the same reason a lecture with no note still renders on the notes tab.
"""

import io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal


def cards():
    out = []
    for c in portal.COURSES:
        q, w, l = portal.counts(c)
        if not c["blocks"]:
            out.append(
                u'<div class="block-card is-empty" style="--hue:%s">\n'
                u'<p class="bmeta">%s</p>\n'
                u'<h2>%s</h2>\n<p>%s</p>\n'
                u'<span class="tally"><span>not built yet</span></span>\n'
                u'</div>' % (c["accent"], c["year"], c["name"], c["blurb"]))
            continue
        notes = (u'<span><b>%d</b> of %d lecture notes</span>' % (w, l)) if l else u''
        out.append(
            u'<a class="block-card" href="%s/index.html" style="--hue:%s">\n'
            u'<p class="bmeta">%s &middot; %d blocks</p>\n'
            u'<h2>%s</h2>\n<p>%s</p>\n'
            u'<span class="tally">\n%s\n'
            u'<span><b>%s</b> practice questions</span>\n'
            u'</span>\n'
            u'</a>' % (c["slug"], c["accent"], c["year"], len(c["blocks"]),
                       c["name"], c["blurb"], notes, "{:,}".format(q)))
    return "\n".join(out)


def totals():
    q = w = l = 0
    for c in portal.COURSES:
        a, b, d = portal.counts(c)
        q += a; w += b; l += d
    return q, w, l


TEMPLATE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pre-clerkship</title>
<meta name="description" content="Notes and practice questions for the pre-clerkship years at Schulich: Foundations of Medicine, Principles of Medicine 1 and 2, and Transition to Clerkship.">
<meta name="robots" content="noindex, nofollow">
{favicon}

{fonts}
<link rel="stylesheet" href="{base_css}">
<link rel="stylesheet" href="{portal_css}">
<style>
:root{{--q-accent:#1f4e5f;--q-accent-soft:#dfecf0;--q-accent-ink:#193f4d;}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

<nav class="pill-nav">
<a href="https://noorsimsam.com/#top">Noor</a>
<a href="https://noorsimsam.com/writing.html">Writing</a>
<a href="https://noorsimsam.com/#projects">Projects</a>
</nav>

<div class="page-hero">
<h1>Pre-clerkship.</h1>
<p>
{total} practice questions across the pre-clerkship years, filed by week and by where
they came from, with a <strong>notes</strong> tab per course listing every lecture in it
so what is written up and what is not are both visible. Progress saves per course, on
your own device.
</p>
</div>

<div class="block-grid">
{cards}
</div>

<div class="prose">

<details class="fold">
<summary>What is here, and what is not</summary>
<div class="body">

<p>
Four courses, two of them still empty. <strong>Foundations of Medicine</strong> and
<strong>Principles of Medicine 2</strong> are built. <strong>Principles of Medicine 1</strong>
and <strong>Transition to Clerkship</strong> have cards and nothing behind them.
</p>

<p>
They are listed anyway. The portal's habit throughout is to show the shape of the whole
thing and mark the gaps: a lecture with no note still appears on the notes tab, greyed;
a question set with nothing in it still appears in the filter rail, saying so. A course
with nothing in it is the same idea one level up.
</p>

</div>
</details>

<details class="fold">
<summary>Where the questions come from</summary>
<div class="body">

<p>
No AI-generated trivia. Every question traces back to a source in the curriculum, keeps
the set it arrived in, and can be filtered by that set. Each course lists its own sources
on its own page, because they differ: Foundations draws on the class question banks and
the Pre-Clerkship Workbook, Principles of Medicine 2 on the Elentra modules, the weekly
quizzes, the workbook and the case sessions.
</p>

<p>
Where a bank handed between years has a gap or an error, it is flagged on the face of the
question rather than quietly patched, so you can see what you are trusting before you
trust it.
</p>

</div>
</details>

<details class="fold">
<summary>Progress stays on your device</summary>
<div class="body">

<p>
Answers, stars and per-lecture accuracy are written to your browser's local storage, under
a separate key per course, so the courses never read or overwrite each other. Nothing is
sent anywhere and there is no backend. The flip side is that it does not follow you between
browsers or machines, so each course's questions tab has <strong>Download all my
progress</strong> and <strong>Restore from a file</strong> to move a JSON file by hand.
</p>

</div>
</details>

</div>

{footer}

</div>

</body>
</html>
"""


def main():
    q, w, l = totals()
    html = TEMPLATE.format(
        favicon=portal.favicon("PC", "1f4e5f"), fonts=portal.FONTS,
        base_css="base.css?v=" + portal.digest("base.css"),
        portal_css="portal.css?v=" + portal.digest("portal.css"),
        cf=portal.CF, total="{:,}".format(q), cards=cards(), footer=portal.footer())
    io.open("index.html", "w", encoding="utf-8", newline="\n").write(html)
    print("index.html: %d courses, %d built, %d questions, %d/%d lecture notes"
          % (len(portal.COURSES),
             len([c for c in portal.COURSES if c["blocks"]]), q, w, l))


if __name__ == "__main__":
    main()
