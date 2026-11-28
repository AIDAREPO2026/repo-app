// Row selection and the row menu for data tables (P1-UI-02). A table opts in by giving its
// data_table() call column names; each row then carries data-export (its values, in that
// order) and data-copy (the one value people usually want).
//
// Everything here only reads the page: it copies or downloads what the reader already sees.
// Actions that change records belong on the server, behind a route guard and an audit event.

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
  // The highlight starts on the first item without sliding there from the last place.
  menu.classList.add("is-opening");
  const first = menu.querySelector("button:not([hidden])");
  first.focus();
  glideTo(menu, first); // Focus may already be there, which sends no focusin.
  requestAnimationFrame(() => requestAnimationFrame(() => menu.classList.remove("is-opening")));
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

// Slide the highlight under an item. offsetTop is measured from the menu itself.
function glideTo(menu, item) {
  const glider = menu.querySelector(".menu-glider");
  glider.style.transform = `translateY(${item.offsetTop}px)`;
  glider.style.height = `${item.offsetHeight}px`;
}

// The pointer and the arrow keys move the same highlight, as in a desktop menu.
function followFocus(menu) {
  menu.addEventListener("focusin", (event) => {
    if (event.target.matches("button")) glideTo(menu, event.target);
  });
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

document.addEventListener("DOMContentLoaded", () => {
  for (const table of document.querySelectorAll("[data-columns]")) enhanceTable(table);
});
