// Dark mode toggle (Flowbite pattern). The initial theme is applied by the
// inline script in templates/partials/theme_init.html; this handles clicks
// and follows OS changes until the user picks a theme explicitly.
(function () {
  const STORAGE_KEY = "color-theme";
  const root = document.documentElement;
  const buttons = document.querySelectorAll("[data-theme-toggle]");

  function storedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null; // storage blocked (private mode, disabled cookies)
    }
  }

  function render() {
    const dark = root.classList.contains("dark");
    buttons.forEach((button) => {
      button.querySelector("[data-theme-icon=dark]").classList.toggle("hidden", dark);
      button.querySelector("[data-theme-icon=light]").classList.toggle("hidden", !dark);
      button.setAttribute("aria-pressed", String(dark));
      const label = dark ? "Switch to light mode" : "Switch to dark mode";
      button.setAttribute("aria-label", label);

      const tooltipId = button.getAttribute("data-tooltip-target");
      const tooltipLabel = tooltipId && document.getElementById(tooltipId)?.querySelector("[data-theme-tooltip-label]");
      if (tooltipLabel) tooltipLabel.textContent = label;
    });
  }

  buttons.forEach((button) =>
    button.addEventListener("click", () => {
      const dark = root.classList.toggle("dark");
      try {
        localStorage.setItem(STORAGE_KEY, dark ? "dark" : "light");
      } catch (e) {
        // Still toggles for this page view; it just won't be remembered.
      }
      render();
    })
  );

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (event) => {
    if (!storedTheme()) {
      root.classList.toggle("dark", event.matches);
      render();
    }
  });

  render();
})();
