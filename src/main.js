import './styles.css';
import { Header } from './components/Header.js';
import { Hero } from './components/Hero.js';
import { Approach } from './components/Approach.js';
import { Features } from './components/Features.js';
import { Evidence } from './components/Evidence.js';
import { Proof } from './components/Proof.js';
import { UrgentHelp } from './components/UrgentHelp.js';
import { Footer } from './components/Footer.js';
import { HelplineModal } from './components/HelplineModal.js';
import { AmbientBackdrop } from './components/AmbientBackdrop.js';
import { initHero3D, initEmpathyOrb3D } from './components/Miora3DScene.js';

const app = document.querySelector('#app');

app.innerHTML = `
  <a class="skip-link" href="#main-content">Skip to main content</a>
  ${AmbientBackdrop()}
  ${Header()}
  <main id="main-content">
    ${Hero()}
    ${Approach()}
    ${Features()}
    ${Evidence()}
    ${Proof()}
    ${UrgentHelp()}
  </main>
  ${Footer()}
  ${HelplineModal()}
`;

// 3D Interactive Scenes (gracefully falls back when WebGL is unavailable)
const heroCanvas = document.getElementById('hero-3d-canvas');
const heroVisual = document.querySelector('.hero-visual');
initHero3D(heroCanvas, heroVisual);

const orbCanvas = document.getElementById('orb-3d-canvas');
const orbStage = document.getElementById('orb-stage');
const orbStatusLabel = document.getElementById('orb-status-label');
const orbController = initEmpathyOrb3D(orbCanvas, orbStage);

const ORB_STATUS_TEXT = {
  share: 'Listening calmly · Voice & words',
  understand: 'Sensing subtle vocal & pattern cues',
  support: 'Sharing personalized care & guidance',
};

const orbModeBtns = document.querySelectorAll('.orb-mode-btn');
const stepTriggers = document.querySelectorAll('[data-orb-trigger]');

const selectOrbMode = (mode) => {
  if (!ORB_STATUS_TEXT[mode]) return;
  orbController.setMode(mode);
  if (orbStatusLabel) {
    orbStatusLabel.textContent = ORB_STATUS_TEXT[mode];
  }
  orbModeBtns.forEach((btn) => {
    const active = btn.dataset.orbMode === mode;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-pressed', String(active));
  });
  stepTriggers.forEach((card) => {
    card.classList.toggle('is-orb-active', card.dataset.orbTrigger === mode);
  });
};

orbModeBtns.forEach((btn) => {
  btn.addEventListener('click', () => selectOrbMode(btn.dataset.orbMode));
});

stepTriggers.forEach((card) => {
  card.addEventListener('mouseenter', () => selectOrbMode(card.dataset.orbTrigger));
  card.addEventListener('click', () => selectOrbMode(card.dataset.orbTrigger));
});

// Regional Helplines Modal Logic
const helplineDialog = document.getElementById('helplines-dialog');
const openHelplinesBtn = document.querySelector('.open-helplines-btn');
const modalCloseBtn = helplineDialog?.querySelector('.modal-close');
const modalBackdrop = helplineDialog?.querySelector('.modal-backdrop');

const openHelplineModal = () => {
  if (!helplineDialog) return;
  helplineDialog.hidden = false;
  document.body.style.overflow = 'hidden';
  modalCloseBtn?.focus();
};

const closeHelplineModal = () => {
  if (!helplineDialog || helplineDialog.hidden) return;
  helplineDialog.hidden = true;
  document.body.style.overflow = '';
  openHelplinesBtn?.focus();
};

openHelplinesBtn?.addEventListener('click', openHelplineModal);
modalCloseBtn?.addEventListener('click', closeHelplineModal);
modalBackdrop?.addEventListener('click', closeHelplineModal);

window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && helplineDialog && !helplineDialog.hidden) {
    closeHelplineModal();
  }
});

// Ensure all sections and lazy images are immediately renderable for printing & full-page captures
const revealElements = document.querySelectorAll('.reveal');
const revealAllForCapture = () => {
  revealElements.forEach((el) => el.classList.add('is-visible'));
  document.querySelectorAll('img[loading="lazy"]').forEach((img) => {
    img.loading = 'eager';
  });
};

revealElements.forEach((el) => el.classList.add('is-visible'));
window.addEventListener('beforeprint', revealAllForCapture);
