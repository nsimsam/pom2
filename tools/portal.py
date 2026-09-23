# -*- coding: utf-8 -*-
"""What the portal is built from: the block roster and the shared helpers.

Purpose: hold the course roster, the block-page template and the cache-busting
         helpers in one place.
Author:  Noor Sims
Date:    2026-09-22

This is the Principles of Medicine 2 site at noorsimsam.com/pom2/, which is
being retired on 2026-10-01. It carries one course and that course sits at the
repo root, so `dir` is "." and the pages name the engine without a prefix.

The four-course pre-clerkship hub this grew into lives on in its own repo
(schulichmedfriend/preclerkship), where a course is a directory one level down
and build_hub.py builds the front door over the top. Both layouts ran off this
file; what is left here is the single-course half of it.
"""

import hashlib
import io
import json
import os

# Progress is keyed in localStorage under this prefix, block by block. It is the
# prefix the site has always used, so a browser part way through keeps its
# answers - and so the file the questions tab exports is the one the new site
# imports.
COURSES = [
    {
        "slug": "pom2",
        "dir": ".",
        "short": u"PoM 2",
        "name": u"Principles of Medicine 2",
        "year": u"Year 2",
        "blurb": u"The five blocks of second year, with a written note for every "
                 u"lecture that has one and a coverage map for the rest.",
        "accent": u"#84223b",
        "store": "nsq.v1.",
        "blocks": [
            ("endo",  1, u"Endocrinology",   u"1–3"),
            ("repro", 2, u"Reproduction",    u"4–6"),
            ("msk",   3, u"Musculoskeletal", u"7–11"),
            ("neuro", 4, u"Neurology",       u"12–16"),
            ("psych", 5, u"Psychiatry",      u"17–20"),
        ],
        "families": [
            {"key": "module", "name": u"Course modules",
             "blurb": u"The Elentra module knowledge checks and the concept checks on the "
                      u"lecture slides. Cases live under Meds 2029 instead, wherever they "
                      u"came from."},
            {"key": "weekly", "name": u"Weekly quizzes",
             "blurb": u"The weekly quizzes, both the Microsoft Forms ones and the ones sat "
                      u"in Elentra. Kept whole as their own set, so a week's quiz can be "
                      u"drilled the way it was written."},
            {"key": "workbook", "name": u"Pre-Clerkship Workbook",
             "blurb": u"The Pre-Clerkship Workbook (2023 edition), the student bank passed "
                      u"down through the Schulich classes of 2015-2025. It has a written "
                      u"key, but the key is peer-written and contains real errors. Every "
                      u"one found is flagged on the question."},
            {"key": "meds2029", "name": u"Meds 2029",
             "blurb": u"Questions built from patient cases in the modules, DSSGs and "
                      u"in-class lectures, since exams tend to recycle similar cases."},
            {"key": "reviews", "name": u"Schulich Reviews",
             "blurb": u"The Schulich Reviews sessions, both their practice questions and "
                      u"their summary content. TBD."},
        ],
    },
]

BY_SLUG = dict((c["slug"], c) for c in COURSES)


def cdir(course):
    """The directory a course's pages and data live in, "." here."""
    return course.get("dir", course["slug"])

# the engine, shared by every course and living at the repo root
ASSETS = ["base.css", "portal.css", "portal.js", "quiz.js", "notes.js"]


def digest(path):
    """The content hash of a file, for cache busting."""
    return hashlib.md5(io.open(path, "rb").read()).hexdigest()[:8]


def asset(name):
    """<name>?v=<hash>, as a page beside the engine refers to it.

    Static hosts serve these with a cache lifetime of several minutes, long
    enough for a browser to paint new markup with last deploy's rules. Stamping
    the content hash into the URL makes a changed file a different URL; an
    unchanged one keeps its hash and stays cached. Re-run the builders after
    editing any of the hand-maintained css or js, or the pages keep pointing at
    the previous hash.
    """
    return "%s?v=%s" % (name, digest(name))


def counts(course):
    """(questions, notes written, lectures) for a course, from its own data."""
    d = cdir(course)
    q = w = l = 0
    for slug, _n, _name, _weeks in course["blocks"]:
        qp = os.path.join(d, "data", "questions", "%s.json" % slug)
        np = os.path.join(d, "data", "notes", "%s.json" % slug)
        if os.path.exists(qp):
            q += len(json.load(io.open(qp, encoding="utf-8")))
        if os.path.exists(np):
            lects = [x for wk in json.load(io.open(np, encoding="utf-8"))["weeks"]
                     for x in wk["lectures"]]
            l += len(lects)
            w += len([x for x in lects if x.get("hasNote")])
    return q, w, l


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;'
         '9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

# The CSS, JS and JSON are all content-hashed, so the browser may cache them
# forever. The pages that name those hashes must NOT be cached that way, or a
# rebuild is invisible until someone thinks to hard-refresh - which is exactly
# what happened. "no-cache" is not "don't store": it stores the page and asks
# whether it changed, so an unchanged page still costs one 304 and no download.
NOCACHE = ('<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">\n'
           '<meta http-equiv="Pragma" content="no-cache">')

# the portal ships without analytics; drop your own snippet in here if you want it
CF = ""


# Where "All courses" points. Absolute, not relative: the portal is served from
# more than one place, and the hub every page should return to is this one
# wherever the copy being read happens to live.
HUB_URL = "https://schulichmedfriend.github.io/preclerkship/"


def uplink(depth=None):
    """The one way back up to the hub, for pages that have no block nav."""
    return '<a class="uplink" href="%s">&larr; All courses</a>' % HUB_URL


def footer():
    return "<footer>\nGrown by Noor &#127793;\n</footer>"


def favicon(label="PC", fill="1f4e5f"):
    return ("<link rel=\"icon\" href=\"data:image/svg+xml,"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
            "<rect width='32' height='32' rx='7' fill='%%23%s'/>"
            "<text x='16' y='23' font-family='Georgia,serif' font-size='%d' "
            "font-weight='600' fill='%%23ffffff' text-anchor='middle'>%s</text>"
            "</svg>\">" % (fill, 17 if len(label) < 3 else 13, label))
