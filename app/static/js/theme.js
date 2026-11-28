// The theme switcher (P1-UI-02). tokens.css follows the device setting unless <html> carries
// .theme-light or .theme-dark; this adds that class from the choice saved in this browser.
// Loaded in <head> without defer, so the page never flashes the wrong theme.
const KEY = "aida-theme";
const root = document.documentElement;

// Storage can be blocked by browser settings; the switcher then lasts for this page only.
function savedTheme() {
  try {
    return localStorage.getItem(KEY) || "system";
  } catch {
    return "system";
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(KEY, theme);
  } catch {}
}

function applyTheme(theme) {
  root.classList.toggle("theme-light", theme === "light");
  root.classList.toggle("theme-dark", theme === "dark");
  for (const button of document.querySelectorAll("[data-theme-choice]")) {
    button.setAttribute("aria-pressed", String(button.dataset.themeChoice === theme));
  }
}

applyTheme(savedTheme());

document.addEventListener("DOMContentLoaded", () => {
  applyTheme(savedTheme());
  // Hidden in the HTML, because without this script the buttons would do nothing.
  for (const switcher of document.querySelectorAll(".theme-switcher")) {
    switcher.hidden = false;
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-theme-choice]");
  if (!button) return;
  saveTheme(button.dataset.themeChoice);
  applyTheme(button.dataset.themeChoice);
});
