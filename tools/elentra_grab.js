/* Grab an Elentra exam off the page it is being displayed on.
 *
 * This is the readable source of the bookmarklet. tools/make_bookmarklet.py
 * turns it into the javascript: URL that actually goes in the bookmark bar.
 *
 * It reads a page two ways. `elentraScan` knows the markup Schulich's Elentra
 * actually renders and reads it exactly, key and rationale included. Anything
 * that shape does not cover falls through to a structural reader: a group of
 * radios or checkboxes sharing a name is one question, its container is the
 * smallest ancestor holding that group and nothing else's, and the correct
 * answer is guessed from the classes and icons around each option.
 *
 * Both paths record the class names they saw in a `signals` array and keep each
 * question's own outerHTML, because the first version of this was pure guesswork
 * and it took one real capture to show that guessing `right` in a class name
 * matches Bootstrap's `space-right` and marks every option correct. The signals
 * are what made that a five-minute fix rather than another trip to the LMS.
 *
 * Run it on the feedback view after submitting, `?section=feedback&progress_id=N`:
 * that is the only view carrying the key. Run it once per page if the review
 * paginates - captures accumulate in localStorage under one id and Download
 * writes the merge.
 */
(function () {
  'use strict';

  var NS = 'pom2.elentra.';
  var MAX_HTML = 24000;          // per-question outerHTML kept, in chars
  var MAX_PAGE_HTML = 400000;    // whole-body fallback, only when nothing parsed

  var SKIP = 'nav,header,footer,aside,.navbar,#header,#footer,' +
             '[role=navigation],[role=search],[role=banner],[role=contentinfo]';
  var LANDMARK = 'body,main,form,[role=main],#content,#container,#wrapper,#page';
  var FEEDBACK = '[class*=feedback],[class*=rationale],[class*=explanation],' +
                 '[class*=comment],[id*=feedback],[id*=rationale]';

  var RX_WRONG = /incorrect|wrong|danger|fa-times|fa-xmark|fa-close|times-circle|x-circle|cross|missed/i;
  /* no bare `right` here: Elentra's own option rows carry Bootstrap's
     `space-right` and `pull-right`, and matching those marked every option
     correct on the first real capture */
  var RX_RIGHT = /(?:^|[\s_-])correct|answer-key|success|fa-check|check-circle|checkmark/i;
  var RX_LETTER = /^\s*[\(\[]?([A-Ha-h])[\)\].:,\-]\s+/;
  var RX_QNUM = /\b(?:question|item|q)\s*#?\s*(\d+)/i;
  var RX_KEYLINE = /correct\s+(?:answer|response|option)(?:\s+is)?\s*[:\-]?\s*[\(\[]?([A-H])\b/i;

  /* ---------- small helpers ---------- */

  function txt(el) {
    if (!el) return '';
    return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  }
  function attr(el, name) {
    return (el && el.getAttribute && el.getAttribute(name)) || '';
  }
  function esc(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/["\\\]\[#.:]/g, '\\$&');
  }
  function matches(el, sel) {
    if (!el || el.nodeType !== 1) return false;
    var f = el.matches || el.msMatchesSelector || el.webkitMatchesSelector;
    try { return f.call(el, sel); } catch (e) { return false; }
  }
  function closest(el, sel) {
    while (el && el.nodeType === 1) { if (matches(el, sel)) return el; el = el.parentElement; }
    return null;
  }
  function arr(list) { return Array.prototype.slice.call(list || []); }
  function clip(s, n) { return s && s.length > n ? s.slice(0, n) + '\n<!-- truncated -->' : s; }

  /* Every document we are allowed to read: this one plus same-origin frames.
     Elentra has been known to run the exam player inside an iframe. */
  function docs() {
    var out = [document];
    arr(document.querySelectorAll('iframe,frame')).forEach(function (f) {
      try {
        var d = f.contentDocument;
        if (d && d.body) out.push(d);
      } catch (e) { /* cross-origin, nothing to be done */ }
    });
    return out;
  }

  function ancestors(el) {
    var a = [];
    while (el) { a.push(el); el = el.parentElement; }
    return a;
  }
  function commonAncestor(nodes) {
    var chain = ancestors(nodes[0]);
    for (var i = 1; i < nodes.length; i++) {
      var mine = ancestors(nodes[i]), hit = null;
      for (var j = 0; j < chain.length; j++) {
        if (mine.indexOf(chain[j]) >= 0) { hit = chain[j]; break; }
      }
      if (!hit) return nodes[0].ownerDocument.body;
      chain = ancestors(hit);
    }
    return chain[0];
  }

  /* Climb until the stem is inside, but stop before swallowing the page. */
  function expand(el, own) {
    var hops = 0;
    while (el && el.parentElement && hops < 8) {
      var p = el.parentElement;
      if (matches(p, LANDMARK)) break;
      if (p.querySelector(SKIP)) break;
      var extra = arr(p.querySelectorAll('input[type=radio],input[type=checkbox]'))
                    .some(function (i) { return own.indexOf(i) < 0; });
      if (extra) break;
      el = p; hops++;
    }
    return el;
  }

  /* ---------- options ---------- */

  function labelFor(inp, container) {
    var d = inp.ownerDocument;
    if (inp.id) {
      var l = d.querySelector('label[for="' + esc(inp.id) + '"]');
      if (l) return l;
    }
    var wrap = closest(inp, 'label');
    if (wrap) return wrap;
    /* largest ancestor below the container that still holds only this input */
    var best = inp.parentElement, p = inp.parentElement, depth = 0;
    while (p && p !== container && depth < 5) {
      if (p.querySelectorAll('input[type=radio],input[type=checkbox]').length !== 1) break;
      best = p; p = p.parentElement; depth++;
    }
    return best;
  }

  function optionSignals(label, inp, container) {
    var out = [], n = label, hops = 0;
    if (label) {
      arr(label.querySelectorAll('i,svg,img,span')).slice(0, 8).forEach(function (ic) {
        var c = attr(ic, 'class');
        var t = attr(ic, 'title') || attr(ic, 'alt') || attr(ic, 'aria-label');
        if (c) out.push('icon:' + c);
        if (t) out.push('icon-title:' + t);
      });
    }
    while (n && hops < 6) {
      var c = attr(n, 'class');
      if (c) out.push('class:' + c);
      ['title', 'aria-label', 'data-correct', 'data-answer', 'data-status'].forEach(function (a) {
        var v = attr(n, a);
        if (v) out.push(a + '=' + v);
      });
      if (n === container) break;
      n = n.parentElement; hops++;
    }
    if (inp.checked) out.push('state:checked');
    if (inp.disabled) out.push('state:disabled');
    return out;
  }

  function verdict(signals) {
    var joined = signals.join(' ');
    if (RX_WRONG.test(joined)) return 'wrong';
    if (RX_RIGHT.test(joined)) return 'right';
    return '';
  }

  /* ---------- one question ---------- */

  function buildQuestion(name, inputs, index) {
    var container = expand(commonAncestor(inputs), inputs);

    var opts = inputs.map(function (inp, i) {
      var label = labelFor(inp, container);
      var raw = txt(label);
      var m = raw.match(RX_LETTER);
      return {
        letter: String.fromCharCode(65 + i),
        sourceLetter: m ? m[1].toUpperCase() : '',
        text: m ? raw.slice(m[0].length) : raw,
        html: label ? label.innerHTML.replace(/<input\b[^>]*>/gi, '').trim() : '',
        value: inp.value || '',
        chosen: !!inp.checked,
        signals: optionSignals(label, inp, container),
        el: label
      };
    });

    opts.forEach(function (o) { o.verdict = verdict(o.signals); });

    /* feedback / rationale blocks, kept out of the stem */
    var fbEls = arr(container.querySelectorAll(FEEDBACK)).filter(function (f) {
      return !opts.some(function (o) { return o.el && o.el.contains(f); });
    });

    /* stem = the container with options, feedback and controls cut out */
    opts.forEach(function (o, i) { if (o.el) o.el.setAttribute('data-pom2-opt', i); });
    fbEls.forEach(function (f, i) { f.setAttribute('data-pom2-fb', i); });
    var clone = container.cloneNode(true);
    arr(clone.querySelectorAll('[data-pom2-opt],[data-pom2-fb],input,textarea,select,button,script,style'))
      .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    var stemHtml = clone.innerHTML.replace(/\s+/g, ' ').trim();
    var stemText = txt(clone);
    opts.forEach(function (o) { if (o.el) o.el.removeAttribute('data-pom2-opt'); });
    fbEls.forEach(function (f) { f.removeAttribute('data-pom2-fb'); });

    var all = txt(container);

    /* a key stated in prose beats a guessed class name */
    var keyLine = all.match(RX_KEYLINE);
    if (keyLine) {
      var want = keyLine[1].toUpperCase();
      opts.forEach(function (o) {
        if (o.sourceLetter === want || o.letter === want) o.verdict = o.verdict || 'right';
      });
    }

    var kind = inputs[0].type === 'checkbox' ? 'multi' : 'mcq';
    var labels = opts.map(function (o) { return o.text.toLowerCase().trim(); }).join('|');
    if (opts.length === 2 && /^(true|t)\|(false|f)$/.test(labels)) kind = 'tf';

    return {
      id: (name.match(/(\d{2,})/) || [])[1] || ('n' + index),
      inputName: name,
      number: (stemText.match(RX_QNUM) || all.match(RX_QNUM) || [])[1] || '',
      kind: kind,
      stemText: stemText,
      stemHtml: stemHtml,
      options: opts.map(function (o) {
        return {
          letter: o.letter, sourceLetter: o.sourceLetter, text: o.text,
          html: o.html, value: o.value, chosen: o.chosen,
          verdict: o.verdict, signals: o.signals
        };
      }),
      correct: opts.filter(function (o) { return o.verdict === 'right'; })
                   .map(function (o) { return o.letter; }),
      chosen: opts.filter(function (o) { return o.chosen; })
                  .map(function (o) { return o.letter; }),
      feedback: fbEls.map(function (f) { return { text: txt(f), html: f.innerHTML.trim() }; }),
      containerText: all,
      html: clip(container.outerHTML, MAX_HTML),
      _c: container
    };
  }

  /* short answer / essay: a textarea or text box no MCQ has claimed */
  function buildWritten(el, claimed, index) {
    if (closest(el, SKIP)) return null;
    /* Elentra puts a ScratchPad textarea under every question; it is the
       student's own jotting, not a short-answer response */
    if (attr(el, 'data-type') === 'learner_comments') return null;
    if (closest(el, '.learner_comments')) return null;
    var name = el.name || el.id || '';
    if (/search|filter|login|user|pass|token|csrf/i.test(name)) return null;
    if (claimed.some(function (c) { return c.contains(el); })) return null;
    var container = expand(el.parentElement || el, []);
    if (claimed.some(function (c) { return c.contains(container) || container.contains(c); })) return null;
    var clone = container.cloneNode(true);
    arr(clone.querySelectorAll(FEEDBACK + ',input,textarea,select,button,script,style'))
      .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    return {
      id: (name.match(/(\d{2,})/) || [])[1] || ('w' + index),
      inputName: name,
      number: (txt(clone).match(RX_QNUM) || [])[1] || '',
      kind: 'short',
      stemText: txt(clone),
      stemHtml: clone.innerHTML.replace(/\s+/g, ' ').trim(),
      options: [],
      correct: [],
      chosen: [],
      response: el.value || txt(el),
      feedback: arr(container.querySelectorAll(FEEDBACK)).map(function (f) {
        return { text: txt(f), html: f.innerHTML.trim() };
      }),
      containerText: txt(container),
      html: clip(container.outerHTML, MAX_HTML),
      _c: container
    };
  }

  /* ---------- the shape Elentra actually renders ----------

     Confirmed against Schulich's feedback view, `?section=feedback&progress_id=N`,
     in September 2026. One `.exam-question` per question, holding a
     `[data-type=question_text]` stem, a `tr.question-answer-view` per option
     carrying `answer-correct` or `answer-incorrect`, and a `.feedback-report`
     of `<h5>Label: value</h5>` lines - Points, Correct Answer, Rationale.

     The key is therefore stated twice, and both are read. The prose line wins:
     a class name is a theme's business and can be restyled out from under this,
     whereas "Correct Answer: A" is the page telling the student the answer and
     cannot quietly stop being true. */

  function reportFields(report) {
    var out = {};
    arr((report && report.querySelectorAll('h5')) || []).forEach(function (h) {
      var m = txt(h).match(/^([^:]{1,40}):\s*(.*)$/);
      if (m) out[m[1].trim().toLowerCase()] = m[2].trim();
    });
    return out;
  }

  function elentraScan(doc) {
    var out = [];
    arr(doc.querySelectorAll('.exam-question')).forEach(function (root) {
      var rows = arr(root.querySelectorAll('.question-answer-view'));
      if (!rows.length) return;

      var stemEl = root.querySelector('[data-type=question_text]');
      var report = root.querySelector('.feedback-report');
      var fields = reportFields(report);
      var table = root.querySelector('.question-table');

      var opts = rows.map(function (row, j) {
        var inp = row.querySelector('input[type=radio],input[type=checkbox]');
        var textEl = row.querySelector('[data-type=answer_text]');
        var cls = ' ' + (attr(row, 'class') || '') + ' ';
        var letter = (inp && attr(inp, 'data-answer-letter')) ||
                     txt(row.querySelector('.question-letter')).replace(/[^A-Za-z]/g, '') ||
                     String.fromCharCode(65 + j);
        return {
          letter: letter.toUpperCase(),
          sourceLetter: letter.toUpperCase(),
          text: txt(textEl) || txt(row),
          html: textEl ? textEl.innerHTML.trim() : '',
          value: attr(row, 'data-qanswer-id') || (inp && inp.value) || '',
          chosen: !!(inp && inp.checked),
          verdict: /\sanswer-correct\s/.test(cls) ? 'right'
                 : (/\sanswer-incorrect\s/.test(cls) ? 'wrong' : ''),
          signals: ['class:' + (attr(row, 'class') || '')]
        };
      });

      /* "Correct Answer: A" - or "A, B, D, E" on a select-all */
      var stated = (fields['correct answer'] || '').match(/\b[A-H]\b/g) || [];
      var correct = stated.length
        ? stated
        : opts.filter(function (o) { return o.verdict === 'right'; })
              .map(function (o) { return o.letter; });
      if (stated.length) {
        opts.forEach(function (o) {
          o.verdict = stated.indexOf(o.letter) >= 0 ? 'right' : (o.chosen ? 'wrong' : '');
        });
      }

      var rationale = fields.rationale || '';
      if (/^n\s*\/?\s*a\.?$/i.test(rationale)) rationale = '';

      var inputs = arr(root.querySelectorAll('input[type=radio],input[type=checkbox]'));
      var kind = (inputs[0] && inputs[0].type === 'checkbox') ? 'multi' : 'mcq';
      var labels = opts.map(function (o) { return o.text.toLowerCase().trim(); }).join('|');
      if (opts.length === 2 && /^(true|t)\|(false|f)$/.test(labels)) kind = 'tf';

      out.push({
        id: attr(root, 'data-question-id') || attr(root, 'id') || '',
        inputName: (inputs[0] && inputs[0].name) || '',
        number: txt(root.querySelector('.question_number')).replace(/[^\d]/g, ''),
        kind: kind,
        via: 'elentra',
        flagged: /\bflagged\b/.test(attr(table, 'class')),
        points: fields.points || '',
        stemText: txt(stemEl) || txt(root.querySelector('#question_stem')),
        stemHtml: stemEl ? stemEl.innerHTML.replace(/\s+/g, ' ').trim() : '',
        options: opts,
        correct: correct,
        chosen: opts.filter(function (o) { return o.chosen; })
                    .map(function (o) { return o.letter; }),
        feedback: rationale ? [{ text: rationale, html: rationale }] : [],
        containerText: txt(root),
        html: clip(root.outerHTML, MAX_HTML),
        _c: root
      });
    });
    return out;
  }

  /* ---------- scan the page ---------- */

  function scan() {
    var found = [], seq = 0;

    docs().forEach(function (doc) {
      var native = elentraScan(doc);
      var roots = native.map(function (q) { return q._c; });
      found = found.concat(native);

      var groups = {};
      arr(doc.querySelectorAll('input[type=radio],input[type=checkbox]')).forEach(function (inp) {
        if (closest(inp, SKIP)) return;
        /* anything the native reader already understood */
        if (roots.some(function (r) { return r.contains(inp); })) return;
        var n = inp.name || ('anon:' + (inp.id || inp.value || 'x'));
        (groups[n] = groups[n] || []).push(inp);
      });
      Object.keys(groups).forEach(function (n) {
        if (groups[n].length < 2) return;                    // a lone box is a UI toggle
        if (/page|sort|filter|select.?all|agree|terms/i.test(n)) return;
        var q = buildQuestion(n, groups[n], seq++);
        if (!q.stemText && !q.options.length) return;
        found.push(q);
      });

      var claimed = found.map(function (f) { return f._c; }).filter(Boolean);
      arr(doc.querySelectorAll('textarea,input[type=text]')).forEach(function (el) {
        var w = buildWritten(el, claimed, seq++);
        if (w) { found.push(w); claimed.push(w._c); }
      });
    });

    found.forEach(function (q) { delete q._c; });
    return found;
  }

  /* ---------- probe ----------
     The Rise grab never reads the page: Rise ships the whole course as one
     runtime-data.js and the bookmarklet just fetches it. If Elentra's exam
     player has anything of that kind - an API call, a bootstrapped global, an
     inline JSON island - then scraping the DOM is the wrong approach and this
     is what says so. It reports what the page loaded and what it is holding;
     it does not fetch or open anything. */

  function probe() {
    var res = [], frames = [];
    function walk(w) {
      try { frames.push(w.location.href); } catch (e) { frames.push('[cross-origin]'); }
      try {
        w.performance.getEntriesByType('resource').forEach(function (r) {
          res.push({ url: r.name, type: r.initiatorType, size: r.transferSize || 0 });
        });
      } catch (e) { /* no timing api here */ }
      try { for (var i = 0; i < w.frames.length; i++) walk(w.frames[i]); } catch (e) { /* nope */ }
    }
    try { walk(window.top); } catch (e) { walk(window); }

    /* anything that smells like data rather than a stylesheet or a sprite */
    var interesting = res.filter(function (r) {
      return /(?:xmlhttprequest|fetch)/i.test(r.type) ||
             /\.json|\/api\/|api\.php|runtime-data|\bdata\b.*\.js(\?|$)/i.test(r.url);
    });

    var islands = [];
    docs().forEach(function (d) {
      arr(d.querySelectorAll('script')).forEach(function (s) {
        var t = s.textContent || '';
        if (s.src || t.length < 40) return;
        if (!/question|answer|choice|response|exam|quiz/i.test(t)) return;
        islands.push({ type: attr(s, 'type') || 'text/javascript', text: clip(t, 8000) });
      });
    });

    var globals = [];
    try {
      Object.getOwnPropertyNames(window).forEach(function (k) {
        if (globals.length > 40) return;
        if (!/exam|quiz|question|attempt|assessment|item|answer/i.test(k)) return;
        var v;
        try { v = window[k]; } catch (e) { return; }
        if (!v || typeof v !== 'object') return;
        var json;
        try { json = JSON.stringify(v); } catch (e) { return; }
        if (!json || json.length < 40) return;
        globals.push({ name: k, size: json.length, value: clip(json, 8000) });
      });
    } catch (e) { /* exotic window, skip it */ }

    var forms = [];
    docs().forEach(function (d) {
      arr(d.querySelectorAll('form')).forEach(function (f) {
        forms.push({ action: f.action || '', method: f.method || '' });
      });
    });

    return {
      schema: 'pom2-elentra-probe/1',
      at: new Date().toISOString(),
      url: location.href,
      frames: frames,
      forms: forms,
      dataRequests: interesting,
      allResources: res.map(function (r) { return r.url; }).slice(0, 400),
      scriptIslands: islands,
      globals: globals
    };
  }

  /* ---------- store ---------- */

  function param(k) {
    var m = new RegExp('[?&]' + k + '=([^&#]*)').exec(location.search);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /* the feedback view drops `id` and carries only `progress_id`, so one attempt
     is keyed by whichever the URL offers */
  var examId = param('id') || param('progress_id') || 'unknown';
  var key = NS + examId;

  function load() {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; }
  }
  function save(store) {
    try { localStorage.setItem(key, JSON.stringify(store)); return true; }
    catch (e) { window.__pom2Elentra = store; return false; }
  }

  function pageTitle() {
    var h = document.querySelector('h1,h2,.page-title,#page-title');
    return txt(h) || document.title || '';
  }

  var store = load() || window.__pom2Elentra || {
    schema: 'pom2-elentra-grab/1',
    examId: examId,
    origin: location.origin,
    title: pageTitle(),
    captures: [],
    questions: {}
  };
  if (!store.title) store.title = pageTitle();

  var questions = scan();
  var pageKey = location.pathname + location.search;

  questions.forEach(function (q, i) {
    var id = q.id || ('p' + store.captures.length + '-' + i);
    var prev = store.questions[id];
    q.page = pageKey;
    q.order = (prev && prev.order) || (Object.keys(store.questions).length + 1);
    /* a later pass that lost the key must not erase one an earlier pass found */
    if (prev && prev.correct.length && !q.correct.length) q.correct = prev.correct;
    if (prev && prev.chosen.length && !q.chosen.length) q.chosen = prev.chosen;
    store.questions[id] = q;
  });

  store.captures.push({
    at: new Date().toISOString(),
    url: location.href,
    page: pageKey,
    progressId: param('progress_id'),
    action: param('action'),
    title: pageTitle(),
    found: questions.length,
    /* if the parser found nothing, the page itself is the only evidence left */
    bodyHtml: questions.length ? '' : clip(document.body.innerHTML, MAX_PAGE_HTML)
  });

  var persisted = save(store);
  var total = Object.keys(store.questions).length;
  var keyed = Object.keys(store.questions).filter(function (k) {
    return store.questions[k].correct.length;
  }).length;

  /* ---------- panel ---------- */

  function stamp() {
    return new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
  }

  function saveJson(name, obj) {
    var blob = new Blob([JSON.stringify(obj, null, 1)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  }

  function download() {
    saveJson('elentra-' + examId + '-' + stamp() + '.json', store);
  }

  function copy() {
    var text = JSON.stringify(store, null, 1);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
      return;
    }
    var ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) { /* nothing else to try */ }
    ta.remove();
  }

  var old = document.getElementById('pom2-elentra-panel');
  if (old) old.remove();
  var host = document.createElement('div');
  host.id = 'pom2-elentra-panel';
  host.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483647';
  var root = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;
  root.innerHTML =
    '<style>' +
    '.c{font:13px/1.45 ui-sans-serif,system-ui,sans-serif;background:#141a22;color:#e8eef5;' +
    'border:1px solid #2c3846;border-radius:10px;padding:12px 14px;width:272px;' +
    'box-shadow:0 8px 28px rgba(0,0,0,.35)}' +
    'b{color:#8fd3ff}.m{color:#9fb0c2;font-size:12px;margin:3px 0 0}' +
    '.r{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}' +
    'button{font:12px ui-sans-serif,system-ui,sans-serif;background:#22303f;color:#e8eef5;' +
    'border:1px solid #3a4a5c;border-radius:6px;padding:5px 9px;cursor:pointer}' +
    'button:hover{background:#2c3d4f}.w{color:#ffcf7a}' +
    '</style>' +
    '<div class="c">' +
    '<div><b>Exam ' + examId + '</b> - ' + questions.length + ' found on this page</div>' +
    '<div class="m">' + total + ' question' + (total === 1 ? '' : 's') + ' held, ' +
    keyed + ' with a detected key</div>' +
    (questions.length ? '' : '<div class="m w">Nothing parsed here. The page HTML went into ' +
     'the file so the parser can be fixed from it.</div>') +
    (persisted ? '' : '<div class="m w">localStorage refused the write - download now, ' +
     'leaving this page loses it.</div>') +
    '<div class="m">Paginated review? Run me again on each page.</div>' +
    '<div class="r"><button id="d">Download JSON</button><button id="c">Copy</button>' +
    '<button id="p">Probe page</button>' +
    '<button id="x">Clear exam</button><button id="q">Close</button></div>' +
    '</div>';
  document.body.appendChild(host);

  root.querySelector('#d').addEventListener('click', download);
  root.querySelector('#p').addEventListener('click', function () {
    saveJson('elentra-probe-' + examId + '-' + stamp() + '.json', probe());
  });
  root.querySelector('#c').addEventListener('click', copy);
  root.querySelector('#q').addEventListener('click', function () { host.remove(); });
  root.querySelector('#x').addEventListener('click', function () {
    try { localStorage.removeItem(key); } catch (e) { /* already gone */ }
    delete window.__pom2Elentra;
    host.remove();
  });
})();
