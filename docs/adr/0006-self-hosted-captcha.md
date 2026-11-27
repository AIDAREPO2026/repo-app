# 0006 — Self-hosted proof-of-work CAPTCHA (ALTCHA)

| Field | Value |
| --- | --- |
| Status | Accepted |
| Date | 2026-11-27 |
| Task | `P0-SEC-01` |
| Requirements | FR-1.2, FR-13.7, SRS 5.3 (data in India), SRS 5.5 (accessibility, Hindi later) |

## Context

Registration, password reset and the anonymous download limit need a CAPTCHA (FR-1.2, FR-13.7). The SRS requires:

- visitor data to stay in India (SRS 5.3)
- pages that meet WCAG 2.1 AA (SRS 5.5)

Hosted services such as reCAPTCHA and hCaptcha send visitor data to servers abroad, and image or audio puzzles are hard for people using assistive technology. Our Content Security Policy also allows scripts, styles and workers from our own site only.

## Decision

Use [ALTCHA](https://altcha.org), a self-hosted proof-of-work CAPTCHA:

- **Server:** the `altcha` Python library, version 2.5.0 (MIT licence, no dependencies, last released 21 November 2026). `app.core.captcha.new_challenge()` issues a signed challenge. `app.core.captcha.verify()` checks the answer.
- **Browser:** the `altcha` web component, version 3.7.0 or later (MIT licence). It solves the challenge in a Web Worker in about a second, with no picture to read. Use its `dist/external` build with its separate CSS file and workers, because the default build puts styles and workers inline, which our CSP blocks. `P1-ACC-02` adds the widget.
- **Puzzle settings:**
    - PBKDF2/SHA-256 with 5,000 rounds and the `00` key prefix, which takes 256 tries on average
    - the challenge expires after 10 minutes
    - the challenge is signed with the app's `SECRET_KEY`
- **Replay protection:** the library does not track used challenges, so `verify()` records each solved challenge's nonce in Redis with `SET NX` for the full 10-minute lifetime. A second use of the same answer is refused.

### Evaluation

| Check | Finding |
| --- | --- |
| Maintenance | Both the Python library and the widget had releases in November 2026. The widget has about 2,900 GitHub stars and is not archived |
| Server-side library | The official `altcha` package covers creating challenges, verifying them, checking signatures and expiry. It is typed (`py.typed`) |
| Accessibility | No visual or audio puzzle. The widget is a labelled checkbox that works by keyboard and with screen readers. The vendor states WCAG 2.2 AA conformance. A Hindi string file is included for SRS 5.5 |
| Data location | Nothing leaves our servers: the browser gets its challenge from us and sends the answer back to us. No cookies and no third-party requests |
| CSP | Compatible, using the `dist/external` build served from `/static/` |

The spike in `tests/core/test_captcha.py` shows that a solved challenge is accepted. It also shows that each of these is refused:

- a replayed answer
- an answer to a challenge signed with another key
- an expired challenge
- a wrong answer
- a malformed or oversized payload

## Consequences

- No visitor data goes to any third party, and no one has to solve a picture or sound puzzle.
- A determined attacker can still pay the computing cost. Proof of work slows bots down rather than stopping them, so Nginx rate limits and the lockout rules (FR-1.7) still apply. If abuse appears, raise `COST` in `app/core/captcha.py`.
- Very old or slow devices take longer to solve the puzzle, but never longer than the 10-minute expiry in practice.
- Redis now holds short-lived replay records. Losing them, for example when Redis restarts, only reopens replay for answers less than 10 minutes old.
- Rejected alternatives:
    - **reCAPTCHA, hCaptcha and Cloudflare Turnstile:** each sends visitor data outside India.
    - **Self-hosted image or audio CAPTCHAs:** they need extra work to be accessible, and are now easily solved by bots.
