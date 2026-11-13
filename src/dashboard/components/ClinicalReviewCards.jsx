import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import {
  ADDITIONAL_SUPPORT_OPTIONS,
  CARE_ACTION_OPTIONS,
  NEXT_SCREENING_OPTIONS,
  getAssessmentComparison,
} from '../utils/clinicalReviewHelpers.js';

function toneClass(tone) {
  if (tone === 'high') return 'is-high';
  if (tone === 'moderate') return 'is-moderate';
  if (tone === 'low') return 'is-low';
  return 'is-muted';
}

export function AIScreeningSummaryCard({ summaryRows }) {
  return (
    <section
      className="miora-card miora-review-card"
      aria-labelledby="ai-screening-summary-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="sparkle" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="ai-screening-summary-title" className="miora-card-title">
            AI Screening Summary
          </h2>
        </div>
      </div>

      <div className="miora-review-summary-list">
        {summaryRows.map((row) => (
          <div key={row.key} className="miora-review-summary-row">
            <div className="miora-review-summary-left">
              <span className="miora-modality-mini-badge" aria-hidden="true">
                <DashboardIcon name={row.icon} size={15} strokeWidth={1.7} />
              </span>
              <span className="miora-review-summary-label">{row.label}</span>
            </div>
            <span className={`miora-review-score-pill ${toneClass(row.tone)}`}>
              {row.value}
            </span>
          </div>
        ))}
      </div>

      <p className="miora-review-helper-caption">
        Screening indicator scores only; not diagnostic probabilities.
      </p>
    </section>
  );
}

