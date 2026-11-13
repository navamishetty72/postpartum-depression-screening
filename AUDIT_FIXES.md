# Miora Landing Page — Bug & Fix Audit

## Bugs

### 1. Conflicting `margin-left: auto` in header
- **Location:** `src/styles.css:32` and `:35`
- **Issue:** `.desktop-nav` and `.header-actions` both use `margin-left: auto` inside a flex container with `justify-content: space-between`, causing the two auto-margins to fight and shift navigation/actions unpredictably (notably at the 980px breakpoint).
- **Fix:** Apply `margin-left: auto` to only one of them, or restructure spacing using `gap`/`margin-right: auto` on the brand side.

### 2. `.desktop-only` `<br>` has no CSS rule
- **Location:** `src/main.js:151`
- **Issue:** `<br class="desktop-only" />` in the urgent-help banner references a `.desktop-only` class that does not exist anywhere in `styles.css`. The line break always applies, wrapping text mid-sentence even on mobile.
- **Fix:** Add `.desktop-only { display: none; }` at base, and `.desktop-only { display: block; }` inside the desktop media query (or reword the copy to avoid the break).

---

## Accessibility Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| A1 | No skip-to-content link | `index.html` / `main.js` | Add a visually-hidden skip link at the top of `<main>` |
| A2 | Hamburger `<span>`s not hidden from screen readers | `main.js:44-46` | Add `aria-hidden="true"` to the three toggle `<span>` elements |
| A3 | Decorative empty `<span></span>` in `.eyebrow` not hidden | `main.js:60` et al. | Add `aria-hidden="true"` to the decorative span |
| A4 | No `:focus-visible` outline styles | `styles.css` | Add `:focus-visible` outline styles for links and buttons |
| A5 | Mobile menu lacks Escape-to-close / outside-click / scroll-lock | `main.js:166-176` | Add keyboard dismissal, outside-click close, and body scroll lock |
| A6 | Social links use non-descriptive text ("GH", "in", "X") | `main.js:161` | Use visible descriptive labels or visually-hidden text |

---

## Performance Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| P1 | Hero image 196 KB PNG, no WebP/AVIF fallback, no `loading="eager"` | `main.js:70` | Convert to WebP/AVIF, add `loading="eager"`, add width/height |
| P2 | Testimonial image lacks `loading="lazy"` | `main.js:133` | Add `loading="lazy"` |
| P3 | Images missing `width`/`height` attributes → CLS | `main.js` | Add explicit `width` and `height` to all `` tags |
| P4 | Google Fonts `@import` is render-blocking, no `font-display: swap` | `styles.css:1` | Add `font-display=swap` or self-host fonts |
| P5 | Unused `reference.png` (1.27 MB) bloats repo | `public/assets/` | Remove from public assets if unused |

---

## SEO & Meta Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| S1 | Missing favicon / apple-touch-icon | `index.html` | Add `<link rel="icon">` and apple-touch-icon |
| S2 | Missing manifest.json | project root | Add `manifest.json` and link it |
| S3 | Missing Open Graph / Twitter Card tags | `index.html` head | Add `og:`, `twitter:` meta tags |
| S4 | Missing canonical link and JSON-LD | `index.html` head | Add canonical URL and organization JSON-LD |

---

## Code Quality Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| C1 | Entire UI in one template literal (hard to maintain) | `main.js:25-164` | Modularize into components |
| C2 | No lint/typecheck/test scripts | `package.json` | Add eslint/vitest scripts |
| C3 | `icon()` silently falls back to `arrow` for unknown names | `main.js:20` | Warn/throw on unknown icon names |
| C4 | Anchor clicks scroll section titles behind sticky 76px header | `styles.css:26` | Add `scroll-margin-top` to sections |
| C5 | Mobile menu state not synced on resize (mobile ↔ desktop) | `main.js:166-176` | Reset menu state on resize |
