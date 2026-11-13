import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { INITIAL_SCREENINGS } from '../data/mockClinicalData.js';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { RiskBadge } from '../components/Badges.jsx';
import {
  CarePlanPdfModal,
  RecommendationDetailModal,
  ScheduleFollowUpModal,
  SupportResourceModal,
} from '../components/InsightsModals.jsx';

const CARE_RECOMMENDATIONS = [
  {
    id: 'emotional-support',
    icon: 'leaf',
    title: 'Emotional Support',
    description: 'Provide empathetic check-ins and active listening.',
    guidance:
      'Schedule unhurried, empathetic check-ins acknowledging postpartum transitions without judgement. Validate emotional experiences and invite partner or family support when consented.',
  },
  {
    id: 'counselling-referral',
    icon: 'users',
    title: 'Counselling Referral',
    description: 'Consider a brief mental health consultation.',
    guidance:
      'When screening indicators suggest moderate or persistent distress, discuss an optional referral to a licensed perinatal mental health specialist for clinical evaluation.',
  },
  {
    id: 'wellbeing-practices',
    icon: 'dumbbell',
    title: 'Wellbeing Practices',
    description: 'Encourage sleep, rest and stress-reduction activities.',
    guidance:
      'Explore practical rest scheduling, gentle restorative movement cleared by the mother’s OB/GYN, and brief daily grounding practices alongside clinical follow-up.',
  },
];

