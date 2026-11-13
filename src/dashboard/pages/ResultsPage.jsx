import React, { useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { RiskBadge, StatusBadge } from '../components/Badges.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';

export function ResultsPage() {
  const { screenings } = useClinicalData();
  const { motherId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const riskFilter = searchParams.get('risk') || 'all';

  const filteredScreenings = useMemo(() => {
    if (riskFilter === 'all') return screenings;
    const normalized = riskFilter.replace(' Risk', '').toLowerCase();
    return screenings.filter(
      (s) =>
        s.risk.toLowerCase() === normalized ||
        (normalized === 'requires review' && s.status !== 'Completed')
    );
  }, [screenings, riskFilter]);

  const activeResult = motherId
    ? screenings.find((s) => s.motherId.toLowerCase() === motherId.toLowerCase()) ||
      filteredScreenings[0] ||
      screenings[0]
    : filteredScreenings[0] || screenings[0];

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <div className="miora-subpage-header">
          <div>
            <div className="miora-dash-eyebrow">
              <span>SCREENING RESULTS</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title miora-subpage-title">
              Wellbeing <em>Results</em> Archive
            </h1>
            <p className="miora-dash-subtitle">
              Completed multimodal screening outcomes, EPDS-equivalent scores, and risk stratification.
            </p>
          </div>
          <button
            type="button"
            className="miora-cta-primary"
            onClick={() => navigate('/live-screening')}
          >
            <DashboardIcon name="plus" size={16} />
            <span>Start Screening</span>
          </button>
        </div>

        <div className="miora-filter-bar">
          <div className="miora-filter-pills" role="tablist" aria-label="Risk category filter">
            {['all', 'Low Risk', 'Moderate Risk', 'High Risk'].map((cat) => (
              <button
                key={cat}
                type="button"
                role="tab"
                aria-selected={riskFilter === cat}
                className={`miora-filter-pill ${riskFilter === cat ? 'is-active' : ''}`}
                onClick={() => setSearchParams(cat === 'all' ? {} : { risk: cat })}
              >
                {cat === 'all' ? 'All Results' : cat}
              </button>
            ))}
          </div>
        </div>

        <div className="miora-master-detail">
          <section className="miora-card" aria-label="Screening results list">
            <div className="miora-recent-list">
              {filteredScreenings.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  className={`miora-recent-item ${
                    activeResult?.id === entry.id ? 'is-selected' : ''
                  }`}
                  onClick={() => navigate(`/results/${entry.motherId}`)}
                >
                  <div className="miora-recent-left">
                    <span className="miora-recent-avatar" aria-hidden="true">
                      <DashboardIcon name="user" size={17} />
                    </span>
                    <span className="miora-recent-id">
                      {entry.motherId} · {entry.motherName}
                    </span>
                    <span className="miora-recent-meta">
                      {entry.status} · {entry.completedAgo}
                    </span>
                  </div>
                  <div className="miora-recent-right">
                    <RiskBadge risk={entry.risk} />
                    <DashboardIcon name="chevronRight" size={16} />
                  </div>
                </button>
              ))}
            </div>
          </section>

          {activeResult && (
            <aside className="miora-card miora-case-detail" aria-label="Selected screening details">
              <div className="miora-case-detail-head">
                <div>
                  <span className="miora-case-id-tag">
                    {activeResult.id} · {activeResult.motherId}
                  </span>
                  <h3>{activeResult.motherName}</h3>
                  <p>
                    {activeResult.modality} · Week {activeResult.postpartumWeek} ·{' '}
                    {activeResult.completedAgo}
                  </p>
                </div>
                <RiskBadge risk={activeResult.risk} />
              </div>

              <div className="miora-detail-grid">
                <div className="miora-detail-block">
                  <span>Screening Status</span>
                  <StatusBadge status={activeResult.status} />
                </div>
                <div className="miora-detail-block">
                  <span>EPDS Equivalent</span>
                  <strong>{activeResult.epdsEquivalent} / 30</strong>
                </div>
                <div className="miora-detail-block">
                  <span>Discordance Index</span>
                  <strong>{Math.round(activeResult.discordanceScore * 100)}%</strong>
                </div>
              </div>

              <div className="miora-detail-notes">
                <div>
                  <h4>Clinical Summary</h4>
                  <p>{activeResult.summary}</p>
                </div>
              </div>

              <div className="miora-detail-footer">
                <button
                  type="button"
                  className="miora-btn-secondary"
                  onClick={() => navigate(`/mothers/${activeResult.motherId}`)}
                >
                  Open Mother Profile
                </button>
                <button
                  type="button"
                  className="miora-cta-primary"
                  onClick={() => navigate(`/live-screening?mother=${activeResult.motherId}`)}
                >
                  Re-screen Mother
                </button>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

