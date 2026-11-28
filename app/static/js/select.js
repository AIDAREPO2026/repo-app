// The select box (P1-UI-02), drawn over the native <select> that macros/forms.html renders.
// The <select> keeps the form value; this adds the picker: search, options loaded from an
// address page by page, and a list that opens wherever there is room (components.css).

const SEARCH_FROM = 11; // Search appears once there are more than 10 options.
const TYPING_PAUSE = 250; // Milliseconds without a key before the server is asked.

function element(tag, className, attributes = {}) {
  const node = document.createElement(tag);
  node.className = className;
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  return node;
}

// Build the button, the popover and the list, and return them with the field's state.
function build(field) {
  const native = field.querySelector("select");
  const label = field.querySelector("label");
  const id = native.id;
  const remote = Boolean(field.dataset.source);
  const searchable = remote || [...native.options].filter((o) => o.value).length >= SEARCH_FROM;

  const button = element("button", "input select-button", {
    type: "button", popovertarget: `${id}-popup`, "aria-haspopup": "listbox",
    "aria-expanded": "false", "aria-labelledby": `${id}-label ${id}-value`,
  });
  const value = element("span", "select-value", { id: `${id}-value` });
  button.append(value);

  const popup = element("div", "menu select-menu", { id: `${id}-popup`, popover: "" });
  const list = element("ul", "select-list", { id: `${id}-list`, role: "listbox", "aria-labelledby": `${id}-label` });
  const status = element("p", "select-status", { role: "status" });
  let search = null;
  if (searchable) {
    search = element("input", "input find-input select-search", {
      type: "search", role: "combobox", autocomplete: "off", "aria-expanded": "true",
      "aria-controls": list.id, "aria-label": field.dataset.search, placeholder: field.dataset.search,
    });
    popup.append(search);
  } else {
    list.tabIndex = 0;
  }
  popup.append(list, status);

  for (const attribute of ["aria-describedby", "aria-invalid"]) {
    if (native.hasAttribute(attribute)) button.setAttribute(attribute, native.getAttribute(attribute));
  }
  // Hidden from sight, not removed: the browser still checks "required" and submits it.
  native.classList.add("select-native");
  native.tabIndex = -1;
  native.setAttribute("aria-hidden", "true"); // Or screen readers would meet every option twice.
  native.after(button, popup);
  label.addEventListener("click", (event) => {
    event.preventDefault();
    button.focus();
  });

  return { field, native, button, value, popup, search, list, status, remote, active: -1, page: 0, more: false };
}

function showChosen(state) {
  const chosen = state.native.selectedOptions[0];
  state.value.textContent = chosen ? chosen.textContent : state.field.dataset.placeholder;
  state.value.classList.toggle("is-placeholder", !state.native.value);
}

function addOption(state, value, text) {
  const item = element("li", "select-option", {
    role: "option", id: `${state.list.id}-${state.list.children.length}`,
    "aria-selected": String(value === state.native.value),
  });
  item.dataset.value = value;
  item.textContent = text; // textContent, so an option's text is never read as HTML.
  state.list.append(item);
}

// Mark one option as the one Enter would choose.
function setActive(state, index) {
  const items = state.list.children;
  const keyboardTarget = state.search || state.list;
  for (const item of items) item.classList.remove("is-active");
  state.active = items.length ? Math.max(0, Math.min(index, items.length - 1)) : -1;
  if (state.active < 0) {
    state.popup.querySelector(":scope > .menu-glider")?.setAttribute("hidden", "");
    keyboardTarget.removeAttribute("aria-activedescendant");
    return;
  }
  items[state.active].classList.add("is-active");
  items[state.active].scrollIntoView({ block: "nearest" });
  keyboardTarget.setAttribute("aria-activedescendant", items[state.active].id);
  highlight(state);
}

// Slide the highlight under the active option (glide.js). Before the list is on screen
// there is nothing to measure.
function highlight(state) {
  const item = state.list.children[state.active];
  if (item && state.popup.matches(":popover-open")) glideTo(state.popup, item, state.list);
}

// Options already in the page: show those holding the text.
function showLocal(state) {
  const text = state.search ? state.search.value.trim().toLowerCase() : "";
  state.list.replaceChildren();
  for (const option of state.native.options) {
    if (option.value && option.textContent.toLowerCase().includes(text)) {
      addOption(state, option.value, option.textContent);
    }
  }
  state.status.textContent = state.list.children.length ? "" : state.field.dataset.empty;
  const chosen = [...state.list.children].findIndex((item) => item.dataset.value === state.native.value);
  setActive(state, Math.max(chosen, 0));
}

