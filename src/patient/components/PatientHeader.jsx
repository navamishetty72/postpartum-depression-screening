import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from './PatientIcons.jsx';

export function PatientHeader({ onToggleMobile }) {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    patient,
    notifications = [],
    markNotificationRead,
    markAllNotificationsRead,
  } = usePatient();

  const [notifDropdownOpen, setNotifDropdownOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  const notifRef = useRef(null);
  const profileRef = useRef(null);

  // Close dropdowns on outside click or escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifDropdownOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileDropdownOpen(false);
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setNotifDropdownOpen(false);
        setProfileDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Determine current page title dynamically
  const getPageTitle = () => {
    const p = location.pathname;
    if (p.includes('/medical-history')) return 'Medical History';
    if (p.includes('/screening/results') || p.includes('/screening-results')) return 'Screening Results';
    if (p.includes('/screening')) return 'AI Screening';
    if (p.includes('/ai-assistant') || p.includes('/assistant')) return 'AI Assistant';
    if (p.includes('/connect-doctor') || p.includes('/connect')) return 'Connect to a Doctor';
    if (p.includes('/care-suggestions') || p.includes('/suggestions')) return 'Care Suggestions';
    if (p.includes('/profile')) return 'Patient Profile';
    if (p.includes('/settings')) return 'Settings';
    return 'My Reports';
  };

  const unreadNotifs = notifications.filter((n) => !n.read);
  const unreadCount = unreadNotifs.length;

  const patientName = patient?.name || 'Amara';
  const patientInitials = patient?.avatarInitials || (patientName
    ? patientName[0].toUpperCase()
    : 'A');

  return (
    <header className="patient-header">
      <div className="patient-header-left">
        {/* Mobile Hamburger Button */}
        <button
          type="button"
          className="patient-header-mobile-toggle"
          onClick={onToggleMobile}
          aria-label="Open sidebar menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        {/* Dynamic Page Title */}
        <div className="patient-header-title-group">
          <span className="patient-header-title">{getPageTitle()}</span>
          <span className="patient-confidential-badge">
            <span className="patient-badge-dot" aria-hidden="true" />
            Confidential Maternal Emotional Care
          </span>
        </div>
      </div>

      {/* Right: Notifications & Profile */}
      <div className="patient-header-right">
        {/* Notification Bell Button */}
        <div className="patient-header-menu-wrap" ref={notifRef}>
          <button
            type="button"
            className={`patient-icon-btn ${unreadCount > 0 ? 'has-badge' : ''}`}
            onClick={() => {
              setNotifDropdownOpen((prev) => !prev);
              setProfileDropdownOpen(false);
            }}
            aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ''}`}
            aria-expanded={notifDropdownOpen}
          >
            <PatientIcon name="bell" size={18} />
            {unreadCount > 0 && (
              <span className="patient-notif-indicator">{unreadCount}</span>
            )}
          </button>

          {notifDropdownOpen && (
            <div className="patient-dropdown-popover patient-notif-popover" role="dialog" aria-label="Notifications list">
              <div className="patient-popover-header">
                <span className="patient-popover-title">Notifications</span>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    className="patient-popover-action-btn"
                    onClick={() => markAllNotificationsRead?.()}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="patient-popover-list">
                {notifications.length === 0 ? (
                  <div className="patient-popover-empty">No new notifications</div>
                ) : (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className={`patient-notif-row ${!notif.read ? 'is-unread' : ''}`}
                      onClick={() => markNotificationRead?.(notif.id)}
                    >
                      <div className="patient-notif-row-header">
                        <strong className="patient-notif-row-title">{notif.title}</strong>
                        <span className="patient-notif-row-date">{notif.date}</span>
                      </div>
                      <p className="patient-notif-row-msg">{notif.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Patient Profile / Avatar */}
        <div className="patient-header-menu-wrap" ref={profileRef}>
          <button
            type="button"
            className="patient-profile-pill"
            onClick={() => {
              setProfileDropdownOpen((prev) => !prev);
              setNotifDropdownOpen(false);
            }}
            aria-label="Patient profile menu"
            aria-expanded={profileDropdownOpen}
          >
            <span className="patient-avatar-circle">{patientInitials}</span>
            <span className="patient-avatar-name">{patientName}</span>
            <svg className="patient-chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {profileDropdownOpen && (
            <div className="patient-dropdown-popover patient-profile-popover" role="menu">
              <div className="patient-profile-popover-info">
                <span className="patient-profile-popover-name">{patientName}</span>
                <span className="patient-profile-popover-meta">{patient?.stage || 'Postpartum Care'} &bull; ID: {patient?.id || 'P-104'}</span>
              </div>
              <div className="patient-popover-divider" />
              <NavLink
                to="/patient/reports"
                className="patient-popover-item"
                onClick={() => setProfileDropdownOpen(false)}
              >
                <PatientIcon name="reports" size={16} />
                <span>Patient Dashboard</span>
              </NavLink>
              <NavLink
                to="/patient/care-suggestions"
                className="patient-popover-item"
                onClick={() => setProfileDropdownOpen(false)}
              >
                <PatientIcon name="care-suggestions" size={16} />
                <span>My Care Suggestions</span>
              </NavLink>
              <NavLink
                to="/dashboard"
                className="patient-popover-item"
                onClick={() => setProfileDropdownOpen(false)}
              >
                <PatientIcon name="connect-doctor" size={16} />
                <span>Switch to Doctor Portal</span>
              </NavLink>
              <div className="patient-popover-divider" />
              <button
                type="button"
                className="patient-popover-item is-logout"
                onClick={() => {
                  setProfileDropdownOpen(false);
                  navigate('/login');
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
