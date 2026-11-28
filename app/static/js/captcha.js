// Loads the ALTCHA CAPTCHA widget (decision record 0006) for any page with <altcha-widget>.
// The external build carries no workers, so the proof-of-work worker is registered here,
// from our own origin, which keeps the strict CSP (script-src and worker-src 'self').
import "/static/vendor/altcha-3.7.0/altcha.min.js";

const WORKER_URL = "/static/vendor/altcha-3.7.0/workers/pbkdf2.js";

// app.core.captcha.ALGORITHM: the server issues PBKDF2/SHA-256 challenges only.
globalThis.$altcha.algorithms.set("PBKDF2/SHA-256", () => new Worker(WORKER_URL));
