import React, { useMemo } from 'react';
import { NavLink, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useClinicalData } from '../../dashboard/context/ClinicalContext.jsx';
import { getCurrentUser } from '../../auth/authService.js';
import { DEMO_INTERVIEW_TIMELINE } from '../services/demoInterviewData.js';
import './screening-results.css';

export function ScreeningResultsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const clinical = useClinicalData();

  const isDemoMode = searchParams.get('demo') === 'true' || Boolean(location.state?.isDemo);

  const currentUser = getCurrentUser();
  const patientName = isDemoMode ? 'Demo Mother (Interview)' : (currentUser?.name || 'Amara');

  const { riskPercentage, rawScore, riskLabel } = useMemo(() => {
    const paramScore = searchParams.get('score');
    if (paramScore && !isNaN(Number(paramScore))) {
      const val = Number(paramScore);
      if (val <= 30) {
        const pct = Math.round((val / 30) * 100);
        let label = 'Low Risk Category';
        if (val >= 13) label = 'High Risk Category';
        else if (val >= 10) label = 'Moderate Risk Category';
        return { riskPercentage: pct, rawScore: val, riskLabel: label };
      }
      return {
        riskPercentage: Math.round(val),
        rawScore: Math.round((val / 100) * 30),
        riskLabel: val >= 43 ? 'High Risk Category' : val >= 33 ? 'Moderate Risk Category' : 'Low Risk Category',
      };
    }

    if (isDemoMode) {
      return { riskPercentage: 60, rawScore: 18, riskLabel: 'High Risk Category' };
    }

    const motherParam = searchParams.get('mother') || 'M-108';
    const match = clinical?.screenings?.find(
      (s) => s.motherId?.toLowerCase() === motherParam.toLowerCase()
    );

    if (match) {
      if (Array.isArray(match.riskHistory) && match.riskHistory.length > 0) {
        const lastEntry = match.riskHistory[match.riskHistory.length - 1];
        if (typeof lastEntry.score === 'number') {
          return {
            riskPercentage: Math.round(lastEntry.score * 100),
            rawScore: Math.round(lastEntry.score * 30),
            riskLabel: lastEntry.score >= 0.43 ? 'High Risk Category' : 'Moderate Risk Category',
          };
        }
      }
      if (typeof match.combinedScore === 'number') {
        return {
          riskPercentage: Math.round(match.combinedScore * 100),
          rawScore: Math.round(match.combinedScore * 30),
          riskLabel: match.combinedScore >= 0.43 ? 'High Risk Category' : 'Moderate Risk Category',
        };
      }
    }

    return { riskPercentage: 64, rawScore: 19, riskLabel: 'Moderate Risk Category' };
  }, [searchParams, clinical, isDemoMode]);

  const gaugeRadius = 50;
  const gaugeCircumference = 2 * Math.PI * gaugeRadius;
  const strokeOffset = gaugeCircumference * (1 - Math.min(Math.max(riskPercentage, 0), 100) / 100);

  return (
    <div className="results-page-shell">
      {/* Top Breadcrumb & Tracker Bar */}
      <div className="screening-top-bar-area">
        <div className="screening-header-titles">
          <div className="screening-breadcrumb">
            <NavLink to="/patient/reports" className="screening-breadcrumb-link">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
                <path d="M9.5 21v-7h5v7" />
              </svg>
              <span>Home</span>
            </NavLink>
            <span className="screening-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
            <NavLink to="/patient/screening" className="screening-breadcrumb-link">
              <span>AI Screening</span>
            </NavLink>
            <span className="screening-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
            <span className="screening-breadcrumb-current">Results</span>
          </div>
          <h1 className="patient-page-heading screening-page-title">
            {isDemoMode ? 'Demo Screening Results' : 'Screening Results'}
          </h1>
          <p className="patient-page-subheading screening-page-sub">
            {isDemoMode
              ? 'Results from the Gemini Companion AI Prerecorded Mother Interview demonstration.'
              : "Your AI screening has been analysed. Here's a clear, supportive overview of your assessment."}
          </p>
        </div>

        {/* 4-Stage Progress Tracker */}
        <div className="screening-stages-tracker" aria-label="Screening progress stages">
          <NavLink to="/patient/medical-history" className="tracker-stage is-completed">
            <div className="tracker-circle">
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
              </svg>
            </div>
            <span className="tracker-label">Medical History</span>
          </NavLink>

          <div className="tracker-line is-active-line" aria-hidden="true" />

          <NavLink to="/patient/screening" className="tracker-stage is-completed">
            <div className="tracker-circle">
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
              </svg>
            </div>
            <span className="tracker-label">Screening</span>
          </NavLink>

          <div className="tracker-line is-active-line" aria-hidden="true" />

          <div className="tracker-stage is-completed">
            <div className="tracker-circle">
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
              </svg>
            </div>
            <span className="tracker-label">Analysis</span>
          </div>

          <div className="tracker-line is-active-line" aria-hidden="true" />

          <div className="tracker-stage is-active">
            <div className="tracker-circle">
              <span className="tracker-inner-dot" />
            </div>
            <span className="tracker-label">Results</span>
          </div>
        </div>
      </div>

      {/* Main Content Cards */}
      <div className="results-content-stack">
        {/* Demo Mode Notice Banner */}
        {isDemoMode && (
          <div className="results-demo-banner" role="alert">
            <div className="results-demo-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              <span>DEMO / TEST MODE EVALUATION</span>
            </div>
            <p className="results-demo-desc">
              This screening assessment was evaluated from the <strong>Gemini Companion AI Prerecorded Mother Interview</strong> demonstration.
              <br />
              <strong>Strict Data Isolation:</strong> This demo evaluation data is completely isolated and has <em>NOT</em> been submitted to any real patient clinical records.
            </p>
          </div>
        )}

        {/* Card 1: About PPD (Left) + Estimated Risk of PPD (Right Gauge) */}
        <section className="patient-card results-top-card" aria-label="Screening Overview">
          <div className="results-about-section">
            <span className="results-about-tag">
              {isDemoMode ? 'Demo Assessment Overview' : 'About Postpartum Wellbeing'}
            </span>

            <p className="results-about-text">
              Postpartum Depression (PPD) is a common, treatable medical condition that can happen after childbirth. It can cause feelings of sadness, emotional fatigue, sleep disturbance, or feeling overwhelmed.
            </p>

            <div className="results-reassurance-box" role="note">
              <svg className="results-heart-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
              <p className="results-reassurance-text">
                <strong>Please be gentle with yourself.</strong> This is a preliminary screening estimate, not a clinical diagnosis. Many mothers experience similar phases, and with compassionate support, they recover fully.
              </p>
            </div>
          </div>

          <div className="results-card-vdivider" aria-hidden="true" />

          <div className="results-risk-section">
            <h2 className="results-risk-heading">Estimated Risk of PPD</h2>

            <div className="results-circular-gauge" aria-label={`Estimated risk of PPD is ${riskPercentage} percent`}>
              <svg className="results-gauge-svg" viewBox="0 0 124 124">
                <circle
                  className="results-gauge-bg"
                  cx="62"
                  cy="62"
                  r={gaugeRadius}
                />
                <circle
                  className="results-gauge-fill"
                  cx="62"
                  cy="62"
                  r={gaugeRadius}
                  strokeDasharray={gaugeCircumference}
                  strokeDashoffset={strokeOffset}
                />
              </svg>
              <span className="results-gauge-value">{riskPercentage}%</span>
            </div>

            <span className="results-risk-label-pill">{riskLabel}</span>
            <span className="results-raw-score-sub">{rawScore} / 30 EPDS Total</span>
          </div>
        </section>

        {/* Card 2: Key Insights */}
        <section className="patient-card results-insights-card" aria-label="Key Insights">
          <div className="results-insights-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <h2 className="results-insights-title">Key Observed Signals</h2>
          </div>

          <div className="results-insights-grid">
            <div className="results-insight-item">
              <div className="insight-icon-pill">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
                  <circle cx="9" cy="9" r="1" fill="currentColor" stroke="none" />
                  <circle cx="15" cy="9" r="1" fill="currentColor" stroke="none" />
                </svg>
              </div>
              <strong className="results-insight-name">Mood Changes</strong>
              <p className="results-insight-desc">Vocal tone and conversational pauses indicate emotional weariness.</p>
            </div>

            <div className="results-insight-item">
              <div className="insight-icon-pill">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  <circle cx="18.5" cy="6" r="0.75" fill="currentColor" stroke="none" />
                  <circle cx="20.5" cy="9.5" r="0.6" fill="currentColor" stroke="none" />
                </svg>
              </div>
              <strong className="results-insight-name">Sleep Disturbances</strong>
              <p className="results-insight-desc">Multiple nighttime awakenings correlated with high fatigue levels.</p>
            </div>

            <div className="results-insight-item">
              <div className="insight-icon-pill">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 3c-1.5 3-4 6.5-7 8.5 2 1.5 4.5 2 7 2 2.5 0 5-.5 7-2-3-2-5.5-5.5-7-8.5z" />
                  <path d="M12 13.5c-2.5 3-5 5.5-9 6 3 1.5 6 1.5 9 1.5s6 0 9-1.5c-4-.5-6.5-3-9-6z" />
                </svg>
              </div>
              <strong className="results-insight-name">Emotional Sensitivity</strong>
              <p className="results-insight-desc">Heightened sensory vulnerability observed during self-reflection.</p>
            </div>
          </div>
        </section>

        {/* Demo Interview 10-Item Dialogue & Score Breakdown (only in Demo Mode) */}
        {isDemoMode && (
          <section className="patient-card results-demo-breakdown-card" aria-label="Demo Interview Breakdown">
            <div className="results-demo-breakdown-header">
              <h2 className="results-demo-breakdown-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                <span>10-Item EPDS Spoken Dialogue &amp; Score Mapping</span>
              </h2>
              <span className="mode-badge-demo">Gemini Companion Source</span>
            </div>
            <div className="results-demo-table-wrapper">
              <table className="results-demo-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Interviewer Question</th>
                    <th>Mother's Spoken Response</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {DEMO_INTERVIEW_TIMELINE.map((item) => (
                    <tr key={item.qid}>
                      <td className="demo-table-qnum">Q{item.questionNumber}</td>
                      <td>{item.interviewerText}</td>
                      <td><em>&ldquo;{item.motherText}&rdquo;</em></td>
                      <td>
                        <span className={`demo-table-score-pill ${item.expectedScore === 0 ? 'score-0' : item.expectedScore >= 3 ? 'score-high' : 'score-mid'}`}>
                          {item.expectedScore} / 3
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Action Row */}
        <div className="results-actions-row">
          {isDemoMode ? (
            <>
              <button
                type="button"
                className="patient-btn-secondary results-action-btn"
                onClick={() => navigate('/patient/screening?mode=demo')}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21.5 2v6h-6" />
                  <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-1.19" />
                </svg>
                <span>Replay Demo Video</span>
              </button>

              <button
                type="button"
                className="patient-btn-primary results-action-btn"
                onClick={() => navigate('/patient/screening?mode=live')}
              >
                <span>Start Live Patient Screening</span>
                <span aria-hidden="true">&rarr;</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="patient-btn-secondary results-action-btn"
                onClick={() => navigate('/patient/screening')}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21.5 2v6h-6" />
                  <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-1.19" />
                </svg>
                <span>Retake Screening</span>
              </button>

              <button
                type="button"
                className="patient-btn-secondary results-action-btn"
                onClick={() => navigate('/patient/care-suggestions')}
              >
                <span>Explore Care Plan</span>
              </button>

              <button
                type="button"
                className="patient-btn-primary results-action-btn"
                onClick={() => navigate('/patient/connect-doctor')}
              >
                <span>Consult Dr. Elena Rostova</span>
                <span aria-hidden="true">&rarr;</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ScreeningResultsPage;
