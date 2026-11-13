import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge } from './Badges.jsx';

export function PreliminaryResultPanel({
  analysisState, // 'idle' | 'processing' | 'ready'
  preliminaryResult,
  indicators,
  nextSteps,
}) {
  const hasOutput = analysisState === 'ready' && preliminaryResult;
  const ringRatio = hasOutput ? Math.min(Math.max(preliminaryResult.score, 0), 1) : 0;
  const circumference = 2 * Math.PI * 38;
  const dashOffset = circumference * (1 - ringRatio);

  return (
    <section
      className="miora-card miora-prelim-panel"
      aria-labelledby="preliminary-result-title"
    >
      {/* Column A: Preliminary Result */}
      <div className="miora-prelim-col">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="pieChart" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="preliminary-result-title" className="miora-card-title">
            Preliminary Result
          </h2>
        </div>

        {hasOutput ? (
          <div className="miora-prelim-score-row">
            <div className="miora-prelim-ring-wrap">
              <svg viewBox="0 0 100 100" className="miora-prelim-ring" aria-hidden="true">
                <circle cx="50" cy="50" r="38" className="miora-ring-bg" />
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  className="miora-ring-fill"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashOffset}
                />
              </svg>
              <div className="miora-prelim-ring-center">
                <span>{preliminaryResult.risk}</span>
                <small>Estimate</small>
              </div>
            </div>

            <div className="miora-prelim-meta">
              <span className="miora-prelim-caption">Assistive Signal Index</span>
              <div className="miora-prelim-value">
                <strong>{preliminaryResult.score.toFixed(2)}</strong>
                <span>/ 1.00</span>
              </div>
              <RiskBadge risk={preliminaryResult.risk} />
              <p className="miora-prelim-disclaimer">
                Assistive signal summary only — not a clinical diagnosis.
              </p>
            </div>
          </div>
        ) : (
          <div className="miora-prelim-empty">
            <div className="miora-prelim-ring-wrap">
              <svg viewBox="0 0 100 100" className="miora-prelim-ring" aria-hidden="true">
                <circle cx="50" cy="50" r="38" className="miora-ring-bg" />
              </svg>
              <div className="miora-prelim-ring-center">
                <span>{analysisState === 'processing' ? 'Analyzing' : 'Pending'}</span>
              </div>
            </div>
            <div className="miora-prelim-meta">
              <span className="miora-prelim-caption">
                {analysisState === 'processing'
                  ? 'Processing captured modalities...'
                  : 'Awaiting session completion'}
              </span>
              <p className="miora-prelim-disclaimer">
                Capture conversation or media signals, then click Complete Screening to run analysis. Outputs are assistive only and not diagnoses.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Column B: Key Indicators */}
      <div className="miora-prelim-col miora-prelim-col-bordered">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="barChart" size={20} strokeWidth={1.65} />
          </span>
          <h3 className="miora-card-title">Key Indicators</h3>
        </div>
        <ul className="miora-prelim-list">
          {indicators.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      {/* Column C: Next Steps */}
      <div className="miora-prelim-col miora-prelim-col-bordered">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="calendar" size={19} strokeWidth={1.65} />
          </span>
          <h3 className="miora-card-title">Next Steps</h3>
        </div>
        <ul className="miora-prelim-list">
          {nextSteps.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

