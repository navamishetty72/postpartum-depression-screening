import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge } from './Badges.jsx';

export function OverallRiskCard({ screening }) {
  const hasScore = typeof screening?.combinedScore === 'number';
  const riskLabel = `${screening?.risk || 'Moderate'} Risk`;
  const circumference = 2 * Math.PI * 38;
  const ratio = hasScore ? Math.min(Math.max(screening.combinedScore, 0), 1) : 0;
  const dashOffset = circumference * (1 - ratio);

  const explanation = !hasScore
    ? 'Combined risk score is pending completion of required screening modalities.'
    : screening.risk === 'High'
      ? 'Indicates elevated postpartum distress signals. Prompt clinical review is recommended.'
      : screening.risk === 'Moderate'
        ? 'Indicates a noticeable risk of postpartum distress. A follow-up is recommended.'
        : 'Indicates low observed postpartum distress cues. Routine check-in cadence recommended.';

  return (
    <section className="miora-card miora-results-card" aria-labelledby="overall-risk-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="target" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="overall-risk-title" className="miora-card-title">
            Overall Risk Assessment
          </h2>
        </div>
      </div>

      <div className="miora-overall-risk-body">
        <div className="miora-overall-ring-wrap">
          <svg viewBox="0 0 100 100" className="miora-prelim-ring" aria-hidden="true">
            <defs>
              <linearGradient id="mioraOverallRingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#f5c6a8" />
                <stop offset="50%" stopColor="#ea7ca3" />
                <stop offset="100%" stopColor="#d94678" />
              </linearGradient>
            </defs>
            <circle cx="50" cy="50" r="38" className="miora-ring-bg" />
            {hasScore && (
              <circle
                cx="50"
                cy="50"
                r="38"
                className="miora-ring-fill"
                stroke="url(#mioraOverallRingGrad)"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
              />
            )}
          </svg>
          <div className="miora-prelim-ring-center">
            <span>{hasScore ? screening.risk : 'Pending'}</span>
            {hasScore && <small>Risk</small>}
          </div>
        </div>

        <div className="miora-overall-meta">
          <span className="miora-prelim-caption">Risk Score</span>
          {hasScore ? (
            <div className="miora-prelim-value">
              <strong>{screening.combinedScore.toFixed(2)}</strong>
              <span>/ 1.00</span>
            </div>
          ) : (
            <div className="miora-prelim-value">
              <strong>Pending</strong>
            </div>
          )}
          <RiskBadge risk={riskLabel} />
          <p className="miora-overall-desc">{explanation}</p>
        </div>
      </div>
    </section>
  );
}

