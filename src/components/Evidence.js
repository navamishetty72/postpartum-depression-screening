import { icon } from './icons.js';

export const Evidence = () => `
  <section class="evidence" id="evidence">
    <div class="shell evidence-strip reveal">
      <div class="evidence-title">Guided by <em>Research.</em> Built for <em>Care.</em></div>
      <div class="evidence-items">
        <div class="evidence-item">
          <span>${icon('flask', 27)}</span>
          <span>Research-Informed<br />Frameworks</span>
        </div>
        <div class="evidence-item">
          <span>${icon('shield', 27)}</span>
          <span>Privacy-First<br />Design</span>
        </div>
        <div class="evidence-item">
          <span>${icon('heart', 27)}</span>
          <span>Non-Diagnostic<br />Companion</span>
        </div>
      </div>
    </div>
  </section>
`;
