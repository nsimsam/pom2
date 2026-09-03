/* Tab strip for a PoM 2 block page.

   Notes and questions are two views of the same week, so they share a page.
   The block's question JSON runs to hundreds of kilobytes, so neither half is
   fetched until its tab is first opened - POM2_QUIZ.boot and POM2_NOTES.boot
   are both no-ops on a second call, which is what makes switching back free.

   The tab lives in the hash, so a link can point straight at the notes and the
   back button steps between them. */

(function () {
  "use strict";

  var BLOCK = window.QUIZ_BLOCK;

  var TABS = {
    notes: {
      tab: "tab-notes",
      panel: "panel-notes",
      board: "sb-notes",
      boot: function () { if (window.POM2_NOTES) window.POM2_NOTES.boot(); }
    },
    questions: {
      tab: "tab-questions",
      panel: "panel-questions",
      board: "sb-questions",
      boot: function () { if (window.POM2_QUIZ) window.POM2_QUIZ.boot(); }
    }
  };

  function byId(id) { return document.getElementById(id); }

  /* Notes come first when there are any - they are what you read before you
     test yourself. A block with none of them written yet would otherwise open
     on a page of nothing but gaps, so it falls through to the questions. */
  function fallback() {
    var tc = byId("tc-notes");
    var written = tc ? parseInt(tc.textContent, 10) : 0;
    return written > 0 ? "notes" : "questions";
  }

  function wanted() {
    var h = (window.location.hash || "").replace("#", "");
    return TABS[h] ? h : fallback();
  }

  function show(key) {
    Object.keys(TABS).forEach(function (k) {
      var t = TABS[k], on = k === key;
      byId(t.tab).setAttribute("aria-selected", on ? "true" : "false");
      byId(t.panel).hidden = !on;
      byId(t.board).hidden = !on;
    });
    TABS[key].boot();
  }

  function init() {
    /* quiz.js used to write this, but it only runs once questions are booted -
       landing on the notes tab would have left the masthead blank */
    byId("m-eyebrow").textContent =
      "Schulich PoM 2 · Block " + BLOCK.n + " · Weeks " + BLOCK.weeks;

    Object.keys(TABS).forEach(function (k) {
      byId(TABS[k].tab).addEventListener("click", function () {
        if (wanted() === k) { show(k); return; }
        window.location.hash = k;   // hashchange does the rest, and history keeps it
      });
    });

    window.addEventListener("hashchange", function () { show(wanted()); });
    show(wanted());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
