import React, { useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

function riskLevelPillClass(level) {
  if (level === 'High') return 'miora-disc-level-pill is-high';
  if (level === 'Moderate') return 'miora-disc-level-pill is-moderate';
  if (level === 'Low') return 'miora-disc-level-pill is-low';
  return 'miora-disc-level-pill is-muted';
}

function severityPillClass(tone) {
  if (tone === 'peach') return 'miora-disc-severity-pill is-peach';
  if (tone === 'green') return 'miora-disc-severity-pill is-green';
  return 'miora-disc-severity-pill is-muted';
}

export function ModalityComparisonCard({ modalityRows }) {
  return (
    <section
      className="miora-card miora-disc-card"
      aria-labelledby="modality-comparison-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="scale" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="modality-comparison-title" className="miora-card-title">
            Modality Comparison
          </h2>
        </div>
      </div>

      {/* Desktop / Tablet Structured Table */}
      <div className="miora-disc-table-wrap">
        <table className="miora-disc-table">
          <thead>
            <tr>
              <th scope="col">Modality</th>
              <th scope="col">Risk Score</th>
              <th scope="col">Risk Level</th>
            </tr>
          </thead>
          <tbody>
            {modalityRows.map((row) => (
              <tr key={row.key}>
                <td>
                  <div className="miora-disc-mod-cell">
                    <span className="miora-modality-mini-badge" aria-hidden="true">
                      <DashboardIcon name={row.icon} size={15} strokeWidth={1.7} />
                    </span>
                    <div className="miora-disc-mod-name">
                      <strong>{row.name}</strong>
                      <span>({row.subLabel})</span>
                    </div>
                  </div>
                </td>
                <td className="miora-disc-score-cell">
                  {row.isCompleted ? row.score.toFixed(2) : '—'}
                </td>
                <td>
                  <span className={riskLevelPillClass(row.riskLevel)}>{row.riskLevel}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Stacked Card Rows (shown below 560px via CSS) */}
      <div className="miora-disc-mobile-rows" aria-label="Modality comparison summary">
        {modalityRows.map((row) => (
          <div key={`${row.key}-mobile`} className="miora-disc-mobile-row">
            <div className="miora-disc-mod-cell">
              <span className="miora-modality-mini-badge" aria-hidden="true">
                <DashboardIcon name={row.icon} size={15} strokeWidth={1.7} />
              </span>
              <div className="miora-disc-mod-name">
                <strong>{row.name}</strong>
                <span>({row.subLabel})</span>
              </div>
            </div>
            <div className="miora-disc-mobile-row-right">
              <span className="miora-disc-score-cell">
                {row.isCompleted ? row.score.toFixed(2) : '—'}
              </span>
              <span className={riskLevelPillClass(row.riskLevel)}>{row.riskLevel}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

const Y_TICKS = [1, 0.75, 0.5, 0.25, 0];

export function RiskByModalityCard({ modalityRows, highestModalityKey }) {
  const [hoveredKey, setHoveredKey] = useState(null);
  const activeHover = modalityRows.find((r) => r.key === hoveredKey) || null;

  return (
    <section className="miora-card miora-disc-card" aria-labelledby="risk-by-modality-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="barChart" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="risk-by-modality-title" className="miora-card-title">
            Risk by Modality
          </h2>
        </div>

        {activeHover && (
          <div className="miora-disc-bar-tooltip" role="status">
            <strong>{activeHover.name}:</strong>{' '}
            {activeHover.isCompleted
              ? `${activeHover.score.toFixed(2)} (${activeHover.riskLevel})`
              : `${activeHover.riskLevel} (excluded)`}
          </div>
        )}
      </div>

      <div
        className="miora-disc-barchart"
        role="img"
        aria-label={`Risk score by modality bar chart: ${modalityRows
          .map((r) => `${r.name} ${r.isCompleted ? r.score.toFixed(2) : 'Unavailable'}`)
          .join(', ')}`}
      >
        <div className="miora-disc-yaxis" aria-hidden="true">
          {Y_TICKS.map((tick) => (
            <span key={tick}>{tick.toFixed(2)}</span>
          ))}
        </div>

        <div className="miora-disc-plot-area">
          <div className="miora-disc-gridlines" aria-hidden="true">
            {Y_TICKS.map((tick) => (
              <span key={tick} className="miora-disc-gridline" />
            ))}
          </div>

          <div className="miora-disc-bars-row">
            {modalityRows.map((row) => {
              const isHighlighted = row.isCompleted && row.key === highestModalityKey;
              const heightPct = row.isCompleted ? Math.max(8, Math.round(row.score * 100)) : 0;

              return (
                <div
                  key={row.key}
                  className="miora-disc-bar-col"
                  tabIndex={0}
                  onMouseEnter={() => setHoveredKey(row.key)}
                  onMouseLeave={() => setHoveredKey(null)}
                  onFocus={() => setHoveredKey(row.key)}
                  onBlur={() => setHoveredKey(null)}
                  aria-label={`${row.name} (${row.subLabel}): ${
                    row.isCompleted ? `${row.score.toFixed(2)}, ${row.riskLevel}` : row.riskLevel
                  }`}
                >
                  <div className="miora-disc-bar-stage">
                    {row.isCompleted ? (
                      <>
                        <span className="miora-disc-bar-val">{row.score.toFixed(2)}</span>
                        <div
                          className={`miora-disc-bar-fill ${isHighlighted ? 'is-highlighted' : ''}`}
                          style={{ height: `${heightPct}%` }}
                          title={`${row.name}: ${row.score.toFixed(2)} (${row.riskLevel})`}
                        />
                      </>
                    ) : (
                      <div
                        className="miora-disc-bar-missing"
                        title={`${row.name}: ${row.riskLevel} — excluded from comparison`}
                      >
                        <span>N/A</span>
                      </div>
                    )}
                  </div>
                  <span className="miora-disc-bar-label">{row.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

export function DiscordanceResultCard({ discordance, overallRisk }) {
  const radius = 58;
  const arcLength = Math.PI * radius;
  const clampedScore = discordance.available ? Math.min(Math.max(discordance.score, 0), 1) : 0;
  const dashOffset = arcLength * (1 - clampedScore);

  const categoryLines = discordance.category.split(' ');
  const firstWord = categoryLines[0] || discordance.category;
  const restWords = categoryLines.slice(1).join(' ');

  return (
    <section
      className="miora-card miora-disc-card miora-disc-result-card"
      aria-labelledby="discordance-result-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="bolt" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="discordance-result-title" className="miora-card-title">
            Discordance Result
          </h2>
        </div>
      </div>

      <div className="miora-disc-result-body">
        <div className="miora-disc-gauge-wrap">
          <svg
            viewBox="0 0 156 96"
            className="miora-disc-gauge-svg"
            role="img"
            aria-label={
              discordance.available
                ? `Discordance gauge: ${discordance.score.toFixed(2)}, ${discordance.category}`
                : 'Discordance gauge unavailable due to missing modalities'
            }
          >
            <defs>
              <linearGradient id="mioraDiscordanceGaugeGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#f5c6d4" />
                <stop offset="55%" stopColor="#ec6f9d" />
                <stop offset="100%" stopColor="#df3b74" />
              </linearGradient>
            </defs>
            <path
              d={`M ${78 - radius} 82 A ${radius} ${radius} 0 0 1 ${78 + radius} 82`}
              className="miora-disc-gauge-track"
            />
            {discordance.available && (
              <path
                d={`M ${78 - radius} 82 A ${radius} ${radius} 0 0 1 ${78 + radius} 82`}
                className="miora-disc-gauge-fill"
                stroke="url(#mioraDiscordanceGaugeGrad)"
                strokeDasharray={arcLength}
                strokeDashoffset={dashOffset}
              />
            )}
          </svg>
          <div className="miora-disc-gauge-center">
            <strong>{firstWord}</strong>
            {restWords && <span>{restWords}</span>}
          </div>
        </div>

        <div className="miora-disc-result-meta">
          <span className="miora-disc-meta-caption">Discordance Score</span>
          <div className="miora-disc-score-numeral">
            {discordance.available ? discordance.score.toFixed(2) : 'Unavailable'}
          </div>
          <span className={severityPillClass(discordance.badgeTone)}>
            {discordance.severityBadge}
          </span>
        </div>
      </div>

      <p className="miora-disc-result-desc">{discordance.explanation}</p>

      <div className="miora-disc-separate-metric">
        <span>Overall Postpartum Risk (Separate):</span>
        <strong>
          {overallRisk.available
            ? `${overallRisk.category} (${overallRisk.score.toFixed(2)})`
            : 'Pending'}
        </strong>
      </div>
    </section>
  );
}

export function SignalAlignmentCard({ pairwiseAlignment }) {
  return (
    <section className="miora-card miora-disc-card" aria-labelledby="signal-alignment-title">
      <div className="miora-card-header miora-disc-align-head">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="target" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="signal-alignment-title" className="miora-card-title">
            Signal Alignment
          </h2>
        </div>
      </div>

      <p className="miora-disc-metric-legend">
        Pairwise alignment score (1.00 = closely aligned · 0.00 = high divergence)
      </p>

      <div className="miora-disc-align-rows">
        {pairwiseAlignment.map((pair) => (
          <div key={pair.key} className="miora-disc-align-row">
            <span className="miora-disc-pair-label">{pair.label}</span>
            {pair.available ? (
              <>
                <div
                  className="miora-contrib-bar-track"
                  title={`${pair.label}: alignment ${pair.score.toFixed(2)}${
                    pair.delta !== null ? ` (score difference Δ ${pair.delta.toFixed(2)})` : ''
                  }`}
                >
                  <div
                    className="miora-disc-align-fill"
                    style={{ width: `${pair.barPercent}%` }}
                  />
                </div>
                <span className="miora-disc-align-val" title={`Δ ${pair.delta?.toFixed(2) ?? '—'}`}>
                  {pair.score.toFixed(2)}
                </span>
              </>
            ) : (
              <div className="miora-modality-unavail-row">
                <span className="miora-signal-pill tone-muted">{pair.unavailableReason}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export function KeyObservationsCard({ observations }) {
  return (
    <section className="miora-card miora-disc-card" aria-labelledby="key-observations-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="leaf" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="key-observations-title" className="miora-card-title">
            Key Observations
          </h2>
        </div>
      </div>

      {observations.length > 0 ? (
        <ul className="miora-factors-list">
          {observations.map((obs) => (
            <li key={obs.id} className="miora-disc-observation-row">
              <span className="miora-factor-icon" aria-hidden="true">
                <DashboardIcon name={obs.icon || 'info'} size={16} />
              </span>
              <span className="miora-factor-text">{obs.text}</span>
              {obs.indicator && (
                <span className={riskLevelPillClass(obs.indicator)}>{obs.indicator}</span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="miora-trend-empty">
          <p>
            No cross-modal observations generated for this session. Complete at least two modalities
            to review modality divergence cues.
          </p>
        </div>
      )}
    </section>
  );
}

export function ClinicalInterpretationCard({
  interpretation,
  limitations,
  sessionNotes,
  onOpenAddNote,
}) {
  return (
    <section
      className="miora-card miora-disc-card"
      aria-labelledby="clinical-interpretation-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="fileText" size={19} strokeWidth={1.65} />
          </span>
          <h2 id="clinical-interpretation-title" className="miora-card-title">
            Clinical Interpretation
          </h2>
        </div>
      </div>

      <ul className="miora-interpretation-list">
        {interpretation.map((bullet) => (
          <li key={bullet}>{bullet}</li>
        ))}
      </ul>

      <p className="miora-disc-limitation-note">
        <strong>Limitations:</strong> {limitations}
      </p>

      {sessionNotes.length > 0 && (
        <div className="miora-disc-saved-notes" aria-label="Saved clinician notes for this session">
          <div className="miora-disc-saved-notes-head">
            <span>Clinician Notes ({sessionNotes.length})</span>
            <button type="button" className="miora-disc-inline-link" onClick={onOpenAddNote}>
              + Add Note
            </button>
          </div>
          <ul>
            {sessionNotes.map((entry) => (
              <li key={entry.id}>
                <span className="miora-disc-note-meta">
                  {entry.category} · {entry.createdAt}
                </span>
                <p>{entry.note}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

