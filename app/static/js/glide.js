// The sliding highlight shared by every menu and select list (P1-UI-02). One block of
// colour moves under the item in use, in place of a separate background on each item.
// Without this script the items keep their own hover colour.

// Put the highlight of `menu` under `item`. `list` is the part of the menu that scrolls,
// when it is not the menu itself.
function glideTo(menu, item, list = null) {
  let glider = menu.querySelector(":scope > .menu-glider");
  if (!glider) {
    glider = document.createElement("span");
    glider.className = "menu-glider";
    glider.setAttribute("aria-hidden", "true");
    glider.hidden = true;
    menu.prepend(glider);
    menu.classList.add("has-glider");
  }
  // offsetTop is measured from the menu, which is the nearest positioned parent.
  const top = item.offsetTop - (list ? list.scrollTop : 0);
  glider.style.width = `${item.offsetWidth}px`;
  glider.style.height = `${item.offsetHeight}px`;
  glider.style.transform = `translate(${item.offsetLeft}px, ${top}px)`;
  // Shown after it is placed, so the first time it appears where it is needed without
  // sliding in from somewhere else. It hides when the list has scrolled the item away.
  const outOfView = list && (top < list.offsetTop - 1 || top + item.offsetHeight > list.offsetTop + list.offsetHeight + 1);
  glider.hidden = Boolean(outOfView);
}

function glideFromEvent(event) {
  const item = event.target.closest?.(".menu .menu-item");
  if (item) glideTo(item.closest(".menu"), item);
}

document.addEventListener("pointerover", glideFromEvent);
document.addEventListener("focusin", glideFromEvent);

// A menu opens with no highlight left over from the last time.
document.addEventListener(
  "beforetoggle",
  (event) => {
    const glider = event.target.querySelector?.(":scope > .menu-glider");
    if (glider) glider.hidden = true;
  },
  true,
);
