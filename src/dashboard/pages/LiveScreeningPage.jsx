import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';

export function LiveScreeningPage() {
  const { mothers, recordScreening } = useClinicalData();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialMother = searchParams.get('mother') || mothers[0]?.id || 'M-104';
  const initialMode = searchParams.get('mode') === 'text' ? 'Text Check-in' : 'Voice + Text';

  const [motherId, setMotherId] = useState(initialMother);
  const [modality, setModality] = useState(initialMode);
  const [epdsEquivalent, setEpdsEquivalent] = useState(8);
  const [discordanceDetected, setDiscordanceDetected] = useState(false);
  const [summary, setSummary] = useState(
    'Clinician-assisted postpartum emotional check-in; steady rapport with mild fatigue noted.'
  );
  const [recordingActive, setRecordingActive] = useState(false);

  const computedRisk =
    Number(epdsEquivalent) >= 14 ? 'High' : Number(epdsEquivalent) >= 9 ? 'Moderate' : 'Low';

  const handleSubmit = (e) => {
    e.preventDefault();
    const created = recordScreening({
      motherId,
      risk: computedRisk,
      modality,
      summary,
      epdsEquivalent,
      discordanceDetected,
    });
    navigate(`/results/${created.motherId}`);
  };

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        <div className="miora-subpage-header">
          <div>
            <div className="miora-dash-eyebrow">
              <span>LIVE SCREENING WORKFLOW</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 className="miora-dash-title miora-subpage-title">
              Multimodal <em>Screening</em> Session
            </h1>
            <p className="miora-dash-subtitle">
              Capture gentle voice prosody and structured reflection cues for real-time postpartum triage.
            </p>
          </div>
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => navigate('/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>

        <div className="miora-screening-grid">
          <form className="miora-card miora-screening-form" onSubmit={handleSubmit}>
            <div className="miora-field-row">
              <label className="miora-field">
                <span>Select Mother Profile</span>
                <select value={motherId} onChange={(e) => setMotherId(e.target.value)}>
                  {mothers.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id} — {m.name} (Week {m.postpartumWeek})
                    </option>
                  ))}
                </select>
              </label>

              <label className="miora-field">
                <span>Screening Modality</span>
                <select value={modality} onChange={(e) => setModality(e.target.value)}>
                  <option value="Voice + Text">Voice + Text</option>
                  <option value="Text Check-in">Text Check-in</option>
                  <option value="Voice + Optional Video">Voice + Optional Video</option>
                </select>
              </label>
            </div>

            <div className="miora-voice-capture-box">
              <div className="miora-voice-capture-left">
                <span className="miora-kpi-icon-wrap" aria-hidden="true">
                  <DashboardIcon name={recordingActive ? 'waveform' : 'mic'} size={22} />
                </span>
                <div>
                  <strong>{recordingActive ? 'Listening to Vocal Prosody…' : 'Voice Cue Capture'}</strong>
                  <p>
                    {recordingActive
                      ? 'Analyzing cadence, pause latency, and pitch stability (simulated).'
                      : 'Optional voice prompt capture for multimodal discordance check.'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                className={recordingActive ? 'miora-cta-primary' : 'miora-btn-secondary'}
                onClick={() => setRecordingActive((prev) => !prev)}
              >
                {recordingActive ? 'Stop Capture' : 'Simulate Capture'}
              </button>
            </div>

            <label className="miora-field">
              <span>EPDS Equivalent Score: {epdsEquivalent} / 30 ({computedRisk} Risk)</span>
              <input
                type="range"
                min="0"
                max="24"
                value={epdsEquivalent}
                onChange={(e) => setEpdsEquivalent(Number(e.target.value))}
              />
            </label>

            <label className="miora-checkbox-field">
              <input
                type="checkbox"
                checked={discordanceDetected}
                onChange={(e) => setDiscordanceDetected(e.target.checked)}
              />
              <span>Flag voice-text discordance for clinician review</span>
            </label>

            <label className="miora-field">
              <span>Session Observations &amp; Summary</span>
              <textarea
                rows="3"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                required
              />
            </label>

            <div className="miora-modal-actions">
              <button
                type="button"
                className="miora-btn-secondary"
                onClick={() => navigate('/dashboard')}
              >
                Cancel
              </button>
              <button type="submit" className="miora-cta-primary">
                Complete &amp; Save Screening
              </button>
            </div>
          </form>

          <aside className="miora-card miora-screening-guide">
            <h3>Triage Guidance</h3>
            <p className="miora-guide-note">
              Mock interactive workflow: completing this session updates Dashboard totals, Recent Screenings, and Risk Distribution immediately.
            </p>
            <ul className="miora-guide-list">
              <li>
                <strong>0–8 (Low Risk):</strong> Continue routine postpartum monitoring.
              </li>
              <li>
                <strong>9–13 (Moderate Risk):</strong> Schedule supportive follow-up and rest assessment.
              </li>
              <li>
                <strong>14+ (High Risk):</strong> Immediate clinician review &amp; care escalation.
              </li>
            </ul>
          </aside>
        </div>
      </div>
    </div>
  );
}

