import React, { useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

const RISK_OPTIONS = [
  { value: 'Low', pillClass: 'filter-pill-low' },
  { value: 'Moderate', pillClass: 'filter-pill-moderate' },
  { value: 'High', pillClass: 'filter-pill-high' },
  { value: 'Requires Review', pillClass: 'filter-pill-review' },
];

const STATUS_OPTIONS = ['Active', 'Follow-up', 'Pending', 'Completed'];

export function FiltersSidebar({
  selectedRisks,
  onToggleRisk,
  weekRange,
  onWeekRangeChange,
  selectedStatuses,
  onToggleStatus,
  onClearFilters,
  activeFilterCount,
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [minWeek, maxWeek] = weekRange;

  const minPercent = (minWeek / 24) * 100;
  const maxPercent = (maxWeek / 24) * 100;

  const handleMinChange = (e) => {
    const nextMin = Math.min(Number(e.target.value), maxWeek);
    onWeekRangeChange([nextMin, maxWeek]);
  };

  const handleMaxChange = (e) => {
    const nextMax = Math.max(Number(e.target.value), minWeek);
    onWeekRangeChange([minWeek, nextMax]);
  };

  const panelContent = (
    <div className="miora-filters-inner">
      <div className="miora-filters-header">
        <span className="miora-card-icon" aria-hidden="true">
          <DashboardIcon name="filter" size={18} strokeWidth={1.7} />
        </span>
        <h2 className="miora-filters-title">Filters</h2>
        <button
          type="button"
          className="miora-filters-mobile-close"
          aria-label="Close filters"
          onClick={() => setMobileOpen(false)}
        >
          <DashboardIcon name="close" size={18} />
        </button>
      </div>

      {/* Risk Level */}
      <fieldset className="miora-filter-group">
        <legend className="miora-filter-legend">Risk Level</legend>
        <div className="miora-filter-checks">
          {RISK_OPTIONS.map((opt) => {
            const checked = selectedRisks.includes(opt.value);
            return (
              <label key={opt.value} className="miora-filter-check-row">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggleRisk(opt.value)}
                />
                <span className={`miora-filter-risk-chip ${opt.pillClass}`}>
                  {opt.value}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="miora-filter-divider" aria-hidden="true" />

      {/* Postpartum Week Range */}
      <fieldset className="miora-filter-group">
        <legend className="miora-filter-legend">Postpartum Week</legend>
        <div className="miora-range-slider">
          <div className="miora-range-track" aria-hidden="true">
            <div
              className="miora-range-fill"
              style={{
                left: `${minPercent}%`,
                width: `${Math.max(maxPercent - minPercent, 0)}%`,
              }}
            />
          </div>
          <input
            type="range"
            min={0}
            max={24}
            value={minWeek}
            onChange={handleMinChange}
            aria-label="Minimum postpartum week"
            className="miora-range-input miora-range-input-min"
          />
          <input
            type="range"
            min={0}
            max={24}
            value={maxWeek}
            onChange={handleMaxChange}
            aria-label="Maximum postpartum week"
            className="miora-range-input miora-range-input-max"
          />
        </div>
        <div className="miora-range-labels">
          <span>Week {minWeek}</span>
          <span className="miora-range-dash" aria-hidden="true">
            –
          </span>
          <span>Week {maxWeek}</span>
        </div>
      </fieldset>

      <div className="miora-filter-divider" aria-hidden="true" />

      {/* Case Status */}
      <fieldset className="miora-filter-group">
        <legend className="miora-filter-legend">Case Status</legend>
        <div className="miora-filter-checks">
          {STATUS_OPTIONS.map((status) => {
            const checked = selectedStatuses.includes(status);
            return (
              <label key={status} className="miora-filter-check-row">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggleStatus(status)}
                />
                <span className="miora-filter-status-text">{status}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="miora-filter-divider" aria-hidden="true" />

      <button
        type="button"
        className="miora-clear-filters-btn"
        onClick={onClearFilters}
      >
        <DashboardIcon name="refresh" size={14} strokeWidth={1.9} />
        <span>Clear Filters</span>
      </button>
    </div>
  );

  return (
    <>
      <div className="miora-mobile-filter-bar">
        <button
          type="button"
          className="miora-btn-secondary miora-mobile-filter-trigger"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
        >
          <DashboardIcon name="filter" size={16} />
          <span>
            Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
          </span>
        </button>
      </div>

      <aside className="miora-card miora-filters-sidebar" aria-label="Registry filters">
        {panelContent}
      </aside>

      {mobileOpen && (
        <div
          className="miora-filters-drawer-backdrop"
          role="presentation"
          onClick={() => setMobileOpen(false)}
        >
          <div
            className="miora-filters-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Filter mother registry"
            onClick={(e) => e.stopPropagation()}
          >
            {panelContent}
          </div>
        </div>
      )}
    </>
  );
}

