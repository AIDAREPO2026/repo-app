# P0-SEC-01 — Confirm the self-hosted CAPTCHA approach

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p0-sec-01-captcha-approach` |
| Pull request | [#7](https://github.com/AIDAREPO2026/repo-app/pull/7) |
| Started | 2026-11-27 |
| Finished | 2026-11-27 |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Approved and merged #7. |
| 2026-11-27 | Raghvendra Singh | Evaluated ALTCHA (maintenance, Python library, accessibility, data location, CSP) and accepted it in decision record 0006. Built the spike as `app/core/captcha.py` (`new_challenge()` and `verify()`) with Redis replay protection, and 8 tests in `tests/core/test_captcha.py`. Added `altcha==2.5.0`. |
| 2026-11-27 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | The spike is the real `app/core/captcha.py`, which `P1-ACC-02` was to create. `P1-ACC-02` now adds only the challenge route and the widget | The spike already holds the whole server side, and keeping it saves rewriting it | Raghvendra Singh |
| 2026-11-27 | Challenges are signed with the existing `SECRET_KEY`, not a new variable | One fewer secret to manage. The key never leaves the server | Raghvendra Singh |
| 2026-11-27 | Used challenges are remembered in Redis for 10 minutes | The ALTCHA library is stateless, so replay protection is ours to add | Raghvendra Singh |
| 2026-11-27 | Decision record 0006 is the first file in `docs/adr/`, ahead of `P0-ARC-02`, which adds the template and records 0001 to 0005 | The spec asks for 0006 in this task | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
