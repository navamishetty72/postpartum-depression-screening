import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { CLINICIAN_PROFILE } from '../data/mockClinicalData.js';
import { BrandWordmark } from './BrandWordmark.jsx';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge, StatusBadge } from './Badges.jsx';

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Mothers & Cases', to: '/mothers' },
  { label: 'Screening', to: '/live-screening', matchPaths: ['/live-screening', '/upload-analyze'] },
  { label: 'Results', to: '/results' },
  { label: 'Discordance', to: '/discordance' },
  { label: 'Insights & Care', to: '/insights' },
  { label: 'Clinical Review', to: '/clinical-review' },
];

export function TopNav() {
  const { alerts, mothers, screenings } = useClinicalData();
  const navigate = useNavigate();
  const location = useLocation();

  const [openMenu, setOpenMenu] = useState(null); // 'search' | 'alerts' | 'profile' | 'mobile'
  const [searchQuery, setSearchQuery] = useState('');
  const navRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpenMenu(null);
      }
    };
    const handleEsc = (e) => {
      if (e.key === 'Escape') setOpenMenu(null);
    };
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEsc);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEsc);
    };
  }, []);

  useEffect(() => {
    if (openMenu === 'search') {
      setTimeout(() => searchInputRef.current?.focus(), 40);
    }
  }, [openMenu]);

  const trimmedQuery = searchQuery.trim().toLowerCase();
  const matchedMothers = trimmedQuery
    ? mothers
        .filter(
          (m) =>
            m.id.toLowerCase().includes(trimmedQuery) ||
            m.name.toLowerCase().includes(trimmedQuery) ||
            m.reasonForReview.toLowerCase().includes(trimmedQuery)
        )
        .slice(0, 5)
    : mothers.slice(0, 4);

  const matchedScreenings = trimmedQuery
    ? screenings
        .filter(
          (s) =>
            s.motherId.toLowerCase().includes(trimmedQuery) ||
            s.id.toLowerCase().includes(trimmedQuery)
        )
        .slice(0, 3)
    : [];

  return (
    <header className="dash-topnav" ref={navRef}>
      <div className="dash-topnav-inner">
        <div className="dash-brand-group">
          <Link
            to="/dashboard"
            className="dash-brand-link"
            aria-label="Miora Dashboard"
          >
            <BrandWordmark />
          </Link>
        </div>

        <nav className="dash-nav-links" aria-label="Clinician workspace navigation">
          {NAV_ITEMS.map((item) => {
            const extraActive = item.matchPaths?.some((p) =>
              location.pathname.startsWith(p)
            );
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `dash-nav-link ${isActive || extraActive ? 'is-active' : ''}`
                }
              >
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="dash-nav-utilities">
          <div className="dash-utility-wrap">
            <button
              type="button"
              className={`dash-icon-btn ${openMenu === 'search' ? 'is-open' : ''}`}
              aria-label="Search mothers and screenings"
              aria-expanded={openMenu === 'search'}
              onClick={() => setOpenMenu((prev) => (prev === 'search' ? null : 'search'))}
            >
              <DashboardIcon name="search" size={18} strokeWidth={1.8} />
            </button>

            {openMenu === 'search' && (
              <div className="dash-popover dash-search-popover" role="dialog" aria-label="Quick search">
                <div className="dash-search-input-row">
                  <DashboardIcon name="search" size={16} />
                  <input
                    ref={searchInputRef}
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search Mother ID (e.g. M-104) or cue..."
                    aria-label="Search Mother ID or clinical cue"
                  />
                </div>
                <div className="dash-popover-section">
                  <div className="dash-popover-label">Mothers &amp; Cases</div>
                  {matchedMothers.length > 0 ? (
                    matchedMothers.map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        className="dash-search-result"
                        onClick={() => {
                          setOpenMenu(null);
                          setSearchQuery('');
                          navigate(`/mothers/${m.id}`);
                        }}
                      >
                        <div>
                          <strong>{m.id}</strong> · {m.name} <span>(Week {m.postpartumWeek})</span>
                        </div>
                        <RiskBadge risk={m.risk} />
                      </button>
                    ))
                  ) : (
                    <p className="dash-popover-empty">No matching mothers found.</p>
                  )}
                </div>
                {matchedScreenings.length > 0 && (
                  <div className="dash-popover-section">
                    <div className="dash-popover-label">Recent Screenings</div>
                    {matchedScreenings.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        className="dash-search-result"
                        onClick={() => {
                          setOpenMenu(null);
                          setSearchQuery('');
                          navigate(`/results/${s.motherId}`);
                        }}
                      >
                        <div>
                          <strong>{s.id}</strong> · {s.motherId} <span>({s.completedAgo})</span>
                        </div>
                        <StatusBadge status={s.status} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="dash-utility-wrap">
            <button
              type="button"
              className={`dash-icon-btn dash-bell-btn ${openMenu === 'alerts' ? 'is-open' : ''}`}
              aria-label={`Notifications (${alerts.length} clinical alerts)`}
              aria-expanded={openMenu === 'alerts'}
              onClick={() => setOpenMenu((prev) => (prev === 'alerts' ? null : 'alerts'))}
            >
              <DashboardIcon name="bell" size={18} strokeWidth={1.8} />
              {alerts.length > 0 && <span className="dash-bell-dot" aria-hidden="true" />}
            </button>

            {openMenu === 'alerts' && (
              <div className="dash-popover dash-alerts-popover" role="dialog" aria-label="Clinical alerts">
                <div className="dash-popover-header">
                  <span>Clinical Notifications</span>
                  <span className="dash-popover-count">{alerts.length} active</span>
                </div>
                <div className="dash-alerts-list">
                  {alerts.map((alert) => (
                    <button
                      key={alert.id}
                      type="button"
                      className="dash-alert-item"
                      onClick={() => {
                        setOpenMenu(null);
                        navigate(`/mothers/${alert.motherId}`);
                      }}
                    >
                      <span className={`dash-alert-dot severity-${alert.severity}`} aria-hidden="true" />
                      <div className="dash-alert-copy">
                        <p>{alert.title}</p>
                        <span>{alert.time}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="dash-utility-wrap">
            <button
              type="button"
              className="dash-avatar-btn"
              aria-label="Clinician profile menu"
              aria-expanded={openMenu === 'profile'}
              onClick={() => setOpenMenu((prev) => (prev === 'profile' ? null : 'profile'))}
            >
              {CLINICIAN_PROFILE.initials}
            </button>

            {openMenu === 'profile' && (
              <div className="dash-popover dash-profile-popover" role="dialog" aria-label="Clinician profile">
                <div className="dash-profile-meta">
                  <strong>{CLINICIAN_PROFILE.name}</strong>
                  <span>{CLINICIAN_PROFILE.role}</span>
                  <small>{CLINICIAN_PROFILE.clinic}</small>
                </div>
                <div className="dash-profile-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setOpenMenu(null);
                      navigate('/insights');
                    }}
                  >
                    Care &amp; Practice Insights
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setOpenMenu(null);
                      navigate('/patient/dashboard');
                    }}
                  >
                    Switch to Patient Portal
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setOpenMenu(null);
                      navigate('/');
                    }}
                  >
                    View Miora Landing Page
                  </button>
                  <button
                    type="button"
                    style={{ color: '#c73566', fontWeight: '500' }}
                    onClick={() => {
                      setOpenMenu(null);
                      navigate('/login');
                    }}
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>

          <button
            type="button"
            className="dash-mobile-menu-btn"
            aria-label="Toggle navigation menu"
            aria-expanded={openMenu === 'mobile'}
            onClick={() => setOpenMenu((prev) => (prev === 'mobile' ? null : 'mobile'))}
          >
            <DashboardIcon name={openMenu === 'mobile' ? 'close' : 'menu'} size={20} />
          </button>
        </div>
      </div>

      {openMenu === 'mobile' && (
        <nav className="dash-mobile-drawer" aria-label="Mobile clinician navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `dash-mobile-link ${isActive ? 'is-active' : ''}`
              }
              onClick={() => setOpenMenu(null)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}

