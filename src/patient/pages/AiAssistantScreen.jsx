import React, { useState, useRef, useEffect, useCallback } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import '../styles/ai-assistant.css';

// SVG Icons matching Miora's clean refined stroke style
const Icons = {
  home: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
      <path d="M9.5 21v-7h5v7" />
    </svg>
  ),
  mic: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  ),
  micOff: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="1" y1="1" x2="23" y2="23" />
      <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V5a3 3 0 0 0-5.94-.6" />
      <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  ),
  interrupt: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
    </svg>
  ),
  replay: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </svg>
  ),
  send: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" stroke="none" />
    </svg>
  ),
  sparkles: (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '2px', color: '#d93c75', fontSize: '13px', lineHeight: 1 }} aria-hidden="true">
      ✦✦
    </span>
  ),
  leaf: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </svg>
  ),
  lotus: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3c-1.5 3-4 6-8 7 3 2 5.5 5 8 9 2.5-4 5-7 8-9-4-1-6.5-4-8-7z" />
      <path d="M12 12c-2.5 2-4 4.5-5 7 2.5 1 5 1.5 5 1.5s2.5-.5 5-1.5c-1-2.5-2.5-5-5-7z" />
    </svg>
  ),
  calendarCheck: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <path d="m9 16 2 2 4-4" />
    </svg>
  ),
  barChart: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  book: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  playCircle: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polygon points="10 8 16 12 10 16 10 8" fill="none" stroke="currentColor" />
    </svg>
  ),
  stethoscope: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4.5 3v5a4.5 4.5 0 0 0 9 0V3" />
      <path d="M9 12.5v4a3.5 3.5 0 0 0 7 0v-2.5" />
      <circle cx="16" cy="14" r="2.5" />
      <path d="M3 3h3M12 3h3" />
    </svg>
  ),
  chatDots: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      <circle cx="8" cy="11.5" r="1" fill="currentColor" />
      <circle cx="12" cy="11.5" r="1" fill="currentColor" />
      <circle cx="16" cy="11.5" r="1" fill="currentColor" />
    </svg>
  ),
  documentHeart: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="14" y2="17" />
    </svg>
  ),
  endPhone: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 11.38 11.38 0 0 0 3.58.57 2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A19 19 0 0 1 3 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2 11.38 11.38 0 0 0 .58 3.58 2 2 0 0 1-.45 2.11L8.86 10.96" />
      <line x1="23" y1="1" x2="1" y2="23" />
    </svg>
  ),
  paperclip: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l7.88-7.88" />
    </svg>
  ),
};

// 8 Supported Languages matching backend voice assistant
const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', speechLang: 'en-US', ttsLocale: 'en-US' },
  { code: 'hi', label: 'हिन्दी (Hindi)', speechLang: 'hi-IN', ttsLocale: 'hi-IN' },
  { code: 'bn', label: 'বাংলা (Bengali)', speechLang: 'bn-IN', ttsLocale: 'bn-IN' },
  { code: 'ta', label: 'தமிழ் (Tamil)', speechLang: 'ta-IN', ttsLocale: 'ta-IN' },
  { code: 'te', label: 'తెలుగు (Telugu)', speechLang: 'te-IN', ttsLocale: 'te-IN' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)', speechLang: 'kn-IN', ttsLocale: 'kn-IN' },
  { code: 'ml', label: 'മലയാളം (Malayalam)', speechLang: 'ml-IN', ttsLocale: 'ml-IN' },
  { code: 'mr', label: 'मराठी (Marathi)', speechLang: 'mr-IN', ttsLocale: 'mr-IN' },
];

// 5 Mood face SVGs
const MoodFaces = [
  {
    id: 'distressed',
    label: 'Distressed',
    render: (size = 22) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="8" y1="9" x2="10" y2="9.5" />
        <line x1="16" y1="9" x2="14" y2="9.5" />
        <path d="M8 16c1-1.5 2-2 4-2s3 .5 4 2" />
      </svg>
    ),
  },
  {
    id: 'down',
    label: 'Down',
    render: (size = 22) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="9" cy="9.5" r="1" fill="currentColor" />
        <circle cx="15" cy="9.5" r="1" fill="currentColor" />
        <path d="M9 16c1-1.2 2-1.8 3-1.8s2 .6 3 1.8" />
      </svg>
    ),
  },
  {
    id: 'neutral',
    label: 'Neutral',
    render: (size = 22) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="9" cy="9.5" r="1" fill="currentColor" />
        <circle cx="15" cy="9.5" r="1" fill="currentColor" />
        <line x1="9" y1="15.5" x2="15" y2="15.5" />
      </svg>
    ),
  },
  {
    id: 'okay',
    label: 'Okay',
    render: (size = 22) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="9" cy="9.5" r="1" fill="currentColor" />
        <circle cx="15" cy="9.5" r="1" fill="currentColor" />
        <path d="M9 14.5c.8 1 1.8 1.5 3 1.5s2.2-.5 3-1.5" />
      </svg>
    ),
  },
  {
    id: 'happy',
    label: 'Happy',
    render: (size = 22) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="9" cy="9.5" r="1" fill="currentColor" />
        <circle cx="15" cy="9.5" r="1" fill="currentColor" />
        <path d="M8 13.5c1 2.2 2.5 3 4 3s3-.8 4-3" />
      </svg>
    ),
  },
];

