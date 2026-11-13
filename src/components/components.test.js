import { describe, it, expect } from 'vitest';
import { iconPaths, icon } from './icons.js';
import { Header } from './Header.js';
import { Hero } from './Hero.js';
import { Approach } from './Approach.js';
import { Features } from './Features.js';
import { Evidence } from './Evidence.js';
import { Proof } from './Proof.js';
import { UrgentHelp } from './UrgentHelp.js';
import { Footer } from './Footer.js';
import { HelplineModal } from './HelplineModal.js';
import { AmbientBackdrop } from './AmbientBackdrop.js';
import { initEmpathyOrb3D } from './Miora3DScene.js';

describe('Miora Components & Fixes', () => {
  it('eye icon uses valid SVG path syntax', () => {
    const eyeSvg = icon('eye', 37);
    expect(eyeSvg).toContain(iconPaths.eye);
    expect(eyeSvg).toContain('M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z');
  });

  it('Approach section uses consistent American spelling and clear phrasing', () => {
    const html = Approach();
    expect(html).toContain('Gently analyzes your words, voice, or patterns.');
    expect(html).toContain('Provides timely guidance and clear next steps.');
  });

  it('Features card 2 displays Core Capability badge and grammatical subject-verb agreement', () => {
    const html = Features();
    expect(html).toContain('<span class="badge">Core Capability</span>');
    expect(html).toContain('Spots subtle signs of distress that can be easily overlooked.');
    expect(html).toContain('voice, text, and optional video.');
  });

  it('Evidence section uses honest hackathon-ready design principles without false validation claims', () => {
    const html = Evidence();
    expect(html).toContain('Research-Informed<br />Frameworks');
    expect(html).toContain('Privacy-First<br />Design');
    expect(html).toContain('Non-Diagnostic<br />Companion');
    expect(html).not.toContain('Expert Validated');
  });

  it('Proof section has id="about", clean eyebrow wrapper, and mission spotlight without fabricated user reviews', () => {
    const html = Proof();
    expect(html).toContain('id="about"');
    expect(html).toContain('<span class="eyebrow-label">WHY IT <em>MATTERS</em></span>');
    expect(html).toContain('Why We Built Miora');
    expect(html).not.toContain('Aishwarya');
    expect(html).not.toContain('<blockquote');
  });

  it('UrgentHelp section uses id="urgent-help" and opens helpline modal without forced desktop break', () => {
    const html = UrgentHelp();
    expect(html).toContain('id="urgent-help"');
    expect(html).toContain('open-helplines-btn');
    expect(html).not.toContain('href="tel:988"');
    expect(html).not.toContain('desktop-only');
  });

  it('Header renders Miora calligraphic logo without side tagline text and links Dashboard to /dashboard on top right', () => {
    const html = Header();
    expect(html).toContain('brand-wordmark');
    expect(html).toContain('brand-m');
    expect(html).toContain('iora');
    expect(html).toContain('Dashboard');
    expect(html).toContain('href="/dashboard"');
    expect(html).toContain('header-cta');
    expect(html).not.toContain('Get Started Free');
    expect(html).not.toContain('brand-rule');
    expect(html).not.toContain('brand-tagline');
    expect(html).not.toContain('Watch Demo');
    expect(html).not.toContain('<nav');
    expect(html).not.toContain('mobile-toggle');
    expect(html).not.toContain('mobile-menu');
    expect(html).not.toContain('sign-in');
  });

  it('Hero keeps Watch Demo button in hero-ctas', () => {
    const html = Hero();
    expect(html).toContain('hero-ctas');
    expect(html).toContain('Watch Demo');
    expect(html).not.toContain('Get Started Free');
  });

  it('HelplineModal contains regional crisis numbers with consistent spelling', () => {
    const modalHtml = HelplineModal();
    expect(modalHtml).toContain('988 Suicide &amp; Crisis Lifeline');
    expect(modalHtml).toContain('111');
    expect(modalHtml).toContain('999');
    expect(modalHtml).toContain('14416');
    expect(modalHtml).toContain('741741');
    expect(modalHtml).toContain('mental health counseling');
  });

  it('AmbientBackdrop is decorative and hidden from assistive tech', () => {
    const html = AmbientBackdrop();
    expect(html).toContain('class="page-ambient"');
    expect(html).toContain('aria-hidden="true"');
  });

  it('Hero keeps portrait clean and Approach includes interactive 3D Empathy Core stage with WebGL fallback', () => {
    expect(Hero()).not.toContain('hero-3d-canvas');
    const approachHtml = Approach();
    expect(approachHtml).toContain('id="orb-3d-canvas"');
    expect(approachHtml).toContain('data-orb-mode="share"');
    expect(approachHtml).toContain('data-orb-mode="understand"');
    expect(approachHtml).toContain('data-orb-mode="support"');

    const orbCtrl = initEmpathyOrb3D(null, null);
    expect(typeof orbCtrl.setMode).toBe('function');
    expect(typeof orbCtrl.destroy).toBe('function');
    orbCtrl.setMode('understand');
    orbCtrl.destroy();
  });

  it('Footer keeps only Miora logo and note without footer nav links or social placeholders', () => {
    const html = Footer();
    expect(html).toContain('brand-wordmark');
    expect(html).toContain('Maternal Emotional Intelligence');
    expect(html).not.toContain('footer-links');
    expect(html).not.toContain('footer-socials');
    expect(html).not.toContain('GH');
  });
});
