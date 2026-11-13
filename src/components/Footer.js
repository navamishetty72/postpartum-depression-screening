import { BrandLogo } from './BrandLogo.js';

export const Footer = () => `
  <footer class="site-footer">
    <div class="shell footer-inner">
      <a class="brand" href="#top" aria-label="Miora home">
        ${BrandLogo()}
      </a>
      <p class="footer-note">Maternal Emotional Intelligence · Built for compassionate support</p>
    </div>
  </footer>
`;
