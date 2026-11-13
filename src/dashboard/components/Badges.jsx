import React from 'react';

export function StatusBadge({ status }) {
  const normalized = (status || '').toLowerCase();
  let variant = 'status-completed';
  if (normalized === 'review') variant = 'status-review';
  else if (normalized === 'follow-up') variant = 'status-followup';
  else if (normalized === 'pending') variant = 'status-pending';

  return (
    <span className={`miora-badge ${variant}`}>
      <span className="miora-badge-dot" aria-hidden="true" />
      <span>{status}</span>
    </span>
  );
}

export function RiskBadge({ risk }) {
  const normalized = (risk || '').toLowerCase();
  let variant = 'risk-low';
  if (normalized === 'high') variant = 'risk-high';
  else if (normalized === 'moderate') variant = 'risk-moderate';
  else if (normalized === 'requires review') variant = 'risk-review';

  return <span className={`miora-badge ${variant}`}>{risk}</span>;
}

export function TrendBadge({ value, tone = 'positive' }) {
  return (
    <span className={`miora-trend miora-trend-${tone}`}>
      <span aria-hidden="true">↑</span> {value}
    </span>
  );
}

