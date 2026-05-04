(function () {
  // ---- Language (i18n) ----
  // Source of truth: <html lang="en|th">. Each page also declares
  // data-title-en / data-title-th on <html> so we can swap document.title.
  var LANG_KEY = "myda-lang";
  var html = document.documentElement;

  function detectInitialLang() {
    var saved = null;
    try { saved = localStorage.getItem(LANG_KEY); } catch (e) {}
    if (saved === "en" || saved === "th") return saved;
    var nav = (navigator.language || "").toLowerCase();
    if (nav.indexOf("th") === 0) return "th";
    return "en";
  }

  function applyLang(lang) {
    html.setAttribute("lang", lang);
    var t = html.getAttribute("data-title-" + lang);
    if (t) document.title = t;
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
    document.querySelectorAll("[data-toggle-lang]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", lang === "th" ? "true" : "false");
    });
    // <input>/<textarea> placeholders
    document.querySelectorAll("[data-ph-" + lang + "]").forEach(function (el) {
      el.placeholder = el.getAttribute("data-ph-" + lang);
    });
    // <option> text — children of <select>
    document.querySelectorAll("option[data-" + lang + "]").forEach(function (el) {
      el.textContent = el.getAttribute("data-" + lang);
    });
  }

  applyLang(detectInitialLang());

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-toggle-lang]");
    if (!btn) return;
    e.preventDefault();
    var current = html.getAttribute("lang") === "th" ? "en" : "th";
    applyLang(current);
  });

  // ---- Drawer ----
  var drawer = document.getElementById("drawer");
  var openBtn = document.getElementById("menuOpen");
  var closeBtn = document.getElementById("menuClose");
  function openDrawer() {
    if (!drawer) return;
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("no-scroll");
  }
  function closeDrawer() {
    if (!drawer) return;
    drawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("no-scroll");
  }
  if (openBtn) openBtn.addEventListener("click", openDrawer);
  if (closeBtn) closeBtn.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDrawer();
  });
})();
