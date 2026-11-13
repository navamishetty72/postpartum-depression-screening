import { icon } from './icons.js';

export const Approach = () => `
  <section class="approach section-pad" id="approach">
    <div class="shell approach-grid">
      <div class="section-intro reveal">
        <div class="eyebrow">OUR APPROACH <span aria-hidden="true"></span></div>
        <h2>How <em>Miora</em><br />Works</h2>
        <p>A simple, supportive journey from listening to care.</p>
      </div>
      <div class="steps reveal reveal-delay-1">
        <article class="step-card" data-orb-trigger="share">
          <div class="step-top">
            <span class="step-icon">${icon('mic', 31)}</span>
            <span class="step-arrow">${icon('arrow', 30)}</span>
          </div>
          <h3>1. Share</h3>
          <p>A natural, private conversation.</p>
        </article>
        <article class="step-card" data-orb-trigger="understand">
          <div class="step-top">
            <span class="step-icon">${icon('sparkles', 31)}</span>
            <span class="step-arrow">${icon('arrow', 30)}</span>
          </div>
          <h3>2. Understand</h3>
          <p>Gently analyzes your words, voice, or patterns.</p>
        </article>
        <article class="step-card" data-orb-trigger="support">
          <div class="step-top">
            <span class="step-icon">${icon('hand', 31)}</span>
          </div>
          <h3>3. Support</h3>
          <p>Provides timely guidance and clear next steps.</p>
        </article>
      </div>
    </div>

    <div class="shell orb-showcase reveal">
      <div class="orb-stage" id="orb-stage">
        <canvas class="orb-3d-canvas" id="orb-3d-canvas" aria-hidden="true"></canvas>
        <div class="orb-fallback" aria-hidden="true"></div>
        <span class="orb-status-pill" id="orb-status-label">Listening calmly · Voice &amp; words</span>
      </div>
      <div class="orb-details">
        <div class="orb-kicker">INTERACTIVE 3D EMPATHY CORE</div>
        <h3>See how Miora adapts to every stage of care</h3>
        <p class="orb-summary">Move your cursor over the 3D companion orb or select a stage below to preview how Miora shifts from gentle listening to personalized support.</p>
        <div class="orb-controls" role="group" aria-label="Companion stage preview">
          <button type="button" class="orb-mode-btn is-active" data-orb-mode="share" aria-pressed="true">
            <span class="orb-mode-num">01</span>
            <span>
              <strong>Share</strong>
              <small>Calm, unhurried check-in</small>
            </span>
          </button>
          <button type="button" class="orb-mode-btn" data-orb-mode="understand" aria-pressed="false">
            <span class="orb-mode-num">02</span>
            <span>
              <strong>Understand</strong>
              <small>Sensing subtle vocal &amp; text cues</small>
            </span>
          </button>
          <button type="button" class="orb-mode-btn" data-orb-mode="support" aria-pressed="false">
            <span class="orb-mode-num">03</span>
            <span>
              <strong>Support</strong>
              <small>Tailored guidance &amp; trusted steps</small>
            </span>
          </button>
        </div>
      </div>
    </div>
  </section>
`;
