# -*- coding: utf-8 -*-
"""Resolve a vault image, re-compress it, and print the <img> tag to paste into a question.

Purpose: turn an Obsidian embed into the one thing data/questions/*.json ships.
Author:  Noor Simsam
Date:    2026-09-07
Input:   an image name as the vault writes it - "cortisol excess and deficiency.jpg",
         or the whole embed including the width hint, "![[incretin effect.png|600]]"
Output:  <img loading="lazy" src="data:image/jpeg;base64,..."> on stdout

Pictures ship *inside* the question, as a data: URI in the stem HTML. There is no
image field and no assets directory, so quiz.js needs no image handling: it
renders the stem as HTML and the browser does the rest. That is already how the
seven endo pictures work, and this only automates the arithmetic.

Two things it does that doing it by hand does not:

  * **Re-compresses.** The vault original can be far larger than the site needs -
    the incretin graph is a 3 MB PNG and ships as a 75 KB JPEG. This walks the
    JPEG quality down, then the width, until the encoded bytes fit the budget.
  * **Reports the size it landed on**, so a picture that will not fit is a visible
    failure rather than a 400 KB line quietly pasted into the bank.

Unlike the four rebuild scripts this one needs Pillow (present in the pyenv 3.9.13
that already carries PyMuPDF). It is an authoring helper for Stage 4, not part of
the portal build.

It cannot tell a cadaveric image from a clinical photograph, and does not try.
That call is made by looking at the picture; see the pom2-week skill.
"""

import argparse
import base64
import io
import logging
import os
import re
import sys
from pathlib import Path

from PIL import Image

LOG = logging.getLogger("embed_image")

# The site never shows a question picture wider than the question column, and
# 100 KB encoded keeps a block's JSON from being mostly pictures.
MAX_KB = 100
MAX_WIDTH = 900

# Quality floor is where JPEG artefacts start showing on a radiograph; below
# this, drop the width instead and re-try at good quality.
QUALITY_STEPS = (85, 75, 65, 55)
WIDTH_STEPS = (900, 750, 600, 480)

VAULT = os.environ.get("POM2_VAULT", u"C:/Users/nsims/medwiki/01 - Lectures/99 - PoM 2")
ATTACHMENTS = os.environ.get("POM2_ATTACHMENTS", "")


def attachment_roots() -> tuple:
    """Where to look for an embed's target, most likely first.

    Obsidian resolves ![[name]] against the whole vault, so the folder the note
    lives in is irrelevant and only the filename matters. POM2_VAULT points at
    the lectures subtree, so the vault root is two levels above it.

    Returns (recursive roots, vault root). The vault root is checked only at its
    top level, never walked: rglob over the whole vault dies on the anatomy
    folder, whose nested-structure directories run past the Windows path limit.
    """
    roots = []
    if ATTACHMENTS:
        roots.append(Path(ATTACHMENTS))
    vault_root = Path(VAULT).parent.parent
    roots.append(vault_root / "Attachments")
    return roots, vault_root


def clean_name(raw: str) -> str:
    """Accept a bare filename, a full ![[embed|600]], or a path; return the filename."""
    s = raw.strip()
    m = re.search(r"!\[\[([^\]|]+)", s)
    if m:
        s = m.group(1)
    s = s.split("|")[0].strip()
    return Path(s).name


def resolve(name: str) -> Path:
    """Find the image in the vault, or raise with the places that were tried."""
    direct = Path(name)
    if direct.is_file():
        return direct
    roots, vault_root = attachment_roots()
    tried = []
    for root in roots + [vault_root]:
        candidate = root / name
        tried.append(str(candidate))
        if candidate.is_file():
            return candidate
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for found in root.rglob(name):
                return found
        except OSError as exc:
            # a path past the Windows limit, or a folder that vanished under us
            LOG.warning("stopped searching %s: %s", root, exc)
    raise SystemExit(
        "cannot find %r. Tried:\n  %s\nSet POM2_ATTACHMENTS if the vault is elsewhere."
        % (name, "\n  ".join(tried))
    )


def encode(path: Path, max_kb: int, max_width: int) -> tuple:
    """Re-compress to the smallest JPEG that still looks right, under max_kb.

    Returns (base64 string, encoded byte count, width used, quality used).
    Quality is spent first because dropping pixels is what actually loses
    detail, and a keyed anatomy or radiology image is often keyed on detail.
    """
    src = Image.open(path)
    if src.mode not in ("RGB", "L"):
        # JPEG has no alpha; flatten onto white rather than letting it go black.
        flat = Image.new("RGB", src.size, (255, 255, 255))
        flat.paste(src, mask=src.split()[-1] if "A" in src.mode else None)
        src = flat

    budget = max_kb * 1024
    widths = [w for w in WIDTH_STEPS if w <= max_width] or [max_width]
    best = None

    for width in widths:
        scaled = src
        if src.width > width:
            height = int(round(src.height * (float(width) / src.width)))
            scaled = src.resize((width, height), Image.LANCZOS)
        for quality in QUALITY_STEPS:
            buf = io.BytesIO()
            scaled.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
            raw = buf.getvalue()
            encoded = base64.b64encode(raw).decode("ascii")
            if best is None:
                best = (encoded, len(encoded), scaled.width, quality)
            if len(encoded) <= budget:
                return encoded, len(encoded), scaled.width, quality

    LOG.warning(
        "%s will not fit under %d KB; smallest was %.1f KB at %dpx q%d",
        path.name, max_kb, best[1] / 1024.0, best[2], best[3])
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help='vault image name, or the whole ![[embed]]')
    ap.add_argument("--max-kb", type=int, default=MAX_KB,
                    help="encoded size budget in KB (default %d)" % MAX_KB)
    ap.add_argument("--max-width", type=int, default=MAX_WIDTH,
                    help="widest the picture may ship (default %d)" % MAX_WIDTH)
    ap.add_argument("--alt", default="",
                    help="alt text; worth setting when the picture IS the question")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    name = clean_name(args.name)
    path = resolve(name)
    encoded, size, width, quality = encode(path, args.max_kb, args.max_width)

    LOG.info("%s -> %.1f KB encoded, %dpx wide, q%d", path.name, size / 1024.0, width, quality)
    alt = ' alt="%s"' % args.alt.replace('"', "&quot;") if args.alt else ""
    sys.stdout.write('<img loading="lazy"%s src="data:image/jpeg;base64,%s">\n' % (alt, encoded))
    return 0


if __name__ == "__main__":
    sys.exit(main())
