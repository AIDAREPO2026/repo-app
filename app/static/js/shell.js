// The page shell's choices (P1-UI-02), kept in this browser: theme, and whether the sidebar
// shows. Also the sidebar's "Find a page" box. Loaded in <head> without defer, so the page
// never flashes the wrong theme or layout.
const THEME_KEY = "aida-theme";
const SIDEBAR_KEY = "aida-sidebar";
const root = document.documentElement;

// Storage can be blocked by browser settings; a choice then lasts for this page only.
function read(key, fallback) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {}
}

// tokens.css follows the device unless <html> carries .theme-light or .theme-dark.
function applyTheme(theme) {
  root.classList.toggle("theme-light", theme === "light");
  root.classList.toggle("theme-dark", theme === "dark");
  // Picks the drawing on the theme button (components.css).
  root.dataset.theme = theme;
  for (const button of document.querySelectorAll("[data-theme-choice]")) {
    button.setAttribute("aria-pressed", String(button.dataset.themeChoice === theme));
  }
}

function applySidebar(state) {
  root.classList.toggle("sidebar-hidden", state === "hidden");
  for (const button of document.querySelectorAll("[data-sidebar-toggle]")) {
    button.setAttribute("aria-expanded", String(state !== "hidden"));
  }
}

// The browser snapshots the page before and after, and components.css springs between the
// two. Browsers without view transitions just switch.
function moveSidebar(state) {
  if (!document.startViewTransition) {
    applySidebar(state);
    return;
  }
  root.classList.add("sidebar-moving");
  const transition = document.startViewTransition(() => applySidebar(state));
  transition.finished.finally(() => root.classList.remove("sidebar-moving"));
}

// Show only the menu entries whose name holds the text, opening the sections they are in.
function findPage(box) {
  const text = box.value.trim().toLowerCase();
  const menu = box.closest(".sidebar").querySelector("nav");
  for (const item of menu.querySelectorAll("li")) {
    item.hidden = !item.textContent.toLowerCase().includes(text);
  }
  for (const group of menu.querySelectorAll("details")) {
    group.dataset.wasOpen ??= String(group.open);
    group.hidden = !group.querySelector("li:not([hidden])");
    group.open = text ? true : group.dataset.wasOpen === "true";
  }
}

function applyAll() {
  applyTheme(read(THEME_KEY, "light"));
  applySidebar(read(SIDEBAR_KEY, "shown"));
}

applyAll();

document.addEventListener("DOMContentLoaded", () => {
  applyAll();
  // Hidden in the HTML, because without this script they would do nothing.
  for (const control of document.querySelectorAll(".theme-switcher, [data-needs-script]")) {
    control.hidden = false;
  }
});

document.addEventListener("click", (event) => {
  const choice = event.target.closest("[data-theme-choice]");
  if (choice) {
    save(THEME_KEY, choice.dataset.themeChoice);
    applyTheme(choice.dataset.themeChoice);
  }
  if (event.target.closest("[data-sidebar-toggle]")) {
    const state = root.classList.contains("sidebar-hidden") ? "shown" : "hidden";
    save(SIDEBAR_KEY, state);
    moveSidebar(state);
  }
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-find-page]")) findPage(event.target);
});
