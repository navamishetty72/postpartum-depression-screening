import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { KpiCard } from '../components/KpiCard.jsx';
import { ScreeningActivityChart } from '../components/ScreeningActivityChart.jsx';
import { RiskDistributionCard } from '../components/RiskDistributionCard.jsx';
import { PriorityCasesCard } from '../components/PriorityCasesCard.jsx';
import { RecentScreeningsCard } from '../components/RecentScreeningsCard.jsx';
import { QuickActionsBar } from '../components/QuickActionsBar.jsx';

export function CommandCenterPage() {
  const {
    metrics,
    weeklyRecords,
    priorityCases,
    screenings,
    setIsAddMotherOpen,
  } = useClinicalData();
  const navigate = useNavigate();

  const [ctaMenuOpen, setCtaMenuOpen] = useState(false);
  const ctaRef = useRef(null);

  useEffect(() => {
    const closeOnClickOutside = (e) => {
      if (ctaRef.current && !ctaRef.current.contains(e.target)) {
        setCtaMenuOpen(false);
      }
    };
    const closeOnEsc = (e) => {
      if (e.key === 'Escape') setCtaMenuOpen(false);
    };
    document.addEventListener('mousedown', closeOnClickOutside);
    window.addEventListener('keydown', closeOnEsc);
    return () => {
      document.removeEventListener('mousedown', closeOnClickOutside);
      window.removeEventListener('keydown', closeOnEsc);
    };
  }, []);

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Restrained ambient blush ribbon behind header CTA */}
        <svg
          className="miora-header-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="headerWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="48%" stopColor="#f9cbd7" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.18" />
            </linearGradient>
          </defs>
          <path
            d="M0 140 C 160 135, 220 35, 390 42 C 510 46, 560 92, 640 30 L 640 160 L 0 160 Z"
            fill="url(#headerWaveGrad)"
          />
        </svg>

        {/* Dashboard Header */}
        <section className="miora-dash-header" aria-labelledby="command-center-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>DASHBOARD</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="command-center-heading" className="miora-dash-title">
              Postpartum Health <em>Intelligence</em>
            </h1>
            <p className="miora-dash-subtitle">
              A real-time overview of maternal wellbeing, screenings and cases requiring attention.
            </p>
          </div>

          <div className="miora-dash-header-actions" ref={ctaRef}>
            <button
              type="button"
              className="miora-cta-primary"
              onClick={() => navigate('/live-screening')}
            >
              <DashboardIcon name="plus" size={16} strokeWidth={2.2} />
              <span>Start Screening</span>
            </button>

            <div className="miora-cta-dropdown-wrap">
              <button
                type="button"
                className="miora-cta-circle"
                aria-label="More screening and intake actions"
                aria-expanded={ctaMenuOpen}
                onClick={() => setCtaMenuOpen((prev) => !prev)}
              >
                <DashboardIcon name="chevronDown" size={16} strokeWidth={1.9} />
              </button>

              {ctaMenuOpen && (
                <div className="dash-popover miora-cta-menu" role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setCtaMenuOpen(false);
                      navigate('/live-screening?mode=voice');
                    }}
                  >
                    <DashboardIcon name="mic" size={15} />
                    <span>Voice + Text Screening</span>
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setCtaMenuOpen(false);
                      navigate('/live-screening?mode=text');
                    }}
                  >
                    <DashboardIcon name="clipboardList" size={15} />
                    <span>Quick Text Check-in</span>
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setCtaMenuOpen(false);
                      setIsAddMotherOpen(true);
                    }}
                  >
                    <DashboardIcon name="userPlus" size={15} />
                    <span>Register New Mother</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* 4 KPI Cards */}
        <section className="miora-kpi-grid" aria-label="Key clinical metrics">
          <KpiCard
            icon="users"
            value={metrics.registeredMothers}
            trend={metrics.trends.registeredMothers}
            trendTone="positive"
            label="Registered Mothers"
            onClick={() => navigate('/mothers')}
          />
          <KpiCard
            icon="mic"
            value={metrics.screeningsCompleted}
            trend={metrics.trends.screeningsCompleted}
            trendTone="positive"
            label="Screenings Completed"
            onClick={() => navigate('/results')}
          />
          <KpiCard
            icon="alertTriangle"
            value={metrics.casesForReview}
            trend={metrics.trends.casesForReview}
            trendTone="attention"
            label="Cases for Review"
            onClick={() => navigate('/mothers?filter=priority')}
          />
          <KpiCard
            icon="layers"
            value={metrics.potentialDiscordance}
            trend={metrics.trends.potentialDiscordance}
            trendTone="positive"
            label="Potential Discordance"
            onClick={() => navigate('/discordance')}
          />
        </section>

        {/* Charts Grid: Screening Activity + Risk Distribution */}
        <div className="miora-charts-grid">
          <ScreeningActivityChart records={weeklyRecords} />
          <RiskDistributionCard
            distribution={metrics.riskDistribution}
            total={metrics.totalDistribution}
            onSelectCategory={(riskName) =>
              navigate(`/results?risk=${encodeURIComponent(riskName)}`)
            }
          />
        </div>

        {/* Bottom Lists Grid: Priority Cases + Recent Screenings */}
        <div className="miora-cases-grid">
          <PriorityCasesCard
            cases={priorityCases}
            onSelectCase={(motherId) => navigate(`/mothers/${motherId}`)}
            onViewAll={() => navigate('/mothers?filter=priority')}
          />
          <RecentScreeningsCard
            screenings={screenings}
            onSelectScreening={(entry) => navigate(`/results/${entry.motherId}`)}
            onViewAll={() => navigate('/results')}
          />
        </div>

        {/* Compact Horizontal Quick Actions */}
        <QuickActionsBar
          onAddMother={() => setIsAddMotherOpen(true)}
          onReviewCases={() => navigate('/mothers?filter=review')}
          onViewInsights={() => navigate('/insights')}
          onClinicalReview={() => navigate('/discordance')}
        />
      </div>
    </div>
  );
}
