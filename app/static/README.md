# Static files

CSS, JavaScript and images served by Nginx. Third-party front-end libraries (Bootstrap 5, HTMX, Uppy, PDF.js) are copied into `vendor/` with their version in the folder name, never loaded from a CDN, so the strict Content Security Policy (`script-src 'self'`) holds.
