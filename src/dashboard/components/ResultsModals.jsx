import React, { useEffect, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function buildScreeningReportText(screening, mother) {
  const lines = [
    'MIORA — MATERNAL SCREENING REPORT',
    '====================================',
    `Screening ID: ${screening.id}`,
    `Mother ID: ${screening.motherId} (${screening.motherInitials || mother?.initials || '—'})`,
    `Postpartum Week: Week ${screening.postpartumWeek}`,
    `Screening Date: ${screening.screeningDateTime || screening.completedAgo}`,
    `Screening Type: ${screening.modality}`,
    `Status: ${screening.status}`,
    '',
    'OVERALL ASSESSMENT (ASSISTIVE — NOT A DIAGNOSIS)',
    `Combined Risk Score: ${
      typeof screening.combinedScore === 'number'
        ? `${screening.combinedScore.toFixed(2)} / 1.00`
        : 'Pending / Unavailable'
    }`,
    `Risk Category: ${screening.risk} Risk`,
    '',
    'MODALITY-WISE OUTPUTS',
    `- Text (NLP): ${
      screening.modalities?.text?.status === 'completed'
        ? screening.modalities.text.score.toFixed(2)
        : screening.modalities?.text?.status || 'Unavailable'
    }`,
    `- Voice (Acoustic): ${
      screening.modalities?.voice?.status === 'completed'
        ? screening.modalities.voice.score.toFixed(2)
        : screening.modalities?.voice?.status || 'Unavailable'
    }`,
    `- Video (Facial): ${
      screening.modalities?.video?.status === 'completed'
        ? screening.modalities.video.score.toFixed(2)
        : screening.modalities?.video?.status || 'Unavailable'
    }`,
    '',
    'KEY CONTRIBUTING FACTORS',
    ...(screening.contributingFactors?.length
      ? screening.contributingFactors.map((f) => `- [${f.severity}] ${f.text}`)
      : ['- None reported for this session']),
    '',
    'INTERPRETATION & LIMITATIONS',
    ...(screening.interpretation || [screening.summary]).map((item) => `- ${item}`),
    `Limitations: ${screening.limitations || 'Assistive screening indicators require clinician confirmation.'}`,
  ];
  return lines.join('\n');
}

export function ExportReportModal({ isOpen, onClose, screening, mother }) {
  const [exportError, setExportError] = useState('');
  const [exportSuccess, setExportSuccess] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !screening) return null;

  const reportText = buildScreeningReportText(screening, mother);

  const handleDownload = () => {
    setExportError('');
    setExportSuccess('');
    try {
      if (typeof window === 'undefined' || typeof Blob === 'undefined' || !URL?.createObjectURL) {
        throw new Error('File download is unavailable in this browser environment.');
      }
      const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `miora-screening-${screening.motherId.toLowerCase()}-${screening.id.toLowerCase()}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExportSuccess('Report downloaded successfully.');
    } catch (err) {
      setExportError(err?.message || 'Unable to generate report file.');
    }
  };

  const handlePrint = () => {
    setExportError('');
    try {
      if (typeof window !== 'undefined' && window.print) {
        window.print();
      } else {
        throw new Error('Print is unavailable in this environment.');
      }
    } catch (err) {
      setExportError(err?.message || 'Unable to launch print preview.');
    }
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog miora-report-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-report-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="download" size={20} />
            </span>
            <div>
              <h2 id="export-report-title">Export Screening Report</h2>
              <p>
                {screening.id} · {screening.motherId} ({screening.motherInitials || mother?.initials})
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close export modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <pre className="miora-report-preview">{reportText}</pre>

        {exportError && (
          <div className="miora-live-alert" role="alert">
            {exportError}
          </div>
        )}
        {exportSuccess && (
          <div className="miora-draft-pill" role="status">
            <DashboardIcon name="check" size={14} />
            <span>{exportSuccess}</span>
          </div>
        )}

        <div className="miora-modal-actions">
          <button type="button" className="miora-btn-secondary" onClick={handlePrint}>
            Print / Save PDF
          </button>
          <button type="button" className="miora-cta-primary" onClick={handleDownload}>
            <DashboardIcon name="download" size={15} />
            <span>Download Report (.txt)</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export function ShareCaseModal({ isOpen, onClose, screening, onShare }) {
  const [recipientTeam, setRecipientTeam] = useState('Perinatal Psychiatry Team');
  const [note, setNote] = useState('');
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [sharedEntry, setSharedEntry] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !screening) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!consentConfirmed) {
      setError('Mother consent and clinical authorization are required to share this case.');
      return;
    }
    setError('');
    const entry = onShare({
      screeningId: screening.id,
      motherId: screening.motherId,
      recipientTeam,
      note,
      consentConfirmed,
    });
    setSharedEntry(entry);
  };

  const handleClose = () => {
    setSharedEntry(null);
    setError('');
    setConsentConfirmed(false);
    onClose();
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={handleClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-case-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="share" size={20} />
            </span>
            <div>
              <h2 id="share-case-title">Share Case Securely</h2>
              <p>
                Internal care-team handoff for {screening.motherId} (no public links generated).
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close share case modal"
            onClick={handleClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        {sharedEntry ? (
          <div className="miora-modal-success">
            <div className="miora-success-pill">
              <DashboardIcon name="check" size={16} />
              <span>Shared with {sharedEntry.recipientTeam}</span>
            </div>
            <p>
              Secure internal handoff logged at {sharedEntry.sharedAt} for screening{' '}
              {screening.id}. No external or public URLs were created.
            </p>
            <div className="miora-modal-actions">
              <button type="button" className="miora-cta-primary" onClick={handleClose}>
                Done
              </button>
            </div>
          </div>
        ) : (
          <form className="miora-modal-form" onSubmit={handleSubmit}>
            <label className="miora-field">
              <span>Care Team Recipient</span>
              <select
                value={recipientTeam}
                onChange={(e) => setRecipientTeam(e.target.value)}
              >
                <option value="Perinatal Psychiatry Team">Perinatal Psychiatry Team</option>
                <option value="Assigned OB/GYN Clinician">Assigned OB/GYN Clinician</option>
                <option value="Postpartum Care Coordinator">Postpartum Care Coordinator</option>
              </select>
            </label>

            <label className="miora-field">
              <span>Handoff Note (Optional)</span>
              <textarea
                rows="3"
                placeholder="e.g. Please review Week 2 voice-text indicators and schedule follow-up."
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>

            <label className="miora-checkbox-field" htmlFor="consent-confirmed">
              <input
                id="consent-confirmed"
                type="checkbox"
                checked={consentConfirmed}
                onChange={(e) => setConsentConfirmed(e.target.checked)}
              />
              <span>Confirm patient consent &amp; authorized care-team access</span>
            </label>

            {error && (
              <div className="miora-live-alert" role="alert">
                {error}
              </div>
            )}

            <div className="miora-modal-actions">
              <button type="button" className="miora-btn-secondary" onClick={handleClose}>
                Cancel
              </button>
              <button type="submit" className="miora-cta-primary">
                Send Internal Handoff
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export function SupportResourcesModal({ isOpen, onClose, motherId }) {
  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const resources = [
    {
      region: 'US · National Maternal Mental Health Hotline',
      name: '1-833-TLC-MAMA (1-833-852-6262)',
      desc: 'Free, confidential 24/7 support for pregnant and postpartum mothers.',
    },
    {
      region: 'US · Suicide & Crisis Lifeline',
      name: 'Call or Text 988',
      desc: 'Immediate 24/7 crisis counseling and emotional distress support.',
    },
    {
      region: 'International · Postpartum Support International',
      name: '1-800-944-4773 (4PPD)',
      desc: 'Peer support groups, care coordination, and specialist referrals.',
    },
    {
      region: 'India · Tele-MANAS',
      name: '14416 / 1800-891-4416',
      desc: '24/7 national tele-mental health support service.',
    },
  ];

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-resources-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="heart" size={20} />
            </span>
            <div>
              <h2 id="support-resources-title">Maternal Support Resources</h2>
              <p>Approved support helplines and care guides to share with {motherId}.</p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close support resources modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <ul className="miora-support-resource-list">
          {resources.map((item) => (
            <li key={item.name} className="miora-support-resource-item">
              <span>{item.region}</span>
              <strong>{item.name}</strong>
              <p>{item.desc}</p>
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

