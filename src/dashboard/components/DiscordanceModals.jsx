import React, { useEffect, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import {
  buildDiscordancePdfBlob,
  buildDiscordanceReportText,
} from '../utils/discordanceReportPdf.js';

export function DiscordanceExportModal({ isOpen, onClose, screening, mother, analysis, notes }) {
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !screening || !analysis) return null;

  const reportText = buildDiscordanceReportText({ screening, mother, analysis, notes });

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
      setErrorMsg(err?.message || 'Unable to export discordance report.');
    }
  };

  const handleDownloadPdf = () => {
    const blob = buildDiscordancePdfBlob({ screening, mother, analysis, notes });
    const filename = `miora-discordance-${screening.motherId.toLowerCase()}-${screening.id.toLowerCase()}.pdf`;
    triggerDownload(blob, filename, 'Discordance PDF report downloaded successfully.');
  };

  const handleDownloadText = () => {
    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const filename = `miora-discordance-${screening.motherId.toLowerCase()}-${screening.id.toLowerCase()}.txt`;
    triggerDownload(blob, filename, 'Discordance text summary downloaded.');
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
      setErrorMsg(err?.message || 'Unable to open print preview.');
    }
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="discordance-export-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="download" size={20} />
            </span>
            <div>
              <h2 id="discordance-export-title">Export Discordance Report</h2>
              <p>
                Structured cross-modal comparison, pairwise alignment, observations, and
                limitations for {screening.motherId} ({screening.id}).
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close discordance export modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <pre className="miora-export-preview">{reportText}</pre>

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
            Export PDF
          </button>
        </div>
      </div>
    </div>
  );
}

const NOTE_CATEGORIES = [
  'Contextual Observation',
  'Maternal Conversation Context',
  'Audio / Video Environment Note',
  'Follow-up Plan Note',
];

export function AddClinicalNoteModal({ isOpen, onClose, screening, onSaveNote }) {
  const [category, setCategory] = useState(NOTE_CATEGORIES[0]);
  const [noteText, setNoteText] = useState('');
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
    if (!noteText.trim()) {
      setError('Please enter a contextual clinical observation before saving.');
      return;
    }
    onSaveNote({
      motherId: screening.motherId,
      screeningId: screening.id,
      category,
      note: noteText.trim(),
    });
    setNoteText('');
    setError('');
    onClose();
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-note-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="fileText" size={20} />
            </span>
            <div>
              <h2 id="add-note-modal-title">Add Contextual Note</h2>
              <p>
                Associate clinician context with Mother {screening.motherId} · Session{' '}
                {screening.id}.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close note editor modal"
            onClick={onClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="miora-modal-form">
          <label className="miora-field-label">
            Note Focus
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {NOTE_CATEGORIES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="miora-field-label">
            Clinician Observation
            <textarea
              rows={4}
              placeholder="Document sleep context, psychosocial factors, recording environment, or maternal feedback..."
              value={noteText}
              onChange={(e) => {
                setNoteText(e.target.value);
                if (error) setError('');
              }}
            />
          </label>

          {error && (
            <div className="miora-form-error" role="alert">
              {error}
            </div>
          )}

          <div className="miora-modal-actions">
            <button type="button" className="miora-btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="miora-cta-primary">
              Save Note
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

