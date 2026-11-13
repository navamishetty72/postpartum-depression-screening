import React, { useMemo, useState } from 'react';
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

const TIMEFRAMES = [
  { id: '4w', label: 'Last 4 Weeks', count: 4 },
  { id: '8w', label: 'Last 8 Weeks', count: 8 },
  { id: '12w', label: 'Last 12 Weeks', count: 12 },
];

function ActivityTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;
  return (
    <div className="miora-chart-tooltip">
      <div className="miora-chart-tooltip-title">
        {point.week} ({point.dateRange})
      </div>
      <div className="miora-chart-tooltip-row">
        <span>Screenings</span>
        <strong>{point.screenings}</strong>
      </div>
      <div className="miora-chart-tooltip-row">
        <span>Flagged cues</span>
        <strong>{point.flagged}</strong>
      </div>
    </div>
  );
}

export function ScreeningActivityChart({ records }) {
  const [timeframe, setTimeframe] = useState('4w');

  const selectedWindow = TIMEFRAMES.find((t) => t.id === timeframe) || TIMEFRAMES[0];

  const chartData = useMemo(() => {
    const slice = records.slice(-selectedWindow.count);
    return slice.map((item, idx) => ({
      ...item,
      displayWeek: selectedWindow.count === 4 ? item.week : `W${idx + 1}`,
    }));
  }, [records, selectedWindow.count]);

  return (
    <section className="miora-card miora-chart-card" aria-labelledby="screening-activity-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="barChart" size={21} strokeWidth={1.6} />
          </span>
          <h2 id="screening-activity-title" className="miora-card-title">
            Screening Activity
          </h2>
        </div>

        <div className="miora-select-wrap">
          <label htmlFor="screening-timeframe" className="sr-only">
            Filter screening activity timeframe
          </label>
          <select
            id="screening-timeframe"
            className="miora-pill-select"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf.id} value={tf.id}>
                {tf.label}
              </option>
            ))}
          </select>
          <span className="miora-select-chevron" aria-hidden="true">
            <DashboardIcon name="chevronDown" size={14} strokeWidth={2} />
          </span>
        </div>
      </div>

      <div className="miora-area-chart-wrap">
        <ResponsiveContainer width="100%" height={210}>
          <AreaChart data={chartData} margin={{ top: 12, right: 20, left: -18, bottom: 4 }}>
            <defs>
              <linearGradient id="mioraScreeningFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d9487a" stopOpacity={0.24} />
                <stop offset="85%" stopColor="#f8dce2" stopOpacity={0.08} />
                <stop offset="100%" stopColor="#fff8f7" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#f1e3e5" strokeWidth={1} />
            <XAxis
              dataKey="displayWeek"
              axisLine={{ stroke: '#ead9dc' }}
              tickLine={false}
              tick={{ fill: '#5c4e53', fontSize: 12, fontFamily: 'DM Sans, sans-serif' }}
              dy={8}
            />
            <YAxis
              domain={[0, 80]}
              ticks={[0, 20, 40, 60, 80]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#6c5d62', fontSize: 12, fontFamily: 'DM Sans, sans-serif' }}
            />
            <Tooltip content={<ActivityTooltip />} cursor={{ stroke: '#e8c4cd', strokeWidth: 1 }} />
            <Area
              type="linear"
              dataKey="screenings"
              stroke="#c73566"
              strokeWidth={2.2}
              fill="url(#mioraScreeningFill)"
              dot={{
                r: 4.5,
                fill: '#ffffff',
                stroke: '#c73566',
                strokeWidth: 2.2,
              }}
              activeDot={{
                r: 6,
                fill: '#c73566',
                stroke: '#ffffff',
                strokeWidth: 2,
              }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

