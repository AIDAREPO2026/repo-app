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

function closeToast(toast) {
  toast.classList.add("is-leaving");
  toast.addEventListener("animationend", (event) => {
    if (event.target === toast) toast.remove();
  });
}

// A result arrives as ?done= or ?added= in the address. Once its notice is on screen, take it
// out, so reloading or sharing the page does not announce the change again.
function forgetResult() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("done") && !url.searchParams.has("added")) return;
  url.searchParams.delete("done");
  url.searchParams.delete("added");
  window.history.replaceState(null, "", url);
}

// A Discom picked from the draft list ("name|domain") fills the two fields under it. The
// Admin's confirmation is cleared, because it was given for different details.
function fillDiscom(holder, value) {
  const [name, domain] = value.split("|");
  const form = holder.closest("form");
  const prefix = holder.dataset.fillDiscom;
  form.querySelector(`#${prefix}name`).value = name;
  form.querySelector(`#${prefix}email_domain`).value = domain || "";
  const confirmation = form.querySelector('[name="checked"]');
  if (confirmation) confirmation.checked = false;
}

// A serious action waits for a yes. Runs on submit, so the browser has already checked the
// form's fields, and the same button that was pressed is sent on.
function askBeforeSending(event) {
  const form = event.target;
  if (!form.dataset.confirm || form.dataset.confirmed) return;
  event.preventDefault();
  const dialog = document.getElementById("confirm-dialog");
  dialog.querySelector("#confirm-dialog-title").textContent = form.dataset.confirmTitle;
  dialog.querySelector("#confirm-dialog-text").textContent = form.dataset.confirm;
  const yes = dialog.querySelector("[data-confirm-yes]");
  yes.textContent = form.dataset.confirmAction;
  yes.onclick = () => {
    dialog.close();
    form.dataset.confirmed = "yes";
    form.requestSubmit(event.submitter);
    delete form.dataset.confirmed; // Asked again if the page stays and they press again.
  };
  dialog.showModal();
}

function applyAll() {
  applyTheme(read(THEME_KEY, "light"));
  applySidebar(read(SIDEBAR_KEY, "shown"));
}

applyAll();

document.addEventListener("DOMContentLoaded", () => {
  forgetResult();
  applyAll();
  // Hidden in the HTML, because without this script they would do nothing.
  for (const control of document.querySelectorAll(".theme-switcher, [data-needs-script]")) {
    control.hidden = false;
    // Buttons that must not work without the script start disabled as well.
    if (control.matches("button")) control.disabled = false;
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

document.addEventListener("change", (event) => {
  // Only the select itself: the dropdown's search box, inside the same holder, also fires
  // "change" and would overwrite the pick with the text typed.
  const holder = event.target.closest("[data-fill-discom]");
  if (holder && event.target.matches("select") && event.target.value) fillDiscom(holder, event.target.value);
});

document.addEventListener("submit", askBeforeSending);

// A toast's bar running out closes it.
document.addEventListener("animationend", (event) => {
  if (event.target.matches(".toast-timer")) closeToast(event.target.closest(".toast"));
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-find-page]")) findPage(event.target);
});
