import React, { useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { RiskBadge, StatusBadge } from '../components/Badges.jsx';

export function MothersCasesPage() {
  const { mothers, setIsAddMotherOpen, updateMotherStatus } = useClinicalData();
  const { motherId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialFilter = searchParams.get('filter') || 'all';
  const [query, setQuery] = useState('');

  const filteredMothers = useMemo(() => {
    return mothers.filter((m) => {
      if (initialFilter === 'priority' && !m.priority && m.status === 'Completed') return false;
      if (initialFilter === 'review' && m.status !== 'Review' && m.status !== 'Follow-up') {
        return false;
      }
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        return (
          m.id.toLowerCase().includes(q) ||
          m.name.toLowerCase().includes(q) ||
          m.reasonForReview.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [mothers, initialFilter, query]);

  const activeCase = motherId
    ? mothers.find((m) => m.id.toLowerCase() === motherId.toLowerCase()) || mothers[0]
    : filteredMothers[0] || mothers[0];

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <div className="miora-subpage-header">
          <div>
            <div className="miora-dash-eyebrow">
              <span>MOTHERS &amp; CASES</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title miora-subpage-title">
              Maternal Care <em>Registry</em>
            </h1>
            <p className="miora-dash-subtitle">
              Active postpartum cohort, priority triage statuses, and longitudinal care plans.
            </p>
          </div>

          <div className="miora-subpage-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setIsAddMotherOpen(true)}
            >
              <DashboardIcon name="userPlus" size={16} />
              <span>Add Mother</span>
            </button>
            <button
              type="button"
              className="miora-cta-primary"
              onClick={() => navigate('/live-screening')}
            >
              <DashboardIcon name="plus" size={16} />
              <span>Start Screening</span>
            </button>
          </div>
        </div>

        <div className="miora-filter-bar">
          <div className="miora-filter-pills" role="tablist" aria-label="Case filters">
            {[
              { id: 'all', label: 'All Mothers' },
              { id: 'priority', label: 'Priority Cases' },
              { id: 'review', label: 'Review & Follow-up' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={initialFilter === tab.id}
                className={`miora-filter-pill ${initialFilter === tab.id ? 'is-active' : ''}`}
                onClick={() =>
                  setSearchParams(tab.id === 'all' ? {} : { filter: tab.id })
                }
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="miora-inline-search">
            <DashboardIcon name="search" size={16} />
            <input
              type="search"
              placeholder="Filter by Mother ID, name, or cue..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter mothers"
            />
          </div>
        </div>

        <div className="miora-master-detail">
          <section className="miora-card" aria-label="Mothers case list">
            <div className="miora-table-scroll">
              <table className="miora-priority-table">
                <thead>
                  <tr>
                    <th scope="col">Mother ID</th>
                    <th scope="col">Name</th>
                    <th scope="col">Postpartum Week</th>
                    <th scope="col">Status</th>
                    <th scope="col">Risk</th>
                    <th scope="col">Reason for Review</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMothers.map((item) => (
                    <tr
                      key={item.id}
                      className={`miora-table-row ${activeCase?.id === item.id ? 'is-selected' : ''}`}
                      onClick={() => navigate(`/mothers/${item.id}`)}
                    >
                      <td className="miora-cell-id">{item.id}</td>
                      <td>{item.name}</td>
                      <td className="miora-cell-week">Week {item.postpartumWeek}</td>
                      <td>
                        <StatusBadge status={item.status} />
                      </td>
                      <td>
                        <RiskBadge risk={item.risk} />
                      </td>
                      <td className="miora-cell-reason">{item.reasonForReview}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {activeCase && (
            <aside className="miora-card miora-case-detail" aria-label="Selected mother case profile">
              <div className="miora-case-detail-head">
                <div>
                  <span className="miora-case-id-tag">{activeCase.id}</span>
                  <h3>{activeCase.name}</h3>
                  <p>
                    Week {activeCase.postpartumWeek} Postpartum · Last check-in {activeCase.lastScreeningTime}
                  </p>
                </div>
                <RiskBadge risk={activeCase.risk} />
              </div>

              <div className="miora-detail-grid">
                <div className="miora-detail-block">
                  <span>Current Status</span>
                  <div className="miora-status-select-row">
                    <StatusBadge status={activeCase.status} />
                    <select
                      aria-label={`Update status for ${activeCase.id}`}
                      value={activeCase.status}
                      onChange={(e) => updateMotherStatus(activeCase.id, e.target.value)}
                    >
                      <option value="Review">Review</option>
                      <option value="Follow-up">Follow-up</option>
                      <option value="Pending">Pending</option>
                      <option value="Completed">Completed</option>
                    </select>
                  </div>
                </div>
                <div className="miora-detail-block">
                  <span>EPDS Equivalent</span>
                  <strong>{activeCase.epdsScore} / 30</strong>
                </div>
              </div>

              <div className="miora-detail-notes">
                <div>
                  <h4>Voice &amp; Prosody Cues</h4>
                  <p>{activeCase.voiceCueSummary}</p>
                </div>
                <div>
                  <h4>Text Reflection</h4>
                  <p>{activeCase.textCueSummary}</p>
                </div>
                <div>
                  <h4>Recommended Care Pathway</h4>
                  <p>{activeCase.carePlan}</p>
                </div>
              </div>

              <div className="miora-detail-footer">
                <button
                  type="button"
                  className="miora-btn-secondary"
                  onClick={() => navigate(`/results/${activeCase.id}`)}
                >
                  View Screening Results
                </button>
                <button
                  type="button"
                  className="miora-cta-primary"
                  onClick={() => navigate(`/live-screening?mother=${activeCase.id}`)}
                >
                  Run New Screening
                </button>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

