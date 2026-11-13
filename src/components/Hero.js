import { icon } from './icons.js';

export const Hero = () => `
  <section class="hero section-pad">
    <div class="shell hero-grid reveal">
      <div class="hero-copy">
        <div class="eyebrow">AI FOR MATERNAL WELLBEING <span aria-hidden="true"></span></div>
        <h1>Gentle, Intelligent<br />Support for<br />Every <em>Mother</em></h1>
        <p class="hero-lede">An AI-powered companion for early and sensitive detection of postpartum distress, with compassionate care and personalized support.</p>
        <div class="hero-ctas" style="display: flex; gap: 14px; align-items: center; flex-wrap: wrap;">
          <a class="button hero-cta" href="/login">Get Started <span>${icon('arrow', 15)}</span></a>
          <a class="button button-outline" href="#features"><span class="play-icon">${icon('play', 14)}</span> Watch Demo</a>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-circle" aria-hidden="true"></div>
        <picture>
          <source srcset="/assets/hero-mother.avif" type="image/avif" />
          <source srcset="/assets/hero-mother.webp" type="image/webp" />
          <img
            src="/assets/hero-mother.png"
            alt="Mother holding her baby in a gentle, warm moment"
            width="474"
            height="394"
            loading="eager"
            fetchpriority="high"
            decoding="async"
          />
        </picture>
      </div>
    </div>
    <div class="shell signal-row reveal reveal-delay-1">
      <div class="signal">
        <span class="signal-icon">${icon('leaf', 32)}</span>
        <span>Early &amp;<br />Sensitive Detection</span>
      </div>
      <div class="signal-divider" aria-hidden="true"></div>
      <div class="signal">
        <span class="signal-icon">${icon('layers', 32)}</span>
        <span>Understands<br />Multiple Cues</span>
      </div>
      <div class="signal-divider" aria-hidden="true"></div>
      <div class="signal">
        <span class="signal-icon">${icon('heart', 32)}</span>
        <span>Personalized<br />Care &amp; Guidance</span>
      </div>
    </div>
  </section>
`;
