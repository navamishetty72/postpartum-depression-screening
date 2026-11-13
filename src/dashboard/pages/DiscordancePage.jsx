import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { INITIAL_SCREENINGS } from '../data/mockClinicalData.js';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import {
  ClinicalInterpretationCard,
  DiscordanceResultCard,
  KeyObservationsCard,
  ModalityComparisonCard,
  RiskByModalityCard,
  SignalAlignmentCard,
} from '../components/DiscordanceVisuals.jsx';
import {
  AddClinicalNoteModal,
  DiscordanceExportModal,
} from '../components/DiscordanceModals.jsx';
import { analyzeCrossModalDiscordance } from '../utils/discordanceAnalysis.js';

export function DiscordancePage() {
  const {
    mothers,
    screenings,
    selectedMotherId,
    setSelectedMotherId,
    clinicalNotes,
    addClinicalNote,
    updateMotherStatus,
    addScheduledFollowUp,
  } = useClinicalData();

  const { motherId: routeMotherId } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [exportOpen, setExportOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [actionFeedback, setActionFeedback] = useState('');

  const queryMotherId = searchParams.get('mother');
  const requestedMotherId = routeMotherId || queryMotherId || null;

  const activeScreening = useMemo(() => {
    if (requestedMotherId) {
      return (
        screenings.find((s) => s.motherId.toLowerCase() === requestedMotherId.toLowerCase()) ||
        null
      );
    }
    if (selectedMotherId) {
      const ctxMatch = screenings.find((s) => s.motherId === selectedMotherId);
      if (ctxMatch) return ctxMatch;
    }
    if (screenings.length > INITIAL_SCREENINGS.length) {
      return screenings[0];
    }
    return screenings.find((s) => s.motherId === 'M-108') || screenings[0] || null;
  }, [screenings, requestedMotherId, selectedMotherId]);

  const activeMother = useMemo(() => {
    if (!activeScreening) return null;
    return mothers.find((m) => m.id === activeScreening.motherId) || null;
  }, [mothers, activeScreening]);

  useEffect(() => {
    if (activeScreening?.motherId && activeScreening.motherId !== selectedMotherId) {
      setSelectedMotherId(activeScreening.motherId);
    }
  }, [activeScreening?.motherId, selectedMotherId, setSelectedMotherId]);

  const analysis = useMemo(
    () => analyzeCrossModalDiscordance({ screening: activeScreening, mother: activeMother }),
    [activeScreening, activeMother]
  );

  const sessionNotes = useMemo(() => {
    if (!activeScreening) return [];
    return clinicalNotes.filter(
      (n) => n.motherId === activeScreening.motherId && n.screeningId === activeScreening.id
    );
  }, [clinicalNotes, activeScreening]);

  const handleSelectMotherSession = (nextMotherId) => {
    setActionFeedback('');
    setSelectedMotherId(nextMotherId);
    if (location.pathname.startsWith('/clinical-review')) {
      navigate(`/clinical-review?mother=${nextMotherId}`);
    } else {
      navigate(`/discordance/${nextMotherId}`);
    }
  };

  const handleSaveNote = (notePayload) => {
    const saved = addClinicalNote(notePayload);
    if (saved) {
      setActionFeedback(
        `Contextual note saved for ${notePayload.motherId} (${notePayload.screeningId}).`
      );
    }
  };

  const handleScheduleFollowUp = () => {
    if (!activeScreening) return;
    updateMotherStatus(activeScreening.motherId, 'Follow-up');
    addScheduledFollowUp(activeScreening.motherId, {
      date: 'In 7 Days',
      type: 'Follow-up Screening',
      description: 'Post-discordance contextual screening check-in across consented modalities.',
      clinician: 'Miora Care Team',
    });
    setActionFeedback(
      `7-day follow-up screening scheduled for ${activeScreening.motherId}.`
    );
  };

  const handleScheduleClinicalReview = () => {
    if (!activeScreening) return;
    setSelectedMotherId(activeScreening.motherId);
    updateMotherStatus(activeScreening.motherId, 'Review');
    setActionFeedback(
      `Brief clinical review queued for ${activeScreening.motherId} (${activeScreening.id}).`
    );
    navigate(`/clinical-review?mother=${activeScreening.motherId}`);
  };

  const handleOpenSupportResources = () => {
    if (!activeScreening) return;
    setSelectedMotherId(activeScreening.motherId);
    navigate(`/insights?mother=${activeScreening.motherId}`);
  };

  if (requestedMotherId && !activeScreening) {
    return (
      <div className="miora-command-shell">
        <div className="miora-command-frame">
          <section className="miora-card miora-results-empty-state">
            <h2>Discordance Record Not Found</h2>
            <p>
              No multimodal screening session was found for Mother ID{' '}
              <strong>{requestedMotherId}</strong>.
            </p>
            <div className="miora-modal-actions">
              <button
                type="button"
                className="miora-btn-secondary"
                onClick={() => navigate('/mothers')}
              >
                Open Mothers &amp; Cases
              </button>
              <button
                type="button"
                className="miora-cta-primary"
                onClick={() => navigate('/discordance')}
              >
                View Latest Discordance
              </button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const isCompleted = activeScreening?.status === 'Completed';

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
            <linearGradient id="discordanceWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#discordanceWaveGrad)"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="discordance-page-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>DISCORDANCE ANALYSIS</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="discordance-page-heading" className="miora-dash-title">
              Cross-Modal <em>Discordance</em>
            </h1>
            <p className="miora-dash-subtitle">
              Identify and explore differences between self-reported responses and other observed
              signals.
            </p>
          </div>

          <div className="miora-results-header-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setExportOpen(true)}
            >
              <DashboardIcon name="download" size={15} />
              <span>Export Report</span>
            </button>
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setNoteOpen(true)}
            >
              <DashboardIcon name="fileText" size={15} />
              <span>Add Note</span>
            </button>
          </div>
        </section>

        {/* Patient Information Strip */}
        {activeScreening && (
          <section
            className="miora-card miora-patient-strip"
            aria-label="Selected patient screening context"
          >
            <div className="miora-patient-item">
              <span className="miora-patient-icon" aria-hidden="true">
                <DashboardIcon name="user" size={18} />
              </span>
              <div className="miora-patient-meta">
                <div className="miora-patient-select-row">
                  <label htmlFor="discordance-session-select" className="sr-only">
                    Select mother for discordance analysis
                  </label>
                  <select
                    id="discordance-session-select"
                    className="miora-patient-id-select"
                    value={activeScreening.motherId}
                    onChange={(e) => handleSelectMotherSession(e.target.value)}
                  >
                    {screenings.map((s) => (
                      <option key={s.id} value={s.motherId}>
                        {s.motherId}
                      </option>
                    ))}
                  </select>
                  <Link
                    to={`/mothers/${activeScreening.motherId}`}
                    className="miora-disc-record-link"
                    onClick={() => setSelectedMotherId(activeScreening.motherId)}
                    title={`Open Mother Record ${activeScreening.motherId}`}
                  >
                    <span>Record</span>
                    <DashboardIcon name="externalLink" size={12} />
                  </Link>
                </div>
                <span className="miora-patient-sub">
                  {activeScreening.motherInitials || activeMother?.initials || '—'}
                </span>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="calendar" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Postpartum Week</span>
                <strong>Week {activeScreening.postpartumWeek}</strong>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="layers" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Screening Type</span>
                <strong>{activeScreening.modality}</strong>
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="clock" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Screening Date</span>
                <strong>{activeScreening.screeningDateTime || activeScreening.completedAgo}</strong>
              </div>
            </div>

            <div className="miora-results-status-wrap">
              <span
                className={`miora-results-status-pill ${isCompleted ? 'is-completed' : 'is-pending'
                  }`}
              >
                <DashboardIcon
                  name={isCompleted ? 'checkCircle' : 'clock'}
                  size={15}
                  strokeWidth={1.8}
                />
                <span>
                  {isCompleted ? 'Analysis Completed' : `Analysis ${activeScreening.status}`}
                </span>
              </span>
            </div>
          </section>
        )}

        {/* Row 1: Modality Comparison | Risk by Modality | Discordance Result */}
        {activeScreening && analysis && (
          <div className="miora-results-row-3 miora-disc-row-top">
            <ModalityComparisonCard modalityRows={analysis.modalityRows} />
            <RiskByModalityCard
              modalityRows={analysis.modalityRows}
              highestModalityKey={analysis.highestModality?.key || null}
            />
            <DiscordanceResultCard
              discordance={analysis.discordance}
              overallRisk={analysis.overallRisk}
            />
          </div>
        )}

        {/* Row 2: Signal Alignment | Key Observations | Clinical Interpretation */}
        {activeScreening && analysis && (
          <div className="miora-results-row-3 miora-disc-row-bottom">
            <SignalAlignmentCard pairwiseAlignment={analysis.pairwiseAlignment} />
            <KeyObservationsCard observations={analysis.observations} />
            <ClinicalInterpretationCard
              interpretation={analysis.interpretation}
              limitations={analysis.limitations}
              sessionNotes={sessionNotes}
              onOpenAddNote={() => setNoteOpen(true)}
            />
          </div>
        )}

        {/* Bottom Bar: Recommended Actions */}
        {activeScreening && (
          <section
            className="miora-card miora-next-steps-bar"
            aria-labelledby="recommended-actions-title"
          >
            <div className="miora-next-steps-label">
              <span className="miora-card-icon" aria-hidden="true">
                <DashboardIcon name="calendar" size={20} strokeWidth={1.65} />
              </span>
              <h2 id="recommended-actions-title" className="miora-quick-title">
                Recommended Actions
              </h2>
            </div>

            <div className="miora-next-steps-cards">
              <button
                type="button"
                className="miora-next-step-card"
                onClick={handleScheduleFollowUp}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="calendar" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Conduct follow-up screening in 7 days</strong>
                  <small>Update mother status &amp; schedule check-in</small>
                </span>
              </button>

              <button
                type="button"
                className="miora-next-step-card"
                onClick={handleScheduleClinicalReview}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="users" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Schedule brief clinical review</strong>
                  <small>Queue clinician review for {activeScreening.motherId}</small>
                </span>
              </button>

              <button
                type="button"
                className="miora-next-step-card"
                onClick={handleOpenSupportResources}
              >
                <span className="miora-next-step-icon" aria-hidden="true">
                  <DashboardIcon name="heart" size={19} strokeWidth={1.65} />
                </span>
                <span className="miora-next-step-copy">
                  <strong>Discuss support resources</strong>
                  <small>Open Insights &amp; Care pathway tools</small>
                </span>
              </button>
            </div>
          </section>
        )}

        {actionFeedback && (
          <div className="miora-live-feedback-row miora-results-feedback">
            <div className="miora-draft-pill" role="status">
              <DashboardIcon name="check" size={14} />
              <span>{actionFeedback}</span>
            </div>
          </div>
        )}
      </div>

      <DiscordanceExportModal
        isOpen={exportOpen}
        onClose={() => setExportOpen(false)}
        screening={activeScreening}
        mother={activeMother}
        analysis={analysis}
        notes={sessionNotes}
      />

      <AddClinicalNoteModal
        isOpen={noteOpen}
        onClose={() => setNoteOpen(false)}
        screening={activeScreening}
        onSaveNote={handleSaveNote}
      />
    </div>
  );
}
