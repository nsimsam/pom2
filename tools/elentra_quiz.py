# -*- coding: utf-8 -*-
"""Turn a Grab-quiz capture into a Weekly Quizzes note fragment.

    python tools/make_bookmarklet.py                 # build the bookmark, once
    python tools/elentra_quiz.py elentra-3007-*.json --topic endo --week 3

Reads the JSON the bookmarklet downloads and writes house-format markdown into
build/ - a `#### <lecture>` group of `# N` questions with their answer callouts,
ready to drop into the week's section of `Weekly Quizzes - <topic>.md`.

It writes a fragment rather than the note itself on purpose. The note is a vault
file that other sessions are also editing, and its `## Week N` sections and the
Coverage callout are hand-kept; splicing into that blind is how a week's work
gets clobbered. Pass `--note` and the numbering picks up from where the real
note leaves off, so the fragment drops in without renumbering anything.

Two things the grab cannot decide and this cannot either:

  * **A question with no detected key** gets the `> [!red] No official answer
    key` scaffold, not a guess. Run with `--inspect` to see what class names sat
    around each option; if Elentra marks the key some way the grab does not
    recognise, that listing is what says so.
  * **Select-all and short-answer questions** come through in their original
    shape with the rewrite flagged. House rules say every banked question is MCQ
    or true/false, and turning a select-all into a combinations MCQ is a writing
    job, not a parsing one.
"""

import io, json, os, re, sys

try:
    from html import unescape                       # py3
except ImportError:
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

OUT = "build"

SLUG = {
    "endo": "endo", "endocrinology": "endo",
    "repro": "repro", "reproduction": "repro",
    "msk": "msk", "neuro": "neuro", "neurology": "neuro",
    "psych": "psych", "psychiatry": "psych",
}
TOPIC = {
    "endo": "Endocrinology", "repro": "Repro", "msk": "MSK",
    "neuro": "Neurology", "psych": "Psychiatry",
}

RX_QPREFIX = re.compile(
    r"^\s*(?:question|item|q)\s*#?\s*\d+(?:\s+of\s+\d+)?\s*[.:)\-]?\s*", re.I)
RX_WEEK = re.compile(r"week\s*(\d+)", re.I)
RX_OPTLETTER = re.compile(r"^\s*[\(\[]?[A-Ha-h][\)\].:,\-]\s+")
RX_KEYLINE = re.compile(
    r"^\s*(?:the\s+)?correct\s+(?:answer|response|option)(?:\s+is)?\s*"
    r"[:\-]?\s*[\(\[]?[A-H][\)\]]?[.:]?\s*", re.I)


# ---------------------------------------------------------------- html to md

def emphasis(mark):
    """<strong>x</strong> -> **x**, but <strong></strong> -> nothing.

    Stripping the options out of a stem leaves plenty of empty wrappers behind,
    and a stray `**` swallows the next real one for the rest of the line.
    """
    def sub(m):
        inner = m.group(2).strip()
        return (mark + inner + mark) if inner else ""
    return sub


def md(html, oneline=False):
    """Inline HTML as the vault writes it. Unknown tags are dropped, not kept."""
    s = html or ""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>|</div\s*>|</li\s*>", "\n", s)
    s = re.sub(r"(?i)<li\b[^>]*>", "- ", s)
    s = re.sub(r"(?is)<(strong|b)\b[^>]*>(.*?)</\1>", emphasis("**"), s)
    s = re.sub(r"(?is)<(em|i)\b[^>]*>(.*?)</\1>", emphasis("*"), s)
    s = re.sub(r"(?i)<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
               r"[\2](\1)", s, flags=re.S)
    s = re.sub(r"(?i)<img\b[^>]*src=[\"']([^\"']+)[\"'][^>]*>",
               r"![[TODO save image: \1]]", s)
    s = re.sub(r"(?i)</?(u|sub|sup)\b[^>]*>", lambda m: m.group(0).lower(), s)
    s = re.sub(r"(?is)<(?!/?(?:u|sub|sup)\b)[^>]+>", "", s)
    s = unescape(s)
    s = re.sub(r"(?m)^[ \t]*-[ \t]*$", "", s)       # bullets of emptied <li>
    if oneline:
        return re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def stem_of(q):
    text = md(q.get("stemHtml") or "") or (q.get("stemText") or "")
    text = RX_QPREFIX.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    # the house format bolds the whole stem, so a word Elentra bolded inside it
    # would nest and break; the emphasis has nowhere left to go
    text = text.replace("**", "")
    return "**%s**" % text if text else text


def quoted(text, depth=1):
    """Wrap text in `> ` callout lines at the given nesting depth."""
    p = "> " * depth
    lines = (text or "").split("\n")
    return "\n".join((p + l).rstrip() for l in lines)


# ---------------------------------------------------------------- one question

