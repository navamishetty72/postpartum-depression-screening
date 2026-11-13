import { icon } from './icons.js';

export const Features = () => `
  <section class="features section-pad" id="features">
    <div class="shell">
      <div class="section-heading reveal">
        <div class="eyebrow">KEY FEATURES <span aria-hidden="true"></span></div>
        <h2>Support That Understands <em>You</em></h2>
      </div>
      <div class="feature-grid reveal reveal-delay-1">
        <article class="feature-card">
          <div class="feature-icon">${icon('mic', 37)}</div>
          <h3>Multimodal Screening</h3>
          <p>Understands your wellbeing through voice, text, and optional video.</p>
        </article>
        <article class="feature-card feature-card-accent">
          <span class="badge">Core Capability</span>
          <div class="feature-icon">${icon('eye', 37)}</div>
          <h3>Notices What<br />Words Miss</h3>
          <p>Spots subtle signs of distress that can be easily overlooked.</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon">${icon('heart', 37)}</div>
          <h3>Personalized Care</h3>
          <p>Actionable insights, follow-ups, and supportive resources.</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon">${icon('shield', 37)}</div>
          <h3>Private &amp; Secure</h3>
          <p>Built with privacy-first safeguards so personal reflections stay confidential.</p>
        </article>
      </div>
    </div>
  </section>
`;
