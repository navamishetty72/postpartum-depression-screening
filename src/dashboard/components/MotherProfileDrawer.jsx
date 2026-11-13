import React, { useEffect } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge, StatusBadge } from './Badges.jsx';

export function MotherProfileDrawer({
  mother,
  relatedScreenings,
  onClose,
  onUpdateStatus,
  onOpenResults,
  onStartScreening,
}) {
  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [onClose]);

  if (!mother) return null;

  return (
    <div className="miora-profile-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="miora-profile-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Mother profile ${mother.id}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-profile-drawer-head">
          <div className="miora-profile-identity">
            <span className="miora-initials-avatar miora-initials-avatar-lg" aria-hidden="true">
              {mother.avatarInitials}
            </span>
            <div>
              <span className="miora-case-id-tag">
                {mother.id} · {mother.initials}
              </span>
              <h3>{mother.name}</h3>
              <p>
                Week {mother.postpartumWeek} Postpartum · Last screening {mother.lastScreeningDate}
              </p>
            </div>
          </div>

          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close mother profile"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <div className="miora-detail-grid">
          <div className="miora-detail-block">
            <span>Case Status</span>
            <div className="miora-status-select-row">
              <StatusBadge status={mother.status} showDot={false} />
              <select
                aria-label={`Update status for ${mother.id}`}
                value={mother.status}
                onChange={(e) => onUpdateStatus(mother.id, e.target.value)}
              >
                <option value="Active">Active</option>
                <option value="Review">Review</option>
                <option value="Follow-up">Follow-up</option>
                <option value="Pending">Pending</option>
                <option value="Completed">Completed</option>
              </select>
            </div>
          </div>

          <div className="miora-detail-block">
            <span>Risk Level</span>
            <RiskBadge risk={mother.risk} showDot />
          </div>

          <div className="miora-detail-block">
            <span>EPDS Equivalent</span>
            <strong>{mother.epdsScore} / 30</strong>
          </div>
        </div>

        <div className="miora-detail-notes">
          <div>
            <h4>Reason for Monitoring</h4>
            <p>{mother.reasonForReview}</p>
          </div>
          <div>
            <h4>Voice &amp; Prosody Cues</h4>
            <p>{mother.voiceCueSummary}</p>
          </div>
          <div>
            <h4>Text Reflection</h4>
            <p>{mother.textCueSummary}</p>
          </div>
          <div>
            <h4>Recommended Care Pathway</h4>
            <p>{mother.carePlan}</p>
          </div>
        </div>

        {relatedScreenings.length > 0 && (
          <div className="miora-related-cases">
            <h4>Related Screening Cases</h4>
            <div className="miora-recent-list">
              {relatedScreenings.map((scr) => (
                <button
                  key={scr.id}
                  type="button"
                  className="miora-recent-item"
                  onClick={() => onOpenResults(mother.id)}
                >
                  <div className="miora-recent-left">
                    <span className="miora-recent-id">{scr.id}</span>
                    <span className="miora-recent-meta">
                      {scr.modality} · {scr.completedAgo}
                    </span>
                  </div>
                  <div className="miora-recent-right">
                    <RiskBadge risk={scr.risk} />
                    <DashboardIcon name="chevronRight" size={16} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="miora-detail-footer">
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => onOpenResults(mother.id)}
          >
            View Screening Results
          </button>
          <button
            type="button"
            className="miora-cta-primary"
            onClick={() => onStartScreening(mother.id)}
          >
            Run New Screening
          </button>
        </div>
      </aside>
    </div>
  );
}

