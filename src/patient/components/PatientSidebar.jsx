import React from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { BrandWordmark } from '../../dashboard/components/BrandWordmark.jsx';
import { PatientIcon } from './PatientIcons.jsx';
import '../styles/patientSidebar.css';

const NAV_ITEMS = [
  {
    to: '/patient/dashboard',
    matchPaths: ['/patient/dashboard', '/patient/home', '/patient'],
    label: 'Dashboard',
    icon: 'home',
  },
  {
    to: '/patient/medical-history',
    matchPaths: ['/patient/medical-history', '/medical-history'],
    label: 'Medical History',
    icon: 'medical-history',
  },
  {
    to: '/patient/screening',
    matchPaths: ['/patient/screening', '/screening', '/ai-screening', '/patient-screening', '/patient/ai-screening', '/screening-results', '/patient/screening/results'],
    label: 'AI Screening',
    icon: 'ai-screening',
  },
  {
    to: '/patient/ai-assistant',
    matchPaths: ['/patient/ai-assistant', '/ai-assistant', '/assistant', '/voice-assistant'],
    label: 'AI Assistant',
    icon: 'ai-assistant',
  },
  {
    to: '/patient/connect-doctor',
    matchPaths: ['/patient/connect-doctor', '/connect-doctor'],
    label: 'Connect to a Doctor',
    icon: 'connect-doctor',
  },
  {
    to: '/patient/reports',
    matchPaths: ['/patient/reports', '/patient/my-reports', '/reports', '/my-reports'],
    label: 'My Reports',
    icon: 'reports',
  },
  {
    to: '/patient/care-suggestions',
    matchPaths: ['/patient/care-suggestions', '/care-suggestions', '/patient/suggestions'],
    label: 'Care Suggestions',
    icon: 'care-suggestions',
  },
];

const FOOTER_ITEMS = [
  {
    to: '/patient/profile',
    matchPaths: ['/patient/profile'],
    label: 'Profile',
    icon: 'profile',
  },
  {
    to: '/patient/settings',
    matchPaths: ['/patient/settings'],
    label: 'Settings',
    icon: 'settings',
  },
];

export function PatientSidebar({ isMobileOpen, onCloseMobile }) {
  const location = useLocation();

  const isItemActive = (item) => {
    return item.matchPaths.some((p) => {
      if (p === '/patient/dashboard' || p === '/patient/home' || p === '/patient') {
        return location.pathname === '/patient/dashboard' || location.pathname === '/patient/home' || location.pathname === '/patient';
      }
      if (p === '/patient/reports' || p === '/reports') {
        return location.pathname === '/patient/reports' || location.pathname === '/patient/my-reports' || location.pathname === '/reports' || location.pathname === '/my-reports';
      }
      return location.pathname.startsWith(p);
    });
  };

  return (
    <aside
      className={`patient-sidebar ${isMobileOpen ? 'is-mobile-open' : ''}`}
      aria-label="Patient Portal Navigation"
    >
      <button
        type="button"
        className="patient-sidebar-close-btn"
        onClick={onCloseMobile}
        aria-label="Close navigation menu"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>

      <div>
        {/* Brand Header */}
        <div className="patient-sidebar-brand">
          <div className="patient-brand-row">
            <Link
              to="/"
              className="patient-brand-link"
              onClick={onCloseMobile}
              aria-label="Miora Home"
            >
              <BrandWordmark />
            </Link>
            <div className="patient-brand-divider" aria-hidden="true" />
            <div className="patient-brand-tagline">
              Maternal Emotional<br />Intelligence
            </div>
          </div>
        </div>

        <div className="patient-sidebar-line" aria-hidden="true" />

        {/* Primary Navigation Menu */}
        <nav className="patient-sidebar-nav" aria-label="Main Navigation">
          <p className="patient-nav-section-title">Patient Care</p>
          {NAV_ITEMS.map((item) => {
            const active = isItemActive(item);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`patient-nav-link ${active ? 'is-active' : ''}`}
                onClick={onCloseMobile}
              >
                <span className="patient-nav-icon">
                  <PatientIcon name={item.icon} size={18} />
                </span>
                <span className="patient-nav-label">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Navigation (Profile, Settings) */}
      <div className="patient-sidebar-footer">
        {FOOTER_ITEMS.map((item) => {
          const active = isItemActive(item);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={`patient-nav-link ${active ? 'is-active' : ''}`}
              onClick={onCloseMobile}
            >
              <span className="patient-nav-icon">
                <PatientIcon name={item.icon} size={18} />
              </span>
              <span className="patient-nav-label">{item.label}</span>
            </NavLink>
          );
        })}
      </div>
    </aside>
  );
}

