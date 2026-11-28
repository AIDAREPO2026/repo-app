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

// User ID suggestions on the registration page, from the chosen Discom and the email typed.
// Worked out here only: asking the server whether one is taken would reveal accounts.
function userIdPart(text) {
  return text.toLowerCase().replace(/[^a-z0-9._-]/g, "").replace(/^[._-]+|[._-]+$/g, "");
}

// A short code for a Discom: the one in brackets, such as "(MSEDCL)", else its first word.
function discomCode(name) {
  const bracketed = name.match(/\(([A-Za-z0-9-]{2,15})\)/);
  return userIdPart(bracketed ? bracketed[1] : name.trim().split(/\s+/)[0] || "");
}

function userIdSuggestions(discom, email) {
  const person = userIdPart(email.split("@")[0]);
  const code = discomCode(discom);
  const ideas = [person, code && person && `${code}.${person}`, code && `${code}.portal`];
  // The same rule as USER_ID_PATTERN on the server: 4 to 50 characters.
  return [...new Set(ideas.filter((idea) => idea && idea.length >= 4 && idea.length <= 50))];
}

function refreshUserIdSuggestions(form) {
  const holder = form.querySelector("[data-suggest-user-id]");
  const chosen = form.querySelector('[name="organisation_id"]').selectedOptions[0];
  const email = form.querySelector('[name="email"]').value;
  const ideas = userIdSuggestions(chosen?.value ? chosen.textContent : "", email);
  const list = holder.querySelector(".id-suggestions-list");
  holder.hidden = ideas.length === 0;
  // Leaving the email field fires "change" in the middle of a click on a suggestion. Rebuilding
  // then would remove the button being clicked, so the list changes only when the ideas do.
  if (list.dataset.ideas === ideas.join(" ")) return;
  list.dataset.ideas = ideas.join(" ");
  list.replaceChildren();
  for (const idea of ideas) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "id-suggestion";
    button.textContent = idea;
    button.addEventListener("click", () => {
      const field = form.querySelector('[name="user_id"]');
      field.value = idea;
      field.focus();
    });
    list.append(button);
  }
}

function refreshFromEvent(event) {
  if (!event.target.matches?.('[name="organisation_id"], [name="email"]')) return;
  const form = event.target.form;
  if (form?.querySelector("[data-suggest-user-id]")) refreshUserIdSuggestions(form);
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

document.addEventListener("input", refreshFromEvent);
document.addEventListener("change", refreshFromEvent);

// A toast's bar running out closes it.
document.addEventListener("animationend", (event) => {
  if (event.target.matches(".toast-timer")) closeToast(event.target.closest(".toast"));
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-find-page]")) findPage(event.target);
  if (event.target.matches("[data-filter-table]")) filterTable(event.target);
});
