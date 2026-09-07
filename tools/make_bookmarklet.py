# -*- coding: utf-8 -*-
"""Turn tools/elentra_grab.js into a bookmarklet.

Two things come out, both in build/:

  * `elentra-grab.bookmarklet.txt`, the raw `javascript:` URL, for pasting into
    a bookmark's address field by hand.
  * `elentra-grab.bookmarklet.html`, a page holding one draggable link, which is
    the only sane way to install a bookmarklet in Chrome.

The minifier is deliberately timid. It strips comments and indentation and
nothing else - no statement joining, no renaming - because a bookmarklet that
mangles under a clever minifier fails silently on a page you cannot debug from.
Newlines survive as %0A, so automatic semicolon insertion behaves exactly as it
does in the readable source.
"""

import io, os, re, sys
try:
    from urllib.parse import quote          # py3
except ImportError:
    from urllib import quote                # py2

SRC = os.path.join("tools", "elentra_grab.js")
OUT = "build"

# everything a bookmarklet URL can carry unescaped
SAFE = "!$&'()*+,-./:;=?@[]_~"


def strip_line_comment(line):
    """Cut a trailing // comment, respecting quotes and regex literals."""
    i, n = 0, len(line)
    quote_ch = None
    while i < n:
        c = line[i]
        if quote_ch:
            if c == "\\":
                i += 2
                continue
            if c == quote_ch:
                quote_ch = None
        elif c in "\"'":
            quote_ch = c
        elif c == "/" and i + 1 < n:
            nxt = line[i + 1]
            if nxt == "/":
                return line[:i]
            if nxt == "*":                  # block comments are gone by now
                return line[:i]
        i += 1
    return line


def minify(js):
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    out = []
    for line in js.split("\n"):
        line = strip_line_comment(line).strip()
        if line:
            out.append(line)
    return "\n".join(out)


def main():
    js = io.open(SRC, encoding="utf-8").read()
    small = minify(js)
    url = "javascript:" + quote(small, safe=SAFE)

    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    txt = os.path.join(OUT, "elentra-grab.bookmarklet.txt")
    io.open(txt, "w", encoding="utf-8", newline="\n").write(url + "\n")

    page = os.path.join(OUT, "elentra-grab.bookmarklet.html")
    io.open(page, "w", encoding="utf-8", newline="\n").write(
        u'<!doctype html>\n<meta charset="utf-8">\n'
        u'<title>Grab quiz - install</title>\n'
        u'<style>body{font:16px/1.6 ui-sans-serif,system-ui,sans-serif;'
        u'max-width:38rem;margin:4rem auto;padding:0 1.5rem;color:#1d2530}'
        u'a.bm{display:inline-block;background:#22303f;color:#fff;'
        u'text-decoration:none;padding:.5rem 1rem;border-radius:8px;'
        u'font-weight:600;cursor:grab}code{background:#eef2f6;padding:0 .25em;'
        u'border-radius:3px}ol{padding-left:1.2rem}</style>\n'
        u'<h1>Grab quiz</h1>\n'
        u'<p>Drag this button onto the bookmarks bar. Clicking it here does '
        u'nothing useful - it only works on an Elentra exam page.</p>\n'
        u'<p><a class="bm" href="%s">Grab quiz</a></p>\n'
        u'<ol><li>Sit the weekly quiz in Elentra and submit it.</li>\n'
        u'<li>Open the review view, the one that shows the correct answers.</li>\n'
        u'<li>Click <b>Grab quiz</b>. A panel appears bottom right.</li>\n'
        u'<li>If the review is paginated, click it again on every page - '
        u'captures accumulate under the one exam id.</li>\n'
        u'<li>Press <b>Download JSON</b>, then run '
        u'<code>python tools/elentra_quiz.py &lt;the file&gt;</code>.</li></ol>\n'
        % url.replace(u"&", u"&amp;").replace(u'"', u"&quot;"))

    print("bookmarklet: %d chars" % len(url))
    print("  %s" % txt)
    print("  %s  (open it and drag the button)" % page)


if __name__ == "__main__":
    sys.exit(main())
