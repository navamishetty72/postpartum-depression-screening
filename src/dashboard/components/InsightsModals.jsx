import React, { useEffect, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { buildCarePlanPdfBlob, formatCarePlanLines } from '../utils/carePlanPdf.js';

export function ScheduleFollowUpModal({ isOpen, onClose, motherId, onSave }) {
  const defaultDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const [date, setDate] = useState(defaultDate);
  const [type, setType] = useState('Follow-up screening');
  const [clinician, setClinician] = useState('Dr. Elena Rostova');
  const [description, setDescription] = useState(
    'Reassess maternal emotional wellbeing and review screening cues.'
  );
  const [error, setError] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!date || !description.trim()) {
      setError('Please select a date and provide a follow-up description.');
      return;
    }
    const formattedDate = new Date(`${date}T12:00:00`).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
    onSave({
      date: formattedDate,
      type,
      clinician,
      description: description.trim(),
    });
    setError('');
    onClose();
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="schedule-followup-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="calendar" size={20} />
            </span>
            <div>
              <h2 id="schedule-followup-title">Schedule Follow-up</h2>
              <p>Add a follow-up milestone to {motherId}&apos;s care timeline.</p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close schedule modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <form className="miora-modal-form" onSubmit={handleSubmit}>
          <div className="miora-field-row">
            <label className="miora-field">
              <span>Follow-up Date</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </label>

            <label className="miora-field">
              <span>Follow-up Type</span>
              <select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="Follow-up screening">Follow-up screening</option>
                <option value="Clinical review">Clinical review</option>
                <option value="Counselling check-in">Counselling check-in</option>
                <option value="Re-evaluation">Re-evaluation</option>
              </select>
            </label>
          </div>

          <label className="miora-field">
            <span>Responsible Clinician</span>
            <select value={clinician} onChange={(e) => setClinician(e.target.value)}>
              <option value="Dr. Elena Rostova">Dr. Elena Rostova (Perinatal Psychiatry)</option>
              <option value="Assigned OB/GYN Clinician">Assigned OB/GYN Clinician</option>
              <option value="Postpartum Care Coordinator">Postpartum Care Coordinator</option>
            </select>
          </label>

          <label className="miora-field">
            <span>Follow-up Focus / Description</span>
            <textarea
              rows="2"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </label>

          {error && (
            <div className="miora-live-alert" role="alert">
              {error}
            </div>
          )}

          <div className="miora-modal-actions">
            <button type="button" className="miora-btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="miora-cta-primary">
              Save Appointment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function CarePlanPdfModal({ isOpen, onClose, carePlanDoc }) {
  const [includeNotes, setIncludeNotes] = useState(true);
  const [pdfStatus, setPdfStatus] = useState('');
  const [pdfError, setPdfError] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !carePlanDoc) return null;

  const docWithPrivacy = { ...carePlanDoc, includeNotes };
  const previewText = formatCarePlanLines(docWithPrivacy).join('\n');

  const handleDownloadPdf = () => {
    setPdfError('');
    setPdfStatus('');
    try {
      if (typeof window === 'undefined' || typeof Blob === 'undefined' || !URL?.createObjectURL) {
        throw new Error('PDF download is unavailable in this browser.');
      }
      const blob = buildCarePlanPdfBlob(docWithPrivacy);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `miora-care-plan-${carePlanDoc.mother.id.toLowerCase()}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setPdfStatus('Care Plan PDF downloaded.');
    } catch (err) {
      setPdfError(err?.message || 'Failed to generate Care Plan PDF.');
    }
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog miora-report-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="careplan-pdf-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="download" size={20} />
            </span>
            <div>
              <h2 id="careplan-pdf-title">Care Plan PDF Export</h2>
              <p>
                {carePlanDoc.mother.id} ({carePlanDoc.mother.initials}) · Generated {carePlanDoc.generatedDate}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close Care Plan PDF modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <label className="miora-checkbox-field miora-pdf-privacy-check">
          <input
            type="checkbox"
            checked={includeNotes}
            onChange={(e) => setIncludeNotes(e.target.checked)}
          />
          <span>Include Care Team Notes in exported PDF (authorized access)</span>
        </label>

        <pre className="miora-report-preview">{previewText}</pre>

        {pdfError && (
          <div className="miora-live-alert" role="alert">
            {pdfError}
          </div>
        )}
        {pdfStatus && (
          <div className="miora-draft-pill" role="status">
            <DashboardIcon name="check" size={14} />
            <span>{pdfStatus}</span>
          </div>
        )}

        <div className="miora-modal-actions">
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => window.print && window.print()}
          >
            Print View
          </button>
          <button type="button" className="miora-cta-primary" onClick={handleDownloadPdf}>
            <DashboardIcon name="download" size={15} />
            <span>Download Care Plan (.pdf)</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export function RecommendationDetailModal({
  recommendation,
  included,
  onToggleInclude,
  onClose,
}) {
  if (!recommendation) return null;

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rec-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name={recommendation.icon} size={20} />
            </span>
            <div>
              <h2 id="rec-detail-title">{recommendation.title}</h2>
              <p>Clinician-reviewed postpartum care pathway guidance</p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close recommendation details"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <div className="miora-detail-notes">
          <div>
            <h4>Clinical Guidance</h4>
            <p>{recommendation.guidance}</p>
          </div>
          <div>
            <h4>Safety Note</h4>
            <p>
              Supportive guidance only; adapt or override based on direct clinical evaluation and mother preferences.
            </p>
          </div>
        </div>

        <div className="miora-modal-actions">
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => onToggleInclude(recommendation.id)}
          >
            {included ? 'Remove from Care Plan' : 'Include in Care Plan'}
          </button>
          <button type="button" className="miora-cta-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

const VERIFIED_RESOURCES = {
  coping: {
    title: 'Coping Strategies',
    subtitle: 'Evidence-informed grounding and postpartum self-regulation practices',
    items: [
      {
        heading: 'Paced Breathing & Evening Decompression',
        body: 'Slow 4-6 breathing cycles during feeding transitions to lower acute autonomic tension.',
      },
      {
        heading: 'Micro-Rest & Shared Care Blocks',
        body: 'Coordinate one uninterrupted 4-hour restorative sleep window with a partner or support person when possible.',
      },
    ],
  },
  groups: {
    title: 'Support Groups',
    subtitle: 'Verified maternal mental health peer support & hotlines',
    items: [
      {
        heading: 'Postpartum Support International (PSI) — 1-800-944-4773',
        body: 'Free, confidential peer support groups, local coordinator matching, and specialist referrals.',
      },
      {
        heading: 'National Maternal Mental Health Hotline — 1-833-TLC-MAMA (1-833-852-6262)',
        body: '24/7 confidential voice and text support in English and Spanish.',
      },
      {
        heading: '988 Suicide & Crisis Lifeline — Call or Text 988',
        body: 'Immediate 24/7 clinical crisis escalation support if urgent distress arises.',
      },
    ],
  },
  education: {
    title: 'Educational Resources',
    subtitle: 'Accessible postpartum emotional wellbeing education',
    items: [
      {
        heading: 'Understanding Postpartum Emotional Shifts',
        body: 'Distinguishing transient baby blues (weeks 1–2) from persistent mood or anxiety changes requiring clinical review.',
      },
      {
        heading: 'Partner & Family Support Guide',
        body: 'Practical ways family members can notice fatigue or overwhelm early and encourage gentle care check-ins.',
      },
    ],
  },
};

export function SupportResourceModal({ resourceKey, onClose }) {
  if (!resourceKey || !VERIFIED_RESOURCES[resourceKey]) return null;
  const info = VERIFIED_RESOURCES[resourceKey];

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-res-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="bookOpen" size={20} />
            </span>
            <div>
              <h2 id="support-res-detail-title">{info.title}</h2>
              <p>{info.subtitle}</p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close resource modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <ul className="miora-support-resource-list">
          {info.items.map((item) => (
            <li key={item.heading} className="miora-support-resource-item">
              <strong>{item.heading}</strong>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>

        <div className="miora-modal-actions">
          <button type="button" className="miora-cta-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

