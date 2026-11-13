import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { RiskBadge } from '../components/Badges.jsx';
import { LiveMediaPanel } from '../components/LiveMediaPanel.jsx';
import { ConversationPanel } from '../components/ConversationPanel.jsx';
import { SignalsAndProgressPanel } from '../components/SignalsAndProgressPanel.jsx';
import { PreliminaryResultPanel } from '../components/PreliminaryResultPanel.jsx';

const GUIDED_PROMPTS = [
  'Hi! How have you been feeling over the past few days?',
  "That's completely understandable. Can you tell me what has felt most challenging lately?",
  'How has your rest and sleep been between feedings or caregiving?',
  'Do you feel you have someone you can lean on for support right now?',
];

const QUICK_REPLIES = [
  "I'm mostly okay, just a bit overwhelmed at times.",
  'Sleep has been very fragmented this week.',
  'I feel supported and calmer today.',
];

function formatElapsed(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function formatClockTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function LiveScreeningPage() {
  const {
    mothers,
    screeningDrafts,
    recordScreening,
    saveScreeningDraft,
    clearScreeningDraft,
  } = useClinicalData();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const defaultMotherId = useMemo(() => {
    const paramId = searchParams.get('mother');
    if (paramId && mothers.some((m) => m.id === paramId)) return paramId;
    if (mothers.some((m) => m.id === 'M-108')) return 'M-108';
    return mothers[0]?.id || 'M-104';
  }, [mothers, searchParams]);

  const [motherId, setMotherId] = useState(defaultMotherId);
  const activeMother = useMemo(
    () => mothers.find((m) => m.id === motherId) || mothers[0],
    [mothers, motherId]
  );

  const initialDraft = screeningDrafts[defaultMotherId];

  // Elapsed timer (actual elapsed seconds)
  const [elapsedSeconds, setElapsedSeconds] = useState(
    initialDraft?.elapsedSeconds || 0
  );

  // Media consent & stream state
  const [consentAudio, setConsentAudio] = useState(true);
  const [consentVideo, setConsentVideo] = useState(false);
  const [mediaStatus, setMediaStatus] = useState('awaiting-consent'); // awaiting-consent | requesting | active | denied | unavailable | error
  const [mediaError, setMediaError] = useState(null);
  const [micEnabled, setMicEnabled] = useState(false);
  const [camEnabled, setCamEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceCaptured, setVoiceCaptured] = useState(Boolean(initialDraft?.voiceCaptured));
  const [videoCaptured, setVideoCaptured] = useState(Boolean(initialDraft?.videoCaptured));

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const recordedChunksRef = useRef([]);

  // Guided conversation state
  const [messages, setMessages] = useState(() =>
    initialDraft?.messages?.length
      ? initialDraft.messages
      : [
          {
            id: 'ai-0',
            sender: 'ai',
            text: GUIDED_PROMPTS[0],
            timestamp: formatClockTime(),
          },
        ]
  );
  const [promptIndex, setPromptIndex] = useState(initialDraft?.promptIndex || 1);
  const [isTyping, setIsTyping] = useState(false);

  // Save / completion / cancel UI state
  const [draftNotice, setDraftNotice] = useState(
    initialDraft ? 'Resumed saved draft' : ''
  );
  const [validationError, setValidationError] = useState('');
  const [analysisState, setAnalysisState] = useState('idle'); // idle | processing | ready
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);

  const motherResponses = useMemo(
    () => messages.filter((m) => m.sender === 'mother'),
    [messages]
  );
  const textCaptured = motherResponses.length > 0;

  // Real elapsed timer tick
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Attach active stream to <video> whenever active & camera enabled
  useEffect(() => {
    if (videoRef.current && streamRef.current && camEnabled) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [mediaStatus, camEnabled]);

  // Cleanup all media tracks & recorders on unmount
  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        try {
          recorderRef.current.stop();
        } catch {
          // ignore
        }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const stopMediaTracks = () => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      try {
        recorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
    setMicEnabled(false);
    setCamEnabled(false);
  };

  const handleSelectMother = (nextId) => {
    setMotherId(nextId);
    setSearchParams({ mother: nextId });
    const nextDraft = screeningDrafts[nextId];
    if (nextDraft) {
      setMessages(nextDraft.messages || [{ id: 'ai-0', sender: 'ai', text: GUIDED_PROMPTS[0], timestamp: formatClockTime() }]);
      setElapsedSeconds(nextDraft.elapsedSeconds || 0);
      setPromptIndex(nextDraft.promptIndex || 1);
      setVoiceCaptured(Boolean(nextDraft.voiceCaptured));
      setVideoCaptured(Boolean(nextDraft.videoCaptured));
      setDraftNotice('Resumed saved draft');
    } else {
      setMessages([{ id: 'ai-0', sender: 'ai', text: GUIDED_PROMPTS[0], timestamp: formatClockTime() }]);
      setElapsedSeconds(0);
      setPromptIndex(1);
      setVoiceCaptured(false);
      setVideoCaptured(false);
      setDraftNotice('');
    }
    setValidationError('');
  };

  const handleRequestMedia = async () => {
    setMediaError(null);
    if (!consentAudio && !consentVideo) {
      setMediaError('Please confirm mother consent for at least microphone or camera.');
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMediaStatus('unavailable');
      setMediaError(
        'Camera and microphone APIs are unavailable in this browser. You can continue using text check-in.'
      );
      return;
    }

    setMediaStatus('requesting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: consentAudio,
        video: consentVideo,
      });
      streamRef.current = stream;
      const audioTracks = stream.getAudioTracks();
      const videoTracks = stream.getVideoTracks();

      setMicEnabled(audioTracks.length > 0);
      setCamEnabled(videoTracks.length > 0);
      setMediaStatus('active');

      if (audioTracks.length > 0) setVoiceCaptured(true);
      if (videoTracks.length > 0) setVideoCaptured(true);

      // Start MediaRecorder when supported
      if (typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined') {
        try {
          const recorder = new window.MediaRecorder(stream);
          recordedChunksRef.current = [];
          recorder.ondataavailable = (ev) => {
            if (ev.data && ev.data.size > 0) {
              recordedChunksRef.current.push(ev.data);
            }
          };
          recorder.start(1000);
          recorderRef.current = recorder;
          setIsRecording(true);
        } catch {
          setIsRecording(false);
        }
      }
    } catch (err) {
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setMediaStatus('denied');
        setMediaError(
          'Camera/microphone permission was denied. Grant browser permissions to retry, or continue via Conversation.'
        );
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setMediaStatus('unavailable');
        setMediaError(
          'No microphone or camera device was detected. Missing modalities will be marked unavailable.'
        );
      } else {
        setMediaStatus('error');
        setMediaError(
          err?.message || 'Unable to access media devices. You can continue with text check-in.'
        );
      }
    }
  };

  const handleToggleMic = () => {
    if (!streamRef.current) return;
    const next = !micEnabled;
    streamRef.current.getAudioTracks().forEach((t) => {
      t.enabled = next;
    });
    setMicEnabled(next);
  };

  const handleToggleCam = () => {
    if (!streamRef.current) return;
    const next = !camEnabled;
    streamRef.current.getVideoTracks().forEach((t) => {
      t.enabled = next;
    });
    setCamEnabled(next);
  };

  const handleToggleRecord = () => {
    if (!streamRef.current) return;
    if (isRecording) {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        try {
          recorderRef.current.stop();
        } catch {
          // ignore
        }
      }
      setIsRecording(false);
      if (micEnabled) setVoiceCaptured(true);
      if (camEnabled) setVideoCaptured(true);
    } else if (typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined') {
      try {
        const recorder = new window.MediaRecorder(streamRef.current);
        recordedChunksRef.current = [];
        recorder.ondataavailable = (ev) => {
          if (ev.data && ev.data.size > 0) recordedChunksRef.current.push(ev.data);
        };
        recorder.start(1000);
        recorderRef.current = recorder;
        setIsRecording(true);
        if (micEnabled) setVoiceCaptured(true);
        if (camEnabled) setVideoCaptured(true);
      } catch {
        setIsRecording(false);
      }
    }
  };

  const handleSendMessage = (text) => {
    setValidationError('');
    const motherMsg = {
      id: `mother-${Date.now()}`,
      sender: 'mother',
      text,
      timestamp: formatClockTime(),
    };
    setMessages((prev) => [...prev, motherMsg]);

    if (promptIndex < GUIDED_PROMPTS.length) {
      setIsTyping(true);
      const nextPrompt = GUIDED_PROMPTS[promptIndex];
      setPromptIndex((prev) => prev + 1);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `ai-${Date.now()}`,
            sender: 'ai',
            text: nextPrompt,
            timestamp: formatClockTime(),
          },
        ]);
        setIsTyping(false);
      }, 320);
    }
  };

  const handleSaveDraft = () => {
    saveScreeningDraft(activeMother.id, {
      motherId: activeMother.id,
      messages,
      promptIndex,
      elapsedSeconds,
      voiceCaptured,
      videoCaptured,
    });
    setDraftNotice(`Draft saved at ${formatClockTime()}`);
  };

  const handleRequestCancel = () => {
    const hasUnsavedProgress = textCaptured || voiceCaptured || videoCaptured || elapsedSeconds > 5;
    if (hasUnsavedProgress) {
      setCancelConfirmOpen(true);
    } else {
      stopMediaTracks();
      navigate('/dashboard');
    }
  };

  const handleConfirmDiscard = () => {
    stopMediaTracks();
    clearScreeningDraft(activeMother.id);
    setCancelConfirmOpen(false);
    navigate('/dashboard');
  };

  const handleCompleteScreening = () => {
    if (!textCaptured && !voiceCaptured && !videoCaptured) {
      setValidationError(
        'Please record at least one conversation response or media capture before completing the screening.'
      );
      return;
    }

    setValidationError('');
    setAnalysisState('processing');

    if (isRecording && recorderRef.current && recorderRef.current.state !== 'inactive') {
      try {
        recorderRef.current.stop();
      } catch {
        // ignore
      }
      setIsRecording(false);
    }

    const combinedText = motherResponses.map((m) => m.text).join(' ');
    const distressTerms = /(overwhelmed|exhausted|crying|hopeless|isolated|anxious|struggling)/i;
    const hasDistressCue = distressTerms.test(combinedText);
    const computedRisk = hasDistressCue
      ? activeMother.risk === 'High'
        ? 'High'
        : 'Moderate'
      : activeMother.risk === 'High'
        ? 'Moderate'
        : 'Low';

    const epdsVal = computedRisk === 'High' ? 15 : computedRisk === 'Moderate' ? 10 : 5;
    const scoreVal = Number((epdsVal / 20).toFixed(2));

    const capturedList = [
      textCaptured ? 'Text' : null,
      voiceCaptured ? 'Voice' : null,
      videoCaptured ? 'Video' : null,
    ].filter(Boolean);

    const created = recordScreening({
      motherId: activeMother.id,
      risk: computedRisk,
      modality: `Multimodal (${capturedList.join(' · ')})`,
      summary:
        combinedText ||
        `Live clinician-assisted session (${capturedList.join(', ')}) completed in ${formatElapsed(elapsedSeconds)}.`,
      epdsEquivalent: epdsVal,
      discordanceDetected: hasDistressCue && voiceCaptured,
      capturedModalities: {
        text: textCaptured,
        voice: voiceCaptured,
        video: videoCaptured,
      },
      durationSeconds: elapsedSeconds,
      preliminaryScore: scoreVal,
      conversation: messages,
    });

    stopMediaTracks();
    clearScreeningDraft(activeMother.id);
    setAnalysisState('ready');
    navigate(`/results/${created.motherId}`);
  };

  // Truthful signal summaries (no fabricated emotional classifications)
  const textSignal = textCaptured
    ? {
        badge: `Captured (${motherResponses.length})`,
        tone: 'active',
        detail: `${motherResponses.length} response${motherResponses.length > 1 ? 's' : ''} recorded; model processing runs on completion.`,
      }
    : {
        badge: 'Awaiting input',
        tone: 'neutral',
        detail: 'No mother text responses captured yet.',
      };

  const voiceSignal =
    mediaStatus === 'active'
      ? isRecording && micEnabled
        ? { badge: 'Recording', tone: 'active', detail: 'Microphone stream active and recording audio.' }
        : micEnabled
          ? { badge: 'Ready', tone: 'ready', detail: 'Microphone stream active (standby).' }
          : { badge: 'Muted', tone: 'neutral', detail: 'Microphone is currently muted.' }
      : mediaStatus === 'denied' || mediaStatus === 'unavailable' || mediaStatus === 'error'
        ? { badge: 'Unavailable', tone: 'muted', detail: 'Audio device unavailable; excluded from scoring.' }
        : { badge: 'Pending consent', tone: 'neutral', detail: 'Requires mother consent before capture.' };

  const facialSignal = !consentVideo
    ? { badge: 'Opted out', tone: 'muted', detail: 'Optional facial capture not enabled (consent-based).' }
    : mediaStatus === 'active' && camEnabled
      ? { badge: 'Consent active', tone: 'ready', detail: 'Live camera preview active; facial cues optional.' }
      : mediaStatus === 'active'
        ? { badge: 'Paused', tone: 'neutral', detail: 'Camera temporarily paused by clinician.' }
        : mediaStatus === 'denied' || mediaStatus === 'unavailable' || mediaStatus === 'error'
          ? { badge: 'Unavailable', tone: 'muted', detail: 'Camera unavailable; marked unavailable (not negative).' }
          : { badge: 'Pending consent', tone: 'neutral', detail: 'Awaiting camera consent confirmation.' };

  const modalityStates = {
    text: textCaptured ? 'captured' : 'pending',
    voice: voiceCaptured
      ? 'captured'
      : mediaStatus === 'denied' || mediaStatus === 'unavailable'
        ? 'unavailable'
        : 'pending',
    video: videoCaptured
      ? 'captured'
      : !consentVideo || mediaStatus === 'denied' || mediaStatus === 'unavailable'
        ? 'unavailable'
        : 'pending',
  };

  const keyIndicators = [
    textCaptured
      ? `Text channel: ${motherResponses.length} guided response(s) captured`
      : 'Text channel: Awaiting mother responses in Conversation',
    voiceCaptured
      ? `Voice channel: Audio stream captured (${formatElapsed(elapsedSeconds)})`
      : 'Voice channel: Unavailable / awaiting microphone consent',
    videoCaptured
      ? 'Facial channel: Optional consent-based video stream captured'
      : 'Facial channel: Unavailable or opted out (not treated as negative)',
  ];

  const nextSteps = [
    'Review the captured conversation and observations',
    'Consider scheduling a follow-up check-in if needed',
    'Review any unavailable modalities or concerning cues',
    'Provide maternal support & crisis helpline resources if indicated',
  ];

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Subtle Flowing Blush Header Waves */}
        <svg
          className="miora-header-ribbon miora-mothers-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="liveWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#liveWaveGrad)"
          />
        </svg>

        {/* Page Header + Live Session Status & Elapsed Timer */}
        <section className="miora-dash-header" aria-labelledby="live-screening-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>LIVE SCREENING</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="live-screening-heading" className="miora-dash-title">
              Maternal Screening <em>Session</em>
            </h1>
            <p className="miora-dash-subtitle">
              Choose a screening mode to assess maternal wellbeing through multimodal analysis.
            </p>
          </div>

          <div className="miora-session-timer-pill" aria-label="Live session status and elapsed timer">
            <span className="miora-session-status">
              <span
                className={`miora-session-dot ${
                  mediaStatus === 'active' || textCaptured ? 'is-live' : ''
                }`}
                aria-hidden="true"
              />
              <span>Live Session Active</span>
            </span>
            <span className="miora-timer-divider" aria-hidden="true" />
            <time className="miora-session-elapsed" aria-label="Elapsed session time">
              {formatElapsed(elapsedSeconds)}
            </time>
          </div>
        </section>

        {/* Segmented Screening Mode Selector */}
        <div className="miora-mode-switch" role="tablist" aria-label="Screening mode selector">
          <button
            type="button"
            role="tab"
            aria-selected={true}
            className="miora-mode-tab is-active"
          >
            <DashboardIcon name="video" size={16} />
            <span>Screening</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={false}
            className="miora-mode-tab"
            onClick={() => {
              stopMediaTracks();
              navigate(`/upload-analyze?mother=${activeMother.id}`);
            }}
          >
            <DashboardIcon name="upload" size={16} />
            <span>Upload &amp; Analyze</span>
          </button>
        </div>

        {/* Patient Information Strip */}
        <section className="miora-card miora-patient-strip" aria-label="Selected mother summary">
          <div className="miora-patient-item">
            <span className="miora-patient-icon" aria-hidden="true">
              <DashboardIcon name="user" size={18} />
            </span>
            <div className="miora-patient-meta">
              <div className="miora-patient-select-row">
                <label htmlFor="live-mother-select" className="sr-only">
                  Select mother for screening
                </label>
                <select
                  id="live-mother-select"
                  className="miora-patient-id-select"
                  value={activeMother.id}
                  onChange={(e) => handleSelectMother(e.target.value)}
                >
                  {mothers.slice(0, 25).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
              </div>
              <span className="miora-patient-sub">{activeMother.initials}</span>
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="calendar" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Postpartum Week</span>
              <strong>Week {activeMother.postpartumWeek}</strong>
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="layers" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Previous Risk</span>
              <RiskBadge risk={activeMother.risk} />
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="clock" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Last Screening</span>
              <strong>{activeMother.lastScreeningDate}</strong>
            </div>
          </div>

          <span className="miora-patient-divider" aria-hidden="true" />

          <div className="miora-patient-item">
            <span className="miora-patient-icon is-plain" aria-hidden="true">
              <DashboardIcon name="barChart" size={18} />
            </span>
            <div className="miora-patient-meta">
              <span className="miora-patient-label">Screening Type</span>
              <strong>Multimodal (Text · Voice · Video)</strong>
            </div>
          </div>
        </section>

        {/* Three-Column Screening Workspace */}
        <div className="miora-live-workspace">
          <LiveMediaPanel
            consentAudio={consentAudio}
            consentVideo={consentVideo}
            onConsentAudioChange={setConsentAudio}
            onConsentVideoChange={setConsentVideo}
            mediaStatus={mediaStatus}
            mediaError={mediaError}
            isRecording={isRecording}
            micEnabled={micEnabled}
            camEnabled={camEnabled}
            onRequestMedia={handleRequestMedia}
            onToggleMic={handleToggleMic}
            onToggleCam={handleToggleCam}
            onToggleRecord={handleToggleRecord}
            videoRef={videoRef}
          />

          <ConversationPanel
            messages={messages}
            isTyping={isTyping}
            onSendMessage={handleSendMessage}
            quickReplies={QUICK_REPLIES}
          />

          <SignalsAndProgressPanel
            textSignal={textSignal}
            voiceSignal={voiceSignal}
            facialSignal={facialSignal}
            capturedModalities={{
              text: textCaptured,
              voice: voiceCaptured,
              video: videoCaptured,
            }}
            modalityStates={modalityStates}
          />
        </div>

        {/* Wide 3-Column Preliminary Result Panel */}
        <PreliminaryResultPanel
          analysisState={analysisState}
          preliminaryResult={null}
          indicators={keyIndicators}
          nextSteps={nextSteps}
        />

        {/* Validation / Draft Status Banner */}
        {(validationError || draftNotice) && (
          <div className="miora-live-feedback-row">
            {validationError && (
              <div className="miora-live-alert" role="alert">
                {validationError}
              </div>
            )}
            {draftNotice && (
              <div className="miora-draft-pill" role="status">
                <DashboardIcon name="check" size={14} />
                <span>{draftNotice}</span>
              </div>
            )}
          </div>
        )}

        {/* Bottom Action Bar */}
        <div className="miora-live-action-bar">
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={handleRequestCancel}
          >
            <DashboardIcon name="arrowLeft" size={15} />
            <span>Cancel Screening</span>
          </button>

          <div className="miora-live-action-right">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={handleSaveDraft}
            >
              Save Draft
            </button>

            <button
              type="button"
              className="miora-cta-primary"
              disabled={analysisState === 'processing'}
              onClick={handleCompleteScreening}
            >
              <span>
                {analysisState === 'processing'
                  ? 'Saving & Analyzing...'
                  : 'Complete Screening'}
              </span>
              <DashboardIcon name="check" size={15} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      </div>

      {/* Cancel Screening Confirmation Modal */}
      {cancelConfirmOpen && (
        <div
          className="miora-modal-backdrop"
          role="presentation"
          onClick={() => setCancelConfirmOpen(false)}
        >
          <div
            className="miora-modal-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cancel-confirm-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="miora-modal-head">
              <div className="miora-modal-head-left">
                <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
                  <DashboardIcon name="alertTriangle" size={20} />
                </span>
                <div>
                  <h2 id="cancel-confirm-title">Discard Screening Session?</h2>
                  <p>
                    You have unsaved conversation or media data for {activeMother.id}. Save a draft first or discard this session.
                  </p>
                </div>
              </div>
            </div>

            <div className="miora-modal-actions">
              <button
                type="button"
                className="miora-btn-secondary"
                onClick={() => setCancelConfirmOpen(false)}
              >
                Keep Session
              </button>
              <button
                type="button"
                className="miora-btn-secondary"
                onClick={() => {
                  handleSaveDraft();
                  stopMediaTracks();
                  setCancelConfirmOpen(false);
                  navigate('/dashboard');
                }}
              >
                Save Draft &amp; Exit
              </button>
              <button
                type="button"
                className="miora-cta-primary"
                onClick={handleConfirmDiscard}
              >
                Discard &amp; Exit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
