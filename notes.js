/* The notes half of a PoM 2 block page.

   data/notes/<slug>.json carries the block's whole lecture roster, taken from
   the vault folders, not only the lectures that have a note. A lecture with
   "hasNote": false renders as a dashed gap, so this view doubles as a map of
   what is still left to write - the same reasoning that keeps an empty question
   set visible on the other tab.

   Any note can be sent to PDF on its own, or a whole week at once, so it can be
   annotated by hand afterwards. That runs through the browser's own print
   dialogue: the page marks what should survive, prints, and unmarks.

   Mermaid is only fetched if some lecture in this block actually has a pathway. */

(function () {
  "use strict";

  var BLOCK = window.QUIZ_BLOCK;
  var MERMAID_SRC = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js";

  var WEEKS = [];
  var cov = "all";
  var booted = false;

  function byId(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function html(tag, cls, markup) {
    var n = el(tag, cls);
    if (markup) n.innerHTML = markup;
    return n;
  }

  function lectures() {
    var out = [];
    WEEKS.forEach(function (w) {
      (w.lectures || []).forEach(function (l) { out.push(l); });
    });
    return out;
  }

  /* ---------- printing ---------- */

  /* The browser's print dialogue is the only PDF writer a static page has, and
     it is the right one - it produces a normal PDF that any annotator can mark
     up. Everything not in scope is hidden for the duration of the print. */
  function printScope(nodes) {
    var marked = [];
    nodes.forEach(function (n) { n.classList.add("print-me"); marked.push(n); });
    document.body.dataset.printing = "notes";

    function clear() {
      marked.forEach(function (n) { n.classList.remove("print-me"); });
      delete document.body.dataset.printing;
      window.removeEventListener("afterprint", clear);
    }
    window.addEventListener("afterprint", clear);
    // afterprint does not fire everywhere, so do not rely on it alone
    setTimeout(clear, 60000);

    window.print();
  }

  function printNote(art) {
    printScope([art]);
  }

  function printWeek(weekbar) {
    var nodes = [weekbar], n = weekbar.nextElementSibling;
    while (n && !n.classList.contains("weekbar")) {
      if (n.classList.contains("note") && !n.classList.contains("is-gap")) nodes.push(n);
      n = n.nextElementSibling;
    }
    printScope(nodes);
  }

  function printAll() {
    var nodes = [].slice.call(
      document.querySelectorAll("#note-stream .weekbar, #note-stream .note:not(.is-gap)"));
    printScope(nodes);
  }

  function pdfButton(label, title, onClick) {
    var b = el("button", "pdf-btn", label);
    b.type = "button";
    b.title = title;
    b.addEventListener("click", function (e) {
      e.preventDefault();
      onClick();
    });
    return b;
  }

  /* ---------- one note ---------- */

  function buildTable(spec) {
    var wrap = el("div", "ct-wrap");
    var t = el("table", "ct");
    if (spec.cols && spec.cols.length) {
      var thead = el("thead"), tr = el("tr");
      spec.cols.forEach(function (c) { tr.appendChild(html("th", null, c)); });
      thead.appendChild(tr);
      t.appendChild(thead);
    }
    var tb = el("tbody");
    (spec.rows || []).forEach(function (row) {
      var r = el("tr");
      row.forEach(function (cell) { r.appendChild(html("td", null, cell)); });
      tb.appendChild(r);
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }

  /* the parts arrive in the order they were written, because the sentence above
     a table is the reason the table is there - splitting them into separate
     fields would have shuffled the argument */
  function buildBlock(b) {
    if (b.t === "pathway") {
      var p = el("div", "pathway");
      // mermaid parses the element's own text, so this must not be innerHTML
      p.textContent = b.mermaid;
      return p;
    }
    if (b.t === "table") {
      var box = el("div", "tblock");
      if (b.lead) box.appendChild(html("div", "tlead", b.lead));
      box.appendChild(buildTable(b));
      return box;
    }
    if (b.t === "callout") {
      var c = el("div", "callout k-" + (/^[a-z]+$/.test(b.kind || "") ? b.kind : "note"));
      c.appendChild(el("span", "ct", b.title || "Note"));
      c.appendChild(html("div", null, b.html));
      return c;
    }
    if (b.t === "list") return html("div", "clist", b.html);
    return html("div", "cnote", b.html);
  }

  function buildNote(lec) {
    var art = el("article", "note");
    art.id = "n-" + lec.id;
    art.dataset.id = lec.id;

    var head = el("div", "note-head");
    head.appendChild(el("span", "note-num", lec.num));
    head.appendChild(el("h4", null, lec.name));
    head.appendChild(el("span", "spacer"));
    head.appendChild(pdfButton("PDF", "Save this note as a PDF",
      function () { printNote(art); }));
    art.appendChild(head);

    if (lec.title) art.appendChild(el("p", "note-title", lec.title));
    if (lec.framing) art.appendChild(html("div", "framing", lec.framing));

    (lec.blocks || []).forEach(function (b) { art.appendChild(buildBlock(b)); });

    if (lec.keypoints) {
      var kp = el("div", "keypoints");
      kp.appendChild(el("span", "kt", "High-yield discriminators"));
      kp.appendChild(html("div", null, lec.keypoints));
      art.appendChild(kp);
    }

    return art;
  }

  function buildGap(lec) {
    var art = el("article", "note is-gap");
    art.id = "n-" + lec.id;
    art.dataset.id = lec.id;
    var head = el("div", "note-head");
    head.appendChild(el("span", "note-num", lec.num));
    head.appendChild(el("h4", null, lec.name));
    art.appendChild(head);
    art.appendChild(el("span", "gapnote", "no note yet"));
    return art;
  }

  /* ---------- mermaid, only if this block needs it ---------- */

  function themeVars() {
    var cs = getComputedStyle(document.documentElement);
    function v(name, fallback) {
      var got = cs.getPropertyValue(name).trim();
      return got || fallback;
    }
    return {
      background: v("--card-bg", "#ffffff"),
      primaryColor: v("--q-accent-soft", "#eeeeee"),
      primaryTextColor: v("--text", "#27060f"),
      primaryBorderColor: v("--q-accent", "#84223b"),
      lineColor: v("--muted", "#8a7a7d"),
      secondaryColor: v("--bg", "#faf7f7"),
      tertiaryColor: v("--bg", "#faf7f7"),
      fontFamily: v("--sans", "Inter, sans-serif"),
      fontSize: "13px"
    };
  }

  function drawPathways() {
    var nodes = [].slice.call(document.querySelectorAll("#note-stream .pathway"));
    if (!nodes.length) return;

    var s = document.createElement("script");
    s.src = MERMAID_SRC;
    s.async = true;
    s.onload = function () {
      if (!window.mermaid) return;
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "base",
        themeVariables: themeVars(),
        flowchart: { htmlLabels: true, useMaxWidth: true }
      });
      try {
        window.mermaid.run({ nodes: nodes });
      } catch (e) {
        // a diagram that will not parse should cost the page nothing; the
        // source text stays on screen and the rest of the note is unaffected
      }
    };
    s.onerror = function () {
      nodes.forEach(function (n) {
        n.textContent = "";
        n.appendChild(el("p", null, "The diagram library could not be loaded, so this pathway is not drawn."));
      });
    };
    document.head.appendChild(s);
  }

  /* ---------- filter ---------- */

  var COV_DEFS = [
    { k: "all", label: "All" },
    { k: "written", label: "Written" },
    { k: "gap", label: "Not yet" }
  ];

  function matches(lec) {
    if (cov === "written") return lec.hasNote === true;
    if (cov === "gap") return lec.hasNote !== true;
    return true;
  }

  function applyFilter() {
    var shown = 0;
    lectures().forEach(function (lec) {
      var art = byId("n-" + lec.id);
      if (!art) return;
      var ok = matches(lec);
      art.hidden = !ok;
      if (ok) shown++;
    });

    // a week heading survives only while a lecture under it is still visible
    [].forEach.call(document.querySelectorAll("#note-stream .weekbar"), function (h) {
      var any = false, n = h.nextElementSibling;
      while (n && !n.classList.contains("weekbar")) {
        if (n.classList.contains("note") && !n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      h.hidden = !any;
    });

    byId("note-empty").hidden = shown > 0;
    paintChips();
  }

  function counts() {
    var all = lectures();
    var written = all.filter(function (l) { return l.hasNote === true; }).length;
    return { all: all.length, written: written, gap: all.length - written };
  }

  function paintChips() {
    var c = counts();
    [].forEach.call(document.querySelectorAll("#cov-chips .chip"), function (b) {
      b.setAttribute("aria-pressed", cov === b.dataset.k ? "true" : "false");
      b.querySelector(".n").textContent = c[b.dataset.k];
    });
  }

  function paintCoverage() {
    var c = counts();
    var weeksWith = WEEKS.filter(function (w) {
      return (w.lectures || []).some(function (l) { return l.hasNote === true; });
    }).length;

    byId("cv-notes").textContent = c.written;
    byId("cv-of").textContent = "/" + c.all;
    byId("cv-weeks").textContent = weeksWith;
    byId("cv-weeks-of").textContent = "/" + WEEKS.length;

    var tc = byId("tc-notes");
    if (tc) tc.textContent = c.written + "/" + c.all;

    byId("print-all").disabled = c.written === 0;
  }

  /* ---------- boot ---------- */

  function buildRail() {
    var box = byId("cov-chips");
    COV_DEFS.forEach(function (d) {
      var b = el("button", "chip");
      b.type = "button";
      b.dataset.k = d.k;
      b.setAttribute("aria-pressed", d.k === "all" ? "true" : "false");
      b.appendChild(document.createTextNode(d.label));
      b.appendChild(el("span", "n", "0"));
      b.addEventListener("click", function () { cov = d.k; applyFilter(); });
      box.appendChild(b);
    });

    byId("print-all").addEventListener("click", printAll);
  }

  function buildStream() {
    var stream = byId("note-stream"), frag = document.createDocumentFragment();

    WEEKS.forEach(function (w) {
      var wb = el("div", "weekbar");
      wb.appendChild(el("h3", null, w.label || ("Week " + w.n)));
      if ((w.lectures || []).some(function (l) { return l.hasNote === true; })) {
        wb.appendChild(pdfButton("Save week as PDF",
          "Save every note in this week as one PDF",
          function () { printWeek(wb); }));
      }
      frag.appendChild(wb);
      (w.lectures || []).forEach(function (lec) {
        frag.appendChild(lec.hasNote === true ? buildNote(lec) : buildGap(lec));
      });
    });

    var empty = el("div", "empty", "Nothing matches that filter.");
    empty.id = "note-empty";
    empty.hidden = true;
    frag.appendChild(empty);

    stream.innerHTML = "";
    stream.appendChild(frag);
  }

  function start(data) {
    WEEKS = (data && data.weeks) || [];
    buildRail();
    buildStream();
    paintCoverage();
    applyFilter();
    drawPathways();
  }

  window.POM2_NOTES = {
    boot: function () {
      if (booted) return;
      booted = true;
      fetch("data/notes/" + BLOCK.slug + ".json")
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(start)
        .catch(function () {
          var stream = byId("note-stream");
          stream.innerHTML = "";
          stream.appendChild(el("div", "empty",
            "The notes could not be loaded. If you are opening this file straight from disk, serve the folder over HTTP instead - browsers block local fetches."));
        });
    }
  };
})();
