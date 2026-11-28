// The page shell's choices (P1-UI-02), kept in this browser: theme, and whether the sidebar
// shows. Also the search boxes: "Find a page" and the one above a data table. Loaded in <head> without defer, so the page
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

// Pages arrive light. tokens.css reads .theme-light or .theme-dark on <html>.
function applyTheme(theme) {
  const dark = theme === "dark";
  root.classList.toggle("theme-light", !dark);
  root.classList.toggle("theme-dark", dark);
  // Picks the drawing on the theme button (components.css).
  root.dataset.theme = dark ? "dark" : "light";
  for (const button of document.querySelectorAll("[data-theme-toggle]")) {
    const label = dark ? button.dataset.toLight : button.dataset.toDark;
    button.setAttribute("aria-label", label);
    button.title = label;
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

// Show only the rows holding the text. Dialogs inside a row are not part of what it says.
function filterTable(box) {
  const table = box.closest(".data-table");
  const text = box.value.trim().toLowerCase();
  let shown = 0;
  for (const row of table.querySelectorAll("tbody tr")) {
    const copy = row.cloneNode(true);
    copy.querySelectorAll("dialog").forEach((dialog) => dialog.remove());
    row.hidden = !copy.textContent.toLowerCase().includes(text);
    if (!row.hidden) shown += 1;
  }
  table.querySelector("[data-shown]").textContent = shown;
}

function closeToast(toast) {
  toast.classList.add("is-leaving");
  toast.addEventListener("animationend", (event) => {
    if (event.target === toast) toast.remove();
  });
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
  if (event.target.closest("[data-theme-toggle]")) {
    const theme = root.classList.contains("theme-dark") ? "light" : "dark";
    save(THEME_KEY, theme);
    applyTheme(theme);
  }
  const dismiss = event.target.closest("[data-toast-close]");
  if (dismiss) closeToast(dismiss.closest(".toast"));
  if (event.target.closest("[data-sidebar-toggle]")) {
    const state = root.classList.contains("sidebar-hidden") ? "shown" : "hidden";
    save(SIDEBAR_KEY, state);
    moveSidebar(state);
  }
});

// A toast's bar running out closes it.
document.addEventListener("animationend", (event) => {
  if (event.target.matches(".toast-timer")) closeToast(event.target.closest(".toast"));
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-find-page]")) findPage(event.target);
  if (event.target.matches("[data-filter-table]")) filterTable(event.target);
});
