import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { RiskBadge, StatusBadge } from '../components/Badges.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';

export function DiscordancePage() {
  const { mothers, updateMotherStatus } = useClinicalData();
  const navigate = useNavigate();

  const discordanceCases = mothers.filter((m) => m.discordanceFlag);

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <div className="miora-subpage-header">
          <div>
            <div className="miora-dash-eyebrow">
              <span>MULTIMODAL DISCORDANCE</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title miora-subpage-title">
              Voice–Text <em>Discordance</em> Review
            </h1>
            <p className="miora-dash-subtitle">
              Cases where acoustic vocal markers diverge from written self-reports and benefit from gentle clinician review.
            </p>
          </div>
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => navigate('/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>

        <div className="miora-discordance-grid">
          {discordanceCases.map((item) => (
            <article key={item.id} className="miora-card miora-discordance-card">
              <div className="miora-case-detail-head">
                <div>
                  <span className="miora-case-id-tag">{item.id}</span>
                  <h3>
                    {item.name} · Week {item.postpartumWeek}
                  </h3>
                  <p>{item.discordanceType || item.reasonForReview}</p>
                </div>
                <div className="miora-badge-pair">
                  <StatusBadge status={item.status} />
                  <RiskBadge risk={item.risk} />
                </div>
              </div>

              <div className="miora-cue-compare">
                <div className="miora-cue-box">
                  <div className="miora-cue-label">
                    <DashboardIcon name="mic" size={15} />
                    <span>Voice Prosody Cue</span>
                  </div>
                  <p>{item.voiceCueSummary}</p>
                </div>
                <div className="miora-cue-box">
                  <div className="miora-cue-label">
                    <DashboardIcon name="clipboardList" size={15} />
                    <span>Written Self-Report</span>
                  </div>
                  <p>{item.textCueSummary}</p>
                </div>
              </div>

              <div className="miora-detail-footer">
                <button
                  type="button"
                  className="miora-btn-secondary"
                  onClick={() => updateMotherStatus(item.id, 'Follow-up')}
                >
                  Mark Follow-up Scheduled
                </button>
                <button
                  type="button"
                  className="miora-cta-primary"
                  onClick={() => navigate(`/mothers/${item.id}`)}
                >
                  Open Clinical Profile
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