function WellbeingTooltip({ active, payload }) {
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

export function InsightsCarePage() {
  const {
    mothers,
    screenings,
    getCarePlan,
    saveCareNotes,
    saveFollowUpMilestones,
    addScheduledFollowUp,
    toggleRecommendationInPlan,
    finalizeCarePlan,
  } = useClinicalData();
  const { motherId } = useParams();
  const navigate = useNavigate();

  const activeScreening = useMemo(() => {
    if (motherId) {
      return (
        screenings.find((s) => s.motherId.toLowerCase() === motherId.toLowerCase()) ||
        null
      );
    }
    if (screenings.length > INITIAL_SCREENINGS.length) {
      return screenings[0];
    }
    return screenings.find((s) => s.motherId === 'M-108') || screenings[0] || null;
  }, [screenings, motherId]);

  const activeMother = useMemo(() => {
    const targetId = motherId || activeScreening?.motherId || 'M-108';
    return mothers.find((m) => m.id.toLowerCase() === targetId.toLowerCase()) || mothers[0];
  }, [mothers, motherId, activeScreening]);

  const plan = getCarePlan(activeMother.id);

  const [notesDraft, setNotesDraft] = useState(plan.notes);
  const [notesStatus, setNotesStatus] = useState('');
  const [notesError, setNotesError] = useState('');
  const [editingMilestoneId, setEditingMilestoneId] = useState(null);
  const [editTimeframe, setEditTimeframe] = useState('');
  const [editTitle, setEditTitle] = useState('');

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const [activeRecModal, setActiveRecModal] = useState(null);
  const [activeResourceKey, setActiveResourceKey] = useState(null);
  const [finalizeMessage, setFinalizeMessage] = useState('');
  const [finalizeError, setFinalizeError] = useState('');

  useEffect(() => {
    setNotesDraft(getCarePlan(activeMother.id).notes);
    setNotesStatus('');
    setNotesError('');
    setFinalizeMessage('');
    setFinalizeError('');
    setEditingMilestoneId(null);
    // Intentionally scoped to patient switches so saving notes preserves notesStatus.
  }, [activeMother.id]);

  const discordanceLabel = useMemo(() => {
    if (!activeScreening) return activeMother.discordanceFlag ? 'High' : 'Low';
    if (activeScreening.discordanceScore >= 0.65) return 'High';
    if (activeScreening.discordanceScore >= 0.3) return 'Moderate';
    return 'Low';
  }, [activeScreening, activeMother]);

  const keyInsights = useMemo(() => {
    if (!activeScreening) {
      return [
        {
          id: 'ins-empty',
          icon: 'barChart',
          text: 'No screening session outputs recorded yet for this mother.',
        },
      ];
    }

    const list = [];
    if (typeof activeScreening.combinedScore === 'number') {
      list.push({
        id: 'ins-risk',
        icon: 'barChart',
        text: `${activeScreening.risk} risk of postpartum distress (Score: ${activeScreening.combinedScore.toFixed(
          2
        )}).`,
      });
    } else {
      list.push({
        id: 'ins-risk-pending',
        icon: 'barChart',
        text: `Combined risk score pending completion (${activeScreening.modality}).`,
      });
    }

    if (typeof activeScreening.discordanceScore === 'number') {
      const prefix =
        activeScreening.discordanceScore >= 0.3
          ? 'Notable cross-modal difference'
          : 'Low cross-modal divergence';
      list.push({
        id: 'ins-disc',
        icon: 'bolt',
        text: `${prefix} (Discordance: ${activeScreening.discordanceScore.toFixed(2)}).`,
      });
    }

    const mods = activeScreening.modalities || {};
    if (mods.voice?.status === 'completed' && typeof mods.voice.score === 'number') {
      list.push({
        id: 'ins-voice',
        icon: 'waveform',
        text: `Voice acoustic signal observation (Score: ${mods.voice.score.toFixed(2)}).`,
      });
    } else {
      list.push({
        id: 'ins-voice-unavail',
        icon: 'waveform',
        text: 'Voice acoustic signal unavailable for this session.',
      });
    }

    if (mods.video?.status === 'completed' && typeof mods.video.score === 'number') {
      list.push({
        id: 'ins-video',
        icon: 'smile',
        text: `Facial expressiveness signal observation (Score: ${mods.video.score.toFixed(2)}).`,
      });
    } else if (mods.text?.status === 'completed' && typeof mods.text.score === 'number') {
      list.push({
        id: 'ins-text',
        icon: 'fileText',
        text: `Text sentiment signal observation (Score: ${mods.text.score.toFixed(2)}).`,
      });
    }

    return list;
  }, [activeScreening]);

  const includedRecommendations = useMemo(
    () =>
      CARE_RECOMMENDATIONS.filter((r) =>
        plan.includedRecommendations.includes(r.id)
      ),
    [plan.includedRecommendations]
  );

  const dynamicSummary = useMemo(() => {
    const recTitles = includedRecommendations.map((r) => r.title.toLowerCase()).join(', ');
    const riskWord = (activeScreening?.risk || activeMother.risk || 'Moderate').toLowerCase();
    return `A personalized, multi-modal care plan addressing ${riskWord} distress indicators and ${discordanceLabel.toLowerCase()} cross-modal discordance, focused on ${
      recTitles || 'supportive monitoring'
    } across ${plan.milestones.length} scheduled follow-up milestone${
      plan.milestones.length === 1 ? '' : 's'
    }.`;
  }, [activeScreening, activeMother, discordanceLabel, includedRecommendations, plan.milestones.length]);

  const lastScreeningDate = useMemo(() => {
    if (activeScreening?.screeningDateTime) {
      return activeScreening.screeningDateTime.split('·')[0].trim();
    }
    return activeMother.lastScreeningDate;
  }, [activeScreening, activeMother]);

  const handleSaveNotes = () => {
    setNotesError('');
    setNotesStatus('');
    const result = saveCareNotes(activeMother.id, notesDraft);
    if (!result.ok) {
      setNotesError(result.error);
      return;
    }
    setNotesStatus(`Notes saved at ${result.savedAt}`);
  };

  const handleToggleMilestoneDone = (msId) => {
    const next = plan.milestones.map((ms) =>
      ms.id === msId ? { ...ms, completed: !ms.completed } : ms
    );
    saveFollowUpMilestones(activeMother.id, next);
  };

  const handleStartEditMilestone = (ms) => {
    setEditingMilestoneId(ms.id);
    setEditTimeframe(ms.timeframe);
    setEditTitle(ms.title);
  };

  const handleSaveEditMilestone = (msId) => {
    if (!editTimeframe.trim() || !editTitle.trim()) return;
    const next = plan.milestones.map((ms) =>
      ms.id === msId
        ? { ...ms, timeframe: editTimeframe.trim(), title: editTitle.trim() }
        : ms
    );
    saveFollowUpMilestones(activeMother.id, next);
    setEditingMilestoneId(null);
  };

  const handleFinalizePlan = () => {
    setFinalizeError('');
    setFinalizeMessage('');
    const result = finalizeCarePlan(activeMother.id, dynamicSummary);
    if (!result.ok) {
      setFinalizeError(result.error);
      return;
    }
    setFinalizeMessage(`Care plan finalized for ${activeMother.id} at ${result.finalizedAt}.`);
  };

  const carePlanPdfDoc = {
    mother: activeMother,
    screening: activeScreening,
    overallRisk: activeScreening?.risk || activeMother.risk,
    discordanceLabel,
    insights: keyInsights,
    recommendations: includedRecommendations,
    milestones: plan.milestones,
    notes: notesDraft,
    summaryText: dynamicSummary,
    generatedDate: new Date().toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
  };

  const trendHistory = activeScreening?.riskHistory || [];

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Flowing Blush Header Waves */}
        <svg
          className="miora-header-ribbon miora-mothers-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="insightsWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#insightsWaveGrad)"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="insights-care-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>INSIGHTS &amp; CARE</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="insights-care-heading" className="miora-dash-title">
              Personalized <em>Insights &amp; Care</em>
            </h1>
            <p className="miora-dash-subtitle">
              Actionable insights, care recommendations and follow-up planning for maternal wellbeing.
            </p>
          </div>

          <div className="miora-results-header-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setScheduleOpen(true)}
            >
              <DashboardIcon name="calendar" size={15} />
              <span>Schedule Follow-up</span>
            </button>
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setPdfModalOpen(true)}
            >
              <DashboardIcon name="download" size={15} />
              <span>Care Plan (PDF)</span>
            </button>
          </div>
        </section>

        {/* Patient Information Strip */}
        <section className="miora-card miora-patient-strip miora-insights-strip" aria-label="Mother care plan context">
          <div className="miora-patient-item">
            <span className="miora-patient-icon" aria-hidden="true">
              <DashboardIcon name="user" size={18} />
            </span>
            <div className="miora-patient-meta">
              <div className="miora-patient-select-row">
                <label htmlFor="insights-mother-select" className="sr-only">
                  Select mother for care plan
                </label>
                <select
                  id="insights-mother-select"
                  className="miora-patient-id-select"
                  value={activeMother.id}
                  onChange={(e) => navigate(`/insights/${e.target.value}`)}
                >
                  {mothers.slice(0, 15).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
              </div>
              <span className="miora-patient-sub">{activeMother.initials}</span>
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="calendar" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Postpartum Week</span>
              <strong>Week {activeMother.postpartumWeek}</strong>
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="layers" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Overall Risk</span>
              <RiskBadge risk={activeScreening?.risk || activeMother.risk} />
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="bolt" size={17} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Discordance</span>
              <RiskBadge risk={discordanceLabel} />
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="clock" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Last Screening</span>
              <strong>{lastScreeningDate}</strong>
            </div>
          </div>

          <div className="miora-results-status-wrap">
            <span className="miora-results-status-pill is-completed">
              <DashboardIcon name="checkCircle" size={15} strokeWidth={1.8} />
              <span>{plan.finalized ? 'Care Plan Finalized' : 'Care Plan Ready'}</span>
            </span>
          </div>
        </section>

        {/* Row 1: Key Insights | Care Recommendations | Follow-up Plan */}
        <div className="miora-results-row-3">
          {/* A. Key Insights */}
          <section className="miora-card miora-results-card" aria-labelledby="key-insights-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="clipboardList" size={20} strokeWidth={1.65} />
                </span>
                <h2 id="key-insights-title" className="miora-card-title">
                  Key Insights
                </h2>
              </div>
            </div>

            <ul className="miora-insights-rows">
              {keyInsights.map((item) => (
                <li key={item.id} className="miora-insight-item-row">
                  <span className="miora-factor-icon" aria-hidden="true">
                    <DashboardIcon name={item.icon} size={17} strokeWidth={1.65} />
                  </span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ul>
            <p className="miora-insights-disclaimer">
              Screening observations only — do not diagnose or replace clinical judgement.
            </p>
          </section>

          {/* B. Care Recommendations */}
          <section className="miora-card miora-results-card" aria-labelledby="care-recs-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="heart" size={20} strokeWidth={1.65} />
                </span>
                <h2 id="care-recs-title" className="miora-card-title">
                  Care Recommendations
                </h2>
              </div>
            </div>

            <div className="miora-care-rec-list">
              {CARE_RECOMMENDATIONS.map((rec) => {
                const included = plan.includedRecommendations.includes(rec.id);
                return (
                  <button
                    key={rec.id}
                    type="button"
                    className={`miora-care-rec-card ${included ? 'is-included' : 'is-excluded'}`}
                    onClick={() => setActiveRecModal(rec)}
                  >
                    <span className="miora-care-rec-icon" aria-hidden="true">
                      <DashboardIcon name={rec.icon} size={18} strokeWidth={1.65} />
                    </span>
                    <div className="miora-care-rec-copy">
                      <div className="miora-care-rec-top">
                        <strong>{rec.title}</strong>
                        <span className="miora-care-rec-action">View Details</span>
                      </div>
                      <p>{rec.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* C. Follow-up Plan */}
          <section className="miora-card miora-results-card" aria-labelledby="followup-plan-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="calendar" size={20} strokeWidth={1.65} />
                </span>
                <h2 id="followup-plan-title" className="miora-card-title">
                  Follow-up Plan
                </h2>
              </div>
            </div>

            <ol className="miora-timeline-list">
              {plan.milestones.map((ms) => (
                <li
                  key={ms.id}
                  className={`miora-timeline-item ${ms.completed ? 'is-completed' : ''}`}
                >
                  <div className="miora-timeline-time-col">
                    <span className="miora-timeline-dot" aria-hidden="true">
                      <span />
                    </span>
                    <span className="miora-timeline-timeframe">{ms.timeframe}</span>
                  </div>

                  <div className="miora-timeline-card">
                    {editingMilestoneId === ms.id ? (
                      <div className="miora-timeline-edit-form">
                        <input
                          type="text"
                          value={editTimeframe}
                          onChange={(e) => setEditTimeframe(e.target.value)}
                          aria-label="Milestone timeframe"
                        />
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          aria-label="Milestone title"
                        />
                        <div className="miora-timeline-edit-actions">
                          <button
                            type="button"
                            className="miora-timeline-mini-btn"
                            onClick={() => handleSaveEditMilestone(ms.id)}
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            className="miora-timeline-mini-btn"
                            onClick={() => setEditingMilestoneId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="miora-timeline-card-top">
                          <strong>{ms.title}</strong>
                          <div className="miora-timeline-controls">
                            <button
                              type="button"
                              className="miora-timeline-mini-btn"
                              aria-label={`Edit ${ms.title}`}
                              onClick={() => handleStartEditMilestone(ms)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className={`miora-timeline-mini-btn ${
                                ms.completed ? 'is-done' : ''
                              }`}
                              aria-label={`Mark ${ms.title} ${
                                ms.completed ? 'incomplete' : 'completed'
                              }`}
                              onClick={() => handleToggleMilestoneDone(ms.id)}
                            >
                              {ms.completed ? 'Done' : 'Complete'}
                            </button>
                          </div>
                        </div>
                        <p>{ms.description}</p>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>

        {/* Row 2: Wellbeing Trend | Support Resources | Care Team Notes */}
        <div className="miora-results-row-3">
          {/* A. Wellbeing Trend */}
          <section className="miora-card miora-results-card" aria-labelledby="wellbeing-trend-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="trendingUp" size={20} strokeWidth={1.65} />
                </span>
                <h2 id="wellbeing-trend-title" className="miora-card-title">
                  Wellbeing Trend
                </h2>
              </div>
            </div>

            {trendHistory.length > 0 ? (
              <div className="miora-trend-chart-wrap">
                <ResponsiveContainer width="100%" height={185}>
                  <AreaChart data={trendHistory} margin={{ top: 10, right: 16, left: -14, bottom: 2 }}>
                    <defs>
                      <linearGradient id="mioraWellbeingFill" x1="0" y1="0" x2="0" y2="1">
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
                    <Tooltip content={<WellbeingTooltip />} />
                    <Area
                      type="linear"
                      dataKey="score"
                      stroke="#c73566"
                      strokeWidth={2.2}
                      fill="url(#mioraWellbeingFill)"
                      dot={{ r: 4, fill: '#fff', stroke: '#c73566', strokeWidth: 2 }}
                      activeDot={{ r: 5.5, fill: '#c73566', stroke: '#fff', strokeWidth: 2 }}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="miora-trend-empty">
                <p>No historical wellbeing trend available yet for this mother.</p>
              </div>
            )}
          </section>

          {/* B. Support Resources */}
          <section className="miora-card miora-results-card" aria-labelledby="support-resources-card-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="bookOpen" size={20} strokeWidth={1.65} />
                </span>
                <h2 id="support-resources-card-title" className="miora-card-title">
                  Support Resources
                </h2>
              </div>
            </div>

            <div className="miora-support-tiles-grid">
              {[
                { key: 'coping', icon: 'lotus', label: 'Coping Strategies' },
                { key: 'groups', icon: 'users', label: 'Support Groups' },
                { key: 'education', icon: 'bookOpen', label: 'Educational Resources' },
              ].map((res) => (
                <button
                  key={res.key}
                  type="button"
                  className="miora-support-tile"
                  onClick={() => setActiveResourceKey(res.key)}
                >
                  <span className="miora-support-tile-icon" aria-hidden="true">
                    <DashboardIcon name={res.icon} size={22} strokeWidth={1.6} />
                  </span>
                  <strong>{res.label}</strong>
                  <span className="miora-support-tile-arrow" aria-hidden="true">
                    <DashboardIcon name="arrowRight" size={14} strokeWidth={1.9} />
                  </span>
                </button>
              ))}
            </div>
          </section>

          {/* C. Care Team Notes */}
          <section className="miora-card miora-results-card" aria-labelledby="care-team-notes-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="checkSquare" size={19} strokeWidth={1.65} />
                </span>
                <h2 id="care-team-notes-title" className="miora-card-title">
                  Care Team Notes
                </h2>
              </div>
              <button
                type="button"
                className="miora-pill-btn"
                onClick={handleSaveNotes}
              >
                Save Notes
              </button>
            </div>

            <div className="miora-notes-box-wrap">
              <label htmlFor="care-team-notes-input" className="sr-only">
                Care team clinical notes
              </label>
              <textarea
                id="care-team-notes-input"
                className="miora-notes-textarea"
                rows="5"
                maxLength={500}
                placeholder="Add clinical notes, observations or care instructions..."
                value={notesDraft}
                onChange={(e) => {
                  setNotesDraft(e.target.value);
                  setNotesStatus('');
                  setNotesError('');
                }}
              />
              <div className="miora-notes-footer">
                <span className="miora-notes-status">
                  {notesError ? (
                    <span className="miora-notes-err">{notesError}</span>
                  ) : notesStatus ? (
                    <span className="miora-notes-ok">{notesStatus}</span>
                  ) : plan.notesSavedAt ? (
                    <span>Last saved at {plan.notesSavedAt}</span>
                  ) : (
                    <span>Visible to authorized care team only</span>
                  )}
                </span>
                <span className="miora-notes-counter">{notesDraft.length} / 500</span>
              </div>
            </div>
          </section>
        </div>

        {/* Care Plan Summary Bar */}
        <section className="miora-card miora-care-summary-bar" aria-labelledby="care-plan-summary-title">
          <div className="miora-care-summary-left">
            <span className="miora-care-summary-icon" aria-hidden="true">
              <DashboardIcon name="heart" size={20} strokeWidth={1.65} />
            </span>
            <h2 id="care-plan-summary-title" className="miora-quick-title">
              Care Plan Summary
            </h2>
          </div>

          <p className="miora-care-summary-copy">{dynamicSummary}</p>

          <button
            type="button"
            className="miora-cta-primary"
            onClick={handleFinalizePlan}
          >
            <span>{plan.finalized ? 'Update Finalized Plan' : 'Finalize Care Plan'}</span>
            <DashboardIcon name="arrowRight" size={16} strokeWidth={2} />
          </button>
        </section>

        {(finalizeMessage || finalizeError) && (
          <div className="miora-live-feedback-row miora-results-feedback">
            {finalizeError && (
              <div className="miora-live-alert" role="alert">
                {finalizeError}
              </div>
            )}
            {finalizeMessage && (
              <div className="miora-draft-pill" role="status">
                <DashboardIcon name="check" size={14} />
                <span>{finalizeMessage}</span>
                <button
                  type="button"
                  className="miora-inline-reset"
                  onClick={() => navigate(`/mothers/${activeMother.id}`)}
                >
                  View Mother Case
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <ScheduleFollowUpModal
        isOpen={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        motherId={activeMother.id}
        onSave={(appt) => addScheduledFollowUp(activeMother.id, appt)}
      />

      <CarePlanPdfModal
        isOpen={pdfModalOpen}
        onClose={() => setPdfModalOpen(false)}
        carePlanDoc={carePlanPdfDoc}
      />

      <RecommendationDetailModal
        recommendation={activeRecModal}
        included={
          activeRecModal
            ? plan.includedRecommendations.includes(activeRecModal.id)
            : false
        }
        onToggleInclude={(recId) => toggleRecommendationInPlan(activeMother.id, recId)}
        onClose={() => setActiveRecModal(null)}
      />

      <SupportResourceModal
        resourceKey={activeResourceKey}
        onClose={() => setActiveResourceKey(null)}
      />
    </div>
  );
}
