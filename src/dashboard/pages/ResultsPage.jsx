import React, { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { INITIAL_SCREENINGS } from '../data/mockClinicalData.js';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { RiskBadge } from '../components/Badges.jsx';
import {
  ModalityAnalysisCard,
  MultimodalSummaryCard,
  OverallRiskCard,
  RiskTrendCard,
} from '../components/ResultsChartsAndVisuals.jsx';
import {
  ExportReportModal,
  ShareCaseModal,
  SupportResourcesModal,
} from '../components/ResultsModals.jsx';

export function ResultsPage() {
  const {
    mothers,
    screenings,
    updateMotherStatus,
    shareCaseHandoff,
  } = useClinicalData();
  const { motherId } = useParams();
  const navigate = useNavigate();

  const [exportOpen, setExportOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const [followUpNotice, setFollowUpNotice] = useState('');

  const activeScreening = useMemo(() => {
    if (motherId) {
      return (
        screenings.find((s) => s.motherId.toLowerCase() === motherId.toLowerCase()) ||
        null
      );
    }
    if (screenings.length > INITIAL_SCREENINGS.length) {
      return screenings[0];
    }
    return screenings.find((s) => s.motherId === 'M-108') || screenings[0] || null;
  }, [screenings, motherId]);

  const activeMother = useMemo(() => {
    if (!activeScreening) return null;
    return mothers.find((m) => m.id === activeScreening.motherId) || null;
  }, [mothers, activeScreening]);

  const handleSelectSession = (nextMotherId) => {
    setFollowUpNotice('');
    navigate(`/results/${nextMotherId}`);
  };

  const handleScheduleFollowUp = () => {
    if (!activeScreening) return;
    updateMotherStatus(activeScreening.motherId, 'Follow-up');
    setFollowUpNotice(`7-day follow-up scheduled for ${activeScreening.motherId}`);
  };

  if (motherId && !activeScreening) {
    return (
      <div className="miora-command-shell">
        <div className="miora-command-frame">
          <section className="miora-card miora-results-empty-state">
            <h2>Screening Record Not Found</h2>
            <p>
              No completed or pending screening record was found for Mother ID{' '}
              <strong>{motherId}</strong>.
            </p>
            <div className="miora-modal-actions">
              <button
                type="button"
                className="miora-btn-secondary"
                onClick={() => navigate('/mothers')}
              >
                Open Mothers &amp; Cases
              </button>
              <button
                type="button"
                className="miora-cta-primary"
                onClick={() => navigate('/results')}
              >
                View Latest Results
              </button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const isCompleted = activeScreening?.status === 'Completed';

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Flowing Blush Header Waves */}
        <svg
          className="miora-header-ribbon miora-mothers-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="resultsWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#resultsWaveGrad)"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="results-page-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>SCREENING RESULTS</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="results-page-heading" className="miora-dash-title">
              Maternal Screening <em>Results</em>
            </h1>
            <p className="miora-dash-subtitle">
              Multimodal analysis of the screening session with risk assessment and key insights.
            </p>
          </div>

          <div className="miora-results-header-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setExportOpen(true)}
            >
              <DashboardIcon name="download" size={15} />
              <span>Export Report</span>
            </button>
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setShareOpen(true)}
            >
              <DashboardIcon name="share" size={15} />
              <span>Share Case</span>
            </button>
          </div>
        </section>

        {/* Patient Information Strip */}
        {activeScreening && (
          <section className="miora-card miora-patient-strip" aria-label="Screening session summary">
            <div className="miora-patient-item">
              <span className="miora-patient-icon" aria-hidden="true">
                <DashboardIcon name="user" size={18} />
              </span>
              <div className="miora-patient-meta">
                <div className="miora-patient-select-row">
                  <label htmlFor="results-session-select" className="sr-only">
                    Select screening session
                  </label>
                  <select
                    id="results-session-select"
                    className="miora-patient-id-select"
                    value={activeScreening.motherId}
                    onChange={(e) => handleSelectSession(e.target.value)}
                  >
                    {screenings.map((s) => (
                      <option key={s.id} value={s.motherId}>
                        {s.motherId}
                      </option>
                    ))}
                  </select>
                </div>
                <span className="miora-patient-sub">
                  {activeScreening.motherInitials || activeMother?.initials || '—'}
                </span>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="calendar" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Postpartum Week</span>
                <strong>Week {activeScreening.postpartumWeek}</strong>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="layers" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Screening Type</span>
                <strong>{activeScreening.modality}</strong>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="clock" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Screening Date</span>
                <strong>{activeScreening.screeningDateTime || activeScreening.completedAgo}</strong>
              </div>
            </div>

            <div className="miora-results-status-wrap">
              <span
                className={`miora-results-status-pill ${
                  isCompleted ? 'is-completed' : 'is-pending'
                }`}
              >
                <DashboardIcon
                  name={isCompleted ? 'checkCircle' : 'clock'}
                  size={15}
                  strokeWidth={1.8}
                />
                <span>
                  {isCompleted ? 'Screening Completed' : `Screening ${activeScreening.status}`}
                </span>
              </span>
            </div>
          </section>
        )}

        {/* Row 1: Overall Risk Assessment | Modality-wise Analysis | Multimodal Summary */}
        {activeScreening && (
          <div className="miora-results-row-3">
            <OverallRiskCard screening={activeScreening} />
            <ModalityAnalysisCard modalities={activeScreening.modalities} />
            <MultimodalSummaryCard screening={activeScreening} />
          </div>
        )}

        {/* Row 2: Risk Trend | Key Contributing Factors | Interpretation */}
        {activeScreening && (
          <div className="miora-results-row-3">
            <RiskTrendCard history={activeScreening.riskHistory} />

            {/* Key Contributing Factors */}
            <section
              className="miora-card miora-results-card"
              aria-labelledby="contributing-factors-title"
            >
              <div className="miora-card-header">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="leaf" size={20} strokeWidth={1.65} />
                  </span>
                  <h2 id="contributing-factors-title" className="miora-card-title">
                    Key Contributing Factors
                  </h2>
                </div>
              </div>

              {activeScreening.contributingFactors?.length > 0 ? (
                <ul className="miora-factors-list">
                  {activeScreening.contributingFactors.map((factor) => (
                    <li key={factor.id} className="miora-factor-row">
                      <span className="miora-factor-icon" aria-hidden="true">
                        <DashboardIcon name={factor.icon || 'alertTriangle'} size={16} />
                      </span>
                      <span className="miora-factor-text">{factor.text}</span>
                      <RiskBadge risk={factor.severity} />
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="miora-trend-empty">
                  <p>No contributing factor outputs were generated for this session.</p>
                </div>
              )}
            </section>

            {/* Interpretation */}
            <section
              className="miora-card miora-results-card"
              aria-labelledby="interpretation-title"
            >
              <div className="miora-card-header">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="fileText" size={19} strokeWidth={1.65} />
                  </span>
                  <h2 id="interpretation-title" className="miora-card-title">
                    Interpretation
                  </h2>
                </div>
              </div>

              <ul className="miora-interpretation-list">
                {(activeScreening.interpretation || [activeScreening.summary]).map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </section>
          </div>
        )}

        {/* Recommended Next Steps */}
        {activeScreening && (
          <section
            className="miora-card miora-next-steps-bar"
            aria-labelledby="recommended-next-steps-title"
          >
            <div className="miora-next-steps-label">
              <span className="miora-card-icon" aria-hidden="true">
                <DashboardIcon name="calendar" size={20} strokeWidth={1.65} />
              </span>
              <h2 id="recommended-next-steps-title" className="miora-quick-title">
                Recommended Next Steps
              </h2>
            </div>

            <div className="miora-next-steps-cards">
              <button
                type="button"
                className="miora-next-step-card"
                onClick={handleScheduleFollowUp}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="calendar" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Schedule follow-up in 7 days</strong>
                  <small>Update mother status &amp; queue check-in</small>
                </span>
              </button>

              <button
                type="button"
                className="miora-next-step-card"
                onClick={() => navigate('/clinical-review')}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="users" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Consider brief clinical review</strong>
                  <small>Inspect discordance &amp; multimodal notes</small>
                </span>
              </button>

              <button
                type="button"
                className="miora-next-step-card"
                onClick={() => setResourcesOpen(true)}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="heart" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Provide support resources</strong>
                  <small>View approved helplines &amp; care guides</small>
                </span>
              </button>
            </div>
          </section>
        )}

        {followUpNotice && (
          <div className="miora-live-feedback-row miora-results-feedback">
            <div className="miora-draft-pill" role="status">
              <DashboardIcon name="check" size={14} />
              <span>{followUpNotice}</span>
            </div>
          </div>
        )}
      </div>

      <ExportReportModal
        isOpen={exportOpen}
        onClose={() => setExportOpen(false)}
        screening={activeScreening}
        mother={activeMother}
      />

      <ShareCaseModal
        isOpen={shareOpen}
        onClose={() => setShareOpen(false)}
        screening={activeScreening}
        onShare={shareCaseHandoff}
      />

      <SupportResourcesModal
        isOpen={resourcesOpen}
        onClose={() => setResourcesOpen(false)}
        motherId={activeScreening?.motherId || 'Mother'}
      />
    </div>
  );
}
