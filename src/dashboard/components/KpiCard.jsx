import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { TrendBadge } from './Badges.jsx';

export function KpiCard({
  icon,
  value,
  trend,
  trendTone = 'positive',
  trendDirection = 'up',
  label,
  onClick,
}) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      className={`miora-kpi-card ${onClick ? 'is-clickable' : ''}`}
      onClick={onClick}
    >
      <div className="miora-kpi-icon-wrap" aria-hidden="true">
        <DashboardIcon name={icon} size={23} strokeWidth={1.65} />
      </div>
      <div className="miora-kpi-content">
        <div className="miora-kpi-top">
          <span className="miora-kpi-value">{value}</span>
          <TrendBadge value={trend} tone={trendTone} direction={trendDirection} />
        </div>
        <div className="miora-kpi-label">{label}</div>
      </div>
    </Tag>
  );
}

