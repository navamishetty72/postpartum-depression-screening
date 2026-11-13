import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge } from './Badges.jsx';

export function AnalysisPreviewCard({
  status, // 'idle' | 'processing' | 'error' | 'ready'
  errorMessage,
  analysisResult,
  selectedModalities,
  availableModalities,
  onRetry,
}) {
  const modalities = [
    { key: 'text', label: 'Text' },
    { key: 'voice', label: 'Voice' },
    { key: 'video', label: 'Video' },
  ];

  const hasResult = status === 'ready' && analysisResult;
  const circumference = 2 * Math.PI * 38;
  const ratio = hasResult ? Math.min(Math.max(analysisResult.combinedScore || 0, 0), 1) : 0;
  const dashOffset = circumference * (1 - ratio);

  return (
    <section className="miora-card miora-analysis-preview" aria-labelledby="analysis-preview-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="clipboardCheck" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="analysis-preview-title" className="miora-card-title">
            Analysis Preview
          </h2>
        </div>
        {status === 'processing' && (
          <span className="miora-signal-pill tone-active">Processing…</span>
        )}
      </div>

      {status === 'idle' && (
        <div className="miora-analysis-empty">
          <div className="miora-analysis-empty-grid">
            <div className="miora-prelim-ring-wrap">
              <svg viewBox="0 0 100 100" className="miora-prelim-ring" aria-hidden="true">
                <circle cx="50" cy="50" r="38" className="miora-ring-bg" />
              </svg>
              <div className="miora-prelim-ring-center">
                <span>Pending</span>
              </div>
            </div>

            <div className="miora-analysis-empty-copy">
              <strong>Your analysis preview will appear here after processing.</strong>
              <p>
                Upload at least one valid file, confirm selection &amp; consent, then click Run Analysis.
              </p>
            </div>
          </div>
        </div>
      )}

      {status === 'processing' && (
        <div className="miora-analysis-loading" role="status" aria-live="polite">
          <div className="miora-spinner" aria-hidden="true" />
          <div>
            <strong>Running multimodal analysis…</strong>
            <p>Validating patient association and submitting selected modalities to backend.</p>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="miora-analysis-error" role="alert">
          <div className="miora-analysis-error-copy">
            <strong>Analysis Could Not Complete</strong>
            <p>{errorMessage}</p>
          </div>
          {onRetry && (
            <button type="button" className="miora-btn-secondary" onClick={onRetry}>
              <DashboardIcon name="refresh" size={14} />
              <span>Retry Analysis</span>
            </button>
          )}
        </div>
      )}

      {hasResult && (
        <div className="miora-analysis-populated">
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
                <span>{analysisResult.riskCategory}</span>
              </div>
            </div>

            <div className="miora-prelim-meta">
              <span className="miora-prelim-caption">Risk Score</span>
              <div className="miora-prelim-value">
                <strong>{Number(analysisResult.combinedScore).toFixed(2)}</strong>
                <span>/ 1.00</span>
              </div>
              <RiskBadge risk={analysisResult.riskCategory} />
            </div>
          </div>

          <div className="miora-contrib-col">
            <div className="miora-contrib-title">Modality Contribution</div>
            <div className="miora-contrib-list">
              {modalities.map((mod) => {
                const value = analysisResult.modalityContributions?.[mod.key];
                const isSelected = selectedModalities.includes(mod.key);
                const isAvailable = availableModalities[mod.key];
                const hasValue = typeof value === 'number' && isSelected && isAvailable;
                return (
                  <div key={mod.key} className="miora-contrib-row">
                    <span className="miora-contrib-label">{mod.label}</span>
                    <div className="miora-contrib-bar-track">
                      <div
                        className="miora-contrib-bar-fill"
                        style={{ width: hasValue ? `${Math.round(value * 100)}%` : '0%' }}
                      />
                    </div>
                    <span className="miora-contrib-val">
                      {hasValue ? value.toFixed(2) : 'N/A'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

