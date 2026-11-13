export const Proof = () => `
  <section class="proof section-pad" id="about">
    <div class="shell proof-grid">
      <div class="testimonial reveal">
        <div class="testimonial-photo">
          <picture>
            <source srcset="/assets/testimonial-mother.avif" type="image/avif" />
            <source srcset="/assets/testimonial-mother.webp" type="image/webp" />
            <img
              src="/assets/testimonial-mother.png"
              alt="A smiling new mother"
              width="166"
              height="155"
              loading="lazy"
              decoding="async"
            />
          </picture>
        </div>
        <div class="quote-card">
          <span class="spotlight-kicker">Why We Built Miora</span>
          <p class="spotlight-copy">Many new mothers carry postpartum overwhelm quietly—often before anyone thinks to ask how they truly feel.</p>
          <p class="spotlight-note">Designed as a gentle, judgment-free first step toward support.</p>
        </div>
      </div>
      <div class="matters reveal reveal-delay-1">
        <div class="eyebrow"><span class="eyebrow-label">WHY IT <em>MATTERS</em></span><span aria-hidden="true"></span></div>
        <ul>
          <li><span class="check" aria-hidden="true">✓</span>Creates a calm, private space to be heard</li>
          <li><span class="check" aria-hidden="true">✓</span>Encourages early, timely emotional check-ins</li>
          <li><span class="check" aria-hidden="true">✓</span>Connects mothers with trusted next steps &amp; care</li>
        </ul>
      </div>
    </div>
  </section>
`;
