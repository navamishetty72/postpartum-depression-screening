import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { RiskBadge } from '../components/Badges.jsx';
import {
  AIScreeningSummaryCard,
  ClinicalAssessmentCard,
  ClinicalDecisionCard,
  ComparisonCard,
  FollowUpCarePlanCard,
  KeyEvidenceCard,
} from '../components/ClinicalReviewCards.jsx';
import {
  ExportClinicalNoteModal,
  FinalizeConfirmationModal,
  PreviousResultsModal,
} from '../components/ClinicalReviewModals.jsx';
import {
  ADDITIONAL_SUPPORT_OPTIONS,
  CARE_ACTION_OPTIONS,
  NEXT_SCREENING_OPTIONS,
  extractClinicalReviewSummary,
} from '../utils/clinicalReviewHelpers.js';
import { submitClinicalReview } from '../services/clinicalReviewService.js';

function getInitialFormState({ motherId, savedReview, draftReview }) {
  const source = draftReview || savedReview?.clinicianAssessment;
  const planSource = draftReview || savedReview?.followUpPlan;

  return {
    reviewNotes: source?.reviewNotes || '',
    clinicianRisk: source?.risk || source?.clinicianRisk || '',
    decision: source?.decision || '',
    decisionReason: source?.decisionReason || '',
    nextScreening: planSource?.nextScreening || NEXT_SCREENING_OPTIONS[0],
    careAction: planSource?.careAction || CARE_ACTION_OPTIONS[0],
    additionalSupport: planSource?.additionalSupport || ADDITIONAL_SUPPORT_OPTIONS[0],
    hydratedFor: motherId,
  };
}