def render(q, n, qid):
    out = ["# %d" % n, stem_of(q)]

    note = None
    if q["kind"] == "multi":
        note = ("*(originally select all that apply; rewrite as one MCQ whose "
                "options are complete combinations)*")
    elif q["kind"] == "short":
        note = "*(originally short answer; rewrite as MCQ)*"
    if note:
        out.append(note)

    out.append("")
    for o in q["options"]:
        text = md(o["html"], oneline=True) or o["text"]
        if o.get("sourceLetter"):               # Elentra printed its own A) B) C)
            text = RX_OPTLETTER.sub("", text)
        out.append("%s) %s" % (o["letter"], text))
    if q["kind"] == "short":
        out.append("*Response typed in Elentra: %s*" % (q.get("response") or "(blank)"))
    out.append("")

    feedback = "\n\n".join(md(f["html"]) or f["text"] for f in q.get("feedback", []) if
                           (f.get("html") or f.get("text")))
    if q["correct"]:
        # the callout already opens with the key; don't say it twice
        feedback = RX_KEYLINE.sub("", feedback)

    if q["correct"]:
        body = ["**The correct answer is %s.**" % ", ".join(q["correct"])]
        if feedback:
            body += ["", feedback]
        out.append("> [!q]- Answer")
        out.append(quoted("\n".join(body)))
        if not feedback:
            out.append(">")
            out.append("> > [!warning] No explanation in Elentra")
            out.append("> > The review gave the key and no rationale.")
    else:
        out.append("> [!red] No official answer key")
        out.append("> Elentra's review did not mark a correct option in a way the")
        out.append("> grab recognised. Run elentra_quiz.py --inspect to see what it saw.")
        if feedback:
            out.append(">")
            out.append(quoted(feedback, 1))
        out.append(">")
        out.append("> > [!success]- Reasoned answer")
        out.append("> > **TODO** - reason this from the lecture note and say so.")

    out.append("")
    out.append("<!-- %s -->" % qid)
    return "\n".join(out)


# ---------------------------------------------------------------- captures

def questions_of(store):
    qs = list(store.get("questions", {}).values())
    qs.sort(key=lambda q: (q.get("order") or 0, q.get("number") or ""))
    return qs


def lecture_of(store, override):
    if override:
        return override
    title = (store.get("title") or "").strip()
    title = re.sub(r"\s*[|\-–]\s*Elentra.*$", "", title, flags=re.I)
    title = re.sub(r"^\s*(weekly\s+quiz|quiz)\s*[:\-–]\s*", "", title, flags=re.I)
    return title or ("Exam %s" % store.get("examId", "?"))


def week_of(store, override):
    if override:
        return override
    m = RX_WEEK.search(store.get("title") or "")
    return int(m.group(1)) if m else 0


def start_from_note(path):
    if not path or not os.path.exists(path):
        return None
    nums = [int(m) for m in
            re.findall(r"^#\s+(\d+)\s*$", io.open(path, encoding="utf-8").read(), re.M)]
    return max(nums) + 1 if nums else 1


def inspect(store):
    for q in questions_of(store):
        print("  Q%-4s %-6s key=%s" % (q.get("number") or "?", q["kind"],
                                       ",".join(q["correct"]) or "-"))
        for o in q["options"]:
            print("    %s %-40s %s" % (o["letter"], o["text"][:40],
                                       " ".join(o["signals"])[:150]))


# ---------------------------------------------------------------- main

def main(argv):
    files, opts = [], {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            k = a[2:]
            if k in ("inspect",):
                opts[k] = True
            else:
                i += 1
                opts[k] = argv[i] if i < len(argv) else ""
        else:
            files.append(a)
        i += 1

    if not files:
        sys.stderr.write(__doc__)
        return 2

    slug = SLUG.get((opts.get("topic") or "").lower().strip(), "")
    if not slug and not opts.get("inspect"):
        sys.stderr.write("need --topic (%s)\n" % "|".join(sorted(TOPIC)))
        return 2

    note = opts.get("note")
    n = int(opts.get("start") or 0) or start_from_note(note) or 1
    if not opts.get("start") and not note and not opts.get("inspect"):
        print("no --start and no --note: numbering from 1, which will collide")
        print("  with anything already in the note. Pass --note <the vault file>.")

    for path in files:
        store = json.load(io.open(path, encoding="utf-8"))
        qs = questions_of(store)
        print("")
        print("%s  exam %s" % (os.path.basename(path), store.get("examId")))
        print('  "%s"' % (store.get("title") or "")[:70])
        blank = [c for c in store.get("captures", []) if not c["found"]]
        if blank:
            print("  %d capture(s) parsed nothing; their page HTML is in the file"
                  % len(blank))
        if not qs:
            print("  no questions - send the file over, the HTML in it says why")
            continue

        if opts.get("inspect"):
            inspect(store)
            continue

        week = week_of(store, int(opts.get("week") or 0))
        lecture = lecture_of(store, opts.get("lecture"))
        first, chunks = n, []
        for q in qs:
            qid = "weekly-%s-Q%d" % (slug, n)
            chunks.append(render(q, n, qid))
            n += 1

        body = (u"## Week %d\n\n#### %s\n*Source: Elentra weekly quiz %s, "
                u"review view, %d questions.*\n\n%s\n"
                % (week, lecture, store.get("examId"), len(qs),
                   "\n\n".join(chunks)))

        if not os.path.isdir(OUT):
            os.makedirs(OUT)
        dest = opts.get("out") or os.path.join(
            OUT, "weekly-%s-w%d-exam%s.md" % (slug, week, store.get("examId")))
        io.open(dest, "w", encoding="utf-8", newline="\n").write(body)

        keyed = sum(1 for q in qs if q["correct"])
        rewrite = [q for q in qs if q["kind"] in ("multi", "short")]
        print("  %d questions, %d keyed, %d without a key"
              % (len(qs), keyed, len(qs) - keyed))
        if rewrite:
            print("  %d need rewriting into MCQ: %s"
                  % (len(rewrite), ", ".join(q["kind"] for q in rewrite)))
        print("  wrote %s" % dest)
        print("  # %d - # %d   qids weekly-%s-Q%d - Q%d"
              % (first, n - 1, slug, first, n - 1))
        print("  goes under '## Week %d' in Weekly Quizzes - %s.md"
              % (week, TOPIC[slug]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
