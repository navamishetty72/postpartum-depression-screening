import React, { useRef, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function LiveMediaPanel({
  consentAudio,
  consentVideo,
  onConsentAudioChange,
  onConsentVideoChange,
  mediaStatus,
  mediaError,
  isRecording,
  micEnabled,
  camEnabled,
  onRequestMedia,
  onToggleMic,
  onToggleCam,
  onToggleRecord,
  videoRef,
}) {
  const stageRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleToggleFullscreen = async () => {
    const el = stageRef.current;
    if (!el) return;
    try {
      if (!document.fullscreenElement) {
        if (el.requestFullscreen) {
          await el.requestFullscreen();
          setIsFullscreen(true);
        }
      } else if (document.exitFullscreen) {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch {
      setIsFullscreen((prev) => !prev);
    }
  };

  const streamActive = mediaStatus === 'active';

  return (
    <section className="miora-card miora-live-panel" aria-labelledby="live-session-panel-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="video" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="live-session-panel-title" className="miora-card-title">
            Live Session
          </h2>
        </div>
      </div>

      <div
        ref={stageRef}
        className={`miora-media-stage ${isFullscreen ? 'is-fullscreen' : ''}`}
      >
        {/* Top badges & fullscreen */}
        <div className="miora-media-topbar">
          {streamActive ? (
            <span className={`miora-live-pill ${isRecording ? 'is-recording' : ''}`}>
              <span className="miora-live-dot" aria-hidden="true" />
              <span>{isRecording ? 'Live · Recording' : 'Live'}</span>
            </span>
          ) : (
            <span className="miora-live-pill is-standby">
              <span className="miora-live-dot" aria-hidden="true" />
              <span>Standby</span>
            </span>
          )}

          <button
            type="button"
            className="miora-media-expand-btn"
            aria-label={isFullscreen ? 'Exit fullscreen preview' : 'Enter fullscreen preview'}
            onClick={handleToggleFullscreen}
          >
            <DashboardIcon name="maximize" size={15} strokeWidth={1.8} />
          </button>
        </div>

        {/* Actual Webcam Video or Consent / Status Placeholder (never a stock image) */}
        {streamActive && camEnabled ? (
          <video
            ref={videoRef}
            className="miora-live-video"
            autoPlay
            playsInline
            muted
            aria-label="Live webcam preview"
          />
        ) : streamActive && !camEnabled ? (
          <div className="miora-media-placeholder">
            <span className="miora-kpi-icon-wrap" aria-hidden="true">
              <DashboardIcon name={micEnabled ? 'waveform' : 'videoOff'} size={24} />
            </span>
            <strong>{consentVideo ? 'Camera Paused' : 'Audio-Only Mode'}</strong>
            <p>
              {micEnabled
                ? 'Microphone is active; facial video capture is off.'
                : 'Audio and video are currently paused.'}
            </p>
          </div>
        ) : (
          <div className="miora-consent-box">
            <span className="miora-kpi-icon-wrap" aria-hidden="true">
              <DashboardIcon name="shieldCheck" size={22} />
            </span>
            <h3>Media Consent Required</h3>
            <p>
              Confirm mother consent before accessing microphone or camera streams.
            </p>

            <div className="miora-consent-checks">
              <label className="miora-checkbox-field">
                <input
                  type="checkbox"
                  checked={consentAudio}
                  onChange={(e) => onConsentAudioChange(e.target.checked)}
                />
                <span>Consent to microphone audio capture</span>
              </label>

              <label className="miora-checkbox-field">
                <input
                  type="checkbox"
                  checked={consentVideo}
                  onChange={(e) => onConsentVideoChange(e.target.checked)}
                />
                <span>Consent to optional live camera &amp; facial signals</span>
              </label>
            </div>

            {mediaError && (
              <div className="miora-media-error" role="alert">
                {mediaError}
              </div>
            )}

            <button
              type="button"
              className="miora-cta-primary miora-consent-btn"
              disabled={(!consentAudio && !consentVideo) || mediaStatus === 'requesting'}
              onClick={onRequestMedia}
            >
              {mediaStatus === 'requesting'
                ? 'Requesting Device Access...'
                : mediaStatus === 'denied' || mediaStatus === 'error'
                  ? 'Retry Camera & Mic'
                  : 'Consent & Start Media'}
            </button>
          </div>
        )}

        {/* Bottom Overlay Media Controls */}
        <div className="miora-media-controls" role="group" aria-label="Media session controls">
          <button
            type="button"
            className={`miora-media-ctrl-btn ${!micEnabled ? 'is-muted' : ''}`}
            aria-label={micEnabled ? 'Mute microphone' : 'Unmute microphone'}
            aria-pressed={!micEnabled}
            disabled={!streamActive}
            onClick={onToggleMic}
          >
            <DashboardIcon name={micEnabled ? 'mic' : 'micOff'} size={17} />
          </button>

          <button
            type="button"
            className={`miora-media-ctrl-btn ${!camEnabled ? 'is-muted' : ''}`}
            aria-label={camEnabled ? 'Disable camera' : 'Enable camera'}
            aria-pressed={!camEnabled}
            disabled={!streamActive || !consentVideo}
            onClick={onToggleCam}
          >
            <DashboardIcon name={camEnabled ? 'video' : 'videoOff'} size={17} />
          </button>

          <button
            type="button"
            className={`miora-media-record-btn ${isRecording ? 'is-recording' : ''}`}
            aria-label={isRecording ? 'Stop recording' : 'Start recording'}
            aria-pressed={isRecording}
            disabled={!streamActive}
            onClick={onToggleRecord}
          >
            <DashboardIcon name={isRecording ? 'stopSquare' : 'mic'} size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}

