import { icon } from './icons.js';
import { BrandLogo } from './BrandLogo.js';

export const Header = () => `
  <header class="brand-header" id="top">
    <div class="shell brand-header-inner">
      <a class="brand" href="#top" aria-label="Miora — Maternal Emotional Intelligence">
        ${BrandLogo()}
      </a>
      <div class="header-actions" style="display: flex; align-items: center; gap: 12px;">
        <a class="button button-small button-outline header-signin" href="/login">
          Sign In
        </a>
        <a class="button button-small header-cta" href="/login">
          Get Started <span>${icon('arrow', 15)}</span>
        </a>
      </div>
    </div>
  </header>
`;
