import React from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { DashboardIcon } from './DashboardIcon.jsx';

function RiskTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;
  return (
    <div className="miora-chart-tooltip">
      <div className="miora-chart-tooltip-title">{item.name}</div>
      <div className="miora-chart-tooltip-row">
        <span>Count</span>
        <strong>
          {item.count} ({item.percentage}%)
        </strong>
      </div>
    </div>
  );
}

export function RiskDistributionCard({ distribution, total, onSelectCategory }) {
  return (
    <section className="miora-card miora-chart-card" aria-labelledby="risk-distribution-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="pieChart" size={21} strokeWidth={1.6} />
          </span>
          <h2 id="risk-distribution-title" className="miora-card-title">
            Risk Distribution
          </h2>
        </div>
      </div>

      <div className="miora-risk-body">
        <div className="miora-donut-wrap">
          <ResponsiveContainer width={174} height={174}>
            <PieChart>
              <Pie
                data={distribution}
                dataKey="count"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={78}
                startAngle={90}
                endAngle={-270}
                stroke="none"
                isAnimationActive={false}
                onClick={(entry) => onSelectCategory?.(entry.name)}
                style={{ cursor: onSelectCategory ? 'pointer' : 'default' }}
              >
                {distribution.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<RiskTooltip />} />
            </PieChart>
          </ResponsiveContainer>

          <div className="miora-donut-center" aria-hidden="true">
            <span className="miora-donut-total">{total}</span>
            <span className="miora-donut-caption">Screenings</span>
          </div>
        </div>

        <ul className="miora-risk-legend" aria-label="Risk distribution breakdown">
          {distribution.map((item) => (
            <li key={item.name}>
              <button
                type="button"
                className="miora-risk-legend-btn"
                onClick={() => onSelectCategory?.(item.name)}
              >
                <span className="miora-risk-legend-left">
                  <span
                    className="miora-risk-swatch"
                    style={{ backgroundColor: item.color }}
                    aria-hidden="true"
                  />
                  <span className="miora-risk-label">{item.name}</span>
                </span>
                <span className="miora-risk-value">
                  {item.percentage}% ({item.count})
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

