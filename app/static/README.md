# Static files

CSS, JavaScript and images, served by the app at `/static/`. Third-party front-end libraries (HTMX, Uppy, PDF.js) are copied into `vendor/` with their version in the folder name, never loaded from a CDN, so the strict Content Security Policy (`script-src 'self'`) holds.

Styles use Tailwind CSS. Every design value is a variable in `css/tokens.css` (light and dark, and the reduced-motion, reduced-transparency and more-contrast variants); shared components are styled in `css/components.css`. `css/app.src.css` exposes the tokens to Tailwind and switches off Tailwind's own palette. Edit those and the templates; `npm run build:css` compiles them into `css/app.css`, which is git-ignored and built inside the Docker image.