// Options from the server: page 1 replaces the list, later pages add to it.
async function loadPage(state, page) {
  state.request?.abort(); // A newer search makes the older answer useless.
  state.request = new AbortController();
  state.loading = true;
  state.status.textContent = state.field.dataset.loading;
  const url = new URL(state.field.dataset.source, window.location.href);
  url.searchParams.set("q", state.search.value.trim());
  url.searchParams.set("page", page);
  try {
    const response = await fetch(url, { headers: { Accept: "application/json" }, signal: state.request.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const answer = await response.json();
    if (page === 1) state.list.replaceChildren();
    for (const item of answer.items) addOption(state, String(item.value), item.label);
    state.page = page;
    state.more = Boolean(answer.more);
    state.status.textContent = state.list.children.length ? "" : state.field.dataset.empty;
    if (page === 1) setActive(state, 0);
  } catch (error) {
    if (error.name === "AbortError") return;
    state.more = false;
    state.status.textContent = state.field.dataset.failed;
  }
  state.loading = false;
  loadNextIfNearEnd(state);
}

// Infinite scroll: ask for the next page before the reader reaches the last option.
function loadNextIfNearEnd(state) {
  const left = state.list.scrollHeight - state.list.scrollTop - state.list.clientHeight;
  if (state.more && !state.loading && state.popup.matches(":popover-open") && left < 48) {
    loadPage(state, state.page + 1);
  }
}

function choose(state, item) {
  if (!item) return;
  const value = item.dataset.value;
  if (![...state.native.options].some((option) => option.value === value)) {
    state.native.add(new Option(item.textContent, value));
  }
  state.native.value = value;
  state.native.dispatchEvent(new Event("change", { bubbles: true }));
  state.button.removeAttribute("aria-invalid");
  showChosen(state);
  state.popup.hidePopover();
  state.button.focus();
}

function onKey(state, event) {
  const moves = { ArrowDown: state.active + 1, ArrowUp: state.active - 1, Home: 0, End: state.list.children.length - 1 };
  if (event.key in moves) {
    event.preventDefault();
    setActive(state, moves[event.key]);
    loadNextIfNearEnd(state);
  } else if (event.key === "Enter") {
    event.preventDefault(); // Or Enter would submit the form behind the list.
    choose(state, state.list.children[state.active]);
  } else if (event.key === "Tab") {
    state.popup.hidePopover();
    state.button.focus();
  } else if (!state.search && event.key.length === 1) {
    // Without a search box, a letter jumps to the next option starting with it.
    const items = [...state.list.children];
    const order = items.slice(state.active + 1).concat(items.slice(0, state.active + 1));
    const next = order.find((item) => item.textContent.toLowerCase().startsWith(event.key.toLowerCase()));
    if (next) setActive(state, items.indexOf(next));
  }
}

// Runs before the list is shown, so nothing typed afterwards can be wiped by the reset.
function prepare(state) {
  if (state.search) state.search.value = "";
  if (state.remote) {
    state.list.replaceChildren();
    loadPage(state, 1);
  } else {
    showLocal(state);
  }
}

function enhance(field) {
  const state = build(field);
  let timer;
  showChosen(state);

  state.popup.addEventListener("beforetoggle", (event) => {
    const open = event.newState === "open";
    state.button.setAttribute("aria-expanded", String(open));
    if (open) prepare(state);
  });
  // Focus has to wait until the list is on screen.
  state.popup.addEventListener("toggle", (event) => {
    if (event.newState !== "open") return;
    (state.search || state.list).focus();
    state.list.children[state.active]?.scrollIntoView({ block: "nearest" });
    highlight(state);
    loadNextIfNearEnd(state);
  });
  state.popup.addEventListener("keydown", (event) => onKey(state, event));
  state.list.addEventListener("click", (event) => choose(state, event.target.closest("[role=option]")));
  state.list.addEventListener("pointermove", (event) => {
    const item = event.target.closest("[role=option]");
    const index = [...state.list.children].indexOf(item);
    if (index >= 0 && index !== state.active) setActive(state, index);
  });
  state.list.addEventListener("scroll", () => {
    highlight(state);
    loadNextIfNearEnd(state);
  });
  state.search?.addEventListener("input", () => {
    if (!state.remote) {
      showLocal(state);
      return;
    }
    clearTimeout(timer);
    timer = setTimeout(() => loadPage(state, 1), TYPING_PAUSE);
  });
  state.button.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      state.popup.showPopover({ source: state.button });
    }
  });
  // The browser found a required select empty: point at the button the person can see.
  state.native.addEventListener("invalid", () => {
    state.button.setAttribute("aria-invalid", "true");
    state.button.focus();
  });
  state.native.form?.addEventListener("reset", () => setTimeout(() => showChosen(state)));
}

document.addEventListener("DOMContentLoaded", () => {
  for (const field of document.querySelectorAll("[data-select]")) enhance(field);
});
