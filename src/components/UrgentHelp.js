import { icon } from './icons.js';

export const UrgentHelp = () => `
  <section class="urgent-section" id="urgent-help">
    <div class="shell urgent-banner reveal">
      <div class="urgent-title">
        <span class="urgent-icon">${icon('phone', 24)}</span>
        <span>Need Urgent Help?</span>
      </div>
      <div class="urgent-rule" aria-hidden="true"></div>
      <p>If you’re in distress or need immediate support, reach out to a trusted helpline.</p>
      <button class="button button-dark open-helplines-btn" type="button" aria-haspopup="dialog" aria-controls="helplines-dialog">
        View Helplines <span>${icon('arrow', 17)}</span>
      </button>
    </div>
  </section>
`;
