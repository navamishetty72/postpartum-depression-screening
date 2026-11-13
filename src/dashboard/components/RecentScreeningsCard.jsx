import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge } from './Badges.jsx';

export function RecentScreeningsCard({ screenings, onSelectScreening, onViewAll }) {
  const visibleScreenings = screenings.slice(0, 3);

  return (
    <section className="miora-card miora-recent-card" aria-labelledby="recent-screenings-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="waveform" size={21} strokeWidth={1.7} />
          </span>
          <h2 id="recent-screenings-title" className="miora-card-title">
            Recent Screenings
          </h2>
        </div>

        <button type="button" className="miora-pill-btn" onClick={onViewAll}>
          <span>View All</span>
          <DashboardIcon name="arrowRight" size={14} strokeWidth={1.8} />
        </button>
      </div>

      <div className="miora-recent-list">
        {visibleScreenings.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className="miora-recent-item"
            onClick={() => onSelectScreening?.(entry)}
          >
            <div className="miora-recent-left">
              <span className="miora-recent-avatar" aria-hidden="true">
                <DashboardIcon name="user" size={17} strokeWidth={1.7} />
              </span>
              <span className="miora-recent-id">{entry.motherId}</span>
              <span className="miora-recent-meta">
                {entry.status} · {entry.completedAgo}
              </span>
            </div>

            <div className="miora-recent-right">
              <RiskBadge risk={entry.risk} />
              <span className="miora-recent-chevron" aria-hidden="true">
                <DashboardIcon name="chevronRight" size={16} strokeWidth={1.7} />
              </span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