export function ClinicalReviewPage({ reviewSubmitter = submitClinicalReview }) {
  const {
    mothers,
    screenings,
    selectedMotherId,
    setSelectedMotherId,
    clinicalReviews,
    reviewDrafts,
    saveReviewDraft,
    saveFinalClinicalReview,
  } = useClinicalData();

  const { motherId: routeMotherId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const requestedMotherId = routeMotherId || searchParams.get('mother') || null;

  const activeMother = useMemo(() => {
    const targetId = requestedMotherId || selectedMotherId || 'M-108';
    const match = mothers.find((m) => m.id.toLowerCase() === targetId.toLowerCase());
    if (match) return match;
    if (requestedMotherId) return null;
    return mothers.find((m) => m.id === 'M-108') || mothers[0] || null;
  }, [mothers, requestedMotherId, selectedMotherId]);

  const motherScreenings = useMemo(() => {
    if (!activeMother) return [];
    return screenings.filter((s) => s.motherId === activeMother.id);
  }, [screenings, activeMother]);

  const activeScreening = motherScreenings[0] || null;

  const savedReview = activeMother ? clinicalReviews[activeMother.id] || null : null;
  const draftReview = activeMother ? reviewDrafts[activeMother.id] || null : null;
  const reviewHistory = savedReview?.history || (savedReview?.id ? [savedReview] : []);

  const [formState, setFormState] = useState(() =>
    getInitialFormState({
      motherId: activeMother?.id || 'M-108',
      savedReview,
      draftReview,
    })
  );

  const [validationErrors, setValidationErrors] = useState({});
  const [previousModalOpen, setPreviousModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    if (activeMother?.id && activeMother.id !== selectedMotherId) {
      setSelectedMotherId(activeMother.id);
    }
  }, [activeMother?.id, selectedMotherId, setSelectedMotherId]);

  useEffect(() => {
    if (!activeMother) return;
    if (formState.hydratedFor !== activeMother.id) {
      setFormState(
        getInitialFormState({
          motherId: activeMother.id,
          savedReview: clinicalReviews[activeMother.id] || null,
          draftReview: reviewDrafts[activeMother.id] || null,
        })
      );
      setValidationErrors({});
      setSaveError('');
      setStatusMessage('');
    }
  }, [activeMother, formState.hydratedFor, clinicalReviews, reviewDrafts]);

  const summary = useMemo(
    () => extractClinicalReviewSummary({ screening: activeScreening, mother: activeMother }),
    [activeScreening, activeMother]
  );

  const updateFormField = (patch) => {
    const next = { ...formState, ...patch };
    setFormState(next);
    if (activeMother?.id) {
      saveReviewDraft(activeMother.id, {
        reviewNotes: next.reviewNotes,
        clinicianRisk: next.clinicianRisk,
        decision: next.decision,
        decisionReason: next.decisionReason,
        nextScreening: next.nextScreening,
        careAction: next.careAction,
        additionalSupport: next.additionalSupport,
      });
    }
  };

  const handleSelectMother = (nextMotherId) => {
    setSelectedMotherId(nextMotherId);
    setStatusMessage('');
    setSaveError('');
    setValidationErrors({});
    navigate(`/clinical-review/${nextMotherId}`);
  };

  const validateForFinalize = () => {
    const errors = {};
    const notesTrimmed = formState.reviewNotes.trim();
    if (!notesTrimmed) {
      errors.reviewNotes = 'Please enter clinician review notes before finalizing.';
    } else if (notesTrimmed.length > 500) {
      errors.reviewNotes = 'Clinician review notes cannot exceed 500 characters.';
    }

    if (!formState.clinicianRisk) {
      errors.clinicianRisk = 'Please select an independent Clinical Risk level.';
    }

    if (!formState.decision) {
      errors.decision = 'Please select a Clinical Decision.';
    } else if (
      (formState.decision === 'partial' || formState.decision === 'disagree') &&
      !formState.decisionReason.trim()
    ) {
      errors.decisionReason =
        formState.decision === 'disagree'
          ? 'Please specify a reason for disagreeing with the AI assessment.'
          : 'Please add notes explaining your partial agreement.';
    }

    if (!formState.nextScreening || !formState.careAction || !formState.additionalSupport) {
      errors.followUpPlan = 'Please confirm Next Screening, Care Action, and Additional Support.';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleOpenFinalizeConfirm = () => {
    setStatusMessage('');
    setSaveError('');
    if (!validateForFinalize()) {
      return;
    }
    setConfirmModalOpen(true);
  };

  const handleConfirmSave = async () => {
    if (!activeMother || !activeScreening || !summary) return;
    setIsSaving(true);
    setSaveError('');

    const payload = {
      motherId: activeMother.id,
      screeningId: activeScreening.id,
      aiAssessment: {
        risk: summary.aiRiskLevel,
        combinedScore: summary.combinedScore,
        discordanceCategory: summary.discordanceBadgeLabel,
        discordanceScore: summary.discordanceAnalysis.discordance.score,
      },
      clinicianAssessment: {
        risk: formState.clinicianRisk,
        reviewNotes: formState.reviewNotes.trim(),
        decision: formState.decision,
        decisionReason:
          formState.decision === 'partial' || formState.decision === 'disagree'
            ? formState.decisionReason.trim()
            : '',
      },
      followUpPlan: {
        nextScreening: formState.nextScreening,
        careAction: formState.careAction,
        additionalSupport: formState.additionalSupport,
      },
    };

    const result = await reviewSubmitter({ payload });
    setIsSaving(false);

    if (!result?.ok) {
      setSaveError(
        result?.message ||
          'Unable to persist clinical review right now. Your entered notes are preserved — please retry.'
      );
      return;
    }

    const saved = saveFinalClinicalReview({
      ...payload,
      persistenceMode: result.persistenceMode || 'local',
    });

    setConfirmModalOpen(false);
    setStatusMessage(
      `Clinical review finalized for ${activeMother.id} (${activeScreening.id}) at ${saved.finalizedAt}. ${
        result.persistenceMode === 'remote'
          ? 'Persisted to backend EHR.'
          : 'Saved in local clinical session.'
      }`
    );
  };

  const handleBackToInsights = () => {
    if (activeMother?.id) {
      saveReviewDraft(activeMother.id, {
        reviewNotes: formState.reviewNotes,
        clinicianRisk: formState.clinicianRisk,
        decision: formState.decision,
        decisionReason: formState.decisionReason,
        nextScreening: formState.nextScreening,
        careAction: formState.careAction,
        additionalSupport: formState.additionalSupport,
      });
      navigate(`/insights/${activeMother.id}`);
    } else {
      navigate('/insights');
    }
  };

  const handleOpenFullResults = () => {
    setPreviousModalOpen(false);
    if (activeMother?.id) {
      navigate(`/results/${activeMother.id}`);
    } else {
      navigate('/results');
    }
  };

  if (requestedMotherId && !activeMother) {
    return (
      <div className="miora-command-shell">
        <div className="miora-command-frame">
          <section className="miora-card miora-results-empty-state">
            <h2>Mother Case Not Found</h2>
            <p>
              No mother record was found for Mother ID <strong>{requestedMotherId}</strong>.
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
                onClick={() => navigate('/clinical-review')}
              >
                Open Default Case
              </button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const isReviewedForCurrentSession = Boolean(
    savedReview && activeScreening && savedReview.screeningId === activeScreening.id
  );

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
            <linearGradient id="clinicalReviewWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#clinicalReviewWaveGrad)"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="clinical-review-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>CLINICAL REVIEW</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="clinical-review-heading" className="miora-dash-title">
              Clinical Review &amp; <em>Assessment</em>
            </h1>
            <p className="miora-dash-subtitle">
              Review AI insights, record clinical assessment and finalize the care plan.
            </p>
          </div>

          <div className="miora-results-header-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setPreviousModalOpen(true)}
            >
              <DashboardIcon name="clock" size={15} />
              <span>Previous Results</span>
            </button>
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => setExportModalOpen(true)}
              disabled={!summary}
            >
              <DashboardIcon name="download" size={15} />
              <span>Export Clinical Note</span>
            </button>
          </div>
        </section>

        {/* Patient Information Strip */}
        {activeMother && (
          <section
            className="miora-card miora-patient-strip miora-review-strip"
            aria-label="Clinical review patient summary"
          >
            <div className="miora-patient-item">
              <span className="miora-patient-icon" aria-hidden="true">
                <DashboardIcon name="user" size={18} />
              </span>
              <div className="miora-patient-meta">
                <div className="miora-patient-select-row">
                  <label htmlFor="clinical-review-mother-select" className="sr-only">
                    Select mother for clinical review
                  </label>
                  <select
                    id="clinical-review-mother-select"
                    className="miora-patient-id-select"
                    value={activeMother.id}
                    onChange={(e) => handleSelectMother(e.target.value)}
                  >
                    {mothers.slice(0, 12).map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.id}
                      </option>
                    ))}
                  </select>
                  <Link
                    to={`/mothers/${activeMother.id}`}
                    className="miora-disc-record-link"
                    title={`Open Mother Record ${activeMother.id}`}
                  >
                    <span>Record</span>
                    <DashboardIcon name="externalLink" size={12} />
                  </Link>
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
                <RiskBadge risk={summary ? summary.aiRiskLevel : activeMother.risk} />
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="bolt" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Discordance</span>
                <RiskBadge
                  risk={
                    summary
                      ? summary.discordanceBadgeLabel
                      : activeMother.discordanceFlag
                        ? 'High'
                        : 'Low'
                  }
                />
              </div>
            </div>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-patient-item">
              <span className="miora-patient-icon is-plain" aria-hidden="true">
                <DashboardIcon name="clock" size={18} />
              </span>
              <div className="miora-patient-meta">
                <span className="miora-patient-label">Screening Date</span>
                <strong>{summary?.screeningDateShort || activeMother.lastScreeningDate}</strong>
              </div>
            </div>

            <div className="miora-results-status-wrap">
              <span className="miora-results-status-pill is-completed">
                <DashboardIcon name="checkCircle" size={15} strokeWidth={1.8} />
                <span>
                  {isReviewedForCurrentSession
                    ? 'Clinical Review Finalized'
                    : 'Under Clinical Review'}
                </span>
              </span>
            </div>
          </section>
        )}

        {/* Unavailable State if Mother Has No Screening Record Yet */}
        {activeMother && !summary && (
          <section className="miora-card miora-results-empty-state">
            <h2>No Completed Screening Available Yet</h2>
            <p>
              Mother <strong>{activeMother.id}</strong> has not completed a multimodal screening
              session yet. Complete a screening session before finalizing a clinical review.
            </p>
            <div className="miora-modal-actions">
              <button
                type="button"
                className="miora-cta-primary"
                onClick={() => navigate(`/live-screening?mother=${activeMother.id}`)}
              >
                Start Screening Session
              </button>
            </div>
          </section>
        )}

        {/* Row 1: AI Screening Summary | Key Evidence | Clinical Assessment */}
        {summary && (
          <div className="miora-review-row-3">
            <AIScreeningSummaryCard summaryRows={summary.summaryRows} />
            <KeyEvidenceCard evidenceItems={summary.evidenceItems} />
            <ClinicalAssessmentCard
              reviewNotes={formState.reviewNotes}
              clinicianRisk={formState.clinicianRisk}
              onChangeNotes={(val) => {
                setValidationErrors((e) => ({ ...e, reviewNotes: undefined }));
                updateFormField({ reviewNotes: val });
              }}
              onChangeRisk={(val) => {
                setValidationErrors((e) => ({ ...e, clinicianRisk: undefined }));
                updateFormField({ clinicianRisk: val });
              }}
              validationErrors={validationErrors}
            />
          </div>
        )}

        {/* Row 2: Comparison: AI vs Clinician | Clinical Decision | Follow-up & Care Plan */}
        {summary && (
          <div className="miora-review-row-3">
            <ComparisonCard summary={summary} clinicianRisk={formState.clinicianRisk} />
            <ClinicalDecisionCard
              decision={formState.decision}
              decisionReason={formState.decisionReason}
              onChangeDecision={(val) => {
                setValidationErrors((e) => ({
                  ...e,
                  decision: undefined,
                  decisionReason: undefined,
                }));
                updateFormField({ decision: val });
              }}
              onChangeDecisionReason={(val) => {
                setValidationErrors((e) => ({ ...e, decisionReason: undefined }));
                updateFormField({ decisionReason: val });
              }}
              validationErrors={validationErrors}
            />
            <FollowUpCarePlanCard
              nextScreening={formState.nextScreening}
              careAction={formState.careAction}
              additionalSupport={formState.additionalSupport}
              onChangeNextScreening={(val) => updateFormField({ nextScreening: val })}
              onChangeCareAction={(val) => updateFormField({ careAction: val })}
              onChangeAdditionalSupport={(val) => updateFormField({ additionalSupport: val })}
              validationErrors={validationErrors}
            />
          </div>
        )}

        {/* Validation Summary Banner if Incomplete on Submit */}
        {Object.values(validationErrors).some(Boolean) && (
          <div className="miora-form-error miora-review-banner-alert" role="alert">
            Please complete all required clinical review fields (Clinician&apos;s Review notes,
            Clinical Risk selection, Clinical Decision, and rationale if partially agreeing or
            disagreeing) before finalizing.
          </div>
        )}

        {/* Bottom Finalization Action Bar */}
        {summary && (
          <section
            className="miora-card miora-review-finalize-bar"
            aria-labelledby="finalize-review-title"
          >
            <button
              type="button"
              className="miora-btn-secondary miora-review-back-btn"
              onClick={handleBackToInsights}
            >
              <DashboardIcon name="arrowLeft" size={16} />
              <span>Back to Insights &amp; Care</span>
            </button>

            <span className="miora-patient-divider" aria-hidden="true" />

            <div className="miora-review-finalize-copy">
              <div className="miora-review-finalize-heading">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="shieldCheck" size={20} strokeWidth={1.7} />
                </span>
                <h2 id="finalize-review-title">Finalize Review</h2>
              </div>
              <p>
                Confirm the clinical assessment and update the care plan for continued support and
                monitoring.
              </p>
            </div>

            <button
              type="button"
              className="miora-cta-primary miora-review-finalize-btn"
              onClick={handleOpenFinalizeConfirm}
            >
              <span>Finalize &amp; Save</span>
              <DashboardIcon name="check" size={16} strokeWidth={2.2} />
            </button>
          </section>
        )}

        {statusMessage && (
          <div className="miora-live-feedback-row miora-results-feedback">
            <div className="miora-draft-pill" role="status">
              <DashboardIcon name="check" size={14} />
              <span>{statusMessage}</span>
            </div>
          </div>
        )}
      </div>

      <PreviousResultsModal
        isOpen={previousModalOpen}
        onClose={() => setPreviousModalOpen(false)}
        mother={activeMother}
        motherScreenings={motherScreenings}
        reviewHistory={reviewHistory}
        onOpenFullResults={handleOpenFullResults}
      />

      <ExportClinicalNoteModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        mother={activeMother}
        screening={activeScreening}
        summary={summary}
        savedReview={savedReview}
        draftReview={formState}
      />

      <FinalizeConfirmationModal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        onConfirm={handleConfirmSave}
        mother={activeMother}
        summary={summary}
        clinicianRisk={formState.clinicianRisk}
        decision={formState.decision}
        decisionReason={formState.decisionReason}
        nextScreening={formState.nextScreening}
        careAction={formState.careAction}
        additionalSupport={formState.additionalSupport}
        isSaving={isSaving}
        saveError={saveError}
      />
    </div>
  );
}
