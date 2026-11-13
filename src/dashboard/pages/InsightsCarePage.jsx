import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';

export function InsightsCarePage() {
  const { weeklyRecords, metrics } = useClinicalData();
  const navigate = useNavigate();

  const recentEight = weeklyRecords.slice(-8).map((item, idx) => ({
    ...item,
    shortWeek: `W${idx + 1}`,
  }));

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <div className="miora-subpage-header">
          <div>
            <div className="miora-dash-eyebrow">
              <span>INSIGHTS &amp; CARE</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title miora-subpage-title">
              Longitudinal Care <em>Insights</em>
            </h1>
            <p className="miora-dash-subtitle">
              Practice-wide screening cadence, early distress detection, and postpartum care engagement.
            </p>
          </div>
          <button
            type="button"
            className="miora-cta-primary"
            onClick={() => navigate('/mothers')}
          >
            Open Mothers &amp; Cases
          </button>
        </div>

        <div className="miora-insights-grid">
          <section className="miora-card miora-chart-card">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="barChart" size={21} />
                </span>
                <h2 className="miora-card-title">8-Week Screening vs. Flagged Cues</h2>
              </div>
            </div>
            <div className="miora-area-chart-wrap">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={recentEight} margin={{ top: 10, right: 16, left: -16, bottom: 4 }}>
                  <CartesianGrid vertical={false} stroke="#f1e3e5" />
                  <XAxis dataKey="shortWeek" axisLine={{ stroke: '#ead9dc' }} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="screenings" name="Completed" fill="#f2b8c9" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="flagged" name="Flagged Cues" fill="#c73566" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="miora-card miora-insights-summary">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="stethoscope" size={21} />
                </span>
                <h2 className="miora-card-title">Care Pathway Highlights</h2>
              </div>
            </div>

            <div className="miora-insight-stat-list">
              <div className="miora-insight-stat">
                <strong>75.3%</strong>
                <span>Screening completion rate across {metrics.registeredMothers} mothers</span>
              </div>
              <div className="miora-insight-stat">
                <strong>Weeks 2–6</strong>
                <span>Peak postpartum window for multimodal voice-text mismatch</span>
              </div>
              <div className="miora-insight-stat">
                <strong>&lt; 24 hrs</strong>
                <span>Median clinician outreach time for High Risk triage cases</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

