(function () {
  const drawer = document.getElementById("drawer");
  const openBtn = document.getElementById("menuOpen");
  const closeBtn = document.getElementById("menuClose");

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
