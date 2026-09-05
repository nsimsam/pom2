/* The questions half of a PoM 2 block page.
   Each block page sets window.QUIZ_BLOCK = { slug, n, name, weeks } and calls
   POM2_QUIZ.boot() when the Questions tab is first opened - the block JSON runs
   to hundreds of kilobytes, so nothing is fetched until it is asked for.
   Progress lives in localStorage under nsq.v1.<slug>. */

(function () {
  "use strict";

  var BLOCK = window.QUIZ_BLOCK;
  var STORE_PREFIX = "nsq.v1.";
  var STORE_KEY = STORE_PREFIX + BLOCK.slug;

  /* the source families are the same in every block, empty ones included:
     an empty family is a visible gap in coverage, which is the point. Schulich
     Reviews is listed for that reason - it is coming, and until it does the
     empty set says so. */
  var FAMILIES = [
    {
      key: "module",
      name: "Course modules",
      blurb: "The module lectures and the weekly Elentra quizzes."
    },
    {
      key: "workbook",
      name: "Pre-Clerkship Workbook",
      blurb: "The Pre-Clerkship Workbook (2023 edition), the student bank passed down through the Schulich classes of 2015-2025. It has a written key, but the key is peer-written and contains real errors. Every one found is flagged on the question."
    },
    {
      key: "meds2029",
      name: "Meds 2029",
      blurb: "Questions built from patient cases in the modules, DSSGs and in-class lectures, since exams tend to recycle similar cases."
    },
    {
      key: "reviews",
      name: "Schulich Reviews",
      blurb: "The Schulich Reviews sessions, both their practice questions and their summary content. TBD."
    }
  ];

  var QUESTIONS = [];
  var QMAP = Object.create(null);
  var progress = Object.create(null);
  var filters = { status: "all", family: null };
  var RESET_SHOWN_IDLE = null;
  var storeWritable = true;

  function byId(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ---------- the store ---------- */

  function sanitize(qid, data) {
    var q = QMAP[qid];
    if (!q || !data || typeof data !== "object") return null;
    return {
      qid: qid,
      source: q.source,
      family: q.family,
      lecture: q.lecture,
      week: q.week === null ? 0 : q.week,
      status: (data.status === "correct" || data.status === "wrong") ? data.status : null,
      flagged: data.flagged === true,
      firstTryCorrect: typeof data.firstTryCorrect === "boolean" ? data.firstTryCorrect : null,
      attempts: Array.isArray(data.attempts)
        ? data.attempts.filter(function (a) { return a && typeof a === "object"; }).slice(-50)
        : [],
      lastTs: typeof data.lastTs === "number" ? data.lastTs : 0
    };
  }

  function load() {
    var raw = null;
    try { raw = window.localStorage.getItem(STORE_KEY); }
    catch (e) { storeWritable = false; return; }
    if (!raw) return;
    var parsed;
    try { parsed = JSON.parse(raw); }
    catch (e) { return; }
    if (!parsed || typeof parsed !== "object") return;
    Object.keys(parsed).forEach(function (qid) {
      var rec = sanitize(qid, parsed[qid]);
      if (rec) progress[qid] = rec;
    });
  }

  function save() {
    if (!storeWritable) return;
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(progress)); }
    catch (e) {
      storeWritable = false;
      note("Progress could not be saved - the browser refused to write to local storage. Every question still works, but nothing is being kept.");
    }
  }

  function note(text) {
    var n = byId("storenote");
    n.hidden = false;
    n.textContent = text;
  }

  /* ---------- progress model ---------- */

  function rec(qid) { return progress[qid] || null; }

  function stateOf(qid) {
    var r = rec(qid);
    if (!r || (r.status !== "correct" && r.status !== "wrong")) return "unseen";
    return r.status;
  }

  function isStarred(qid) { var r = rec(qid); return !!(r && r.flagged === true); }

  function attemptsOf(qid) {
    var r = rec(qid);
    return (r && Array.isArray(r.attempts)) ? r.attempts : [];
  }

  function chosenOf(qid) {
    var a = attemptsOf(qid);
    if (!a.length) return null;
    var c = a[a.length - 1].chosen;
    return typeof c === "string" ? c.split("+").filter(Boolean) : null;
  }

  function persist(qid, patch) {
    var prev = progress[qid] || {}, q = QMAP[qid];
    var next = {
      qid: qid,
      source: q.source,
      family: q.family,
      lecture: q.lecture,
      week: q.week === null ? 0 : q.week,
      status: patch.status !== undefined ? patch.status : (prev.status || null),
      flagged: patch.flagged !== undefined ? patch.flagged : (prev.flagged === true),
      firstTryCorrect: (typeof prev.firstTryCorrect === "boolean") ? prev.firstTryCorrect : null,
      attempts: Array.isArray(prev.attempts) ? prev.attempts.slice(-49) : [],
      lastTs: Date.now()
    };
    if (patch.attempt) {
      if (next.firstTryCorrect === null) next.firstTryCorrect = patch.attempt.correct;
      next.attempts = next.attempts.concat([patch.attempt]);
    }
    progress[qid] = next;
    save();
    paintQuestion(qid);
    paintStats();
    setAnchor(qid);
  }

  function forget(qid) {
    delete progress[qid];
    save();
    paintQuestion(qid);
    paintStats();
    if (ANCHOR === qid) { ANCHOR = null; RESUMING = false; paintPos(); }
  }

  /* ---------- build one question ---------- */

  var KIND_LABEL = { matching: "matching", short: "short answer", broken: "unscorable" };

  function buildQuestion(q) {
    var art = el("article", "q");
    art.id = "q-" + q.qid;
    art.dataset.qid = q.qid;
    art.dataset.kind = q.kind;

    var head = el("div", "qhead");
    head.appendChild(el("span", "qnum", "Q" + q.num));
    head.appendChild(el("span", "tag", q.sourceLabel));
    if (!q.keyed) head.appendChild(el("span", "tag reasoned", "no official key"));
    if (KIND_LABEL[q.kind]) head.appendChild(el("span", "tag kind", KIND_LABEL[q.kind]));
    if (q.multi) head.appendChild(el("span", "tag multi", "select " + q.correct.length));
    if (q.retired) head.appendChild(el("span", "tag retired", "retired"));
    var hasErr = (q.flags || []).some(function (f) {
      return f.type === "bug" || f.type === "red" ||
             (f.type === "warning" && f.title !== "No explanation in the module");
    });
    if (hasErr) head.appendChild(el("span", "tag errflag", "source error flagged"));
    head.appendChild(el("span", "spacer"));

    var star = el("button", "star-btn", "★");
    star.type = "button";
    star.title = "Star for review";
    star.setAttribute("aria-label", "Star question " + q.num);
    star.setAttribute("aria-pressed", "false");
    star.addEventListener("click", function () {
      persist(q.qid, { flagged: !isStarred(q.qid) });
    });
    head.appendChild(star);
    art.appendChild(head);

    if (q.preamble) {
      var pre = el("div", "preamble");
      pre.appendChild(el("span", "pt", q.preamble.title || "Instructions"));
      var pb = el("div");
      pb.innerHTML = q.preamble.html;
      pre.appendChild(pb);
      art.appendChild(pre);
    }

    var stem = el("div", "stem");
    stem.innerHTML = q.stem;
    art.appendChild(stem);

    if (q.options.length) {
      var list = el("ul", "opts");
      q.options.forEach(function (o) {
        var li = document.createElement("li");
        var b = el("button", "opt");
        b.type = "button";
        b.dataset.letter = o.letter;
        b.appendChild(el("span", "L", o.letter));
        var t = el("span", "t");
        t.innerHTML = o.html;
        b.appendChild(t);
        b.appendChild(el("span", "verdict"));
        if (q.unscorable) b.disabled = true;
        else b.addEventListener("click", function () { pick(q, art, o.letter); });
        li.appendChild(b);
        list.appendChild(li);
      });
      art.appendChild(list);
    }

    if (q.unscorable) {
      var bn = el("div", "banner pre");
      bn.appendChild(el("b", null, "Not scored"));
      bn.appendChild(document.createTextNode(
        "The source gives no defensible answer for this one, so it is left out of the accuracy figures. Read why, then move on."));
      art.appendChild(bn);
      var a1 = el("div", "actions");
      var sh = el("button", "btn ghost", "Show the problem");
      sh.type = "button";
      sh.addEventListener("click", function () { art.classList.add("revealed"); });
      a1.appendChild(sh);
      art.appendChild(a1);
    } else if (q.free) {
      var a2 = el("div", "actions");
      var show = el("button", "btn", "Show answer");
      show.type = "button";
      show.addEventListener("click", function () { art.classList.add("revealed"); });
      var got = el("button", "btn ghost", "I had it");
      got.type = "button";
      got.addEventListener("click", function () {
        art.classList.add("revealed");
        persist(q.qid, {
          status: "correct",
          attempt: { ts: Date.now(), chosen: "self", correct: true }
        });
      });
      var mis = el("button", "btn ghost", "I missed it");
      mis.type = "button";
      mis.addEventListener("click", function () {
        art.classList.add("revealed");
        persist(q.qid, {
          status: "wrong",
          attempt: { ts: Date.now(), chosen: "self", correct: false }
        });
      });
      a2.appendChild(show);
      a2.appendChild(got);
      a2.appendChild(mis);
      art.appendChild(a2);
    } else if (q.multi) {
      var a3 = el("div", "actions");
      var check = el("button", "btn", "Check answer");
      check.type = "button";
      check.dataset.role = "check";
      check.disabled = true;
      check.addEventListener("click", function () { submitMulti(q, art); });
      a3.appendChild(check);
      a3.appendChild(el("span", "hint", "select " + q.correct.length + ", then check"));
      art.appendChild(a3);
    }

    var ans = el("div", "answer");
    if (!q.keyed) {
      var nk = el("div", "banner");
      nk.appendChild(el("b", null, "No official answer key"));
      nk.appendChild(document.createTextNode(
        "Reasoned from the lecture content, not transcribed from a key. Verify before relying on it."));
      ans.appendChild(nk);
    }
    ans.appendChild(el("p", "ans-h", q.keyed ? (q.answerTitle || "Answer") : "Reasoned answer"));
    var ab = el("div", "ans-body");
    ab.innerHTML = q.answer;
    ans.appendChild(ab);
    (q.flags || []).forEach(function (f) {
      var c = el("div", "callout k-" + (/^[a-z]+$/.test(f.type) ? f.type : "note"));
      c.appendChild(el("span", "ct", f.title || "Note"));
      var cb = el("div");
      cb.innerHTML = f.html;
      c.appendChild(cb);
      ans.appendChild(c);
    });
    art.appendChild(ans);

    var foot = el("div", "qfoot");
    foot.appendChild(el("span", "qid", q.qid));
    foot.appendChild(el("span", "qid attempts"));
    var rst = el("button", "reset-q", "reset");
    rst.type = "button";
    rst.hidden = true;
    rst.addEventListener("click", function () { forget(q.qid); });
    foot.appendChild(rst);
    art.appendChild(foot);
    return art;
  }

  function pick(q, art, letter) {
    if (q.multi) {
      if (art.classList.contains("revealed")) return;
      var btn = art.querySelector('.opt[data-letter="' + letter + '"]');
      btn.dataset.pick = btn.dataset.pick === "on" ? "" : "on";
      art.querySelector('[data-role="check"]').disabled =
        art.querySelectorAll('.opt[data-pick="on"]').length === 0;
      return;
    }
    var correct = q.correct.indexOf(letter) !== -1;
    persist(q.qid, {
      status: correct ? "correct" : "wrong",
      attempt: { ts: Date.now(), chosen: letter, correct: correct }
    });
  }

  function submitMulti(q, art) {
    var picked = [].slice.call(art.querySelectorAll('.opt[data-pick="on"]'))
      .map(function (b) { return b.dataset.letter; })
      .sort();
    var correct = picked.join("+") === q.correct.slice().sort().join("+");
    persist(q.qid, {
      status: correct ? "correct" : "wrong",
      attempt: { ts: Date.now(), chosen: picked.join("+"), correct: correct }
    });
  }

  function paintQuestion(qid) {
    var art = byId("q-" + qid);
    if (!art) return;
    var q = QMAP[qid], st = stateOf(qid), done = st !== "unseen";

    art.dataset.state = st;
    if (!q.unscorable) art.classList.toggle("revealed", done);
    art.querySelector(".star-btn").setAttribute("aria-pressed", isStarred(qid) ? "true" : "false");

    var chosen = chosenOf(qid) || [];
    [].forEach.call(art.querySelectorAll(".opt"), function (b) {
      if (q.unscorable) return;
      var L = b.dataset.letter;
      b.disabled = done;
      b.dataset.pick = (!done && chosen.indexOf(L) !== -1) ? "on" : "";
      var v = b.querySelector(".verdict");
      v.textContent = "";
      b.dataset.mark = "";
      if (!done) return;
      var isKey = q.correct.indexOf(L) !== -1, wasPicked = chosen.indexOf(L) !== -1;
      if (wasPicked && isKey) { b.dataset.mark = "hit"; v.textContent = "your pick · correct"; }
      else if (wasPicked) { b.dataset.mark = "miss"; v.textContent = "your pick"; }
      else if (isKey) { b.dataset.mark = "key"; v.textContent = "correct"; }
    });

    var check = art.querySelector('[data-role="check"]');
    if (check) check.hidden = done;

    var atts = attemptsOf(qid);
    art.querySelector(".attempts").textContent = atts.length > 1 ? atts.length + " attempts" : "";
    art.querySelector(".reset-q").hidden = !done && !isStarred(qid);
  }

  /* ---------- filters ---------- */

  function matches(qid) {
    var q = QMAP[qid];
    if (filters.family && q.family !== filters.family) return false;
    var st = stateOf(qid);
    switch (filters.status) {
      case "unseen":  return st === "unseen";
      case "wrong":   return st === "wrong";
      case "correct": return st === "correct";
      case "starred": return isStarred(qid);
      default:        return true;
    }
  }

  // qids currently passing the filters that actually have something to clear
  function shownWithProgress() {
    return QUESTIONS.filter(function (q) { return progress[q.qid] && matches(q.qid); })
                    .map(function (q) { return q.qid; });
  }

  function applyFilters() {
    var shown = 0;
    QUESTIONS.forEach(function (q) {
      var art = byId("q-" + q.qid), ok = matches(q.qid);
      art.hidden = !ok;
      if (ok) shown++;
    });
    // a heading survives only while a question under it is still visible
    [].forEach.call(document.querySelectorAll(".lecbar"), function (h) {
      var any = false, n = h.nextElementSibling;
      while (n && n.classList.contains("q")) {
        if (!n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      h.hidden = !any;
    });
    [].forEach.call(document.querySelectorAll(".weekbar"), function (h) {
      var any = false, n = h.nextElementSibling;
      while (n && !n.classList.contains("weekbar")) {
        if (n.classList.contains("q") && !n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      h.hidden = !any;
    });

    var narrowed = filters.status !== "all";
    [].forEach.call(document.querySelectorAll(".family"), function (f) {
      if (filters.family && f.dataset.family !== filters.family) { f.hidden = true; return; }
      if (f.dataset.count === "0") { f.hidden = !!narrowed; return; }
      f.hidden = !f.querySelector(".q:not([hidden])");
    });
    byId("empty").hidden = shown > 0;
    indexVisible();
    paintPos();
    paintChips();
  }

  function setStatus(s) { filters.status = s; applyFilters(); }

  /* ---------- where you are in the stream ---------- */

  /* The stream runs from the first question to the last in one scroll - 279 of
     them in endo - so the bar pinned to the bottom of the viewport is the only
     thing that says where you are, and the only way back to the question you
     were on before you scrolled off to check something.

     Position is read from an IntersectionObserver rather than measured on
     scroll. Asking this many nodes where they are on every scroll event costs
     frames, and a hidden question is not rendered and so never intersects,
     which means the filters fall out of it for free. */

  var VISIBLE = [];                  // qids passing the filters, in stream order
  var VINDEX = Object.create(null);  // qid -> its place in VISIBLE
  var inView = Object.create(null);  // qids currently crossing the sight line
  var CURRENT = null;                // the question at the top of the viewport
  var ANCHOR = null;                 // the question to offer a way back to
  var RESUMING = false;              // showing the reopen offer, not the marker
  var posReady = false;
  var scrollQueued = false;

  /* read off the DOM, not off QUESTIONS: the stream is built family by family,
     so its order is not the order the JSON happens to arrive in */
  function indexVisible() {
    VISIBLE = [];
    VINDEX = Object.create(null);
    [].forEach.call(document.querySelectorAll("#stream .q"), function (art) {
      if (art.hidden) return;
      VINDEX[art.dataset.qid] = VISIBLE.length;
      VISIBLE.push(art.dataset.qid);
    });
  }

  function topmostInView() {
    var best = null, bestAt = Infinity;
    Object.keys(inView).forEach(function (qid) {
      var i = VINDEX[qid];
      if (i !== undefined && i < bestAt) { bestAt = i; best = qid; }
    });
    return best;
  }

  function onIntersect(entries) {
    entries.forEach(function (e) {
      var qid = e.target.dataset.qid;
      if (e.isIntersecting) inView[qid] = true;
      else delete inView[qid];
    });
    var top = topmostInView();
    if (top) CURRENT = top;   // between two questions, the last one still holds
    paintPos();
  }

  function goTo(qid) {
    var art = byId("q-" + qid);
    if (!art) return;
    var top = art.getBoundingClientRect().top + window.pageYOffset - 16;
    var still = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    try { window.scrollTo({ top: top, behavior: still ? "auto" : "smooth" }); }
    catch (e) { window.scrollTo(0, top); }
    CURRENT = qid;
    paintPos();
  }

  function step(delta) {
    if (!VISIBLE.length) return;
    var i = (CURRENT && VINDEX[CURRENT] !== undefined) ? VINDEX[CURRENT] : 0;
    var j = i + delta;
    if (j < 0 || j >= VISIBLE.length) return;
    goTo(VISIBLE[j]);
  }

  function setAnchor(qid) {
    ANCHOR = qid;
    RESUMING = false;
    paintPos();
  }

  /* lastTs has been written on every answer all along and read by nothing, so
     the question you last touched costs no new storage and already rides along
     in the JSON backup */
  function resumePoint() {
    var best = null, bestTs = 0;
    Object.keys(progress).forEach(function (qid) {
      if (QMAP[qid] && progress[qid].lastTs > bestTs) {
        bestTs = progress[qid].lastTs;
        best = qid;
      }
    });
    return best;
  }

  function paintMark(at) {
    var mk = byId("pb-mark");
    if (RESUMING && ANCHOR && QMAP[ANCHOR]) {
      mk.hidden = false;
      mk.textContent = "Resume at Q" + QMAP[ANCHOR].num +
                       " \u00b7 " + QMAP[ANCHOR].lecture;
      return;
    }
    // no anchor, filtered away, or near enough that a button would be noise
    if (!ANCHOR || VINDEX[ANCHOR] === undefined || at === null) {
      mk.hidden = true;
      return;
    }
    var away = VINDEX[ANCHOR] - at;
    if (Math.abs(away) < 2) { mk.hidden = true; return; }
    mk.hidden = false;
    mk.textContent = (away < 0 ? "\u2191" : "\u2193") +
                     " back to Q" + QMAP[ANCHOR].num;
  }

  function paintPos() {
    if (!posReady) return;
    var bar = byId("posbar");
    /* out of the way until you are actually into the stream, except when there
       is a spot to reopen at - that offer has to be visible from the top */
    if (!VISIBLE.length || !(RESUMING || window.pageYOffset > 400)) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;

    if (!CURRENT || VINDEX[CURRENT] === undefined) {
      CURRENT = topmostInView() || VISIBLE[0];
    }
    var at = VINDEX[CURRENT] === undefined ? null : VINDEX[CURRENT];
    var q = QMAP[CURRENT];

    byId("pb-where").textContent = q ? (q.weekLabel + " \u00b7 " + q.lecture) : "";
    byId("pb-count").textContent = (at === null ? "\u2013" : String(at + 1)) +
      " / " + VISIBLE.length +
      ((filters.status !== "all" || filters.family) ? " shown" : "");
    byId("pb-prev").disabled = at === null || at === 0;
    byId("pb-next").disabled = at === null || at === VISIBLE.length - 1;
    paintMark(at);
  }

  function onScroll() {
    if (scrollQueued) return;
    scrollQueued = true;
    window.requestAnimationFrame(function () {
      scrollQueued = false;
      // scrolling in is answer enough: the offer gives way to the live marker
      if (RESUMING && window.pageYOffset > 240) RESUMING = false;
      paintPos();
    });
  }

  function onKey(e) {
    if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;
    if (byId("panel-questions").hidden) return;
    var t = e.target;
    if (t && (t.isContentEditable ||
              /^(input|textarea|select)$/i.test(t.tagName || ""))) return;
    if (e.key === "j") { e.preventDefault(); step(1); }
    else if (e.key === "k") { e.preventDefault(); step(-1); }
    else if (e.key === "b" && ANCHOR) {
      e.preventDefault();
      RESUMING = false;
      goTo(ANCHOR);
    }
  }

  /* a browser without IntersectionObserver gets the stream exactly as it was,
     which is better than a bar that cannot say where it is */
  function initPos() {
    if (!window.IntersectionObserver) return;
    posReady = true;

    // the sight line is the top fifth of the viewport
    var obs = new window.IntersectionObserver(onIntersect,
      { rootMargin: "0px 0px -80% 0px" });
    [].forEach.call(document.querySelectorAll("#stream .q"), function (art) {
      obs.observe(art);
    });

    byId("pb-prev").addEventListener("click", function () { step(-1); });
    byId("pb-next").addEventListener("click", function () { step(1); });
    byId("pb-mark").addEventListener("click", function () {
      if (!ANCHOR) return;
      RESUMING = false;
      goTo(ANCHOR);
    });
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("keydown", onKey);

    var r = resumePoint();
    if (r && matches(r)) { ANCHOR = r; RESUMING = true; }
    paintPos();
  }

  /* ---------- rail ---------- */

  var STATUS_DEFS = [
    { k: "all", label: "All" },
    { k: "unseen", label: "Unseen" },
    { k: "wrong", label: "Wrong", cls: "wrongish" },
    { k: "correct", label: "Correct" },
    { k: "starred", label: "Starred", cls: "starish" }
  ];

  function counts() {
    var c = { all: QUESTIONS.length, unseen: 0, wrong: 0, correct: 0, starred: 0 };
    QUESTIONS.forEach(function (q) {
      var st = stateOf(q.qid);
      if (st === "unseen") c.unseen++;
      else if (st === "wrong") c.wrong++;
      else c.correct++;
      if (isStarred(q.qid)) c.starred++;
    });
    return c;
  }

  function paintChips() {
    var c = counts();
    [].forEach.call(document.querySelectorAll("#status-chips .chip"), function (b) {
      b.setAttribute("aria-pressed", filters.status === b.dataset.k ? "true" : "false");
      b.querySelector(".n").textContent = c[b.dataset.k];
    });
    [].forEach.call(document.querySelectorAll("#fam-btns .fam-btn"), function (b) {
      var k = b.dataset.k || null;
      b.setAttribute("aria-pressed", filters.family === k ? "true" : "false");
    });
    byId("review-wrong").disabled = c.wrong === 0;
    byId("review-n").textContent = c.wrong;
    if (RESET_SHOWN_IDLE) RESET_SHOWN_IDLE();
  }

  function paintStats() {
    var attempted = 0, wrong = 0, starred = 0, ok = 0;
    QUESTIONS.forEach(function (q) {
      var st = stateOf(q.qid);
      if (st !== "unseen") {
        attempted++;
        if (st === "wrong") wrong++; else ok++;
      }
      if (isStarred(q.qid)) starred++;
    });
    byId("sc-done").textContent = attempted;
    byId("sc-first").textContent = attempted ? Math.round(ok / attempted * 100) + "%" : "–";
    byId("sc-wrong").textContent = wrong;
    byId("sc-star").textContent = starred;
    paintChips();
  }

  /* ---------- boot ---------- */

  /* the eyebrow is written by pom2.js instead - it has to be right even when
     the page opens on the notes tab and none of this has run */
  function buildMasthead() {
    byId("sc-of").textContent = "/" + QUESTIONS.length;
  }

  function buildRail() {
    var famCount = {};
    QUESTIONS.forEach(function (q) { famCount[q.family] = (famCount[q.family] || 0) + 1; });

    var fb = byId("fam-btns");
    var rows = [{ key: null, name: "All question sets", n: QUESTIONS.length, all: true }];
    FAMILIES.forEach(function (f) {
      rows.push({ key: f.key, name: f.name, n: famCount[f.key] || 0 });
    });
    rows.forEach(function (r) {
      var b = el("button", "fam-btn" + (r.all ? " is-all" : ""));
      b.type = "button";
      if (r.key) b.dataset.k = r.key;
      b.disabled = r.n === 0;
      b.setAttribute("aria-pressed", r.key === null ? "true" : "false");
      b.appendChild(el("span", "fn", r.name));
      b.appendChild(el("span", "fc", r.n ? String(r.n) : "none"));
      b.addEventListener("click", function () {
        filters.family = (r.key === null || filters.family === r.key) ? null : r.key;
        applyFilters();
      });
      fb.appendChild(b);
    });

    var sc = byId("status-chips");
    STATUS_DEFS.forEach(function (d) {
      var b = el("button", "chip" + (d.cls ? " " + d.cls : ""));
      b.type = "button";
      b.dataset.k = d.k;
      b.setAttribute("aria-pressed", d.k === "all" ? "true" : "false");
      b.appendChild(document.createTextNode(d.label));
      b.appendChild(el("span", "n", "0"));
      b.addEventListener("click", function () { setStatus(d.k); });
      sc.appendChild(b);
    });

    byId("review-wrong").addEventListener("click", function () { setStatus("wrong"); });

    // reset only what is on screen right now
    var rs = byId("reset-shown"), rsArmed = false, rsTimer = null;
    function rsIdle() {
      rsArmed = false;
      rs.classList.remove("armed");
      rs.textContent = "Reset the questions shown (" + shownWithProgress().length + ")";
      rs.disabled = shownWithProgress().length === 0;
    }
    rs.addEventListener("click", function () {
      var hit = shownWithProgress();
      if (!hit.length) return;
      if (!rsArmed) {
        rsArmed = true;
        rs.classList.add("armed");
        rs.textContent = "Clear these " + hit.length + ", click to confirm";
        rsTimer = setTimeout(rsIdle, 5000);
        return;
      }
      clearTimeout(rsTimer);
      hit.forEach(forget);
      rsIdle();
    });
    RESET_SHOWN_IDLE = rsIdle;

    var ra = byId("reset-all"), armed = false, timer = null;
    function raIdle() {
      armed = false;
      ra.classList.remove("armed");
      ra.textContent = "Reset all progress";
    }
    ra.addEventListener("click", function () {
      if (!armed) {
        armed = true;
        ra.classList.add("armed");
        ra.textContent = "Erase every answer in " + BLOCK.name + ", click to confirm";
        timer = setTimeout(raIdle, 5000);
        return;
      }
      clearTimeout(timer);
      raIdle();
      Object.keys(progress).slice().forEach(forget);
    });

    buildBackup();
  }

  /* localStorage is per-browser and the browser can clear it, so the progress
     has to be liftable out of here by hand. One file carries every block: the
     browser keeps all of them under the same key prefix, and a page that can
     read its own key can read its neighbours' just as well. */

  var SLUG_OK = /^[a-z0-9][a-z0-9_-]*$/i;

  function readStored(slug) {
    var raw = null;
    try { raw = window.localStorage.getItem(STORE_PREFIX + slug); }
    catch (e) { return null; }
    if (!raw) return null;
    var parsed;
    try { parsed = JSON.parse(raw); }
    catch (e) { return null; }
    return (parsed && typeof parsed === "object") ? parsed : null;
  }

  /* every block this browser has answered anything in, read off the keys rather
     than a list - the block list stays in tools/, and five stays unspecial */
  function everyBlock() {
    var out = {}, i, key, slug, data;
    try {
      for (i = 0; i < window.localStorage.length; i++) {
        key = window.localStorage.key(i);
        if (!key || key.indexOf(STORE_PREFIX) !== 0) continue;
        slug = key.slice(STORE_PREFIX.length);
        data = readStored(slug);
        if (data) out[slug] = data;
      }
    } catch (e) { /* the scan was refused; the open block still lands below */ }
    out[BLOCK.slug] = progress;   // what is in memory is at least as new
    return out;
  }

  /* a restore adds and advances, it never erases: a record older than the one
     already here loses. That is what makes restoring a stale file safe, and
     what makes it safe to restore onto a machine already part way through. */
  function newer(have, inc) {
    var a = (have && typeof have.lastTs === "number") ? have.lastTs : -1;
    var b = (inc && typeof inc.lastTs === "number") ? inc.lastTs : 0;
    return b > a;
  }

  function buildBackup() {
    byId("export-progress").addEventListener("click", function () {
      var payload = {
        store: "nsq",
        version: 2,
        exported: new Date().toISOString(),
        blocks: everyBlock()
      };
      var url = URL.createObjectURL(
        new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" }));
      var a = document.createElement("a");
      a.href = url;
      /* dated, because the browser otherwise stacks these up as (1), (2) and
         there is no telling them apart from the outside */
      a.download = "pom2-progress-" + new Date().toISOString().slice(0, 10) + ".json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });

    var file = byId("import-file");
    byId("import-progress").addEventListener("click", function () { file.click(); });
    file.addEventListener("change", function () {
      var f = file.files && file.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () { restore(String(reader.result)); };
      reader.readAsText(f);
      file.value = "";
    });
  }

  /* a v2 file holds every block at once. A v1 file held one, named beside it -
     those still restore, they just restore the one. */
  function blocksInFile(parsed) {
    if (!parsed || typeof parsed !== "object") return null;
    if (parsed.blocks && typeof parsed.blocks === "object") return parsed.blocks;
    if (parsed.progress && typeof parsed.progress === "object") {
      var one = {};
      one[typeof parsed.block === "string" ? parsed.block : BLOCK.slug] = parsed.progress;
      return one;
    }
    return null;
  }

  function restore(text) {
    var parsed;
    try { parsed = JSON.parse(text); }
    catch (e) { note("That file is not valid JSON, so nothing was imported."); return; }

    var incoming = blocksInFile(parsed);
    if (!incoming) { note("No progress records found in that file."); return; }

    var here = 0, away = 0, elsewhere = [];

    Object.keys(incoming).forEach(function (slug) {
      var set = incoming[slug];
      if (!SLUG_OK.test(slug) || !set || typeof set !== "object") return;

      if (slug === BLOCK.slug) {
        Object.keys(set).forEach(function (qid) {
          var r = sanitize(qid, set[qid]);
          if (r && newer(progress[qid], r)) { progress[qid] = r; here++; }
        });
        return;
      }

      /* another block's records go to storage unchecked. Its own page sanitizes
         everything it loads against its own question list, so nothing
         unrecognised can reach the screen, and this page has no list to check
         them against without fetching a second question file. */
      var store = readStored(slug) || {}, n = 0;
      Object.keys(set).forEach(function (qid) {
        var inc = set[qid];
        if (!inc || typeof inc !== "object") return;
        if (newer(store[qid], inc)) { store[qid] = inc; n++; }
      });
      if (!n) return;
      try { window.localStorage.setItem(STORE_PREFIX + slug, JSON.stringify(store)); }
      catch (e) { return; }
      away += n;
      elsewhere.push(slug);
    });

    if (!here && !away) {
      note("Nothing in that file was newer than what is already here, so nothing changed.");
      return;
    }

    save();
    QUESTIONS.forEach(function (q) { paintQuestion(q.qid); });
    paintStats();
    applyFilters();

    var msg = here + " question" + (here === 1 ? "" : "s") + " restored in " + BLOCK.name + ".";
    if (away) {
      msg += " Another " + away + " in " + elsewhere.join(", ") +
             ", which appear when you open those blocks.";
    }
    note(msg);
  }

  function buildStream() {
    var stream = byId("stream"), frag = document.createDocumentFragment();
    FAMILIES.forEach(function (f) {
      var mine = QUESTIONS.filter(function (q) { return q.family === f.key; });
      var sec = el("section", "family");
      sec.dataset.family = f.key;
      sec.dataset.count = String(mine.length);

      var head = el("div", "fam-head");
      head.appendChild(el("p", "fam-meta",
        mine.length ? mine.length + " questions" : "nothing transcribed yet"));
      head.appendChild(el("h2", null, f.name));
      head.appendChild(el("p", null, f.blurb));
      sec.appendChild(head);

      if (!mine.length) {
        sec.appendChild(el("p", "fam-empty",
          "No " + f.name.toLowerCase() + " questions exist for this block yet. When they are written, they appear here."));
      }

      var lastWeek = null, lastLecture = null;
      mine.forEach(function (q) {
        if (q.weekLabel !== lastWeek) {
          lastWeek = q.weekLabel;
          lastLecture = null;
          var wb = el("div", "weekbar");
          wb.appendChild(el("h3", null, q.weekLabel));
          sec.appendChild(wb);
        }
        if (q.lecture !== lastLecture) {
          lastLecture = q.lecture;
          var lb = el("div", "lecbar");
          lb.appendChild(el("h4", null, q.lecture));
          if (q.lectureMeta) lb.appendChild(el("p", null, q.lectureMeta.replace(/\[\[|\]\]/g, "")));
          sec.appendChild(lb);
        }
        sec.appendChild(buildQuestion(q));
      });
      frag.appendChild(sec);
    });
    var empty = el("div", "empty", "Nothing matches that filter.");
    empty.id = "empty";
    empty.hidden = true;
    frag.appendChild(empty);
    stream.innerHTML = "";
    stream.appendChild(frag);
  }

  function start(data) {
    QUESTIONS = data;
    QUESTIONS.forEach(function (q) { QMAP[q.qid] = q; });
    load();
    buildMasthead();
    buildRail();
    buildStream();
    paintStats();
    applyFilters();
    QUESTIONS.forEach(function (q) { paintQuestion(q.qid); });
    initPos();
    if (!storeWritable) {
      note("This browser will not let the page use local storage, so answers cannot be saved. Every question still works.");
    }
  }

  /* the tab strip calls this the first time Questions is opened; a second call
     is a no-op so switching tabs never refetches or rebuilds the stream */
  var booted = false;

  window.POM2_QUIZ = {
    boot: function () {
      if (booted) return;
      booted = true;
      fetch("data/questions/" + BLOCK.slug + ".json")
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(start)
        .catch(function () {
          byId("stream").innerHTML = "";
          var e = el("div", "empty",
            "The question set could not be loaded. If you are opening this file straight from disk, serve the folder over HTTP instead - browsers block local fetches.");
          byId("stream").appendChild(e);
        });
    }
  };
})();