export function KeyEvidenceCard({ evidenceItems }) {
  return (
    <section className="miora-card miora-review-card" aria-labelledby="key-evidence-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="barChart" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="key-evidence-title" className="miora-card-title">
            Key Evidence
          </h2>
        </div>
      </div>

      <div className="miora-review-evidence-list">
        {evidenceItems.map((item) => (
          <article
            key={item.key}
            className={`miora-review-evidence-item ${!item.available ? 'is-unavailable' : ''}`}
          >
            <span className="miora-review-evidence-icon" aria-hidden="true">
              <DashboardIcon name={item.icon} size={17} strokeWidth={1.65} />
            </span>
            <div className="miora-review-evidence-copy">
              <div className="miora-review-evidence-top">
                <strong>{item.label}:</strong>
                <span className="miora-review-evidence-meta">{item.meta}</span>
              </div>
              <p>{item.description}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

const CLINICIAN_RISK_OPTIONS = [
  { value: 'Low', dotTone: 'low' },
  { value: 'Moderate', dotTone: 'moderate' },
  { value: 'High', dotTone: 'high' },
];

export function ClinicalAssessmentCard({
  reviewNotes,
  clinicianRisk,
  onChangeNotes,
  onChangeRisk,
  validationErrors,
}) {
  return (
    <section
      className="miora-card miora-review-card"
      aria-labelledby="clinical-assessment-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="clipboardList" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="clinical-assessment-title" className="miora-card-title">
            Clinical Assessment
          </h2>
        </div>
      </div>

      <div className="miora-review-form-group">
        <label htmlFor="clinician-review-textarea" className="miora-review-field-label">
          <span>
            Clinician&apos;s Review <span className="miora-required-star">*</span>
          </span>
        </label>
        <div className="miora-review-textarea-wrap">
          <textarea
            id="clinician-review-textarea"
            rows={4}
            maxLength={500}
            className="miora-review-textarea"
            placeholder="Record your clinical impression, key observations and context..."
            value={reviewNotes}
            onChange={(e) => onChangeNotes(e.target.value)}
            aria-invalid={Boolean(validationErrors?.reviewNotes)}
          />
          <span className="miora-review-char-count" aria-live="polite">
            {reviewNotes.length} / 500
          </span>
        </div>
        {validationErrors?.reviewNotes && (
          <p className="miora-review-field-err" role="alert">
            {validationErrors.reviewNotes}
          </p>
        )}
      </div>

      <fieldset className="miora-review-risk-fieldset">
        <legend className="miora-review-field-label">
          Clinical Risk (Clinician) <span className="miora-required-star">*</span>
        </legend>
        <div className="miora-review-risk-options">
          {CLINICIAN_RISK_OPTIONS.map((opt) => {
            const isSelected = clinicianRisk === opt.value;
            return (
              <label
                key={opt.value}
                className={`miora-review-risk-option is-${opt.dotTone} ${
                  isSelected ? 'is-selected' : ''
                }`}
              >
                <input
                  type="radio"
                  name="clinician-risk"
                  value={opt.value}
                  checked={isSelected}
                  onChange={() => onChangeRisk(opt.value)}
                />
                <span className={`miora-review-radio-circle is-${opt.dotTone}`} aria-hidden="true">
                  {isSelected && <span className="miora-review-radio-dot" />}
                </span>
                <span>{opt.value}</span>
              </label>
            );
          })}
        </div>
        {validationErrors?.clinicianRisk && (
          <p className="miora-review-field-err" role="alert">
            {validationErrors.clinicianRisk}
          </p>
        )}
      </fieldset>
    </section>
  );
}

export function ComparisonCard({ summary, clinicianRisk }) {
  const comparison = getAssessmentComparison({
    aiRiskLevel: summary.aiRiskLevel,
    aiAvailable: summary.combinedScore !== null,
    clinicianRisk,
  });

  return (
    <section
      className="miora-card miora-review-card"
      aria-labelledby="comparison-ai-clinician-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="scale" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="comparison-ai-clinician-title" className="miora-card-title">
            Comparison: AI vs Clinician
          </h2>
        </div>
      </div>

      <div className="miora-review-compare-grid">
        <div className="miora-review-compare-box is-ai">
          <span className="miora-review-compare-caption">AI Assessment</span>
          <strong>{summary.aiRisk}</strong>
          <small>
            {summary.combinedScore !== null
              ? `(${summary.combinedScore.toFixed(2)})`
              : '(Pending)'}
          </small>
        </div>

        <span className="miora-review-compare-arrow" aria-hidden="true">
          ↔
        </span>

        <div
          className={`miora-review-compare-box ${
            clinicianRisk ? 'is-clinician' : 'is-pending'
          }`}
        >
          <span className="miora-review-compare-caption">Clinician Assessment</span>
          <strong>{clinicianRisk ? `${clinicianRisk} Risk` : 'Pending Selection'}</strong>
          <small>{clinicianRisk ? 'Independent clinician rating' : 'Awaiting input'}</small>
        </div>
      </div>

      <div className={`miora-review-compare-status is-${comparison.status}`}>
        <span className="miora-review-compare-badge">{comparison.label}</span>
        <p>{comparison.description}</p>
      </div>
    </section>
  );
}

const DECISION_OPTIONS = [
  { value: 'agree', label: 'Agree with AI assessment' },
  { value: 'partial', label: 'Partially agree (with notes)' },
  { value: 'disagree', label: 'Do not agree (specify reason)' },
];

export function ClinicalDecisionCard({
  decision,
  decisionReason,
  onChangeDecision,
  onChangeDecisionReason,
  validationErrors,
}) {
  const requiresReason = decision === 'partial' || decision === 'disagree';

  return (
    <section
      className="miora-card miora-review-card"
      aria-labelledby="clinical-decision-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="target" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="clinical-decision-title" className="miora-card-title">
            Clinical Decision
          </h2>
        </div>
      </div>

      <fieldset className="miora-review-decision-fieldset">
        <legend className="sr-only">Clinical decision relative to AI assessment</legend>
        <div className="miora-review-decision-list">
          {DECISION_OPTIONS.map((opt) => {
            const checked = decision === opt.value;
            return (
              <label
                key={opt.value}
                className={`miora-review-decision-option ${checked ? 'is-checked' : ''}`}
              >
                <input
                  type="radio"
                  name="clinical-decision"
                  value={opt.value}
                  checked={checked}
                  onChange={() => onChangeDecision(opt.value)}
                />
                <span className="miora-review-check-box" aria-hidden="true">
                  {checked && <DashboardIcon name="check" size={13} strokeWidth={2.4} />}
                </span>
                <span>{opt.label}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {validationErrors?.decision && (
        <p className="miora-review-field-err" role="alert">
          {validationErrors.decision}
        </p>
      )}

      {requiresReason && (
        <div className="miora-review-reason-wrap">
          <label htmlFor="decision-reason-input" className="miora-review-field-label">
            <span>
              {decision === 'disagree' ? 'Disagreement Reason' : 'Notes on Partial Agreement'}{' '}
              <span className="miora-required-star">*</span>
            </span>
          </label>
          <textarea
            id="decision-reason-input"
            rows={2}
            maxLength={350}
            className="miora-review-textarea is-compact"
            placeholder={
              decision === 'disagree'
                ? 'Specify why your independent clinical decision differs from AI screening...'
                : 'Note points of agreement and divergence with AI indicators...'
            }
            value={decisionReason}
            onChange={(e) => onChangeDecisionReason(e.target.value)}
            aria-invalid={Boolean(validationErrors?.decisionReason)}
          />
          {validationErrors?.decisionReason && (
            <p className="miora-review-field-err" role="alert">
              {validationErrors.decisionReason}
            </p>
          )}
        </div>
      )}

      {decision === 'agree' && (
        <p className="miora-review-helper-caption">
          Clinician confirms alignment with AI screening indicators; original AI scores remain
          unchanged.
        </p>
      )}
    </section>
  );
}

export function FollowUpCarePlanCard({
  nextScreening,
  careAction,
  additionalSupport,
  onChangeNextScreening,
  onChangeCareAction,
  onChangeAdditionalSupport,
  validationErrors,
}) {
  return (
    <section
      className="miora-card miora-review-card"
      aria-labelledby="followup-careplan-title"
    >
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="calendar" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="followup-careplan-title" className="miora-card-title">
            Follow-up &amp; Care Plan
          </h2>
        </div>
      </div>

      <div className="miora-review-plan-rows">
        <div className="miora-review-plan-row">
          <label htmlFor="review-next-screening" className="miora-review-plan-label">
            <span className="miora-review-plan-icon" aria-hidden="true">
              <DashboardIcon name="checkSquare" size={16} strokeWidth={1.65} />
            </span>
            <span>Next Screening</span>
          </label>
          <select
            id="review-next-screening"
            className="miora-review-select"
            value={nextScreening}
            onChange={(e) => onChangeNextScreening(e.target.value)}
          >
            {NEXT_SCREENING_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <div className="miora-review-plan-row">
          <label htmlFor="review-care-action" className="miora-review-plan-label">
            <span className="miora-review-plan-icon" aria-hidden="true">
              <DashboardIcon name="heart" size={16} strokeWidth={1.65} />
            </span>
            <span>Care Action</span>
          </label>
          <select
            id="review-care-action"
            className="miora-review-select"
            value={careAction}
            onChange={(e) => onChangeCareAction(e.target.value)}
          >
            {CARE_ACTION_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <div className="miora-review-plan-row">
          <label htmlFor="review-additional-support" className="miora-review-plan-label">
            <span className="miora-review-plan-icon" aria-hidden="true">
              <DashboardIcon name="users" size={16} strokeWidth={1.65} />
            </span>
            <span>Additional Support</span>
          </label>
          <select
            id="review-additional-support"
            className="miora-review-select"
            value={additionalSupport}
            onChange={(e) => onChangeAdditionalSupport(e.target.value)}
          >
            {ADDITIONAL_SUPPORT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      </div>

      {validationErrors?.followUpPlan && (
        <p className="miora-review-field-err" role="alert">
          {validationErrors.followUpPlan}
        </p>
      )}

      <p className="miora-review-helper-caption">
        Editable care recommendations — clinicians retain full care plan authority.
      </p>
    </section>
  );
}

