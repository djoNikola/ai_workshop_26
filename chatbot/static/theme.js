// Runs in <head> so the saved/system theme is applied before first paint.
(function () {
  const saved = localStorage.getItem("theme");
  const theme = saved === "light" || saved === "dark"
    ? saved
    : (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
})();
