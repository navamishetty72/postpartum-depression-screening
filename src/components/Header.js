import { icon } from './icons.js';
import { BrandLogo } from './BrandLogo.js';

export const Header = () => `
  <header class="brand-header" id="top">
    <div class="shell brand-header-inner">
      <a class="brand" href="#top" aria-label="Miora — Maternal Emotional Intelligence">
        ${BrandLogo()}
      </a>
      <a class="button button-small header-cta" href="/dashboard">
        Dashboard <span>${icon('arrow', 15)}</span>
      </a>
    </div>
  </header>
`;
