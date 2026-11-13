import React, { useEffect, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import {
  buildClinicalNotePdfBlob,
  buildClinicalNoteText,
  formatClinicalDecisionLabel,
} from '../utils/clinicalReviewHelpers.js';

export function PreviousResultsModal({
  isOpen,
  onClose,
  mother,
  motherScreenings,
  reviewHistory,
  onOpenFullResults,
}) {
  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !mother) return null;

  const latestScreening = motherScreenings[0] || null;
  const historicalTrend = latestScreening?.riskHistory || [];

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="previous-results-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="clock" size={20} />
            </span>
            <div>
              <h2 id="previous-results-modal-title">
                Previous Results &amp; Review History · {mother.id}
              </h2>
              <p>
                Compare historical AI screening indicators and prior independent clinician
                assessments. Current unsaved review drafts remain preserved.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close previous results modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <div className="miora-review-history-stack">
          <div className="miora-review-history-section">
            <h3>Recorded Screening Sessions ({motherScreenings.length})</h3>
            {motherScreenings.length > 0 ? (
              <ul className="miora-review-history-list">
                {motherScreenings.map((item) => (
                  <li key={item.id} className="miora-review-history-row">
                    <div>
                      <strong>
                        {item.id} · {item.modality}
                      </strong>
                      <span>
                        {item.screeningDateTime || item.completedAgo} · Week {item.postpartumWeek}
                      </span>
                    </div>
                    <span className="miora-review-history-badge">
                      AI: {item.risk}{' '}
                      {typeof item.combinedScore === 'number'
                        ? `(${item.combinedScore.toFixed(2)})`
                        : '(Pending)'}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="miora-review-helper-caption">
                No previous screening sessions recorded for this mother yet.
              </p>
            )}
          </div>

          {historicalTrend.length > 0 && (
            <div className="miora-review-history-section">
              <h3>Longitudinal AI Risk Trend</h3>
              <ul className="miora-review-trend-pills">
                {historicalTrend.map((point) => (
                  <li key={`${point.week}-${point.score}`} className="miora-review-trend-pill">
                    <span>{point.week}</span>
                    <strong>
                      {point.label} ({Number(point.score).toFixed(2)})
                    </strong>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="miora-review-history-section">
            <h3>Saved Clinician Assessments ({reviewHistory.length})</h3>
            {reviewHistory.length > 0 ? (
              <ul className="miora-review-history-list">
                {reviewHistory.map((rev) => (
                  <li key={rev.id} className="miora-review-history-row">
                    <div>
                      <strong>
                        Clinician Risk: {rev.clinicianAssessment.risk} ·{' '}
                        {formatClinicalDecisionLabel(rev.clinicianAssessment.decision)}
                      </strong>
                      <span>
                        {rev.screeningId} · Finalized at {rev.finalizedAt}
                      </span>
                      <p>{rev.clinicianAssessment.reviewNotes}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="miora-review-helper-caption">
                No prior clinician assessments saved yet for {mother.id}.
              </p>
            )}
          </div>
        </div>

        <div className="miora-modal-actions">
          <button type="button" className="miora-btn-secondary" onClick={onClose}>
            Back to Review
          </button>
          <button type="button" className="miora-cta-primary" onClick={onOpenFullResults}>
            <span>Open Full Screening Results</span>
            <DashboardIcon name="arrowRight" size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}

export function ExportClinicalNoteModal({
  isOpen,
  onClose,
  mother,
  screening,
  summary,
  savedReview,
  draftReview,
}) {
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !mother || !screening || !summary) return null;

  const noteText = buildClinicalNoteText({
    mother,
    screening,
    summary,
    savedReview,
    draftReview,
  });

  const triggerDownload = (blob, filename, message) => {
    setErrorMsg('');
    setStatusMsg('');
    try {
      if (typeof window === 'undefined' || typeof Blob === 'undefined' || !URL?.createObjectURL) {
        throw new Error('File export is unavailable in this browser environment.');
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setStatusMsg(message);
    } catch (err) {
      setErrorMsg(err?.message || 'Unable to export clinical note.');
    }
  };

  const handleDownloadPdf = () => {
    const blob = buildClinicalNotePdfBlob({
      mother,
      screening,
      summary,
      savedReview,
      draftReview,
    });
    triggerDownload(
      blob,
      `miora-clinical-note-${mother.id.toLowerCase()}-${screening.id.toLowerCase()}.pdf`,
      'Clinical note PDF downloaded successfully.'
    );
  };

  const handleDownloadText = () => {
    const blob = new Blob([noteText], { type: 'text/plain;charset=utf-8' });
    triggerDownload(
      blob,
      `miora-clinical-note-${mother.id.toLowerCase()}-${screening.id.toLowerCase()}.txt`,
      'Clinical note text summary downloaded.'
    );
  };

  const handlePrint = () => {
    setErrorMsg('');
    try {
      if (typeof window !== 'undefined' && window.print) {
        window.print();
      } else {
        throw new Error('Print is unavailable in this environment.');
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Unable to launch print preview.');
    }
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-clinical-note-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="download" size={20} />
            </span>
            <div>
              <h2 id="export-clinical-note-title">Export Clinical Note</h2>
              <p>
                Structured clinical review summary, independent assessment, and care plan for{' '}
                {mother.id} ({screening.id}).
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close export clinical note modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <pre className="miora-export-preview">{noteText}</pre>

        {errorMsg && (
          <div className="miora-form-error" role="alert">
            {errorMsg}
          </div>
        )}
        {statusMsg && (
          <div className="miora-draft-pill miora-modal-status-msg" role="status">
            <DashboardIcon name="check" size={14} />
            <span>{statusMsg}</span>
          </div>
        )}

        <div className="miora-modal-actions">
          <button type="button" className="miora-btn-secondary" onClick={handlePrint}>
            Print
          </button>
          <button type="button" className="miora-btn-secondary" onClick={handleDownloadText}>
            Download Text
          </button>
          <button type="button" className="miora-cta-primary" onClick={handleDownloadPdf}>
            Download PDF Note
          </button>
        </div>
      </div>
    </div>
  );
}

export function FinalizeConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  mother,
  summary,
  clinicianRisk,
  decision,
  decisionReason,
  nextScreening,
  careAction,
  additionalSupport,
  isSaving,
  saveError,
}) {
  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen && !isSaving) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, isSaving, onClose]);

  if (!isOpen || !mother || !summary) return null;

  return (
    <div
      className="miora-modal-backdrop"
      role="presentation"
      onClick={() => !isSaving && onClose()}
    >
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-finalize-review-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="shieldCheck" size={20} />
            </span>
            <div>
              <h2 id="confirm-finalize-review-title">Confirm Clinical Review Finalization</h2>
              <p>
                Verify the independent clinician assessment and follow-up plan for {mother.id} (
                {mother.initials}). AI screening outputs remain preserved separately.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close confirmation modal"
            disabled={isSaving}
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <div className="miora-review-confirm-summary">
          <div>
            <span>AI Screening Risk (Preserved)</span>
            <strong>{summary.aiRisk}</strong>
          </div>
          <div>
            <span>Clinician Assessment Risk</span>
            <strong>{clinicianRisk} Risk</strong>
          </div>
          <div>
            <span>Clinical Decision</span>
            <strong>{formatClinicalDecisionLabel(decision)}</strong>
          </div>
          {decisionReason?.trim() && (
            <div>
              <span>Decision Rationale</span>
              <strong>{decisionReason.trim()}</strong>
            </div>
          )}
          <div>
            <span>Follow-up &amp; Care Plan</span>
            <strong>
              {nextScreening} · {careAction} · {additionalSupport}
            </strong>
          </div>
        </div>

        {saveError && (
          <div className="miora-form-error" role="alert">
            {saveError}
          </div>
        )}

        <div className="miora-modal-actions">
          <button
            type="button"
            className="miora-btn-secondary"
            disabled={isSaving}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="miora-cta-primary"
            disabled={isSaving}
            onClick={onConfirm}
          >
            {isSaving ? 'Saving Review...' : saveError ? 'Retry Save' : 'Confirm Finalize & Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

