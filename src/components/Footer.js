import { BrandLogo } from './BrandLogo.js';

export const Footer = () => `
  <footer class="site-footer">
    <div class="shell footer-inner">
      <a class="brand" href="#top" aria-label="Miora home">
        ${BrandLogo()}
      </a>
      <div class="footer-links" aria-label="Footer navigation">
        <a href="#top">Home</a>
        <a href="#features">Features</a>
        <a href="#approach">How it Works</a>
        <a href="#evidence">Evidence</a>
        <a href="#about">About</a>
        <a href="#urgent-help">Crisis Support</a>
      </div>
      <div class="footer-socials" aria-label="Social media links">
        <a href="#about" aria-label="Miora on GitHub">
          <span aria-hidden="true">GH</span>
          <span class="sr-only">GitHub</span>
        </a>
        <a href="#about" aria-label="Miora on LinkedIn">
          <span aria-hidden="true">in</span>
          <span class="sr-only">LinkedIn</span>
        </a>
        <a href="#about" aria-label="Miora on X">
          <span aria-hidden="true">X</span>
          <span class="sr-only">X (formerly Twitter)</span>
        </a>
      </div>
    </div>
  </footer>
`;
