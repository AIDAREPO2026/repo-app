// Row selection and the row menu for data tables (P1-UI-02). A table opts in by giving its
// data_table() call column names; each row then carries data-export (its values, in that
// order) and data-copy (the one value people usually want).
//
// Everything here only reads the page: it copies or downloads what the reader already sees.
// Actions that change records belong on the server, behind a route guard and an audit event.

// The search box and the group picker above a table.
const FILTERS = "[data-filter-table], [data-filter-group] select";

function rowsOf(table) {
  return [...table.querySelectorAll("tbody tr[data-export]")];
}

function checkbox(label) {
  const box = document.createElement("input");
  box.type = "checkbox";
  box.setAttribute("aria-label", label);
  return box;
}

function selectedRows(table) {
  return rowsOf(table).filter((row) => row.querySelector(".row-select input").checked);
}

// Show a toast built from the table's template, using the page's toast area.
function announce(table, message) {
  const toast = table.querySelector("template").content.firstElementChild.cloneNode(true);
  toast.querySelector(".toast-text").textContent = message;
  toast.querySelector("[data-toast-close]").hidden = false;
  document.querySelector(".toasts").append(toast);
}

async function copy(table, rows) {
  const text = rows.map((row) => row.dataset.copy).join("\n");
  try {
    await navigator.clipboard.writeText(text);
    announce(table, table.dataset.copied);
  } catch {
    announce(table, table.dataset.copyFailed); // The browser allows copying only on HTTPS or localhost.
  }
}

// One CSV cell. A leading = + - or @ would run as a formula in a spreadsheet, so it is
// quoted away with an apostrophe.
function csvCell(value) {
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${text.replaceAll('"', '""')}"`;
}

