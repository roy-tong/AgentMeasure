/* AgentMeasure website — interaction layer
   console playback · scroll reveals · nav state · active section */

(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── nav: scrolled border ──────────────────────────────────── */
  var nav = document.querySelector(".nav");
  function onScroll() {
    if (window.scrollY > 8) nav.classList.add("scrolled");
    else nav.classList.remove("scrolled");
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ── nav: mobile toggle ────────────────────────────────────── */
  var toggle = document.getElementById("nav-toggle");
  var links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ── reveal on scroll ──────────────────────────────────────── */
  var revealEls = document.querySelectorAll(".reveal");
  if (reduced || !("IntersectionObserver" in window)) {
    revealEls.forEach(function (el) { el.classList.add("in"); });
  } else {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    revealEls.forEach(function (el) { revealObserver.observe(el); });
  }

  /* ── active nav link ───────────────────────────────────────── */
  var sectionIds = ["why", "measure", "how", "standard", "lab"];
  var navAnchors = {};
  document.querySelectorAll(".nav-links a").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (href.charAt(0) === "#") navAnchors[href.slice(1)] = a;
  });
  if ("IntersectionObserver" in window) {
    var sectionObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var a = navAnchors[entry.target.id];
        if (!a) return;
        if (entry.isIntersecting) {
          Object.values(navAnchors).forEach(function (x) { x.classList.remove("active"); });
          a.classList.add("active");
        }
      });
    }, { rootMargin: "-30% 0px -55% 0px" });
    sectionIds.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) sectionObserver.observe(el);
    });
  }

  /* ── measurement console: line-by-line playback ──────────────
     .cline starts hidden via CSS (opacity 0); each line is revealed
     by an inline style on a staggered timer. Replay resets + reruns. */
  var consoleBody = document.getElementById("console-body");
  var replayBtn = document.getElementById("console-replay");
  var playTimers = [];

  function clearTimers() {
    playTimers.forEach(function (t) { clearTimeout(t); });
    playTimers = [];
  }

  function showAllLines() {
    consoleBody.querySelectorAll(".cline").forEach(function (line) {
      line.style.opacity = "1";
      line.style.transform = "none";
    });
  }

  function resetConsole() {
    clearTimers();
    consoleBody.querySelectorAll(".cline").forEach(function (line) {
      line.style.opacity = "";
      line.style.transform = "";
    });
    /* force reflow so a replay restarts from the hidden state */
    void consoleBody.offsetHeight;
  }

  function playConsole() {
    if (!consoleBody) return;
    resetConsole();
    var lines = consoleBody.querySelectorAll(".cline");
    if (reduced) {
      showAllLines();
      return;
    }
    lines.forEach(function (line, i) {
      playTimers.push(setTimeout(function () {
        line.style.opacity = "1";
        line.style.transform = "none";
      }, 180 + i * 100));
    });
  }

  if (consoleBody) {
    if (reduced || !("IntersectionObserver" in window)) {
      showAllLines();
    } else {
      var consoleObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            playConsole();
            consoleObserver.disconnect();
          }
        });
      }, { threshold: 0.3 });
      consoleObserver.observe(consoleBody);
    }
    if (replayBtn) replayBtn.addEventListener("click", playConsole);
  }

  /* ── project status: patch static values from status.json ──
     index.html ships with correct static values as the fallback;
     status.json lets the repo bump them without touching the page.
     Any fetch or parse failure leaves the static values in place. */
  fetch("status.json", { cache: "no-cache" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (s) {
      if (!s) return;
      document.querySelectorAll("[data-status]").forEach(function (el) {
        var key = el.getAttribute("data-status");
        if (s[key] !== undefined && s[key] !== null) el.textContent = s[key];
      });
    })
    .catch(function () { /* offline / file:// — static values stay */ });
})();
