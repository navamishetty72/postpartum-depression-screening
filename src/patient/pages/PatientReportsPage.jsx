import React, { useState, useMemo } from 'react';
import { NavLink, useNavigate, useSearchParams } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from '../components/PatientIcons.jsx';
import './reports.css';

export function PatientReportsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'overview';

  const {
    patient,
    screening,
    notifications,
    markNotificationRead,
    markAllNotificationsRead,
    consultations,
    downloadReport,
    downloadToast,
  } = usePatient();

  const [activeTab, setActiveTab] = useState(initialTab);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [isEmptyStateDemo, setIsEmptyStateDemo] = useState(false);

  // Filter downloadable reports: preserve Screening Report PDF & Conversation Transcript, exclude raw recordings per Change 6
  const downloadableReports = useMemo(() => {
    const list = screening?.reports && screening.reports.length > 0
      ? screening.reports
      : [
          { id: 'rep-pdf', title: 'Screening Report', filename: 'Miora_Screening_Report_17Nov2026.pdf', size: '2.4 MB', type: 'pdf', authorized: true, format: '.pdf' },
          { id: 'rep-txt', title: 'Conversation Transcript', filename: 'Miora_Conversation_Transcript_17Nov2026.txt', size: '24 KB', type: 'txt', authorized: true, format: '.txt' },
        ];
    return list.filter((rep) => {
      const type = (rep.type || '').toLowerCase();
      const title = (rep.title || '').toLowerCase();
      if (type === 'wav' || type === 'mp4' || type === 'audio' || type === 'video') return false;
      if (title.includes('audio recording') || title.includes('video recording')) return false;
      return true;
    });
  }, [screening?.reports]);

  // Gauge calculations for 64% risk circle (circumference = 2 * PI * r = 2 * PI * 38 = 238.76)
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const scorePercent = isEmptyStateDemo || !screening ? 0 : screening.riskScore;
  const strokeDashoffset = circumference - (scorePercent / 100) * circumference;

  // Trend chart points data
  const trendData = (!isEmptyStateDemo && screening?.trend) || [
    { week: 'Week 1', score: 42 },
    { week: 'Week 2', score: 50 },
    { week: 'Week 3', score: 58 },
    { week: 'Week 4', score: 64 },
  ];

  // SVG Chart sizing & mapping:
  const chartWidth = 265;
  const chartHeight = 115;
  const plotLeft = 24;
  const plotRight = 250;
  const plotTop = 10;
  const plotBottom = 92;
  const plotW = plotRight - plotLeft;
  const plotH = plotBottom - plotTop;

  const points = trendData.map((d, i) => {
    const x = plotLeft + (i / (trendData.length - 1)) * plotW;
    const y = plotBottom - (d.score / 100) * plotH;
    return { ...d, x, y };
  });

  const pathD = points.reduce((acc, pt, i) => {
    if (i === 0) return `M ${pt.x} ${pt.y}`;
    const prev = points[i - 1];
    const cpx1 = prev.x + (pt.x - prev.x) / 2;
    const cpy1 = prev.y;
    const cpx2 = prev.x + (pt.x - prev.x) / 2;
    const cpy2 = pt.y;
    return `${acc} C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${pt.x} ${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x} ${plotBottom} L ${points[0].x} ${plotBottom} Z`;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'bar-chart' },
    { id: 'screening', label: 'Screening Reports', icon: 'clipboard' },
    { id: 'consultations', label: 'Doctor Consultations', icon: 'calendar' },
    { id: 'mood', label: 'Mood Tracking', icon: 'trending-up' },
    { id: 'all-reports', label: 'All Reports', icon: 'file-text' },
  ];

  return (
    <div className="reports-page-container">
      {/* Breadcrumb Bar */}
      <div className="medhist-breadcrumb-bar">
        <NavLink to="/patient/dashboard" className="medhist-breadcrumb-link">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
            <path d="M9.5 21v-7h5v7" />
          </svg>
          <span>Home</span>
        </NavLink>
        <span className="medhist-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
        <span className="medhist-breadcrumb-current">My Reports</span>
      </div>

      {/* Hero Header Banner with Mother & Baby Illustration */}
      <div className="patient-card reports-hero-card">
        <div className="reports-hero-text">
          <h1 className="patient-page-heading reports-title">My Reports &amp; Analytics</h1>
          <p className="patient-page-subheading reports-subtitle">
            Track your screenings, clinical evaluations, and emotional well-being trajectory over time.
          </p>
        </div>

        <div className="reports-hero-illu-wrap" aria-hidden="true">
          <img
            src="/assets/mother-baby-header-crop.png"
            alt=""
            className="reports-hero-illustration"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <nav className="reports-tabs-bar" aria-label="Reports Views">
        <div className="reports-tabs-list" role="tablist">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={`reports-tab-btn ${isActive ? 'is-active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <PatientIcon name={tab.icon} size={15} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          className="reports-empty-state-toggle-btn"
          onClick={() => setIsEmptyStateDemo((prev) => !prev)}
        >
          {isEmptyStateDemo ? 'Show Demo Data' : 'Simulate Empty State'}
        </button>
      </nav>

      {/* Tab 1: Overview Dashboard */}
      {activeTab === 'overview' && (
        <div className="reports-overview-grid">
          {/* Top Row: 3 KPI / Summary Cards */}
          <div className="reports-top-cards-row">
            {/* Card 1: Latest Screening Result */}
            <section className="patient-card reports-card reports-screening-card" aria-labelledby="screening-result-title">
              <div className="reports-card-header">
                <span className="reports-card-icon" aria-hidden="true">
                  <PatientIcon name="clipboard" size={17} />
                </span>
                <h2 id="screening-result-title" className="reports-card-title">
                  Latest Screening Result
                </h2>
              </div>

              {isEmptyStateDemo || !screening ? (
                <div className="reports-empty-content">
                  <p>No screening session completed yet.</p>
                  <button
                    type="button"
                    className="patient-btn-primary"
                    onClick={() => navigate('/patient/screening')}
                  >
                    Start AI Screening
                  </button>
                </div>
              ) : (
                <div className="screening-result-content">
                  <div className="screening-gauge-wrap">
                    <svg className="screening-gauge-svg" viewBox="0 0 100 100" width="94" height="94" aria-hidden="true">
                      <circle
                        cx="50"
                        cy="50"
                        r={radius}
                        className="screening-gauge-track"
                        strokeWidth="7"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r={radius}
                        className="screening-gauge-fill"
                        strokeWidth="7"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                      />
                    </svg>
                    <div className="screening-gauge-text">
                      <span className="screening-gauge-pct">{screening.riskScore}%</span>
                    </div>
                  </div>

                  <div className="screening-result-meta">
                    <div className="screening-status-row">
                      <span className="screening-risk-pill status-moderate">
                        {screening.riskLabel}
                      </span>
                    </div>
                    <p className="screening-date-text">
                      Completed: <strong>{screening.latestDate}</strong>
                    </p>
                    <p className="screening-recom-note">
                      {screening.recommendationText}
                    </p>
                    <button
                      type="button"
                      className="reports-inline-link-btn"
                      onClick={() => setActiveTab('screening')}
                    >
                      <span>View Full Screening Report</span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}
            </section>

            {/* Card 2: Emotional Well-being Trend */}
            <section className="patient-card reports-card reports-trend-card" aria-labelledby="trend-title">
              <div className="reports-card-header">
                <span className="reports-card-icon" aria-hidden="true">
                  <PatientIcon name="trending-up" size={17} />
                </span>
                <h2 id="trend-title" className="reports-card-title">
                  Emotional Well-being Trend
                </h2>
              </div>

              <div className="trend-chart-container">
                <svg
                  className="trend-svg"
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  preserveAspectRatio="none"
                  aria-label="Well-being trajectory chart"
                >
                  <defs>
                    <linearGradient id="patientTrendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ea3a7a" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#ea3a7a" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Grid guidelines */}
                  <line x1={plotLeft} y1={plotBottom} x2={plotRight} y2={plotBottom} stroke="#f0dfe2" strokeWidth="1" />
                  <line x1={plotLeft} y1={(plotTop + plotBottom) / 2} x2={plotRight} y2={(plotTop + plotBottom) / 2} stroke="#f8ecf0" strokeDasharray="3 3" />
                  <line x1={plotLeft} y1={plotTop} x2={plotRight} y2={plotTop} stroke="#f8ecf0" strokeDasharray="3 3" />

                  {/* Gradient Area Fill */}
                  <path d={areaD} fill="url(#patientTrendGrad)" />

                  {/* Spline Path */}
                  <path d={pathD} fill="none" stroke="#d93c75" strokeWidth="2.5" strokeLinecap="round" />

                  {/* Data Points */}
                  {points.map((pt, i) => (
                    <g key={i}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={hoveredPoint === i ? 6 : 4}
                        fill="#ffffff"
                        stroke="#d93c75"
                        strokeWidth="2.5"
                        className="trend-point-dot"
                        onMouseEnter={() => setHoveredPoint(i)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      />
                    </g>
                  ))}
                </svg>

                {/* X-Axis labels */}
                <div className="trend-labels-row">
                  {trendData.map((d, i) => (
                    <span key={i} className="trend-x-label">{d.week}</span>
                  ))}
                </div>
              </div>

              <p className="trend-footer-text">
                Observed distress score trending from 42% to 64% across past 4 check-in intervals.
              </p>
            </section>

            {/* Card 3: Download Reports */}
            <section className="patient-card reports-card reports-download-card" aria-labelledby="download-title">
              <div className="reports-card-header">
                <span className="reports-card-icon" aria-hidden="true">
                  <PatientIcon name="file-text" size={17} />
                </span>
                <h2 id="download-title" className="reports-card-title">
                  Download Reports
                </h2>
              </div>

              <div className="reports-download-items-list">
                {downloadableReports.slice(0, 3).map((rep) => (
                  <div key={rep.id} className="reports-download-row">
                    <div className="download-row-info">
                      <strong className="download-row-title">{rep.title}</strong>
                      <span className="download-row-sub">{rep.filename} &bull; {rep.size}</span>
                    </div>

                    <button
                      type="button"
                      className="patient-btn-secondary download-action-btn"
                      onClick={() => downloadReport(rep)}
                      aria-label={`Download ${rep.title}`}
                    >
                      <PatientIcon name="download" size={13} />
                      <span>Download</span>
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* Bottom Row: 2 Wider Analytical Cards */}
          <div className="reports-bottom-cards-row">
            {/* Card 4: Key Insights */}
            <section className="patient-card reports-card reports-insights-card" aria-labelledby="insights-title">
              <div className="reports-card-header">
                <span className="reports-card-icon" aria-hidden="true">
                  <PatientIcon name="sparkles" size={17} />
                </span>
                <h2 id="insights-title" className="reports-card-title">
                  Key Insights &amp; Clinical Signals
                </h2>
              </div>

              <div className="reports-insights-list">
                {(Array.isArray(screening?.insights) ? screening.insights : [
                  {
                    id: 'ins-1',
                    title: 'Sleep Disruption Impact',
                    text: 'Fragmented sleep cycles under 4 continuous hours show strong correlation with maternal fatigue and heightened stress markers.',
                    tag: `Sleep: ${screening?.insights?.sleep || 'Disturbed'}`,
                  },
                  {
                    id: 'ins-2',
                    title: 'Acoustic Tone & Vocal Energy',
                    text: 'Conversational acoustic variance indicates mild vocal flatness and energy drop during evening reflections.',
                    tag: `Stress: ${screening?.insights?.stress || 'Elevated'}`,
                  },
                  {
                    id: 'ins-3',
                    title: 'Grounding Responsiveness',
                    text: 'High engagement and heart-rate recovery recorded when practicing 4-7-8 parasympathetic breathing.',
                    tag: `Support: ${screening?.insights?.support || 'Recommended'}`,
                  },
                ]).map((ins) => (
                  <div key={ins.id} className="reports-insight-box">
                    <div className="insight-box-top">
                      <strong className="insight-box-title">{ins.title}</strong>
                      <span className="insight-box-tag">{ins.tag}</span>
                    </div>
                    <p className="insight-box-p">{ins.text}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Card 5: Assessment Summary & Next Steps */}
            <section className="patient-card reports-card reports-summary-card" aria-labelledby="summary-title">
              <div className="reports-card-header">
                <span className="reports-card-icon" aria-hidden="true">
                  <PatientIcon name="clipboard" size={17} />
                </span>
                <h2 id="summary-title" className="reports-card-title">
                  Assessment Summary &amp; Next Steps
                </h2>
              </div>

              <div className="reports-summary-body">
                <p className="summary-clinical-quote">
                  &ldquo;Overall screening indicators point to moderate postpartum distress consistent with sleep fragmentation and emotional exhaustion. Coordinated follow-up recommended.&rdquo;
                </p>

                <div className="summary-next-steps-list">
                  <div className="summary-step-item">
                    <span className="step-num-circle">1</span>
                    <div>
                      <strong>Review Personalised Care Plan</strong>
                      <p>Implement daily 4-7-8 breathing exercises and sleep hygiene restoration tasks.</p>
                    </div>
                  </div>

                  <div className="summary-step-item">
                    <span className="step-num-circle">2</span>
                    <div>
                      <strong>Virtual Check-in with Dr. Elena Rostova</strong>
                      <p>Next scheduled telehealth consultation on 20 Nov 2026 at 11:00 AM.</p>
                    </div>
                  </div>
                </div>

                <div className="summary-card-actions">
                  <button
                    type="button"
                    className="patient-btn-primary"
                    onClick={() => navigate('/patient/care-suggestions')}
                  >
                    View Care Suggestions
                  </button>
                  <button
                    type="button"
                    className="patient-btn-secondary"
                    onClick={() => navigate('/patient/connect-doctor')}
                  >
                    Consultation Details
                  </button>
                </div>
              </div>
            </section>
          </div>
        </div>
      )}

      {/* Tab 2: Screening Reports View */}
      {activeTab === 'screening' && (
        <div className="reports-tab-view">
          <div className="patient-card reports-tab-card">
            <h2 className="reports-tab-heading">Detailed AI Screening Assessment</h2>
            <p className="reports-tab-sub">
              Full multimodal screening report conducted on 17 Nov 2026 with Dr. Elena Rostova's maternal care unit.
            </p>

            <div className="screening-tab-details-grid">
              <div className="detail-stat-box">
                <span className="detail-stat-label">Edinburgh PPD Score</span>
                <span className="detail-stat-val">14 / 30</span>
                <span className="detail-stat-sub">Moderate Risk Category</span>
              </div>
              <div className="detail-stat-box">
                <span className="detail-stat-label">Session Duration</span>
                <span className="detail-stat-val">04:12</span>
                <span className="detail-stat-sub">Acoustic &amp; Conversational</span>
              </div>
              <div className="detail-stat-box">
                <span className="detail-stat-label">Consent &amp; Privacy</span>
                <span className="detail-stat-val">Verified</span>
                <span className="detail-stat-sub">Encrypted Storage</span>
              </div>
            </div>

            <div className="reports-tab-action-row">
              <button
                type="button"
                className="patient-btn-primary"
                onClick={() => downloadReport({ title: 'Full Screening Report', filename: 'Miora_Screening_17Nov2026.pdf', type: 'pdf' })}
              >
                <PatientIcon name="download" size={14} />
                <span>Download Official PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Doctor Consultations View */}
      {activeTab === 'consultations' && (
        <div className="reports-tab-view">
          <div className="patient-card reports-tab-card">
            <div className="tab-card-header-row">
              <div>
                <h2 className="reports-tab-heading">Doctor Consultations &amp; Care Notes</h2>
                <p className="reports-tab-sub">
                  Direct telehealth consultations and clinical summaries coordinated with Dr. Elena Rostova.
                </p>
              </div>

              <button
                type="button"
                className="patient-btn-primary"
                onClick={() => navigate('/patient/connect-doctor')}
              >
                <PatientIcon name="calendar" size={14} />
                <span>Schedule New Consultation</span>
              </button>
            </div>

            <div className="consultations-tab-list">
              {(consultations || []).map((c) => (
                <div key={c.id} className="consultation-tab-row">
                  <div className="consultation-row-details">
                    <div className="consultation-row-top">
                      <strong>{c.doctorName} &bull; {c.role}</strong>
                      <span className={`connect-status-badge ${c.status === 'Scheduled' ? 'status-scheduled' : 'status-completed'}`}>
                        {c.status}
                      </span>
                    </div>
                    <p className="consultation-row-meta">
                      {c.clinic} &bull; {c.date} at {c.time} ({c.type})
                    </p>
                  </div>
                  <button
                    type="button"
                    className="patient-btn-secondary"
                    onClick={() => navigate('/patient/connect-doctor')}
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Mood Tracking View */}
      {activeTab === 'mood' && (
        <div className="reports-tab-view">
          <div className="patient-card reports-tab-card">
            <h2 className="reports-tab-heading">Mood &amp; Emotional State Tracking</h2>
            <p className="reports-tab-sub">
              Weekly progress records across conversational checkpoints and self-checkins.
            </p>

            <div className="mood-progress-table-wrap">
              <table className="mood-progress-table">
                <thead>
                  <tr>
                    <th>Check-in Period</th>
                    <th>Emotional Score</th>
                    <th>Clinical Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trendData.map((d) => (
                    <tr key={d.week}>
                      <td>{d.week}</td>
                      <td><strong>{d.score}%</strong></td>
                      <td>
                        <span className={`connect-status-badge ${d.score > 60 ? 'status-scheduled' : 'status-completed'}`}>
                          {d.score > 60 ? 'Moderate Alert' : 'Mild Strain'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: All Reports Archive */}
      {activeTab === 'all-reports' && (
        <div className="reports-tab-view">
          <div className="patient-card reports-tab-card">
            <h2 className="reports-tab-heading">Authorized Clinical Records Archive</h2>
            <p className="reports-tab-sub">
              Secure archive of all official reports and health summaries for {patient?.name || 'Amara'}.
            </p>

            <div className="reports-download-items-list">
              {downloadableReports.map((rep) => (
                <div key={rep.id} className="reports-download-row">
                  <div className="download-row-info">
                    <strong className="download-row-title">{rep.title}</strong>
                    <span className="download-row-sub">{rep.filename} &bull; {rep.size} &bull; Confidential (Patient Authorized)</span>
                  </div>

                  <button
                    type="button"
                    className="patient-btn-secondary download-action-btn"
                    onClick={() => downloadReport(rep)}
                  >
                    <PatientIcon name="download" size={13} />
                    <span>Download</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Download Toast Notification */}
      {downloadToast && (
        <div
          className={`patient-toast ${downloadToast.type === 'success' ? 'is-success' : 'is-error'}`}
          role="status"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{downloadToast.message}</span>
        </div>
      )}
    </div>
  );
}

export default PatientReportsPage;
