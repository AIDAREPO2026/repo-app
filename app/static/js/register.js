// Step 3 of registration (P1-ACC-02): pick a suggested User ID, and see whether a typed one is
// free. The server answers only a visitor who has proved their email, a limited number of times.
const ID_CHECK_PAUSE = 400;

function userIdField() {
  return document.querySelector('[name="user_id"]');
}

function showIdState(status, state) {
  status.textContent = status.dataset[state] || "";
  status.dataset.state = state;
}

async function checkUserId(status, value) {
  const response = await fetch(`/register/user-id?value=${encodeURIComponent(value)}`);
  if (!response.ok) return showIdState(status, "");
  const { state } = await response.json();
  // Ignore an answer about text that has changed since.
  if (userIdField().value === value) showIdState(status, state);
}

document.addEventListener("DOMContentLoaded", () => {
  const status = document.querySelector("[data-check-user-id]");
  let timer;
  const changed = () => {
    clearTimeout(timer);
    const value = userIdField().value;
    showIdState(status, "");
    // The shortest allowed ID has 4 characters, so shorter text is not worth asking about.
    if (value.length >= 4) timer = setTimeout(() => checkUserId(status, value), ID_CHECK_PAUSE);
  };
  userIdField().addEventListener("input", changed);
  for (const button of document.querySelectorAll("[data-use-user-id]")) {
    button.addEventListener("click", () => {
      userIdField().value = button.textContent.trim();
      changed();
    });
  }
});