function download(table, rows) {
  const lines = [JSON.parse(table.dataset.columns), ...rows.map((row) => JSON.parse(row.dataset.export))];
  const csv = lines.map((line) => line.map(csvCell).join(",")).join("\r\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([`﻿${csv}`], { type: "text/csv" }));
  link.download = `${table.dataset.file}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// Keep the highlight, the header checkbox and the action bar in step with the ticks.
function refresh(table) {
  const chosen = selectedRows(table);
  for (const row of rowsOf(table)) row.classList.toggle("is-selected", chosen.includes(row));

  const visible = rowsOf(table).filter((row) => !row.hidden);
  const all = table.querySelector("thead .row-select input");
  const ticked = visible.filter((row) => chosen.includes(row)).length;
  all.checked = visible.length > 0 && ticked === visible.length;
  all.indeterminate = ticked > 0 && ticked < visible.length;

  table.querySelector(".selection-bar").togglePopover(chosen.length > 0);
  table.querySelector("[data-selected-count]").textContent = chosen.length;
}

function setSelected(table, rows, selected) {
  for (const row of rows) row.querySelector(".row-select input").checked = selected;
  refresh(table);
}

// The checkbox column is added here, so a page without script shows no dead controls.
function addCheckboxes(table) {
  const head = document.createElement("th");
  head.className = "row-select";
  const all = checkbox(table.dataset.selectAll);
  head.append(all);
  table.querySelector("thead tr").prepend(head);
  all.addEventListener("change", () => setSelected(table, rowsOf(table).filter((row) => !row.hidden), all.checked));

  for (const row of rowsOf(table)) {
    const cell = document.createElement("td");
    cell.className = "row-select";
    const box = checkbox(`${table.dataset.selectRow} ${JSON.parse(row.dataset.export)[0]}`);
    box.addEventListener("change", () => refresh(table));
    cell.append(box);
    row.prepend(cell);
  }
}

// Put the menu at the pointer, pulled back inside the window near an edge or corner.
function placeMenu(menu, x, y) {
  const gap = 8;
  const { offsetWidth: width, offsetHeight: height } = menu;
  menu.style.left = `${Math.max(gap, Math.min(x, window.innerWidth - width - gap))}px`;
  menu.style.top = `${Math.max(gap, y + height + gap > window.innerHeight ? y - height : y)}px`;
}

function openRowMenu(table, row, event) {
  const menu = table.querySelector(".row-menu");
  const box = row.querySelector(".row-select input");
  menu.row = row;
  menu.querySelector("[data-row-open]").hidden = !row.querySelector("[commandfor]");
  menu.querySelector("[data-row-select-label]").textContent = box.checked ? table.dataset.untick : table.dataset.tick;
  menu.showPopover();
  // The keyboard's menu key has no pointer, so the menu opens under the row.
  const bounds = row.getBoundingClientRect();
  placeMenu(menu, event.clientX || bounds.left + 48, event.clientY || bounds.bottom);
  const first = menu.querySelector("button:not([hidden])");
  first.focus();
  glideTo(menu, first); // Focus may already be there, which sends no focusin.
}

function onMenuClick(table, event) {
  const item = event.target.closest("button");
  if (!item) return;
  const menu = table.querySelector(".row-menu");
  const { row } = menu;
  menu.hidePopover();
  if (item.matches("[data-row-open]")) row.querySelector("[commandfor]").click();
  if (item.matches("[data-row-copy]")) copy(table, [row]);
  if (item.matches("[data-row-select]")) setSelected(table, [row], !row.querySelector(".row-select input").checked);
}

// The pointer and the arrow keys move the same highlight, as in a desktop menu.
function followFocus(menu) {
  menu.addEventListener("pointerover", (event) => event.target.closest("button")?.focus());
  menu.addEventListener("keydown", (event) => {
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const items = [...menu.querySelectorAll("button:not([hidden])")];
    const next = (items.indexOf(document.activeElement) + step + items.length) % items.length;
    items[next].focus();
  });
}

function enhanceTable(table) {
  followFocus(table.querySelector(".row-menu"));
  addCheckboxes(table);
  table.addEventListener("contextmenu", (event) => {
    const row = event.target.closest("tbody tr[data-export]");
    // Dialogs live inside rows; they keep the browser's own menu, as does selected text.
    if (!row || event.target.closest("dialog") || String(window.getSelection())) return;
    event.preventDefault();
    openRowMenu(table, row, event);
  });
  table.querySelector(".row-menu").addEventListener("click", (event) => onMenuClick(table, event));
  table.querySelector("[data-bulk-copy]").addEventListener("click", () => copy(table, selectedRows(table)));
  table.querySelector("[data-bulk-export]").addEventListener("click", () => download(table, selectedRows(table)));
  table.querySelector("[data-bulk-clear]").addEventListener("click", () => setSelected(table, rowsOf(table), false));
  // shell.js filters the rows first; then the header checkbox follows what is visible.
  table.addEventListener("input", (event) => {
    if (event.target.matches("[data-filter-table]")) setTimeout(() => refresh(table));
  });
}

// Show the rows that match the search box, but no more than the batch reached so far. Dialogs
// inside a row are not part of what it says.
function showRows(table) {
  const box = table.querySelector("[data-filter-table]");
  const text = box ? box.value.trim().toLowerCase() : "";
  const picker = table.querySelector("[data-filter-group] select");
  const group = picker && picker.value !== "all" ? picker.value : "";
  const limit = Number(table.dataset.limit) || Infinity;
  let matched = 0;
  let shown = 0;
  for (const row of table.querySelectorAll("tbody tr")) {
    const copy = row.cloneNode(true);
    copy.querySelectorAll("dialog").forEach((dialog) => dialog.remove());
    const matches = copy.textContent.toLowerCase().includes(text) && (!group || row.dataset.group === group);
    if (matches) matched += 1;
    row.hidden = !matches || matched > limit;
    if (!row.hidden) shown += 1;
  }
  table.querySelector("[data-shown]").textContent = shown;
  return matched > shown;
}

// Infinite scroll over rows already in the page.
// ponytail: every row arrives with the page, which suits lists of a few thousand at most;
// fetch pages from the server for anything longer.
function revealAsScrolled(table) {
  const marker = table.querySelector(".data-more");
  const step = Number(table.dataset.batch);
  table.dataset.limit = step;
  let waiting = showRows(table);
  const observer = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting || !waiting) return;
    table.dataset.limit = Number(table.dataset.limit) + step;
    waiting = showRows(table);
    // Watch again, in case the marker is still on screen after the new rows.
    observer.unobserve(marker);
    observer.observe(marker);
  });
  observer.observe(marker);
  const filterChanged = (event) => {
    if (!event.target.matches(FILTERS)) return;
    table.dataset.limit = step; // A new search or filter starts from the top again.
    waiting = showRows(table);
    observer.unobserve(marker);
    observer.observe(marker);
  };
  table.addEventListener("input", filterChanged);
  table.addEventListener("change", filterChanged);
}

// Tables without batches only need their rows shown again when a filter changes.
function filterWholeTable(event) {
  const table = event.target.matches?.(FILTERS) && event.target.closest(".data-table");
  if (table && !table.dataset.batch) showRows(table);
}

document.addEventListener("input", filterWholeTable);
document.addEventListener("change", filterWholeTable);

document.addEventListener("DOMContentLoaded", () => {
  for (const table of document.querySelectorAll(".data-table[data-batch]")) revealAsScrolled(table);
  for (const table of document.querySelectorAll("[data-columns]")) enhanceTable(table);
});
