import React from 'react';

export function StatusBadge({ status, showDot = true }) {
  const normalized = (status || '').toLowerCase();
  let variant = 'status-completed';
  if (normalized === 'review') variant = 'status-review';
  else if (normalized === 'follow-up') variant = 'status-followup';
  else if (normalized === 'pending') variant = 'status-pending';
  else if (normalized === 'active') variant = 'status-active';

  return (
    <span className={`miora-badge ${variant}`}>
      {showDot && <span className="miora-badge-dot" aria-hidden="true" />}
      <span>{status}</span>
    </span>
  );
}

export function RiskBadge({ risk, showDot = false }) {
  const normalized = (risk || '').toLowerCase();
  let variant = 'risk-low';
  if (normalized.startsWith('high')) variant = 'risk-high';
  else if (normalized.startsWith('moderate')) variant = 'risk-moderate';
  else if (normalized.startsWith('requires review')) variant = 'risk-review';

  return (
    <span className={`miora-badge ${variant}`}>
      {showDot && <span className="miora-badge-dot" aria-hidden="true" />}
      <span>{risk}</span>
    </span>
  );
}

export function TrendBadge({ value, tone = 'positive', direction = 'up' }) {
  const arrow = direction === 'down' ? '↓' : '↑';
  return (
    <span className={`miora-trend miora-trend-${tone}`}>
      <span aria-hidden="true">{arrow}</span> {value}
    </span>
  );
}
