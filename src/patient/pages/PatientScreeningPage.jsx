import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import './screening.css';

export function PatientScreeningPage() {
  const navigate = useNavigate();

  // Media states
  const [cameraOn, setCameraOn] = useState(true);
  const [micOn, setMicOn] = useState(true);
  const [isRecording, setIsRecording] = useState(true);
  const [mediaStatus, setMediaStatus] = useState('requesting'); // 'requesting' | 'active' | 'denied' | 'unavailable' | 'off'
  const [mediaError, setMediaError] = useState(null);
  const [timerSeconds, setTimerSeconds] = useState(134); // starts at 02:14
  const [progress, setProgress] = useState(40);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Chat message state
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'msg-1',
      sender: 'ai',
      text: "Hi Amara! I'm Miora, your AI screening companion. I'll ask you a few questions to understand how you've been feeling lately. Is it okay if we begin?",
      time: '10:24 AM',
    },
    {
      id: 'msg-2',
      sender: 'user',
      text: 'Yes, we can start.',
      time: '10:24 AM',
    },
    {
      id: 'msg-3',
      sender: 'ai',
      text: 'In the past two weeks, how often have you felt low, sad, or hopeless?',
      time: '10:25 AM',
    },
  ]);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const videoContainerRef = useRef(null);

  // Initialize getUserMedia with real video and audio permissions
  const initMedia = async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMediaStatus('unavailable');
      setMediaError('Camera preview is unavailable in this browser environment.');
      return;
    }

    try {
      setMediaStatus('requesting');
      setMediaError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play?.().catch(() => {});
      }
      setMediaStatus('active');
      setMediaError(null);
    } catch (err) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setMediaStatus('denied');
        setMediaError('Camera and microphone permission was denied. Please allow access in browser settings to view your live camera preview.');
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setMediaStatus('unavailable');
        setMediaError('No camera or microphone detected on this system.');
      } else {
        setMediaStatus('unavailable');
        setMediaError('Unable to access video capture.');
      }
    }
  };

  useEffect(() => {
    initMedia();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  // Ensure stream is attached to video whenever video element mounts or camera is toggled back on
  useEffect(() => {
    if (cameraOn && mediaStatus === 'active' && videoRef.current && streamRef.current) {
      if (videoRef.current.srcObject !== streamRef.current) {
        videoRef.current.srcObject = streamRef.current;
      }
      videoRef.current.play?.().catch(() => {});
    }
  }, [cameraOn, mediaStatus]);

  // Sync camera track enabled state with cameraOn
  useEffect(() => {
    if (streamRef.current) {
      const videoTracks = streamRef.current.getVideoTracks();
      videoTracks.forEach((track) => {
        track.enabled = cameraOn;
      });
    }
  }, [cameraOn]);

  // Sync mic track enabled state with micOn
  useEffect(() => {
    if (streamRef.current) {
      const audioTracks = streamRef.current.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = micOn;
      });
    }
  }, [micOn]);

  // Timer interval for recording
  useEffect(() => {
    let interval = null;
    if (isRecording) {
      interval = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoContainerRef.current?.requestFullscreen?.().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const handleEndScreening = () => {
    setIsRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
    }
    navigate('/screening-results');
  };

  const handleSendMessage = (e) => {
    e?.preventDefault();
    if (!chatInput.trim()) return;
    const newMsg = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text: chatInput.trim(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, newMsg]);
    setChatInput('');
    setProgress((prev) => Math.min(100, prev + 15));
  };

  return (
    <div className="screening-workspace-shell">
      {/* 1. Header & Stage Progress Bar */}
      <div className="screening-top-bar-area">
        <div className="screening-header-titles">
          <div className="screening-breadcrumb">
            <NavLink to="/patient/reports" className="screening-breadcrumb-link">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
                <path d="M9.5 21v-7h5v7" />
              </svg>
              <span>Home</span>
            </NavLink>
            <span className="screening-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
            <span className="screening-breadcrumb-current">AI Screening Session</span>
          </div>
          <h1 className="patient-page-heading screening-page-title">AI Screening Session</h1>
          <p className="patient-page-subheading screening-page-sub">
            A private, conversational screening to understand your emotional well-being after childbirth.
          </p>
        </div>

        {/* 4-Stage Progress Tracker */}
        <div className="screening-stages-tracker" aria-label="Screening progress stages">
          <NavLink to="/patient/medical-history" className="tracker-stage is-completed">
            <div className="tracker-circle">
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
              </svg>
            </div>
            <span className="tracker-label">Medical History</span>
          </NavLink>

          <div className="tracker-line is-active-line" aria-hidden="true" />

          <div className="tracker-stage is-active">
            <div className="tracker-circle">
              <span className="tracker-inner-dot" />
            </div>
            <span className="tracker-label">Screening</span>
          </div>

          <div className="tracker-line" aria-hidden="true" />

          <NavLink to="/screening-results" className="tracker-stage is-upcoming">
            <div className="tracker-circle" />
            <span className="tracker-label">Analysis</span>
          </NavLink>

          <div className="tracker-line" aria-hidden="true" />

          <NavLink to="/screening-results" className="tracker-stage is-upcoming">
            <div className="tracker-circle" />
            <span className="tracker-label">Results</span>
          </NavLink>
        </div>
      </div>

      {/* 2. Main Two-Column Screening Workspace */}
      <div className="screening-two-col-layout">
        {/* Left Column: Live Video & Sensors Panel */}
        <section
          className="screening-video-card"
          ref={videoContainerRef}
          aria-label="Patient Video Feed"
        >
          <div className="screening-video-container">
            {/* Live Video Feed or Neutral State */}
            {cameraOn ? (
              mediaStatus === 'active' ? (
                <video
                  ref={videoRef}
                  className="screening-live-video"
                  autoPlay
                  playsInline
                  muted
                />
              ) : mediaStatus === 'requesting' ? (
                <div className="screening-permission-state">
                  <div className="screening-permission-icon-wrap">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M23 7l-7 5 7 5V7z" />
                      <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                    </svg>
                  </div>
                  <h3 className="screening-permission-title">Connecting to Camera & Mic...</h3>
                  <p className="screening-permission-sub">Please allow camera and microphone access to view your live feed.</p>
                  <div className="screening-permission-spinner" />
                </div>
              ) : (
                <div className="screening-permission-state is-error">
                  <div className="screening-permission-icon-wrap is-error">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  </div>
                  <h3 className="screening-permission-title">
                    {mediaStatus === 'denied' ? 'Camera Permission Denied' : 'Camera Unavailable'}
                  </h3>
                  <p className="screening-permission-sub">
                    {mediaError || 'Unable to access live camera feed. You can try again or continue with audio.'}
                  </p>
                  <button
                    type="button"
                    className="patient-btn-primary screening-retry-btn"
                    onClick={() => initMedia()}
                  >
                    Enable Camera Access
                  </button>
                </div>
              )
            ) : (
              <div className="screening-camera-off-state">
                <div className="camera-off-avatar">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m4 0h5a2 2 0 0 1 2 2v3.5" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                    <path d="M21 15.5V17m0-7.5v2.5l-5 3.5" />
                  </svg>
                </div>
                <span className="camera-off-text">Camera is currently turned off</span>
                <span className="camera-off-sub">Microphone & audio remain active</span>
                <button
                  type="button"
                  className="patient-btn-secondary screening-turn-on-cam-btn"
                  onClick={() => setCameraOn(true)}
                >
                  Turn Camera On
                </button>
              </div>
            )}

            {/* Top Bar Overlay */}
            <div className="screening-video-top-overlay">
              <div className="screening-live-pill">
                <span className={`screening-pulse-dot ${!isRecording ? 'is-paused' : ''}`} aria-hidden="true" />
                <span className="screening-pill-text">Recording</span>
                <time className="screening-pill-time">{formatTime(timerSeconds)}</time>
              </div>

              <button
                type="button"
                className="screening-overlay-btn"
                onClick={toggleFullscreen}
                aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="15 3 21 3 21 9" />
                  <polyline points="9 21 3 21 3 15" />
                  <polyline points="21 15 21 21 15 21" />
                  <polyline points="3 9 3 3 9 3" />
                </svg>
              </button>
            </div>

            {/* Bottom Bar Overlay */}
            <div className="screening-video-bottom-overlay">
              <div className="screening-identity-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M23 7l-7 5 7 5V7z" />
                  <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
                <span>You (Live)</span>
              </div>

              <div className="screening-sensor-badges">
                <span className={`screening-sensor-badge ${micOn ? 'is-active' : 'is-muted'}`}>
                  {micOn ? 'Mic Active' : 'Mic Muted'}
                </span>
                <span className={`screening-sensor-badge ${cameraOn ? 'is-active' : 'is-muted'}`}>
                  {cameraOn ? 'Video Active' : 'Video Off'}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: Miora AI Screening Conversation Panel */}
        <section className="screening-chat-card" aria-label="Miora AI Screening Session">
          {/* Header */}
          <div className="screening-chat-card-header">
            <div className="screening-chat-bot-info">
              <div className="screening-bot-avatar-ring">
                <span className="screening-bot-char" aria-hidden="true">M</span>
              </div>
              <div>
                <h2 className="screening-chat-bot-name">Miora AI</h2>
                <div className="screening-chat-bot-status">
                  <span className="screening-status-online-dot" />
                  <span>Perinatal Screening Companion &bull; Confidential</span>
                </div>
              </div>
            </div>
          </div>

          {/* Conversation History */}
          <div className="screening-chat-messages-container">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`screening-msg-row ${m.sender === 'user' ? 'is-user-msg' : 'is-bot-msg'}`}
              >
                {m.sender === 'ai' && (
                  <div className="screening-msg-avatar">
                    <span className="screening-bot-char-sm" aria-hidden="true">M</span>
                  </div>
                )}
                <div className="screening-bubble-wrapper">
                  <div className={`screening-speech-bubble ${m.sender === 'user' ? 'user-speech' : 'bot-speech'}`}>
                    {m.text}
                  </div>
                  <div className="screening-msg-meta">
                    <span className="screening-msg-time">{m.time}</span>
                    {m.sender === 'user' && (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Active Listening Card with Real-time Waveform */}
            <div className="screening-listening-bubble-card">
              <div className="screening-listening-head">
                <div className="screening-listening-tag">
                  <span className="screening-eq-animation" aria-hidden="true">
                    <span className={`screening-eq-bar bar-1 ${!micOn ? 'is-off' : ''}`} />
                    <span className={`screening-eq-bar bar-2 ${!micOn ? 'is-off' : ''}`} />
                    <span className={`screening-eq-bar bar-3 ${!micOn ? 'is-off' : ''}`} />
                  </span>
                  <span className="screening-listening-label">{micOn ? 'Listening to voice...' : 'Microphone muted'}</span>
                </div>

                {/* Animated Waveform */}
                <div className="screening-audio-waveform-bars" aria-hidden="true">
                  {[...Array(18)].map((_, i) => (
                    <span
                      key={i}
                      className={`screening-wave-col ${!micOn ? 'is-flat' : ''}`}
                      style={{ animationDelay: `${(i % 5) * 0.12}s` }}
                    />
                  ))}
                </div>
              </div>

              <div className="screening-transcription-preview">
                <p className="screening-transcribed-quote">
                  &ldquo;I've been feeling a bit low almost every day.&rdquo;
                </p>
                <span className="screening-transcribed-check" aria-hidden="true">
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
                  </svg>
                </span>
              </div>
            </div>
          </div>

          {/* Chat Input & Response Bar */}
          <form className="screening-chat-input-bar" onSubmit={handleSendMessage}>
            <input
              type="text"
              className="screening-text-input"
              placeholder="Type your response or speak naturally..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
            />
            <button
              type="submit"
              className="screening-send-msg-btn"
              disabled={!chatInput.trim()}
              aria-label="Send response"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </section>
      </div>

      {/* 3. Bottom Session Controls Card */}
      <footer className="patient-card screening-controls-card">
        <div className="screening-controls-left">
          {/* Camera On / Off Button */}
          <button
            type="button"
            className={`screening-toggle-btn ${cameraOn ? 'is-active-btn' : 'is-muted-btn'}`}
            onClick={() => setCameraOn((prev) => !prev)}
            aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M23 7l-7 5 7 5V7z" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
            <span>{cameraOn ? 'Camera On' : 'Camera Off'}</span>
          </button>

          {/* Mic On / Off Button */}
          <button
            type="button"
            className={`screening-toggle-btn ${micOn ? 'is-active-btn' : 'is-muted-btn'}`}
            onClick={() => setMicOn((prev) => !prev)}
            aria-label={micOn ? 'Mute microphone' : 'Unmute microphone'}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
            <span>{micOn ? 'Mic On' : 'Mic Off'}</span>
          </button>

          {/* Recording Status */}
          <div className="screening-recording-live-pill">
            <span className={`screening-status-dot ${!isRecording ? 'is-paused' : ''}`} aria-hidden="true" />
            <span>Recording in progress</span>
          </div>
        </div>

        {/* Center: Session Progress */}
        <div className="screening-progress-box">
          <div className="screening-progress-label-row">
            <span className="screening-progress-name">Session Progress</span>
            <span className="screening-progress-pct">{progress}%</span>
          </div>
          <div className="screening-progress-track-bg" role="progressbar" aria-valuenow={progress} aria-valuemin="0" aria-valuemax="100">
            <div className="screening-progress-fill-bar" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Right: End Screening CTA */}
        <div className="screening-controls-right">
          <button
            type="button"
            className="screening-end-session-btn"
            onClick={handleEndScreening}
          >
            <span className="screening-stop-square" aria-hidden="true" />
            <span>End Screening</span>
          </button>
        </div>
      </footer>
    </div>
  );
}

export default PatientScreeningPage;
