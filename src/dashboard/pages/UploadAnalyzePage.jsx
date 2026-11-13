import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';

export function UploadAnalyzePage() {
  const { mothers, recordScreening } = useClinicalData();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialMother = searchParams.get('mother') || 'M-108';
  const [motherId, setMotherId] = useState(initialMother);
  const [selectedFileName, setSelectedFileName] = useState('');
  const [notes, setNotes] = useState('');
  const [consentChecked, setConsentChecked] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!consentChecked || (!selectedFileName && !notes.trim())) return;
    const created = recordScreening({
      motherId,
      risk: 'Moderate',
      modality: 'Uploaded Media + Notes',
      summary: notes.trim() || `Uploaded screening media (${selectedFileName}) queued for analysis.`,
      epdsEquivalent: 9,
      discordanceDetected: false,
      capturedModalities: {
        text: Boolean(notes.trim()),
        voice: Boolean(selectedFileName),
        video: false,
      },
    });
    navigate(`/results/${created.motherId}`);
  };

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <svg
          className="miora-header-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="uploadWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#uploadWaveGrad)"
          />
        </svg>

        <section className="miora-dash-header">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>UPLOAD &amp; ANALYZE</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title">
              Asynchronous Screening <em>Upload</em>
            </h1>
            <p className="miora-dash-subtitle">
              Upload recorded voice, video, or written reflections when a live consultation is not active.
            </p>
          </div>
        </section>

        <div className="miora-mode-switch" role="tablist" aria-label="Screening mode selector">
          <button
            type="button"
            role="tab"
            aria-selected={false}
            className="miora-mode-tab"
            onClick={() => navigate(`/live-screening?mother=${motherId}`)}
          >
            <DashboardIcon name="video" size={16} />
            <span>Live Screening</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={true}
            className="miora-mode-tab is-active"
          >
            <DashboardIcon name="upload" size={16} />
            <span>Upload &amp; Analyze</span>
          </button>
        </div>

        <form className="miora-card miora-screening-form" onSubmit={handleSubmit}>
          <label className="miora-field">
            <span>Mother Profile</span>
            <select value={motherId} onChange={(e) => setMotherId(e.target.value)}>
              {mothers.slice(0, 20).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} — {m.initials} (Week {m.postpartumWeek})
                </option>
              ))}
            </select>
          </label>

          <label className="miora-field">
            <span>Audio / Video Recording File</span>
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={(e) => setSelectedFileName(e.target.files?.[0]?.name || '')}
            />
          </label>

          <label className="miora-field">
            <span>Written Reflection / Transcript Notes</span>
            <textarea
              rows="4"
              placeholder="Paste mother's written check-in notes or session observations..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>

          <label className="miora-checkbox-field">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
            />
            <span>Mother consent confirmed for asynchronous multimodal analysis</span>
          </label>

          <div className="miora-modal-actions">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={() => navigate('/live-screening')}
            >
              Switch to Live Screening
            </button>
            <button
              type="submit"
              className="miora-cta-primary"
              disabled={!consentChecked || (!selectedFileName && !notes.trim())}
            >
              Submit for Analysis
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