// Initial conversation messages
const INITIAL_MESSAGES = [
  {
    id: 'msg-1',
    sender: 'bot',
    text: `Hi Amara! 💕\nI'm Miora, your AI companion. I'm here to listen, answer your questions, and support you through your postpartum journey.\n\nHow are you feeling today?`,
    timestamp: '10:24 AM',
  },
  {
    id: 'msg-2',
    sender: 'user',
    text: `I've been feeling a bit anxious and overwhelmed lately.`,
    timestamp: '10:26 AM',
    status: 'delivered',
  },
  {
    id: 'msg-3',
    sender: 'bot',
    text: `I'm really sorry you're feeling this way. It's completely understandable, especially after childbirth. 💖\n\nWould you like me to share some simple coping strategies, a calming exercise, or help you decide if it's a good time to talk to a professional?`,
    timestamp: '10:26 AM',
  },
];

export function AiAssistantScreen() {
  const { patient, selectedMood, setPatientMood } = usePatient();
  const navigate = useNavigate();

  // Mode: 'voice' (default) vs 'text'
  const [mode, setMode] = useState('voice');

  // Shared conversation state between Voice and Text modes (never cleared on mode toggle)
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [activeMood, setActiveMood] = useState('okay');
  const [selectedLanguage, setSelectedLanguage] = useState('en');

  // Voice Interaction State Machine: 'idle' | 'listening' | 'thinking' | 'speaking'
  const [voiceState, setVoiceState] = useState('idle');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentSpeakingSentence, setCurrentSpeakingSentence] = useState('');
  const [lastBotMessage, setLastBotMessage] = useState(INITIAL_MESSAGES[2].text);
  const [lastUserMessage, setLastUserMessage] = useState(INITIAL_MESSAGES[1].text);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [speechError, setSpeechError] = useState(null);
  const [backendConfigured, setBackendConfigured] = useState(null);

  // Check Gemini backend readiness on mount
  useEffect(() => {
    fetch('/api/voice-assistant/status')
      .then((r) => r.json())
      .then((data) => {
        if (typeof data?.configured === 'boolean') {
          setBackendConfigured(data.configured);
        }
      })
      .catch(() => {
        setBackendConfigured(false);
      });
  }, []);

  // Real-time audio amplitude for orb reactive animation
  const [audioLevel, setAudioLevel] = useState(0); // 0.0 to 1.0

  // Modals & Refs
  const [activeModal, setActiveModal] = useState(null); // 'audio' | 'meditation' | 'tips' | null
  const recognitionRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const animFrameRef = useRef(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Sync mood with patient context
  useEffect(() => {
    if (selectedMood) {
      const found = MoodFaces.find(
        (m) => m.id === selectedMood.toLowerCase() || m.label.toLowerCase() === selectedMood.toLowerCase()
      );
      if (found) {
        setActiveMood(found.id);
      }
    }
  }, [selectedMood]);

  // Clean text helper for natural speech synthesis
  const cleanForTTS = (text) => {
    return (text || '')
      .replace(/[*_~`#]/g, '')
      .replace(/[✨🌸♥✦•]/g, '')
      .replace(/\n+/g, ' ')
      .trim();
  };

  // Best natural voice selection preferring female voice with graceful fallback
  const getBestVoice = useCallback((langLocale = 'en-US') => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    if (voices.length === 0) return null;

    const langPrefix = langLocale.split('-')[0].toLowerCase();
    const langVoices = voices.filter(
      (v) => v.lang && (v.lang.toLowerCase().startsWith(langPrefix) || v.lang.toLowerCase().replace('_', '-').startsWith(langPrefix))
    );

    // Prioritize natural female voices
    const femaleMatch = (langVoices.length > 0 ? langVoices : voices).find((v) => {
      const name = (v.name || '').toLowerCase();
      return (
        name.includes('female') ||
        name.includes('samantha') ||
        name.includes('zira') ||
        name.includes('victoria') ||
        name.includes('karen') ||
        name.includes('natural') ||
        name.includes('moira') ||
        name.includes('fiona')
      );
    });

    if (femaleMatch) return femaleMatch;
    if (langVoices.length > 0) return langVoices[0];
    return voices.find((v) => v.default) || voices[0];
  }, []);

  // Stop voice speech playback
  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setVoiceState((prev) => (prev === 'speaking' ? 'idle' : prev));
  }, []);

  // Real-time audio amplitude analysis via Web Audio API AnalyserNode
  const startAudioAnalysis = async () => {
    try {
      if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) return;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();
      audioContextRef.current = ctx;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.6;
      analyserRef.current = analyser;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateAmplitude = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const normalized = Math.min(1, avg / 75); // Normalized 0..1
        setAudioLevel(normalized);
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          animFrameRef.current = window.requestAnimationFrame(updateAmplitude);
        }
      };

      updateAmplitude();
    } catch (err) {
      console.warn('Real-time audio analyser init notice:', err);
    }
  };

  const stopAudioAnalysis = useCallback(() => {
    if (animFrameRef.current && typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
      window.cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      stopAudioAnalysis();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    };
  }, [stopSpeaking, stopAudioAnalysis]);

  // Local empathetic maternal response engine (clinical fallback if backend is offline)
  const generateLocalDemoResponse = (userQuery, patientName = 'Amara') => {
    const query = (userQuery || '').toLowerCase();

    if (query.includes('coping') || query.includes('overwhelm') || query.includes('stress')) {
      return `Here are three gentle coping strategies for postpartum overwhelm, ${patientName}:\n\n1. **The 5-4-3-2-1 Grounding:** Notice 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 slow breath.\n2. **Micro-Breaks:** When your baby rests or is safe in the crib, sit quietly with your eyes closed for even 3 minutes with both feet on the floor.\n3. **Lowering the Bar:** Today's only priority is nourishment and rest. Everything else can wait. 🌸`;
    }

    if (query.includes('breath') || query.includes('calm') || query.includes('exercise')) {
      return `Let's take a calming breath together right now, ${patientName}:\n\n✨ **Inhale gently** through your nose for 4 counts...\n✨ **Hold softly** for 4 counts...\n✨ **Exhale slowly** through your mouth for 6 counts...\n\nFeel your shoulders drop and your jaw unclench. You are safe and doing your best.`;
    }

    if (query.includes('doctor') || query.includes('physician') || query.includes('help') || query.includes('see a doctor')) {
      return `Speaking with your healthcare provider or perinatal specialist is always a proactive, loving choice for yourself and your baby.\n\nWe recommend reaching out if feelings of sadness, anxiety, or disconnection last more than 2 weeks, if you feel unable to care for daily needs, or if worry feels constant. You can connect directly with Dr. Elena Rostova from the Connect to Doctor tab.`;
    }

    if (query.includes('sleep') || query.includes('tired') || query.includes('exhausted') || query.includes('insomnia')) {
      return `Postpartum sleep disruption is deeply challenging, ${patientName}. When sleep is fragmented, our emotional resilience is tested.\n\nTry pairing night feeds with dim amber lighting, keeping water nearby, and asking a partner or loved one to protect a 3-hour unbroken sleep window for you when possible. Even resting your eyes without sleeping restores cognitive reserves.`;
    }

    if (query.includes('bond') || query.includes('baby') || query.includes('love') || query.includes('connect')) {
      return `Bonding isn't always an immediate flash of lightning; often it grows like quiet grass. Skin-to-skin contact, resting your baby on your chest, and speaking softly in a warm tone stimulates oxytocin naturally for both of you.\n\nBe gentle with yourself. You are already learning your baby's language step by step.`;
    }

    return `Thank you for sharing this with me, ${patientName}. Taking a moment to express what you're experiencing is an important act of self-care. As a new mother, experiencing these mixed emotions is very common. How have your sleep and physical energy been feeling today?`;
  };

  // Speak response aloud via SpeechSynthesis
  const speakResponseAloud = (text) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      setVoiceState('idle');
      return;
    }

    stopSpeaking();
    const cleanText = cleanForTTS(text);

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      const targetLang = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage);
      utterance.lang = targetLang?.ttsLocale || 'en-US';
      utterance.rate = 0.92;
      utterance.pitch = 1.05;

      const voice = getBestVoice(utterance.lang);
      if (voice) {
        utterance.voice = voice;
      }

      utterance.onstart = () => {
        setIsSpeaking(true);
        setVoiceState('speaking');
        setCurrentSpeakingSentence(cleanText);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        setVoiceState('idle');
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        setVoiceState('idle');
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('TTS execution error:', err);
      setIsSpeaking(false);
      setVoiceState('idle');
    }
  };

  // Send turn to backend Gemini service (or fallback to local engine if offline)
  const handleSendTurn = async (rawText) => {
    const text = (rawText || inputText).trim();
    if (!text) return;

    // Stop ongoing speech before generating new response
    stopSpeaking();

    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: timeString,
      status: 'delivered',
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setLastUserMessage(text);
    setInputText('');
    setInterimTranscript('');
    setVoiceState('thinking');
    setIsTyping(true);

    // Prepare history payload for multi-turn Gemini assistant
    const historyPayload = newHistory.slice(-6, -1).map((m) => ({
      role: m.sender === 'bot' ? 'model' : 'user',
      content: m.text,
    }));

    let botResponseText = '';
    let isEmergency = false;
    let serverError = null;

    try {
      const res = await fetch('/api/voice-assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: historyPayload,
          language: selectedLanguage,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.text) {
          botResponseText = data.text;
          isEmergency = Boolean(data.is_emergency);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        serverError = errData.detail || `Server returned error (${res.status})`;
      }
    } catch (err) {
      serverError = 'Unable to reach backend server at http://127.0.0.1:8000. Please ensure the backend is running.';
    }

    if (serverError) {
      setSpeechError(serverError);
      setVoiceState('idle');
      setIsTyping(false);
      const errMsg = {
        id: `msg-${Date.now() + 1}`,
        sender: 'bot',
        isError: true,
        text: `⚠️ ${serverError}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
      return;
    }

    const botMsg = {
      id: `msg-${Date.now() + 1}`,
      sender: 'bot',
      text: botResponseText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isEmergency,
    };

    setMessages((prev) => [...prev, botMsg]);
    setLastBotMessage(botResponseText);
    setIsTyping(false);

    // Speak response if in Voice Mode
    if (mode === 'voice') {
      speakResponseAloud(botResponseText);
    } else {
      setVoiceState('idle');
    }
  };

  // Start listening through Web Speech API & start live amplitude analyser
  const startListening = () => {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari, or switch to Text Mode.');
      return;
    }

    // Stop speaking if Miora is speaking (instant interruption)
    stopSpeaking();
    setSpeechError(null);
    setInterimTranscript('');

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;

      const targetLang = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage);
      recognition.lang = targetLang?.speechLang || 'en-US';

      recognition.onstart = () => {
        setVoiceState('listening');
        startAudioAnalysis();
      };

      recognition.onresult = (event) => {
        // If user speaks while Miora is speaking, interrupt immediately
        if (window.speechSynthesis && window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
          setIsSpeaking(false);
        }

        const interim = Array.from(event.results)
          .map((r) => r[0].transcript)
          .join('');
        setInterimTranscript(interim);

        const isFinal = event.results[0] && event.results[0].isFinal;
        if (isFinal && interim.trim()) {
          stopAudioAnalysis();
          recognition.stop();
          handleSendTurn(interim.trim());
        }
      };

      recognition.onerror = (event) => {
        stopAudioAnalysis();
        if (event.error === 'not-allowed') {
          setSpeechError('Microphone permission was denied. Please allow microphone access in your browser settings or switch to Text Mode.');
        } else if (event.error === 'no-speech') {
          setVoiceState('idle');
        } else {
          setSpeechError('Could not clearly recognize voice. Please try speaking again.');
          setVoiceState('idle');
        }
      };

      recognition.onend = () => {
        stopAudioAnalysis();
        // If still listening and no final transcript triggered response, return to idle
        setVoiceState((prev) => (prev === 'listening' ? 'idle' : prev));
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err);
      stopAudioAnalysis();
      setSpeechError('Unable to access microphone. Please check browser permissions.');
      setVoiceState('idle');
    }
  };

  // Stop listening manually
  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    stopAudioAnalysis();
    setVoiceState('idle');
    setInterimTranscript('');
  };

  // Toggle microphone state
  const handleToggleMic = () => {
    if (voiceState === 'listening') {
      stopListening();
    } else {
      startListening();
    }
  };

  // Genuine Interruption: stops current speech playback immediately and starts listening
  const handleInterrupt = () => {
    stopSpeaking();
    startListening();
  };

  // Replay Miora's last response
  const handleReplayLastResponse = () => {
    if (lastBotMessage) {
      speakResponseAloud(lastBotMessage);
    }
  };

  // Conclude voice session gracefully
  const handleEndVoiceSession = () => {
    stopSpeaking();
    stopListening();
    setVoiceState('idle');
    setInterimTranscript('');
  };

  // Language change handler
  const handleLanguageChange = (newLangCode) => {
    setSelectedLanguage(newLangCode);
    if (voiceState === 'listening') {
      stopListening();
    }
    stopSpeaking();
  };

  // Scroll messages to bottom in text mode
  useEffect(() => {
    if (mode === 'text') {
      messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
    }
  }, [messages, isTyping, mode]);

  const handleSelectMood = (mood) => {
    setActiveMood(mood.id);
    setPatientMood?.(mood.label);
  };

  return (
    <div className="companion-page-content">
      {/* Breadcrumb Bar */}
      <div className="companion-breadcrumb-bar">
        <NavLink to="/patient/reports" className="companion-breadcrumb-link">
          {Icons.home}
          <span>Home</span>
        </NavLink>
        <span className="companion-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
        <span className="companion-breadcrumb-current">AI Assistant</span>
      </div>

      {/* Hero Header Banner */}
      <div className="patient-card companion-hero-banner">
        <div className="companion-hero-text">
          <h1 className="patient-page-heading companion-title">Your AI Companion</h1>
          <p className="patient-page-subheading companion-sub">
            A safe, confidential space to talk, reflect, and receive compassionate guidance through your postpartum journey.
          </p>
        </div>

        <div className="companion-hero-illu-wrap" aria-hidden="true">
          <img
            src="/assets/companion-mother-baby-smooth.png"
            alt=""
            className="companion-hero-illustration"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="companion-columns-layout">
        {/* Left Column: Voice-First Interface or Text Mode */}
        <section className="patient-card companion-chat-card" aria-label="Miora Voice & Chat Assistant">
          {/* Top Bar: Mode Toggle Pill + Language Selector + Status */}
          <div className="companion-chat-header">
            <div className="companion-header-left-actions">
              {/* Mode Switcher Pill */}
              <div className="companion-mode-toggle" role="tablist" aria-label="Conversation Mode">
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'voice'}
                  className={`companion-mode-pill ${mode === 'voice' ? 'is-active' : ''}`}
                  onClick={() => {
                    stopSpeaking();
                    setMode('voice');
                  }}
                  title="Switch to Voice-First Mode"
                >
                  <span className="companion-mode-pill-icon">{Icons.mic}</span>
                  <span>Voice Mode</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'text'}
                  className={`companion-mode-pill ${mode === 'text' ? 'is-active' : ''}`}
                  onClick={() => {
                    stopAudioAnalysis();
                    if (recognitionRef.current) {
                      try { recognitionRef.current.stop(); } catch {}
                    }
                    setMode('text');
                  }}
                  title="Switch to Text Chat"
                >
                  <span className="companion-mode-pill-icon">{Icons.chatDots}</span>
                  <span>Text Mode</span>
                </button>
              </div>

              {/* Language Selector */}
              <div className="companion-lang-picker">
                <label htmlFor="voice-assistant-lang" className="companion-lang-label">
                  Language:
                </label>
                <select
                  id="voice-assistant-lang"
                  className="companion-lang-select"
                  value={selectedLanguage}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  aria-label="Select conversational language"
                >
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="companion-chat-header-actions">
              <span className={`companion-status-indicator is-${voiceState}`}>
                <span className="companion-online-dot" />
                {voiceState === 'listening'
                  ? 'Listening...'
                  : voiceState === 'thinking'
                  ? 'Thinking...'
                  : voiceState === 'speaking'
                  ? 'Speaking...'
                  : backendConfigured === false
                  ? 'Setup Key in .env'
                  : 'Online • Ready'}
              </span>
            </div>
          </div>

          {backendConfigured === false && !speechError && (
            <div className="companion-speech-error-banner" role="note" style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#92400e' }}>
              <span>ℹ️ <strong>Gemini Voice Setup:</strong> Please set your <code>GEMINI_API_KEY</code> in <code>.env</code> for live generative AI maternal support.</span>
            </div>
          )}

          {/* Speech Permission or Network Error Banner */}
          {speechError && (
            <div className="companion-speech-error-banner" role="alert">
              <span>{speechError}</span>
              <button
                type="button"
                className="companion-dismiss-error-btn"
                onClick={() => setSpeechError(null)}
                aria-label="Dismiss error"
              >
                ✕
              </button>
            </div>
          )}

          {/* =============================================================== */}
          {/* VIEW A: VOICE-FIRST INTERFACE (DEFAULT)                         */}
          {/* =============================================================== */}
          {mode === 'voice' && (
            <div className="companion-voice-workspace" aria-label="Miora Voice Companion Stage">
              {/* Central Animated Orb */}
              <div className="miora-orb-stage">
                <div
                  className={`miora-orb-container is-${voiceState}`}
                  style={{
                    transform: voiceState === 'listening' ? `scale(${1 + audioLevel * 0.35})` : undefined,
                  }}
                >
                  {/* Outer Ripple Rings for Listening/Speaking */}
                  <div
                    className="miora-orb-ripple ring-1"
                    style={{
                      opacity: voiceState === 'listening' ? 0.3 + audioLevel * 0.7 : undefined,
                      transform: voiceState === 'listening' ? `scale(${1 + audioLevel * 0.4})` : undefined,
                    }}
                    aria-hidden="true"
                  />
                  <div
                    className="miora-orb-ripple ring-2"
                    style={{
                      opacity: voiceState === 'listening' ? 0.2 + audioLevel * 0.6 : undefined,
                      transform: voiceState === 'listening' ? `scale(${1 + audioLevel * 0.6})` : undefined,
                    }}
                    aria-hidden="true"
                  />

                  {/* Core Glowing Orb */}
                  <div className="miora-orb-core">
                    <span className="miora-orb-initial">M</span>
                  </div>
                </div>

                {/* State Title & Calm Narrative Caption */}
                <div className="miora-orb-captions">
                  <h2 className="miora-orb-title">
                    {voiceState === 'listening'
                      ? 'Miora is listening...'
                      : voiceState === 'thinking'
                      ? 'Let me think about that...'
                      : voiceState === 'speaking'
                      ? 'Miora is speaking...'
                      : "I'm here whenever you want to talk."}
                  </h2>
                  <p className="miora-orb-sub">
                    {voiceState === 'listening'
                      ? 'Speak freely. Your words are private and supported.'
                      : voiceState === 'thinking'
                      ? 'Gathering supportive guidance for your maternal well-being...'
                      : voiceState === 'speaking'
                      ? 'Listening along with you'
                      : 'Tap the microphone or choose a quick prompt to begin.'}
                  </p>
                </div>
              </div>

              {/* Live Caption / Spoken Sentence Display */}
              <div className="miora-live-caption-box" role="region" aria-live="polite">
                {voiceState === 'listening' && (
                  <div className="miora-live-caption-inner is-listening">
                    <span className="miora-caption-role">You:</span>
                    <span className="miora-caption-text">
                      {interimTranscript || 'Listening for your voice...'}
                    </span>
                  </div>
                )}

                {voiceState === 'thinking' && (
                  <div className="miora-live-caption-inner is-thinking">
                    <span className="miora-caption-role">You:</span>
                    <span className="miora-caption-text">{lastUserMessage}</span>
                    <span className="miora-caption-sub-note"> — Reflecting...</span>
                  </div>
                )}

                {voiceState === 'speaking' && (
                  <div className="miora-live-caption-inner is-speaking" style={{ flexDirection: 'column', gap: '6px' }}>
                    {lastUserMessage && (
                      <div style={{ fontSize: '12.5px', color: 'var(--patient-muted)' }}>
                        <span className="miora-caption-role">You:</span> {lastUserMessage}
                      </div>
                    )}
                    <div>
                      <span className="miora-caption-role">Miora:</span>{' '}
                      <span className="miora-caption-text">{currentSpeakingSentence || lastBotMessage}</span>
                    </div>
                  </div>
                )}

                {voiceState === 'idle' && (
                  <div className="miora-live-caption-inner is-idle" style={{ flexDirection: 'column', gap: '6px' }}>
                    {lastUserMessage && (
                      <div style={{ fontSize: '12.5px', color: 'var(--patient-muted)' }}>
                        <span className="miora-caption-role">You:</span> {lastUserMessage}
                      </div>
                    )}
                    <div>
                      <span className="miora-caption-role">Miora:</span>{' '}
                      <span className="miora-caption-text">{lastBotMessage}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Voice Controls Toolbar */}
              <div className="miora-voice-toolbar" role="toolbar" aria-label="Voice Controls">
                {/* 1. Main Mic Toggle */}
                <button
                  type="button"
                  className={`miora-toolbar-btn miora-btn-mic ${voiceState === 'listening' ? 'is-active' : ''}`}
                  onClick={handleToggleMic}
                  aria-label={voiceState === 'listening' ? 'Stop listening' : 'Start speaking'}
                  title={voiceState === 'listening' ? 'Stop listening' : 'Tap to talk'}
                >
                  <span className="miora-btn-icon">
                    {voiceState === 'listening' ? Icons.micOff : Icons.mic}
                  </span>
                  <span>{voiceState === 'listening' ? 'Mute' : 'Tap to Talk'}</span>
                </button>

                {/* 2. Genuine Interruption Button (Visible when speaking) */}
                {voiceState === 'speaking' && (
                  <button
                    type="button"
                    className="miora-toolbar-btn miora-btn-interrupt"
                    onClick={handleInterrupt}
                    aria-label="Interrupt Miora and speak"
                    title="Stop Miora and start speaking"
                  >
                    <span className="miora-btn-icon">{Icons.interrupt}</span>
                    <span>Interrupt</span>
                  </button>
                )}

                {/* 3. Replay Button */}
                <button
                  type="button"
                  className="miora-toolbar-btn"
                  onClick={handleReplayLastResponse}
                  disabled={!lastBotMessage || voiceState === 'thinking'}
                  aria-label="Replay last response"
                  title="Repeat Miora's last response aloud"
                >
                  <span className="miora-btn-icon">{Icons.replay}</span>
                  <span>Replay</span>
                </button>

                {/* 4. End Session Button */}
                <button
                  type="button"
                  className="miora-toolbar-btn miora-btn-end"
                  onClick={handleEndVoiceSession}
                  disabled={voiceState === 'idle'}
                  aria-label="End voice session"
                  title="End conversation and return to idle"
                >
                  <span className="miora-btn-icon">{Icons.endPhone}</span>
                  <span>End</span>
                </button>
              </div>

              {/* Quick Spoken Prompts Strip */}
              <div className="companion-chips-row" aria-label="Suggested Prompts">
                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Could you share some simple coping strategies?')}
                >
                  <span className="companion-chip-icon">{Icons.leaf}</span>
                  <span>Coping Strategies</span>
                </button>

                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Can you guide me through a calming breathing exercise?')}
                >
                  <span className="companion-chip-icon">{Icons.lotus}</span>
                  <span>Breathing Exercise</span>
                </button>

                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Should I see a doctor about how I am feeling?')}
                >
                  <span className="companion-chip-icon">{Icons.calendarCheck}</span>
                  <span>Should I See a Doctor?</span>
                </button>
              </div>
            </div>
          )}

          {/* =============================================================== */}
          {/* VIEW B: TRADITIONAL TEXT CHAT MODE (SEAMLESS HISTORY SHARE)     */}
          {/* =============================================================== */}
          {mode === 'text' && (
            <div className="companion-text-workspace" aria-label="Traditional Text Chat">
              {/* Messages Stream */}
              <div className="companion-chat-messages" role="log" aria-live="polite">
                {messages.map((msg) => {
                  const isBot = msg.sender === 'bot';
                  return (
                    <div key={msg.id} className={`companion-msg-row ${isBot ? 'is-bot' : 'is-user'}`}>
                      {isBot && (
                        <div className="companion-msg-avatar" aria-hidden="true">
                          <span className="companion-msg-avatar-char">M</span>
                        </div>
                      )}

                      <div className="companion-msg-col">
                        <div className="companion-msg-bubble">
                          {msg.text.split('\n\n').map((para, i) => (
                            <p key={i} style={{ margin: i === 0 ? 0 : '8px 0 0 0' }}>{para}</p>
                          ))}
                        </div>
                        <div className="companion-msg-meta">
                          <time>{msg.timestamp}</time>
                          {isBot && (
                            <button
                              type="button"
                              className="companion-msg-listen-btn"
                              onClick={() => speakResponseAloud(msg.text)}
                              aria-label="Listen to response aloud"
                              title="Listen to response aloud"
                            >
                              <span style={{ fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                                {Icons.mic} Listen
                              </span>
                            </button>
                          )}
                          {!isBot && msg.status && (
                            <span className="companion-check-icon" aria-label="Delivered">
                              ✓
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {isTyping && (
                  <div className="companion-msg-row is-bot">
                    <div className="companion-msg-avatar" aria-hidden="true">
                      <span className="companion-msg-avatar-char">M</span>
                    </div>
                    <div className="companion-typing-row" aria-label="Miora is typing">
                      <span className="companion-typing-dot" />
                      <span className="companion-typing-dot" />
                      <span className="companion-typing-dot" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Prompt Chips */}
              <div className="companion-chips-row" aria-label="Suggested Prompts">
                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Could you share some simple coping strategies?')}
                >
                  <span className="companion-chip-icon">{Icons.leaf}</span>
                  <span>Coping Strategies</span>
                </button>

                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Can you guide me through a calming breathing exercise?')}
                >
                  <span className="companion-chip-icon">{Icons.lotus}</span>
                  <span>Breathing Exercise</span>
                </button>

                <button
                  type="button"
                  className="companion-prompt-chip"
                  onClick={() => handleSendTurn('Should I see a doctor about how I am feeling?')}
                >
                  <span className="companion-chip-icon">{Icons.calendarCheck}</span>
                  <span>Should I See a Doctor?</span>
                </button>
              </div>

              {/* Message Input Bar */}
              <form
                className="companion-input-capsule"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendTurn();
                }}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      handleSendTurn(`[Attached note: ${e.target.files[0].name}]`);
                    }
                  }}
                />
                <button
                  type="button"
                  className="companion-attach-btn"
                  onClick={() => fileInputRef.current?.click()}
                  aria-label="Attach document or note"
                >
                  {Icons.paperclip}
                </button>

                <input
                  type="text"
                  className="companion-text-input"
                  placeholder="Ask me anything about your maternal well-being..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  aria-label="Message Miora AI"
                />

                <button
                  type="button"
                  className="companion-mic-btn"
                  onClick={handleToggleMic}
                  aria-label="Voice input"
                  title="Voice input"
                >
                  {Icons.mic}
                </button>

                <button
                  type="submit"
                  className="companion-send-btn"
                  aria-label="Send message"
                  disabled={!inputText.trim()}
                >
                  {Icons.send}
                </button>
              </form>
            </div>
          )}
        </section>

        {/* Right Column – Guidance, Mood Tracker & Resources */}
        <aside className="companion-info-panels" aria-label="Companion Guidance & Resources">
          {/* Panel 1: Mood Today */}
          <section className="patient-card companion-info-card" aria-labelledby="mood-card-title">
            <div className="companion-card-header">
              <span className="companion-help-icon" style={{ color: '#d93c75' }} aria-hidden="true">
                {Icons.barChart}
              </span>
              <h3 id="mood-card-title" className="companion-card-title">Your Mood Today</h3>
            </div>

            <p className="companion-card-desc">How are you feeling right now?</p>

            <div className="companion-mood-row" role="radiogroup" aria-label="Select your mood today">
              {MoodFaces.map((face) => {
                const isActive = activeMood === face.id;
                return (
                  <button
                    key={face.id}
                    type="button"
                    className={`companion-mood-btn ${isActive ? 'is-active' : ''}`}
                    onClick={() => handleSelectMood(face)}
                    role="radio"
                    aria-checked={isActive}
                    aria-label={face.label}
                  >
                    {face.render(22)}
                  </button>
                );
              })}
            </div>

            <div className="companion-mood-label-row">
              <span className="companion-mood-pill">
                Current: {MoodFaces.find((m) => m.id === activeMood)?.label || 'Okay'}
              </span>
            </div>
          </section>

          {/* Panel 2: How I Can Help */}
          <section className="patient-card companion-info-card" aria-labelledby="help-card-title">
            <div className="companion-card-header">
              <span className="companion-sparkle-icon" aria-hidden="true">{Icons.sparkles}</span>
              <h3 id="help-card-title" className="companion-card-title">How I Can Help</h3>
            </div>
            <ul className="companion-help-list">
              <li
                className="companion-help-item"
                onClick={() => handleSendTurn("I'd like to talk about how I've been feeling.")}
              >
                <span className="companion-help-icon">{Icons.chatDots}</span>
                <span>Talk about your feelings</span>
              </li>
              <li
                className="companion-help-item"
                onClick={() => handleSendTurn("Can you suggest some gentle self-care activities for today?")}
              >
                <span className="companion-help-icon">{Icons.lotus}</span>
                <span>Suggest self-care activities</span>
              </li>
              <li
                className="companion-help-item"
                onClick={() => handleSendTurn("I have questions about postpartum recovery and maternal feelings.")}
              >
                <span className="companion-help-icon">{Icons.book}</span>
                <span>Answer postpartum questions</span>
              </li>
              <li
                className="companion-help-item"
                onClick={() => navigate('/patient/connect-doctor')}
              >
                <span className="companion-help-icon">{Icons.stethoscope}</span>
                <span>Connect with your care team</span>
              </li>
            </ul>
          </section>

          {/* Panel 3: Quick Resources */}
          <section className="patient-card companion-info-card" aria-labelledby="resources-card-title">
            <div className="companion-card-header">
              <span className="companion-help-icon" style={{ color: '#d93c75' }} aria-hidden="true">
                {Icons.book}
              </span>
              <h3 id="resources-card-title" className="companion-card-title">Quick Resources</h3>
            </div>

            <div className="companion-resources-grid">
              <div
                className="companion-resource-card"
                onClick={() => setActiveModal('audio')}
                role="button"
                tabIndex={0}
                aria-label="Open Relaxation Audio"
              >
                <span className="companion-resource-icon">{Icons.playCircle}</span>
                <span className="companion-resource-title">
                  Relaxation<br />Audio
                </span>
              </div>

              <div
                className="companion-resource-card"
                onClick={() => setActiveModal('meditation')}
                role="button"
                tabIndex={0}
                aria-label="Open Guided Meditation"
              >
                <span className="companion-resource-icon">{Icons.lotus}</span>
                <span className="companion-resource-title">
                  Guided<br />Meditation
                </span>
              </div>

              <div
                className="companion-resource-card"
                onClick={() => setActiveModal('tips')}
                role="button"
                tabIndex={0}
                aria-label="Open Postpartum Tips"
              >
                <span className="companion-resource-icon">{Icons.documentHeart}</span>
                <span className="companion-resource-title">
                  Postpartum<br />Tips
                </span>
              </div>
            </div>
          </section>
        </aside>
      </div>

      {/* Interactive Resource Modals */}
      {activeModal && (
        <div className="companion-modal-backdrop" onClick={() => setActiveModal(null)} role="dialog">
          <div className="patient-card companion-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h4 className="companion-modal-title">
                {activeModal === 'audio' && 'Relaxation Audio'}
                {activeModal === 'meditation' && 'Guided Meditation'}
                {activeModal === 'tips' && 'Postpartum Recovery Tips'}
              </h4>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <div className="companion-modal-body">
              {activeModal === 'audio' && (
                <div style={{ textAlign: 'center', padding: '12px 0' }}>
                  <p style={{ fontSize: '13px', color: '#5b4750', marginBottom: '16px' }}>
                    Soothing ocean swell and gentle ambient soundscape designed to calm postpartum nervous system arousal.
                  </p>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: 'var(--patient-blush-soft)', border: '1px solid var(--patient-blush-border)', borderRadius: '30px', color: '#d93c75', fontWeight: 600, fontSize: '13px' }}>
                    <span>▶ Playing: Gentle Ocean Waves (04:12)</span>
                  </div>
                </div>
              )}

              {activeModal === 'meditation' && (
                <div style={{ textAlign: 'center', padding: '12px 0' }}>
                  <p style={{ fontSize: '13px', color: '#5b4750', marginBottom: '16px' }}>
                    A 3-minute mindful pause for mothers: softening body tension and embracing self-compassion.
                  </p>
                  <div style={{ width: '84px', height: '84px', borderRadius: '50%', background: 'var(--patient-blush-pill)', border: '3px solid #ea3b75', margin: '0 auto 12px auto', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d93c75', fontSize: '14px', fontWeight: 700 }}>
                    Inhale
                  </div>
                  <small style={{ color: '#8c747f' }}>Breathe softly with the gentle pulsing rhythm</small>
                </div>
              )}

              {activeModal === 'tips' && (
                <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#4a353f', lineHeight: 1.6 }}>
                  <li><strong>Rest when possible:</strong> Even 15 minutes of quiet resting restores neurological energy.</li>
                  <li><strong>Hydration &amp; Warm Nourishment:</strong> Soups, warm teas, and iron-rich foods aid healing.</li>
                  <li><strong>Ask for specific help:</strong> Let family or friends hold household tasks so you can bond and recover.</li>
                  <li><strong>Be gentle with yourself:</strong> Baby blues and mood fluctuations are natural hormonal transitions.</li>
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AiAssistantScreen;
