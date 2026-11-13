import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { initEmpathyOrb3D } from './components/Miora3DScene.js';

const ORB_STATUS_TEXT = {
  share: 'Listening calmly · Voice & words',
  understand: 'Sensing subtle vocal & pattern cues',
  support: 'Sharing personalized care & guidance',
};

export function LandingPageRoute() {
  const containerRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return undefined;

    root.innerHTML = `
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

    // 3D Interactive Empathy Core Scene
    const orbCanvas = root.querySelector('#orb-3d-canvas');
    const orbStage = root.querySelector('#orb-stage');
    const orbStatusLabel = root.querySelector('#orb-status-label');
    const orbController = initEmpathyOrb3D(orbCanvas, orbStage);

    const orbModeBtns = root.querySelectorAll('.orb-mode-btn');
    const stepTriggers = root.querySelectorAll('[data-orb-trigger]');

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

    const modeClickHandlers = [];
    orbModeBtns.forEach((btn) => {
      const fn = () => selectOrbMode(btn.dataset.orbMode);
      btn.addEventListener('click', fn);
      modeClickHandlers.push([btn, fn]);
    });

    const triggerHandlers = [];
    stepTriggers.forEach((card) => {
      const fn = () => selectOrbMode(card.dataset.orbTrigger);
      card.addEventListener('mouseenter', fn);
      card.addEventListener('click', fn);
      triggerHandlers.push([card, fn]);
    });

    const dashboardCta = root.querySelector('.header-cta');
    const handleDashboardClick = (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      navigate('/dashboard');
    };
    dashboardCta?.addEventListener('click', handleDashboardClick);

    const helplineDialog = root.querySelector('#helplines-dialog');
    const openHelplinesBtn = root.querySelector('.open-helplines-btn');
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

    const onKeyDown = (e) => {
      if (e.key === 'Escape' && helplineDialog && !helplineDialog.hidden) {
        closeHelplineModal();
      }
    };
    window.addEventListener('keydown', onKeyDown);

    const revealElements = root.querySelectorAll('.reveal');
    const revealAllForCapture = () => {
      revealElements.forEach((el) => el.classList.add('is-visible'));
      root.querySelectorAll('img[loading="lazy"]').forEach((img) => {
        img.loading = 'eager';
      });
    };
    revealAllForCapture();
    window.addEventListener('beforeprint', revealAllForCapture);

    return () => {
      document.body.style.overflow = '';
      orbController.destroy();
      modeClickHandlers.forEach(([el, fn]) => el.removeEventListener('click', fn));
      triggerHandlers.forEach(([el, fn]) => {
        el.removeEventListener('mouseenter', fn);
        el.removeEventListener('click', fn);
      });
      dashboardCta?.removeEventListener('click', handleDashboardClick);
      openHelplinesBtn?.removeEventListener('click', openHelplineModal);
      modalCloseBtn?.removeEventListener('click', closeHelplineModal);
      modalBackdrop?.removeEventListener('click', closeHelplineModal);
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('beforeprint', revealAllForCapture);
      root.innerHTML = '';
    };
  }, [navigate]);

  return <div ref={containerRef} className="landing-root" />;
}
