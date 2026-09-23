# -*- coding: utf-8 -*-
"""Regenerate each course's landing page so its cards state the real counts.

Purpose: build one landing page per course from the shared shell, keeping the
         hand-written prose that already sits on the page.
Author:  Noor Sims
Date:    2026-09-21
Input:   tools/portal.py, each course's data/ and block pages, and the landing
         page being replaced (for its hero blurb and its prose section)
Output:  <course>/index.html

Run from the repo root, after build_pages.py. The prose under each landing page
is read back out of the page being replaced rather than held here, for the same
reason the block pages keep their own blurbs: it is written by hand, it is long,
and a rebuild must not quietly revert it. A course with no page yet gets the
seed below, which is deliberately thin - it is a placeholder saying the course
is not built, not a pretence that it is.
"""

import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal

FAVICON = {"pom2": ("P2", "84223b")}

EMPTY_PROSE = u"""<div class="prose">

</div>"""


def part(page, opener, closer="\n</div>"):
    i = page.index(opener)
    j = page.index(closer, i)
    return page[i:j + len(closer)]


def existing(course):
    """(hero blurb, prose block) from the page being replaced, or the seed."""
    p = os.path.join(portal.cdir(course), "index.html")
    if not os.path.exists(p):
        return course["blurb"], EMPTY_PROSE
    s = io.open(p, encoding="utf-8").read()
    hero = re.search(r'<div class="page-hero">\s*<h1>.*?</h1>\s*(.*?)\s*</div>', s, re.S)
    prose = part(s, '<div class="prose">')
    return (hero.group(1) if hero else course["blurb"]), prose


def cards(course):
    """Both halves get the same weight: a block is notes AND questions, and
       leading with the question count made it read as a quiz."""
    out = []
    for slug, n, name, weeks in course["blocks"]:
        page = io.open(os.path.join(portal.cdir(course), "%s.html" % slug),
                       encoding="utf-8").read()
        blurb = re.search(r'<p class="lead">\s*(.*?)\s*</p>', page, re.S).group(1)
        hue = re.search(r'--q-accent:(#\w+);', page).group(1)
        import json
        qs = json.load(io.open(os.path.join(portal.cdir(course), "data", "questions",
                                            "%s.json" % slug), encoding="utf-8"))
        nt = json.load(io.open(os.path.join(portal.cdir(course), "data", "notes",
                                            "%s.json" % slug), encoding="utf-8"))
        lects = [l for w in nt["weeks"] for l in w["lectures"]]
        written = len([l for l in lects if l.get("hasNote")])
        out.append(
            u'<a class="block-card" href="%s.html" style="--hue:%s">\n'
            u'<p class="bmeta">Block %d &middot; Weeks %s</p>\n'
            u'<h2>%s</h2>\n<p>%s</p>\n'
            u'<span class="tally">\n'
            u'<span><b>%d</b> of %d lecture notes</span>\n'
            u'<span><b>%d</b> practice questions</span>\n'
            u'</span>\n'
            u'</a>' % (slug, hue, n, weeks, name, blurb, written, len(lects), len(qs)))
    return "\n".join(out)


TEMPLATE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{short}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
{favicon}

{nocache}
{fonts}
<link rel="stylesheet" href="{base_css}">
<link rel="stylesheet" href="{portal_css}">
<style>
:root{{--q-accent:{accent};--q-accent-soft:#e6e6e6;--q-accent-ink:{accent};}}
</style>
{cf}
</head>
<body>

<div class="pom2-page">

<div class="movebar">
<p>
<strong class="lead">Starting October&nbsp;1, 2026 this site moves to
<a href="https://schulichmedfriend.github.io/preclerkship/">schulichmedfriend.github.io/preclerkship/</a>.</strong>
It is the same portal with the other pre-clerkship years alongside this one, run by the
Open-Source Medicine and AI in Medicine clubs. This address stops being updated then.
</p>
<p>
<strong class="lead">Your progress can come with you.</strong> It is saved in this browser,
and the new site cannot read it from here, so carry it across: open any block, go to
<strong>Practice questions</strong>, and press <strong>Download all my progress</strong> to
save the JSON file. On the new site press <strong>Restore from a file</strong> and pick it.
One file holds every block, and a restore only adds and updates, so nothing you have already
answered is lost.
</p>
</div>

{uplink}

<div class="page-hero">
<h1>{short}.</h1>
{hero}
</div>

<div class="block-grid">
{cards}
</div>

{prose}

{footer}

</div>

</body>
</html>
"""


def main():
    for course in portal.COURSES:
        hero, prose = existing(course)
        label, fill = FAVICON[course["slug"]]
        html = TEMPLATE.format(
            short=course["short"], desc=course["blurb"],
            favicon=portal.favicon(label, fill), fonts=portal.FONTS, nocache=portal.NOCACHE,
            base_css=portal.asset("base.css"), portal_css=portal.asset("portal.css"),
            accent=course["accent"], cf=portal.CF, uplink=portal.uplink(1),
            hero=hero, cards=cards(course) or "", prose=prose, footer=portal.footer())
        io.open(os.path.join(portal.cdir(course), "index.html"), "w",
                encoding="utf-8", newline="\n").write(html)
        q, w, l = portal.counts(course)
        print("%-5s %d blocks  %d/%d lecture notes  %d questions"
              % (course["slug"], len(course["blocks"]), w, l, q))


if __name__ == "__main__":
    main()
