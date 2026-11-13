import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function SignalsAndProgressPanel({
  textSignal,
  voiceSignal,
  facialSignal,
  capturedModalities,
  modalityStates,
}) {
  const capturedCount = [
    capturedModalities.text,
    capturedModalities.voice,
    capturedModalities.video,
  ].filter(Boolean).length;

  const signalRows = [
    {
      id: 'emotion-text',
      icon: 'smile',
      label: 'Emotion',
      sub: '(Text)',
      badge: textSignal.badge,
      tone: textSignal.tone,
      detail: textSignal.detail,
    },
    {
      id: 'voice-acoustic',
      icon: 'waveform',
      label: 'Voice',
      sub: '(Acoustic)',
      badge: voiceSignal.badge,
      tone: voiceSignal.tone,
      detail: voiceSignal.detail,
    },
    {
      id: 'facial-live',
      icon: 'faceScan',
      label: 'Facial',
      sub: '(Live)',
      badge: facialSignal.badge,
      tone: facialSignal.tone,
      detail: facialSignal.detail,
    },
  ];

  const steps = [
    { key: 'text', label: 'Text', captured: capturedModalities.text, state: modalityStates.text },
    { key: 'voice', label: 'Voice', captured: capturedModalities.voice, state: modalityStates.voice },
    { key: 'video', label: 'Video', captured: capturedModalities.video, state: modalityStates.video },
  ];

  return (
    <div className="miora-signals-stack">
      {/* Real-time Signals Card */}
      <section className="miora-card miora-signals-card" aria-labelledby="realtime-signals-title">
        <div className="miora-card-header">
          <div className="miora-card-title-group">
            <span className="miora-card-icon" aria-hidden="true">
              <DashboardIcon name="waveform" size={20} strokeWidth={1.7} />
            </span>
            <h2 id="realtime-signals-title" className="miora-card-title">
              Real-time Signals
            </h2>
          </div>
        </div>

        <div className="miora-signal-list">
          {signalRows.map((row) => (
            <div key={row.id} className="miora-signal-row-item">
              <div className="miora-signal-row-top">
                <div className="miora-signal-row-left">
                  <span className="miora-signal-mini-icon" aria-hidden="true">
                    <DashboardIcon name={row.icon} size={17} strokeWidth={1.65} />
                  </span>
                  <span className="miora-signal-name">
                    <strong>{row.label}</strong> <span>{row.sub}</span>
                  </span>
                </div>
                <span className={`miora-signal-pill tone-${row.tone}`}>
                  {row.badge}
                </span>
              </div>
              <p className="miora-signal-detail">{row.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Session Progress Card */}
      <section className="miora-card miora-progress-card" aria-labelledby="session-progress-title">
        <div className="miora-card-header">
          <div className="miora-card-title-group">
            <span className="miora-card-icon" aria-hidden="true">
              <DashboardIcon name="checkSquare" size={19} strokeWidth={1.65} />
            </span>
            <h2 id="session-progress-title" className="miora-card-title miora-progress-title">
              Session Progress
            </h2>
          </div>
          <span className="miora-progress-count">{capturedCount} / 3 Modalities</span>
        </div>

        <div className="miora-stepper" aria-label="Modality capture progress">
          <div className="miora-stepper-line" aria-hidden="true" />
          {steps.map((step) => (
            <div key={step.key} className="miora-stepper-item">
              <span
                className={`miora-stepper-dot ${
                  step.captured
                    ? 'is-captured'
                    : step.state === 'unavailable'
                      ? 'is-unavailable'
                      : 'is-pending'
                }`}
                aria-hidden="true"
              >
                {step.captured ? (
                  <DashboardIcon name="check" size={13} strokeWidth={2.4} />
                ) : step.state === 'unavailable' ? (
                  '–'
                ) : (
                  ''
                )}
              </span>
              <span className="miora-stepper-label">{step.label}</span>
              <span className="miora-stepper-sub">
                {step.captured
                  ? 'Captured'
                  : step.state === 'unavailable'
                    ? 'Unavailable'
                    : 'Pending'}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

