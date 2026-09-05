# -*- coding: utf-8 -*-
"""Regenerate index.html so the block cards always state the real counts."""

import hashlib, io, json, re


def ver(name):
    """<name>?v=<hash of its contents>.

    GitHub Pages serves these with Cache-Control: max-age=600, so for ten
    minutes after a push a browser will happily keep last deploy's stylesheet
    and paint the new markup with the old rules. Stamping the content hash into
    the URL means a changed asset is simply a different URL and lands at once.
    An unchanged one keeps its hash and stays cached.

    The hash is read off the file on disk, so re-run this after editing any of
    the hand-maintained css or js, or the pages will keep pointing at the
    previous hash. Harmless when it happens, since the query string is ignored
    by the server, but it stops busting the cache.
    """
    h = hashlib.md5(io.open(name, "rb").read()).hexdigest()[:8]
    return "%s?v=%s" % (name, h)

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


def cards():
    """both halves get the same weight on the card - the block is notes AND
       questions, and leading with the question count made it read as a quiz"""
    out = []
    for slug, n, name, weeks in BLOCKS:
        blurb, hue, q, written, lects = facts(slug)
        notes = "<b>%d</b> of %d lecture notes" % (written, lects)
        out.append(
            u'<a class="block-card" href="%s.html" style="--hue:%s">\n'
            u'<p class="bmeta">Block %d &middot; Weeks %s</p>\n'
            u'<h2>%s</h2>\n<p>%s</p>\n'
            u'<span class="tally">\n'
            u'<span>%s</span>\n'
            u'<span><b>%d</b> practice questions</span>\n'
            u'</span>\n'
            u'</a>' % (slug, hue, n, weeks, name, blurb, notes, q))
    return "\n".join(out)


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
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;'
         '9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

# room for a nav back to whatever site you hang the portal off
PILLNAV = """<nav class="pill-nav">
<a href="https://noorsimsam.com/#top">Noor</a>
<a href="https://noorsimsam.com/writing.html">Writing</a>
<a href="https://noorsimsam.com/#projects">Projects</a>
</nav>"""

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
<link rel="stylesheet" href="{base_css}">
<link rel="stylesheet" href="{pom2_css}">
<style>
:root{{--q-accent:#84223b;--q-accent-soft:#f5cdd2;--q-accent-ink:#6d1b31;}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

{pillnav}

<div class="page-hero">
<h1>PoM 2.</h1>
<p>
Each block has <strong>notes</strong> and <strong>practice questions</strong>, week by week.
Notes save to PDF if you would rather annotate them yourself.
</p>
</div>

<div class="block-grid">
{cards}
</div>

<div class="prose">

<details class="fold">
<summary>Where the notes come from</summary>
<div class="body">

<p>
They started as <strong>Maggie&rsquo;s notes</strong>, then were updated against the
<strong>official slides</strong> so they say what is actually being taught this year rather
than what was taught last year.
</p>

<p>
From there they were rewritten in <strong>Nicole&rsquo;s notes style</strong>: one note per
lecture, built to tell things apart rather than to cover everything, with
<strong>bolded keywords</strong> marking the fact that decides between two answers.
</p>

<p>
Every lecture in a block is listed whether or not it has a note yet, so the notes tab reads as
a coverage map rather than a list of what happens to be done. The ones with nothing under them
are the ones still to write.
</p>

</div>
</details>

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
<summary>Open source: customize or improve</summary>
<div class="body">

<p>
The portal is open source at
<a href="https://github.com/nsimsam/pom2" target="_blank" rel="noopener noreferrer">github.com/nsimsam/pom2</a>.
The beauty of open-source is anyone can access the work, improve it or customize it to their
needs. It&rsquo;s crowdsourced expertise that creates user-vetted products.
</p>

<p>
<strong>To customize it.</strong> Anything here can change, from the blocks it covers and
the questions in them to the wording, the layout and the tooling around it. Paste this into
Claude Code:
</p>

<p class="prompt">Clone https://github.com/nsimsam/pom2 and read the README so you understand how the portal is built. I want to make it mine: [what you want changed, for example: cut it down to the blocks I am on, import my own lecture notes and questions, restyle the pages, or build an Anki deck from only the questions I got wrong]. Work out which files that touches, make the change, and rebuild the pages with the scripts in tools/.</p>

<p>
You can also just take the material out. The questions and the notes are both plain JSON under
<code>data/</code>, so you can extract either one into whatever you already study from. Keep in
mind they are being updated week by week, so what you pull is a snapshot of that week.
</p>

<p>
<strong>To improve it.</strong> Suggest a feature, fix an answer you think is wrong, or send
in questions of your own. You need a GitHub account; Claude Code can do the rest. Paste
this into it:
</p>

<p class="prompt">Clone https://github.com/nsimsam/pom2 and read the README so you understand how the portal is built. I want to contribute: [what you are adding, for example: the questions from the week 8 MSK module, a correction to an answer, or a feature]. Match the format the existing files use, rebuild the pages with the scripts in tools/, then create a branch, commit, and open a pull request against nsimsam/pom2 explaining what changed and why.</p>

<p>
Corrections and questions are the two most useful things to send.
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
    html = TEMPLATE.format(base_css=ver('base.css'), pom2_css=ver('pom2.css'), fonts=FONTS, cf=CF, cards=cards(), pillnav=PILLNAV)
    io.open("index.html", "w", encoding="utf-8", newline="\n").write(html)
    print("index.html: %d/%d lectures written, %d questions" % (tw, tl, tq))


if __name__ == "__main__":
    main()
