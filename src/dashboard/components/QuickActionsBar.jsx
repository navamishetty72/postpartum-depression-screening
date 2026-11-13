import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function QuickActionsBar({
  onAddMother,
  onReviewCases,
  onViewInsights,
  onClinicalReview,
}) {
  const actions = [
    { id: 'add-mother', label: 'Add Mother', icon: 'userPlus', onClick: onAddMother },
    { id: 'review-cases', label: 'Review Cases', icon: 'clipboardList', onClick: onReviewCases },
    { id: 'view-insights', label: 'View Insights', icon: 'barChart', onClick: onViewInsights },
    { id: 'clinical-review', label: 'Clinical Review', icon: 'stethoscope', onClick: onClinicalReview },
  ];

  return (
    <section className="miora-quick-actions" aria-labelledby="quick-actions-title">
      <div className="miora-quick-actions-label">
        <span className="miora-card-icon" aria-hidden="true">
          <DashboardIcon name="bolt" size={20} strokeWidth={1.7} />
        </span>
        <h2 id="quick-actions-title" className="miora-quick-title">
          Quick Actions
        </h2>
      </div>

      <span className="miora-quick-divider" aria-hidden="true" />

      <div className="miora-quick-buttons">
        {actions.map((action) => (
          <button
            key={action.id}
            type="button"
            className="miora-quick-btn"
            onClick={action.onClick}
          >
            <span className="miora-quick-btn-icon" aria-hidden="true">
              <DashboardIcon name={action.icon} size={18} strokeWidth={1.65} />
            </span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