export function ModalityAnalysisCard({ modalities }) {
  const rows = [
    { key: 'text', label: 'Text', sub: '(NLP)', icon: 'fileText', data: modalities?.text },
    { key: 'voice', label: 'Voice', sub: '(Acoustic)', icon: 'mic', data: modalities?.voice },
    { key: 'video', label: 'Video', sub: '(Facial)', icon: 'video', data: modalities?.video },
  ];

  return (
    <section className="miora-card miora-results-card" aria-labelledby="modality-analysis-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="barChart" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="modality-analysis-title" className="miora-card-title">
            Modality-wise Analysis
          </h2>
        </div>
      </div>

      <div className="miora-modality-rows">
        {rows.map((row) => {
          const status = row.data?.status || 'unavailable';
          const score = row.data?.score;
          const isCompleted = status === 'completed' && typeof score === 'number';
          return (
            <div key={row.key} className="miora-modality-row">
              <div className="miora-modality-row-left">
                <span className="miora-modality-mini-badge" aria-hidden="true">
                  <DashboardIcon name={row.icon} size={16} strokeWidth={1.65} />
                </span>
                <span className="miora-modality-row-label">
                  <strong>{row.label}</strong> <span>{row.sub}</span>
                </span>
              </div>

              {isCompleted ? (
                <>
                  <div className="miora-contrib-bar-track">
                    <div
                      className="miora-contrib-bar-fill"
                      style={{ width: `${Math.round(score * 100)}%` }}
                    />
                  </div>
                  <span className="miora-contrib-val">{score.toFixed(2)}</span>
                </>
              ) : (
                <div className="miora-modality-unavail-row">
                  <span
                    className={`miora-signal-pill ${
                      status === 'failed' ? 'tone-active' : 'tone-muted'
                    }`}
                  >
                    {status === 'failed' ? 'Failed' : 'Unavailable'}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function MultimodalSummaryCard({ screening }) {
  const mods = screening?.modalities || {};
  const textReady = mods.text?.status === 'completed';
  const voiceReady = mods.voice?.status === 'completed';
  const videoReady = mods.video?.status === 'completed';
  const activeCount = [textReady, voiceReady, videoReady].filter(Boolean).length;
  const hasScore = typeof screening?.combinedScore === 'number';

  return (
    <section className="miora-card miora-results-card" aria-labelledby="multimodal-summary-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="layers" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="multimodal-summary-title" className="miora-card-title">
            Multimodal Summary
          </h2>
        </div>
      </div>

      <div className="miora-fusion-body">
        <div
          className="miora-venn-diagram"
          aria-label={`${activeCount} of 3 modalities included in summary`}
        >
          <div className={`miora-venn-circle is-top ${textReady ? 'is-active' : 'is-missing'}`}>
            <DashboardIcon name="fileText" size={16} />
          </div>
          <div className={`miora-venn-circle is-left ${voiceReady ? 'is-active' : 'is-missing'}`}>
            <DashboardIcon name="mic" size={16} />
          </div>
          <div className={`miora-venn-circle is-right ${videoReady ? 'is-active' : 'is-missing'}`}>
            <DashboardIcon name="video" size={16} />
          </div>
          <div className="miora-venn-core" aria-hidden="true">
            <DashboardIcon name="brain" size={18} strokeWidth={1.7} />
          </div>
        </div>

        <div className="miora-fusion-meta">
          <span className="miora-prelim-caption">Fused Score</span>
          <strong className="miora-fusion-score">
            {hasScore ? screening.combinedScore.toFixed(2) : 'Pending'}
          </strong>
          <RiskBadge risk={`${screening?.risk || 'Moderate'} Risk`} />
          <span className="miora-fusion-count">{activeCount} of 3 modalities processed</span>
        </div>
      </div>
    </section>
  );
}

function TrendTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const pt = payload[0].payload;
  return (
    <div className="miora-chart-tooltip">
      <div className="miora-chart-tooltip-title">{pt.week}</div>
      <div className="miora-chart-tooltip-row">
        <span>Score</span>
        <strong>
          {pt.score.toFixed(2)} ({pt.label})
        </strong>
      </div>
    </div>
  );
}

export function RiskTrendCard({ history }) {
  const hasHistory = Array.isArray(history) && history.length > 0;

  return (
    <section className="miora-card miora-results-card" aria-labelledby="risk-trend-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="trendingUp" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="risk-trend-title" className="miora-card-title">
            Risk Trend
          </h2>
        </div>
      </div>

      {hasHistory ? (
        <div className="miora-trend-chart-wrap">
          <ResponsiveContainer width="100%" height={185}>
            <AreaChart data={history} margin={{ top: 10, right: 16, left: -14, bottom: 2 }}>
              <defs>
                <linearGradient id="mioraRiskTrendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#d9487a" stopOpacity={0.22} />
                  <stop offset="100%" stopColor="#fff8f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#f1e3e5" />
              <XAxis
                dataKey="week"
                axisLine={{ stroke: '#ead9dc' }}
                tickLine={false}
                tick={{ fill: '#5c4e53', fontSize: 11.5 }}
                dy={6}
              />
              <YAxis
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                tickFormatter={(v) => v.toFixed(2)}
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#6c5d62', fontSize: 11.5 }}
              />
              <Tooltip content={<TrendTooltip />} />
              <Area
                type="linear"
                dataKey="score"
                stroke="#c73566"
                strokeWidth={2.2}
                fill="url(#mioraRiskTrendFill)"
                dot={{ r: 4, fill: '#fff', stroke: '#c73566', strokeWidth: 2 }}
                activeDot={{ r: 5.5, fill: '#c73566', stroke: '#fff', strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="miora-trend-empty">
          <p>No historical screening trend available yet for this mother.</p>
        </div>
      )}
    </section>
  );
}

