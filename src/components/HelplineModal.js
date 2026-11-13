import { icon } from './icons.js';

export const HelplineModal = () => `
  <div class="modal-overlay" id="helplines-dialog" role="dialog" aria-modal="true" aria-labelledby="helplines-title" hidden>
    <div class="modal-backdrop"></div>
    <div class="modal-container">
      <div class="modal-header">
        <div class="modal-header-icon" aria-hidden="true">${icon('phone', 22)}</div>
        <div class="modal-header-text">
          <h3 id="helplines-title">Regional Support Helplines</h3>
          <p class="modal-subtitle">Immediate, confidential assistance from trained counselors — 24/7 &amp; free.</p>
        </div>
        <button class="modal-close" type="button" aria-label="Close helplines dialog">${icon('close', 18)}</button>
      </div>
      <div class="modal-body">
        <ul class="helplines-list">
          <li class="helpline-entry">
            <div class="helpline-info">
              <span class="helpline-country">United States &amp; Canada</span>
              <strong>988 Suicide &amp; Crisis Lifeline</strong>
              <p>Free call or text available 24/7 across North America.</p>
            </div>
            <a class="helpline-call-btn" href="tel:988">Call or Text 988</a>
          </li>
          <li class="helpline-entry">
            <div class="helpline-info">
              <span class="helpline-country">United Kingdom</span>
              <strong>NHS 111 &amp; Emergency 999</strong>
              <p>Non-emergency medical advice (111) or urgent emergency response (999).</p>
            </div>
            <div class="helpline-btn-group">
              <a class="helpline-call-btn" href="tel:111">Call 111</a>
              <a class="helpline-call-btn helpline-call-alt" href="tel:999">Emergency 999</a>
            </div>
          </li>
          <li class="helpline-entry">
            <div class="helpline-info">
              <span class="helpline-country">India</span>
              <strong>Tele-MANAS (Govt. of India)</strong>
              <p>24/7 toll-free mental health counseling in multiple regional languages.</p>
            </div>
            <a class="helpline-call-btn" href="tel:14416">Call 14416</a>
          </li>
          <li class="helpline-entry">
            <div class="helpline-info">
              <span class="helpline-country">International &amp; Text</span>
              <strong>Crisis Text Line</strong>
              <p>Free, 24/7 text support with trained volunteer crisis counselors.</p>
            </div>
            <a class="helpline-call-btn" href="sms:741741?&body=HOME">Text HOME to 741741</a>
          </li>
        </ul>
      </div>
      <div class="modal-footer">
        <p>If you or someone you know is in immediate life-threatening physical danger, please contact your local emergency services immediately.</p>
      </div>
    </div>
  </div>
`;
