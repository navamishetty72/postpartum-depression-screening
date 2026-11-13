import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge, StatusBadge } from './Badges.jsx';

export function PriorityCasesCard({ cases, onSelectCase, onViewAll }) {
  const visibleCases = cases.slice(0, 3);

  return (
    <section className="miora-card miora-priority-card" aria-labelledby="priority-cases-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="flag" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="priority-cases-title" className="miora-card-title">
            Priority Cases
          </h2>
        </div>

        <button type="button" className="miora-pill-btn" onClick={onViewAll}>
          <span>View All</span>
          <DashboardIcon name="arrowRight" size={14} strokeWidth={1.8} />
        </button>
      </div>

      <div className="miora-table-scroll">
        <table className="miora-priority-table">
          <thead>
            <tr>
              <th scope="col">Mother ID</th>
              <th scope="col">Postpartum Week</th>
              <th scope="col">Status</th>
              <th scope="col">Risk</th>
              <th scope="col">Reason for Review</th>
              <th scope="col" className="miora-col-action">
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visibleCases.map((item) => (
              <tr
                key={item.id}
                className="miora-table-row"
                onClick={() => onSelectCase?.(item.id)}
              >
                <td className="miora-cell-id">{item.id}</td>
                <td className="miora-cell-week">Week {item.postpartumWeek}</td>
                <td>
                  <StatusBadge status={item.status} />
                </td>
                <td>
                  <RiskBadge risk={item.risk} />
                </td>
                <td className="miora-cell-reason">{item.reasonForReview}</td>
                <td className="miora-cell-action">
                  <button
                    type="button"
                    className="miora-row-arrow-btn"
                    aria-label={`Open case profile for ${item.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCase?.(item.id);
                    }}
                  >
                    <DashboardIcon name="arrowRight" size={16} strokeWidth={1.8} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

