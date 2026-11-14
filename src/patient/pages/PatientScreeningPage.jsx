import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../../dashboard/context/ClinicalContext.jsx';
import epdsTranslationsData from '../../../data/epds_translations.json';
import {
  mapSpokenResponseToEpdsChoice,
  SPEECH_LANG_CODES,
  CLARIFICATION_PROMPTS,
  SILENCE_PROMPTS,
} from '../services/speechEpdsMapper.js';
import {
  DEMO_VIDEO_SRC,
  DEMO_VIDEO_DURATION,
  DEMO_INTERVIEW_TIMELINE,
} from '../services/demoInterviewData.js';
import './screening.css';

const DEFAULT_SUPPORTED_LANGUAGES = epdsTranslationsData.supported_languages || [
  { code: 'en', name: 'English', native_name: 'English' },
  { code: 'hi', name: 'Hindi', native_name: 'हिन्दी' },
  { code: 'bn', name: 'Bengali', native_name: 'বাংলা' },
  { code: 'kn', name: 'Kannada', native_name: 'ಕನ್ನಡ' },
  { code: 'ta', name: 'Tamil', native_name: 'தமிழ்' },
  { code: 'te', name: 'Telugu', native_name: 'తెలుగు' },
  { code: 'ml', name: 'Malayalam', native_name: 'മലയാളം' },
  { code: 'mr', name: 'Marathi', native_name: 'मराठी' },
];

const EPDS_QUESTION_ORDER = [
  'EPDS_Q01',
  'EPDS_Q02',
  'EPDS_Q03',
  'EPDS_Q04',
  'EPDS_Q05',
  'EPDS_Q06',
  'EPDS_Q07',
  'EPDS_Q08',
  'EPDS_Q09',
  'EPDS_Q10',
];

const INTRO_MESSAGES = {
  en: "Hi Amara! I'm Miora, your maternal wellbeing companion. Over the past 7 days, how have you been feeling? I'll guide you through 10 brief questions to understand your emotional wellbeing. There are no right or wrong answers—take all the time you need.",
  hi: "नमस्ते अमरा! मैं मायोरा हूँ, आपकी मातृ कल्याण साथी। पिछले 7 दिनों में आप कैसा महसूस कर रही हैं, यह समझने के लिए मैं आपसे 10 संक्षिप्त प्रश्न पूछूँगी। कोई सही या गलत उत्तर नहीं है—अपना पूरा समय लें।",
  bn: "নমস্কার অমরা! আমি মায়োরা, আপনার মাতৃত্বকালীন সুস্থতার সঙ্গী। গত ৭ দিনে আপনি কেমন অনুভব করছেন তা বোঝার জন্য আমি আপনাকে ১০টি সংক্ষিপ্ত প্রশ্ন জিজ্ঞাসা করব। কোনো সঠিক বা ভুল উত্তর নেই—আপনার প্রয়োজনীয় সময় নিন।",
  kn: "ನಮಸ್ಕಾರ ಅಮರಾ! ನಾನು ಮಯೋರಾ, ನಿಮ್ಮ ಮಾತೃತ್ವ ಕ್ಷೇಮದ ಒಡನಾಡಿ. ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ ನೀವು ಹೇಗೆ ಭಾವಿಸುತ್ತಿದ್ದೀರಿ ಎಂಬುದನ್ನು ತಿಳಿಯಲು ನಾನು 10 ಸಂಕ್ಷಿಪ್ತ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳುತ್ತೇನೆ. ಯಾವುದೇ ಸರಿ ಅಥವಾ ತಪ್ಪು ಉತ್ತರಗಳಿಲ್ಲ—ನಿಮ್ಮ ಸಮಯವನ್ನು ತೆಗೆದುಕೊಳ್ಳಿ.",
  ta: "வணக்கம் அமரா! நான் மயோரா, உங்கள் தாய்மை நல்வாழ்வு தோழி. கடந்த 7 நாட்களில் நீங்கள் எப்படி உணர்கிறீர்கள் என்பதைப் புரிந்துகொள்ள 10 சுருக்கமான கேள்விகளைக் கேட்பேன். சரியான அல்லது தவறான பதில்கள் எதுவும் இல்லை—உங்கள் நேரத்தை எடுத்துக்கொள்ளுங்கள்.",
  te: "నమస్కారం అమరా! నేను మయోరా, మీ మాతృత్వ శ్రేయస్సు సహచరిని. గత 7 రోజులలో మీరు ఎలా భావిస్తున్నారో అర్థం చేసుకోవడానికి నేను 10 సంక్షిప్త ప్రశ్నలను అడుగుతాను. సరైన లేదా తప్పు సమాధానాలు లేవు—మీ సమయాన్ని తీసుకోండి.",
  ml: "നമസ്കാരം അമര! ഞാൻ മയോറ, നിങ്ങളുടെ മാതൃക്ഷേമ സഹായി. കഴിഞ്ഞ 7 ദിവസങ്ങളിൽ നിങ്ങൾക്ക് എങ്ങനെ തോന്നുന്നുവെന്ന് മനസ്സിലാക്കാൻ ഞാൻ 10 ലളിതമായ ചോദ്യങ്ങൾ ചോദിക്കും. ശരിയോ തെറ്റോ ആയ ഉത്തരങ്ങളില്ല—നിങ്ങളുടെ സമയമെടുക്കൂ.",
  mr: "नमस्ते अमरा! मी मायोरा आहे, तुमची मातृ कल्याण साथीदार. मागील ७ दिवसांत तुम्हाला कसे वाटत आहे हे जाणून घेण्यासाठी मी तुम्हाला १० लहान प्रश्न विचारेन. कोणतीही योग्य किंवा अयोग्य उत्तरे नाहीत—तुमचा वेळ घ्या.",
};

const EMPATHETIC_ACKS = {
  en: [
    'Thank you for sharing that with me.',
    'I hear you. Thank you for being open.',
    'Thank you, that helps me understand how you’ve been feeling.',
    'Got it, thank you for letting me know.',
    'I appreciate your openness.',
    'Thank you. Take your time with these next questions.',
    'I understand. You’re doing wonderfully.',
    'Thank you for your honesty.',
    'I’m listening and right here with you.',
    'Thank you for reflecting on that with me.',
  ],
  hi: [
    'यह बात मुझसे साझा करने के लिए धन्यवाद।',
    'मैं समझ सकती हूँ। खुलकर बताने के लिए धन्यवाद।',
    'धन्यवाद, इससे मुझे यह समझने में मदद मिलती है कि आप कैसा महसूस कर रही हैं।',
    'समझा, मुझे बताने के लिए धन्यवाद।',
    'आपकी सच्चाई के लिए धन्यवाद।',
    'धन्यवाद। अगले प्रश्नों के साथ अपना समय लें।',
    'मैं समझती हूँ। आप बहुत अच्छा कर रही हैं।',
    'अपनी भावनाएं साझा करने के लिए धन्यवाद।',
    'मैं आपकी बात सुन रही हूँ।',
    'यह साझा करने के लिए धन्यवाद।',
  ],
  bn: [
    'আমার সাথে এটি ভাগ করার জন্য আপনাকে ধন্যবাদ।',
    'আমি বুঝতে পারছি। খোলামেলা হওয়ার জন্য ধন্যবাদ।',
    'ধন্যবাদ, এটি আমাকে আপনি কেমন বোধ করছেন তা বুঝতে সাহায্য করে।',
    'ধন্যবাদ আমাকে জানানোর জন্য।',
    'আপনার সততার জন্য ধন্যবাদ।',
    'ধন্যবাদ। পরবর্তী প্রশ্নের জন্য সময় নিন।',
    'আমি বুঝতে পেরেছি।',
    'ধন্যবাদ আপনার অনুভূতি প্রকাশ করার জন্য।',
    'আমি আপনার কথা শুনছি।',
    'এটি শেয়ার করার জন্য ধন্যবাদ।',
  ],
  kn: [
    'ಇದನ್ನು ನನ್ನೊಂದಿಗೆ ಹಂಚಿಕೊಂಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು.',
    'ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ಮುಕ್ತವಾಗಿರುವುದಕ್ಕೆ ಧನ್ಯವಾದಗಳು.',
    'ಧನ್ಯವಾದಗಳು, ನೀವು ಹೇಗೆ ಭಾವಿಸುತ್ತಿದ್ದೀರಿ ಎಂದು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಇದು ಸಹಾಯ ಮಾಡುತ್ತದೆ.',
    'ತಿಳಿಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು.',
    'ನಿಮ್ಮ ಪ್ರಾಮಾಣಿಕತೆಗೆ ಧನ್ಯವಾದಗಳು.',
    'ಧನ್ಯವಾದಗಳು. ಮುಂದಿನ ಪ್ರಶ್ನೆಗಳಿಗೆ ನಿಮ್ಮ ಸಮಯವನ್ನು ತೆಗೆದುಕೊಳ್ಳಿ.',
    'ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ.',
    'ಧನ್ಯವಾದಗಳು.',
    'ನಾನು ಕೇಳುತ್ತಿದ್ದೇನೆ.',
    'ಹಂಚಿಕೊಂಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು.',
  ],
  ta: [
    'இதை என்னுடன் பகிர்ந்ததற்கு நன்றி.',
    'நான் புரிந்துகொள்கிறேன். வெளிப்படையாக இருந்ததற்கு நன்றி.',
    'நன்றி, நீங்கள் எப்படி உணர்கிறீர்கள் என்பதைப் புரிந்துகொள்ள இது உதவுகிறது.',
    'தெரிவித்ததற்கு நன்றி.',
    'உங்கள் நேர்மைக்கு நன்றி.',
    'நன்றி. அடுத்த கேள்விகளுக்கு உங்கள் நேரத்தை எடுத்துக்கொள்ளுங்கள்.',
    'நான் புரிந்துகொள்கிறேன்.',
    'நன்றி.',
    'நான் கேட்டுக்கொண்டிருக்கிறேன்.',
    'பகிர்ந்தமைக்கு நன்றி.',
  ],
  te: [
    'దీన్ని నాతో పంచుకున్నందుకు ధన్యవాదాలు.',
    'నేను అర్థం చేసుకున్నాను. నిజాయితీగా ఉన్నందుకు ధన్యవాదాలు.',
    'ధన్యవాదాలు, మీరు ఎలా భావిస్తున్నారో అర్థం చేసుకోవడానికి ఇది సహాయపడుతుంది.',
    'తెలిపినందుకు ధన్యవాదాలు.',
    'మీ నిజాయితీకి ధన్యవాదాలు.',
    'ధన్యవాదాలు. తదుపరి ప్రశ్నలకు మీ సమయాన్ని వెచ్చించండి.',
    'నేను అర్థం చేసుకున్నాను.',
    'ధನ್ಯవాదాలు.',
    'నేను వింటున్నాను.',
    'పంచుకున్నందుకు ధన్యవాదాలు.',
  ],
  ml: [
    'ഇത് എന്നോട് പങ്കുവെച്ചതിന് നന്ദി.',
    'എനിക്ക് മനസ്സിലാകുന്നു. തുറന്നുപറഞ്ഞതിന് നന്ദി.',
    'നന്ദി, നിങ്ങൾക്ക് എങ്ങനെ തോന്നുന്നുവെന്ന് മനസ്സിലാക്കാൻ ഇത് സഹായിക്കുന്നു.',
    'അറിയിച്ചതിന് നന്ദി.',
    'നിങ്ങളുടെ സത്യസന്ധതയ്ക്ക് നന്ദി.',
    'നന്ദി. അടുത്ത ചോദ്യങ്ങൾക്കായി സമയമെടുക്കൂ.',
    'എനിക്ക് മനസ്സിലാകുന്നു.',
    'നന്ദി.',
    'ഞാൻ കേൾക്കുന്നുണ്ട്.',
    'പങ്കുവെച്ചതിന് നന്ദി.',
  ],
  mr: [
    'हे माझ्याशी शेअर केल्याबद्दल धन्यवाद.',
    'मी समजू शकते. मोकळेपणाने सांगितल्याबद्दल धन्यवाद.',
    'धन्यवाद, यामुळे मला तुम्ही कसे अनुभवत आहात हे समजण्यास मदत होते.',
    'सांगितल्याबद्दल धन्यवाद.',
    'तुमच्या प्रामाणिकपणाबद्दल धन्यवाद.',
    'धन्यवाद. पुढील प्रश्नांसाठी तुमचा वेळ घ्या.',
    'मी समजू शकते.',
    'धन्यवाद.',
    'मी ऐकत आहे.',
    'शेअर केल्याबद्दल धन्यवाद.',
  ],
};

export function getQuestionDetails(qid, lang = 'en') {
  const qData = epdsTranslationsData.questions?.[qid];
  if (!qData) return null;
  const trans = qData.translations?.[lang] || qData.translations?.['en'] || {};
  return {
    id: qid,
    questionNumber: qData.question_number,
    reverseScored: qData.reverse_scored,
    safetyCritical: qData.safety_critical,
    questionText: trans.question || '',
    options: trans.response_options || [],
  };
}

export function calculateEpdsScore(answers) {
  let totalScore = 0;
  let q10Score = 0;
  let q10Triggered = false;

  EPDS_QUESTION_ORDER.forEach((qid) => {
    const optIdx = answers[qid];
    if (optIdx !== undefined && optIdx !== null) {
      const qMeta = epdsTranslationsData.questions[qid];
      const isReverse = qMeta?.reverse_scored;
      const score = isReverse ? (3 - optIdx) : optIdx;
      totalScore += score;
      if (qid === 'EPDS_Q10') {
        q10Score = score;
        if (score > 0) {
          q10Triggered = true;
        }
      }
    }
  });

  return { totalScore, q10Score, q10Triggered };
}

export function PatientScreeningPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const clinical = useClinicalData();

  // Mode state: 'live' (Mode A: Live Patient Screening) | 'demo' (Mode B: Prerecorded Mother Interview)
  const initialMode = searchParams.get('mode') === 'demo' ? 'demo' : 'live';
  const [screeningMode, setScreeningMode] = useState(initialMode);

  // Media states for Live Mode
  const [cameraOn, setCameraOn] = useState(true);
  const [micOn, setMicOn] = useState(true);
  const [isRecording, setIsRecording] = useState(true);
  const [mediaStatus, setMediaStatus] = useState('requesting'); // 'requesting' | 'active' | 'denied' | 'unavailable' | 'off'
  const [mediaError, setMediaError] = useState(null);
  const [cameraStatus, setCameraStatus] = useState('requesting');
  const [micStatus, setMicStatus] = useState('requesting');
  const [micVolume, setMicVolume] = useState(0); // 0-100 real audio level from AnalyserNode
  const [timerSeconds, setTimerSeconds] = useState(134); // starts at 02:14
  const [isFullscreen, setIsFullscreen] = useState(false);

  // EPDS Multilingual Questionnaire States (Live Mode)
  const [selectedLang, setSelectedLang] = useState('en');
  const [supportedLanguages] = useState(DEFAULT_SUPPORTED_LANGUAGES);
  const [answers, setAnswers] = useState({}); // { [question_id]: selected_index (0-3) }
  const [currentQIndex, setCurrentQIndex] = useState(0); // 0..9 active, 10 completed
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCrisisModal, setShowCrisisModal] = useState(false);
  const [crisisAlertData, setCrisisAlertData] = useState(null);

  // Chat conversation state (Live Mode)
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [lastUserAnswer, setLastUserAnswer] = useState('');

  // Demo Mode States (Mode B: Prerecorded Gemini Mother Interview)
  const [demoTime, setDemoTime] = useState(0);
  const [isDemoPlaying, setIsDemoPlaying] = useState(true);
  const [isDemoMuted, setIsDemoMuted] = useState(false); // Default unmuted so mother interview audio can be heard
  const [demoAnswers, setDemoAnswers] = useState({});
  const [demoCompletedSteps, setDemoCompletedSteps] = useState(new Set());
  const [demoActiveStepIndex, setDemoActiveStepIndex] = useState(0);
  const [isDemoComplete, setIsDemoComplete] = useState(false);

  // Refs
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const videoStreamRef = useRef(null);
  const audioStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const videoContainerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const demoVideoRef = useRef(null);

  // Web Speech recognition state & ref (Live Mode)
  const recognitionRef = useRef(null);
  const [isListening, setIsListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [spokenDraftText, setSpokenDraftText] = useState('');
  const [speechClarification, setSpeechClarification] = useState(null);

  // SpeechSynthesis TTS helper (Live Mode question reader)
  const stopSpeaking = () => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
  };

  const getBestVoice = (langLocale = 'en-US') => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    if (voices.length === 0) return null;
    const langPrefix = langLocale.split('-')[0].toLowerCase();
    const langVoices = voices.filter(
      (v) => v.lang && (v.lang.toLowerCase().startsWith(langPrefix) || v.lang.toLowerCase().replace('_', '-').startsWith(langPrefix))
    );
    const pool = langVoices.length > 0 ? langVoices : voices;
    const femaleVoice = pool.find((v) => {
      const name = (v.name || '').toLowerCase();
      return (
        name.includes('female') ||
        name.includes('zira') ||
        name.includes('samantha') ||
        name.includes('victoria') ||
        name.includes('kavya') ||
        name.includes('lekha') ||
        name.includes('priya') ||
        name.includes('swara') ||
        name.includes('kalpana') ||
        name.includes('geeta') ||
        name.includes('veena') ||
        name.includes('google us english')
      );
    });
    return femaleVoice || pool[0] || null;
  };

  const speakQuestion = (questionText, lang = 'en') => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    stopSpeaking();
    try {
      const utterance = new SpeechSynthesisUtterance(questionText);
      const locale = SPEECH_LANG_CODES[lang] || 'en-US';
      utterance.lang = locale;
      utterance.rate = 0.94;
      utterance.pitch = 1.05;
      const voice = getBestVoice(locale);
      if (voice) utterance.voice = voice;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('TTS speak notice:', e);
    }
  };

  // Speak active question aloud when index changes in Live Mode
  useEffect(() => {
    if (screeningMode === 'live' && currentQIndex < 10) {
      const qid = EPDS_QUESTION_ORDER[currentQIndex];
      const details = getQuestionDetails(qid, selectedLang);
      if (details?.questionText) {
        speakQuestion(details.questionText, selectedLang);
      }
    }
  }, [currentQIndex, selectedLang, screeningMode]);

  // Decoupled 1: Initialize microphone independently with Web Audio Analyser (AUDIO ONLY)
  const initMicrophone = async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMicStatus('unavailable');
      return null;
    }
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = audioStream;
      setMicStatus('active');

      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          audioContextRef.current = audioCtx;
          const source = audioCtx.createMediaStreamSource(audioStream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          analyser.smoothingTimeConstant = 0.5;
          source.connect(analyser);
          analyserRef.current = analyser;

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const updateVolume = () => {
            if (analyserRef.current) {
              analyserRef.current.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
              }
              const avg = sum / dataArray.length;
              const pct = Math.min(100, Math.round((avg / 128) * 100));
              setMicVolume(pct);
            }
            animFrameRef.current = requestAnimationFrame(updateVolume);
          };
          animFrameRef.current = requestAnimationFrame(updateVolume);
        }
      } catch (audioErr) {
        console.warn('Audio analyser notice:', audioErr);
      }

      return audioStream;
    } catch (err) {
      console.warn('Microphone access notice:', err);
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setMicStatus('denied');
      } else {
        setMicStatus('unavailable');
      }
      return null;
    }
  };

  // Helper to safely bind MediaStream to video element with all browser autoplay/inline requirements
  const attachStreamToVideo = (videoEl, stream) => {
    if (!videoEl || !stream) return;
    try {
      videoEl.muted = true;
      videoEl.defaultMuted = true;
      videoEl.playsInline = true;
      videoEl.setAttribute('muted', '');
      videoEl.setAttribute('playsinline', '');
      if (videoEl.srcObject !== stream) {
        videoEl.srcObject = stream;
      }
      const playPromise = videoEl.play?.();
      if (playPromise && typeof playPromise.catch === 'function') {
        playPromise.catch((err) => {
          console.warn('Video element play() notice:', err);
        });
      }
    } catch (e) {
      console.warn('Failed attaching stream to video element:', e);
    }
  };

  // Decoupled 2: Initialize camera independently (VIDEO ONLY - never requests audio)
  const initCamera = async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setCameraStatus('unavailable');
      setMediaStatus('unavailable');
      setMediaError('Camera preview is unavailable in this browser environment.');
      return null;
    }

    try {
      setCameraStatus('requesting');
      setMediaStatus('requesting');
      setMediaError(null);

      // Attempt high-quality constraints first; fall back to basic video constraint if device/browser throws OverconstrainedError
      let stream = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        });
      } catch (constraintErr) {
        console.warn('High constraint getUserMedia failed, falling back to generic video:', constraintErr);
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: true });
        } catch (fallbackErr) {
          throw fallbackErr;
        }
      }

      videoStreamRef.current = stream;
      streamRef.current = stream;
      setCameraStatus('active');
      setMediaStatus('active');
      setMediaError(null);

      if (videoRef.current) {
        attachStreamToVideo(videoRef.current, stream);
      }
      return stream;
    } catch (err) {
      console.warn('Camera access notice:', err);
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setCameraStatus('denied');
        setMediaStatus('denied');
        setMediaError(
          'Camera permission was denied. Please allow camera access in browser settings to view your live camera preview.'
        );
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setCameraStatus('unavailable');
        setMediaStatus('unavailable');
        setMediaError('No camera detected on this system.');
      } else if (name === 'NotReadableError' || name === 'TrackStartError') {
        setCameraStatus('unavailable');
        setMediaStatus('unavailable');
        setMediaError('Camera is currently in use by another application.');
      } else {
        setCameraStatus('unavailable');
        setMediaStatus('unavailable');
        setMediaError('Unable to access video capture: ' + (err?.message || 'Check browser permissions.'));
      }
      return null;
    }
  };

  const handleToggleCamera = () => {
    setCameraOn((prev) => {
      const next = !prev;
      const stream = videoStreamRef.current || streamRef.current;
      if (next) {
        const hasLiveTrack = stream && stream.getVideoTracks().some((t) => t.readyState === 'live');
        if (!hasLiveTrack) {
          initCamera();
        } else {
          stream.getVideoTracks().forEach((track) => {
            track.enabled = true;
          });
          setCameraStatus('active');
          setMediaStatus('active');
          if (videoRef.current) {
            attachStreamToVideo(videoRef.current, stream);
          }
        }
      } else {
        if (stream) {
          stream.getVideoTracks().forEach((track) => {
            track.enabled = false;
          });
        }
      }
      return next;
    });
  };

  // Safe release of all media streams & audio context
  const releaseMediaHardware = () => {
    stopSpeaking();
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close?.().catch(() => {});
      } catch (_) {}
      audioContextRef.current = null;
    }
    if (videoStreamRef.current) {
      videoStreamRef.current.getTracks().forEach((t) => t.stop());
      videoStreamRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((t) => t.stop());
      audioStreamRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort?.();
      } catch (_) {}
    }
  };

  // Mount effect: initialize hardware ONLY if starting in Live Mode
  useEffect(() => {
    if (initialMode === 'live') {
      initMicrophone();
      initCamera();
    } else {
      setCameraOn(false);
      setMicOn(false);
      setMediaStatus('off');
      setCameraStatus('off');
      setMicStatus('off');
    }

    return () => {
      releaseMediaHardware();
    };
  }, []);

  // Ensure stream is attached to video whenever video element mounts or camera is toggled back on
  useEffect(() => {
    if (screeningMode === 'live' && cameraOn && mediaStatus === 'active') {
      const curStream = videoStreamRef.current || streamRef.current;
      if (videoRef.current && curStream) {
        attachStreamToVideo(videoRef.current, curStream);
      }
    }
  }, [cameraOn, mediaStatus, screeningMode]);

  // Sync camera track enabled state with cameraOn
  useEffect(() => {
    const stream = videoStreamRef.current || streamRef.current;
    if (stream) {
      const videoTracks = stream.getVideoTracks();
      videoTracks.forEach((track) => {
        track.enabled = cameraOn;
      });
    }
  }, [cameraOn]);

  // Sync mic track enabled state with micOn
  useEffect(() => {
    const stream = audioStreamRef.current || streamRef.current;
    if (stream) {
      const audioTracks = stream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = micOn;
      });
    }
  }, [micOn]);

  // Mode switcher handler with strict hardware lifecycle separation
  const handleSwitchMode = (mode) => {
    setScreeningMode(mode);
    setSearchParams(mode === 'demo' ? { mode: 'demo' } : {});

    if (mode === 'demo') {
      // Release camera and mic immediately when entering demo mode (turns off laptop camera indicator)
      releaseMediaHardware();
      setCameraOn(false);
      setMicOn(false);
      setMediaStatus('off');
      setCameraStatus('off');
      setMicStatus('off');
      setMicVolume(0);
    } else {
      // Re-enable camera and mic when entering live mode
      setCameraOn(true);
      setMicOn(true);
      initMicrophone();
      initCamera();
    }
  };

  // Demo Video Controls & Time Sync
  const handleTogglePlayDemoVideo = () => {
    if (!demoVideoRef.current) return;
    if (isDemoPlaying) {
      demoVideoRef.current.pause?.();
      setIsDemoPlaying(false);
    } else {
      demoVideoRef.current.play?.().catch(() => {});
      setIsDemoPlaying(true);
    }
  };

  const handleToggleMuteDemoVideo = () => {
    if (!demoVideoRef.current) return;
    const nextMuted = !isDemoMuted;
    demoVideoRef.current.muted = nextMuted;
    setIsDemoMuted(nextMuted);
  };

  const handleRestartDemo = () => {
    if (demoVideoRef.current) {
      demoVideoRef.current.currentTime = 0;
      demoVideoRef.current.play?.().catch(() => {});
      setIsDemoPlaying(true);
    }
    setDemoTime(0);
    setDemoAnswers({});
    setDemoCompletedSteps(new Set());
    setDemoActiveStepIndex(0);
    setIsDemoComplete(false);
  };

  const handleDemoTimeUpdate = () => {
    if (!demoVideoRef.current) return;
    const curTime = demoVideoRef.current.currentTime;
    setDemoTime(curTime);

    // Evaluate dialogue timeline
    DEMO_INTERVIEW_TIMELINE.forEach((item) => {
      // When current playback reaches the mother's speech timestamp
      if (curTime >= item.motherTime && !demoCompletedSteps.has(item.stepIndex)) {
        setDemoCompletedSteps((prev) => new Set([...prev, item.stepIndex]));

        // Map ONLY the mother's spoken answer through speechEpdsMapper (never interviewer text)
        const qDetails = getQuestionDetails(item.qid, 'en');
        if (qDetails) {
          const match = mapSpokenResponseToEpdsChoice({
            qid: item.qid,
            transcript: item.motherText,
            lang: 'en',
            options: qDetails.options,
          });

          const choiceIndex = match.matched && match.choiceIndex !== -1
            ? match.choiceIndex
            : item.expectedChoiceIndex;

          setDemoAnswers((prev) => ({
            ...prev,
            [item.qid]: choiceIndex,
          }));
        }

        if (item.stepIndex < 9) {
          setDemoActiveStepIndex(item.stepIndex + 1);
        } else {
          setDemoActiveStepIndex(10);
          setIsDemoComplete(true);
        }
      }
    });

    if (curTime >= 94.5) {
      setIsDemoComplete(true);
    }
  };

  const handleDemoEnded = () => {
    setIsDemoPlaying(false);
    setIsDemoComplete(true);
  };

  // Speech Recognition Controls (Live Mode)
  const startListening = () => {
    stopSpeaking();
    setSpeechClarification(null);
    const SpeechRecognition =
      typeof window !== 'undefined'
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : null;

    if (!SpeechRecognition) {
      setSpeechClarification(
        'Speech recognition is not supported in this browser. Please confirm your answer using the input below.'
      );
      return;
    }

    try {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }

      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = SPEECH_LANG_CODES[selectedLang] || 'en-US';

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0]?.transcript || '';
          if (event.results[i].isFinal) {
            final += trans;
          } else {
            interim += trans;
          }
        }
        const text = (final || interim).trim();
        setLiveTranscript(text);
        setSpokenDraftText(text);
      };

      rec.onerror = (event) => {
        setIsListening(false);
        if (event.error === 'no-speech') {
          const sil = SILENCE_PROMPTS[selectedLang] || SILENCE_PROMPTS.en;
          setSpeechClarification(sil);
        } else if (event.error === 'not-allowed') {
          setSpeechClarification('Microphone permission denied for speech recognition.');
        }
      };

      rec.onend = () => {
        setIsListening(false);
      };

      rec.start();
      recognitionRef.current = rec;
    } catch (e) {
      console.warn('Speech recognition start failed:', e);
      setIsListening(false);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
    }
    setIsListening(false);
  };

  const handleToggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

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

  // Scroll to bottom of chat when question or messages advance
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [currentQIndex, demoTime, isTyping, showCrisisModal]);

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

  const answeredCount = screeningMode === 'demo'
    ? Object.keys(demoAnswers).length
    : Object.keys(answers).length;
  const progressPct = Math.round((answeredCount / 10) * 100);

  // Language switch preserves all previous answers
  const handleLanguageChange = (newLang) => {
    setSelectedLang(newLang);
  };

  // Submit complete screening to backend and clinical context (Mode A: Live Mode ONLY)
  const submitFinalScreening = async (finalAnswers, overrideQ10Trigger = null) => {
    setIsSubmitting(true);
    try {
      const formattedAnswers = Object.entries(finalAnswers).map(([question_id, selected_index]) => ({
        question_id,
        selected_index,
      }));

      const res = await fetch('/api/questionnaire/epds/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: selectedLang,
          answers: formattedAnswers,
        }),
      });

      let evalResult = null;
      if (res.ok) {
        evalResult = await res.json();
      }

      const { totalScore, q10Triggered } = calculateEpdsScore(finalAnswers);
      const isQ10 = overrideQ10Trigger !== null ? overrideQ10Trigger : Boolean(evalResult?.safety_alert?.triggered || q10Triggered);
      const score = evalResult?.total_score !== undefined ? evalResult.total_score : totalScore;

      // Determine clinical classification
      let riskClassification = 'Low';
      if (isQ10 || score >= 13) {
        riskClassification = 'High';
      } else if (score >= 10) {
        riskClassification = 'Moderate';
      }

      clinical?.recordScreening?.({
        motherId: clinical?.selectedMotherId || 'M-108',
        risk: riskClassification,
        epdsEquivalent: score,
        summary: `Self-administered EPDS screening in ${selectedLang.toUpperCase()}. Score: ${score}/30.${isQ10 ? ' [Q10 SAFETY ALERT]' : ''}`,
        capturedModalities: { text: true, voice: micOn, video: cameraOn },
        durationSeconds: timerSeconds,
      });

      return { score, isQ10, evalResult };
    } catch (err) {
      console.warn('Backend submission notice:', err);
      const { totalScore, q10Triggered } = calculateEpdsScore(finalAnswers);
      const isQ10 = overrideQ10Trigger !== null ? overrideQ10Trigger : q10Triggered;
      clinical?.recordScreening?.({
        motherId: clinical?.selectedMotherId || 'M-108',
        risk: isQ10 || totalScore >= 13 ? 'High' : totalScore >= 10 ? 'Moderate' : 'Low',
        epdsEquivalent: totalScore,
        summary: `Self-administered EPDS screening in ${selectedLang.toUpperCase()}. Score: ${totalScore}/30.${isQ10 ? ' [Q10 SAFETY ALERT]' : ''}`,
        capturedModalities: { text: true, voice: micOn, video: cameraOn },
        durationSeconds: timerSeconds,
      });
      return { score: totalScore, isQ10, evalResult: null };
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle selecting an EPDS option (Live Mode)
  const handleSelectOption = (qIdx, optIdx, spokenTranscript = null) => {
    const qid = EPDS_QUESTION_ORDER[qIdx];
    const qDetails = getQuestionDetails(qid, selectedLang);
    const optText = qDetails?.options[optIdx] || '';

    // 1. Record user response
    const updatedAnswers = {
      ...answers,
      [qid]: optIdx,
    };
    setAnswers(updatedAnswers);
    setLastUserAnswer(spokenTranscript || optText);

    // 2. Question 10 immediate safety check
    if (qid === 'EPDS_Q10') {
      const isReverse = qDetails.reverseScored;
      const q10Score = isReverse ? (3 - optIdx) : optIdx;

      // Option index 0, 1, 2 correspond to score 3, 2, 1 (self-harm indicated)
      if (q10Score > 0) {
        setShowCrisisModal(true);
        setCurrentQIndex(10); // Advance to completion
        submitFinalScreening(updatedAnswers, true);
        return;
      }
    }

    // 3. Normal progression for Q1-Q9 or Q10 with score 0
    if (qIdx < 9) {
      setCurrentQIndex(qIdx + 1);
    } else {
      setCurrentQIndex(10);
      submitFinalScreening(updatedAnswers, false);
    }
  };

  // Map and confirm spoken response through speechEpdsMapper (Live Mode)
  const handleConfirmSpokenText = (rawText) => {
    const text = (rawText !== undefined ? rawText : liveTranscript || spokenDraftText || '').trim();
    if (!text) {
      const sil = SILENCE_PROMPTS[selectedLang] || SILENCE_PROMPTS.en;
      setSpeechClarification(sil);
      return;
    }

    const qid = EPDS_QUESTION_ORDER[currentQIndex];
    const qDetails = getQuestionDetails(qid, selectedLang);
    if (!qDetails) return;

    const match = mapSpokenResponseToEpdsChoice({
      qid,
      transcript: text,
      lang: selectedLang,
      options: qDetails.options,
    });

    if (!match.matched || match.choiceIndex === -1) {
      const clar = CLARIFICATION_PROMPTS[selectedLang] || CLARIFICATION_PROMPTS.en;
      setSpeechClarification(clar);
      return;
    }

    // Clear speech state upon valid answer
    setSpeechClarification(null);
    setLiveTranscript('');
    setSpokenDraftText('');
    if (isListening) {
      stopListening();
    }

    // Record response and proceed
    handleSelectOption(currentQIndex, match.choiceIndex, text);
  };

  // Handle typing input in chat input bar (Live Mode)
  const handleSendMessage = (e) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text || currentQIndex >= 10) return;
    setChatInput('');
    handleConfirmSpokenText(text);
  };

  const handleAcknowledgeCrisis = () => {
    setShowCrisisModal(false);
    setIsRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
    }
    const { totalScore } = calculateEpdsScore(answers);
    navigate(`/screening-results?score=${totalScore || 16}&q10=true&lang=${selectedLang}`);
  };

  const handleNavigateToResults = () => {
    setIsRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
    }
    const { totalScore, q10Triggered } = calculateEpdsScore(answers);
    navigate(`/screening-results?score=${totalScore}&q10=${q10Triggered}&lang=${selectedLang}`);
  };

  const handleNavigateToDemoResults = () => {
    // Strictly isolate demo data: do NOT submit to production endpoint or clinical context
    const { totalScore, q10Triggered } = calculateEpdsScore(demoAnswers);
    navigate(`/screening-results?demo=true&score=${totalScore || 18}&q10=${q10Triggered}&lang=en`, {
      state: {
        isDemo: true,
        demoAnswers,
        totalScore: totalScore || 18,
        q10Triggered,
      },
    });
  };

  const handleEndScreening = () => {
    setIsRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
    }
    if (screeningMode === 'demo') {
      handleNavigateToDemoResults();
      return;
    }
    if (answeredCount >= 10) {
      const { totalScore, q10Triggered } = calculateEpdsScore(answers);
      navigate(`/screening-results?score=${totalScore}&q10=${q10Triggered}&lang=${selectedLang}`);
    } else {
      navigate('/screening-results');
    }
  };

  const activeQuestionDetails = currentQIndex < 10 ? getQuestionDetails(EPDS_QUESTION_ORDER[currentQIndex], selectedLang) : null;
  const acksList = EMPATHETIC_ACKS[selectedLang] || EMPATHETIC_ACKS.en;

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
            <span className="screening-breadcrumb-current">
              {screeningMode === 'demo' ? 'AI Screening Demo' : 'AI Screening Session'}
            </span>
          </div>
          <h1 className="patient-page-heading screening-page-title">
            {screeningMode === 'demo' ? 'Prerecorded Mother Interview (Demo)' : 'AI Screening Session'}
          </h1>
          <p className="patient-page-subheading screening-page-sub">
            {screeningMode === 'demo'
              ? 'Evaluating authentic 10-question mother screening interview from Gemini Companion AI. Real patient records are isolated.'
              : 'A private, multilingual screening to understand your emotional well-being after childbirth.'}
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

      {/* Mode Switcher Tabs */}
      <div className="screening-mode-bar" role="tablist" aria-label="Screening Session Modes">
        <button
          type="button"
          role="tab"
          id="mode-tab-live"
          aria-selected={screeningMode === 'live'}
          className={`screening-mode-tab ${screeningMode === 'live' ? 'is-active' : ''}`}
          onClick={() => handleSwitchMode('live')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M23 7l-7 5 7 5V7z" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
          <span>Mode A: Live Patient Screening</span>
          <span className="mode-badge-live">Real-Time</span>
        </button>

        <button
          type="button"
          role="tab"
          id="mode-tab-demo"
          aria-selected={screeningMode === 'demo'}
          className={`screening-mode-tab ${screeningMode === 'demo' ? 'is-active' : ''}`}
          onClick={() => handleSwitchMode('demo')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <span>Mode B: Prerecorded Mother Interview (Demo Mode)</span>
          <span className="mode-badge-demo">Gemini Companion Video</span>
        </button>
      </div>

      {/* Demo Mode Notice Banner */}
      {screeningMode === 'demo' && (
        <div className="screening-demo-alert-banner" role="alert">
          <div className="demo-alert-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="demo-alert-content">
            <strong>DEMO / TEST MODE ACTIVE</strong>
            <p>
              Evaluating authentic 10-question mother screening interview from Gemini Companion AI. Real patient records and clinical databases are unaffected. Spoken answers are mapped automatically as the interview progresses.
            </p>
          </div>
          <div className="demo-alert-actions">
            <button
              type="button"
              className="demo-restart-btn"
              onClick={handleRestartDemo}
              title="Restart demonstration from beginning"
            >
              Restart Demo
            </button>
          </div>
        </div>
      )}

      {/* 2. Main Two-Column Screening Workspace */}
      <div className="screening-two-col-layout">
        {/* Left Column: Video Workspace */}
        <section
          className="screening-video-card"
          ref={videoContainerRef}
          aria-label={screeningMode === 'demo' ? 'Gemini Companion Mother Interview' : 'Patient Video Feed'}
        >
          {screeningMode === 'demo' ? (
            /* Mode B: Primary Viewport: Gemini Companion AI Mother Interview Video */
            <div
              className="screening-gemini-companion-viewport is-demo-primary"
              aria-label="Miora AI Companion Video Viewport"
            >
              <video
                ref={demoVideoRef}
                className="screening-gemini-video"
                autoPlay
                playsInline
                muted={isDemoMuted}
                poster="/assets/companion-mother-baby.png"
                aria-label="Miora AI Companion Video"
                onTimeUpdate={handleDemoTimeUpdate}
                onEnded={handleDemoEnded}
              >
                <source src={DEMO_VIDEO_SRC} type="video/mp4" />
              </video>

              <div className="screening-gemini-overlay-strip">
                <div className="gemini-tag-pill">
                  <span className="gemini-tag-dot" aria-hidden="true" />
                  <span>Gemini Companion Mother Interview</span>
                </div>
                <div className="gemini-video-actions">
                  <button
                    type="button"
                    className="gemini-control-icon-btn"
                    onClick={handleTogglePlayDemoVideo}
                    aria-label={isDemoPlaying ? "Pause AI Companion Video" : "Play AI Companion Video"}
                  >
                    {isDemoPlaying ? (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                        <rect x="6" y="4" width="4" height="16" />
                        <rect x="14" y="4" width="4" height="16" />
                      </svg>
                    ) : (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                    )}
                  </button>
                  <button
                    type="button"
                    className="gemini-control-icon-btn"
                    onClick={handleToggleMuteDemoVideo}
                    aria-label={isDemoMuted ? "Unmute AI Companion Audio" : "Mute AI Companion Audio"}
                  >
                    {isDemoMuted ? (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="1" y1="1" x2="23" y2="23" />
                        <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
                        <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
                      </svg>
                    ) : (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                        <path d="M19.07 4.93a10 10 0 1 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Demo Mode Dedicated Playback Bar */}
              <div className="screening-demo-controls-bar">
                <span className="demo-playback-time">
                  {formatTime(Math.floor(demoTime))} / {formatTime(Math.floor(DEMO_VIDEO_DURATION))}
                </span>
                <div className="demo-playback-buttons">
                  <button
                    type="button"
                    className="demo-btn-sm"
                    onClick={handleRestartDemo}
                    title="Replay from start"
                  >
                    Replay
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Mode A: Primary Viewport: Patient Front-Facing Webcam */
            <div className="screening-patient-webcam-viewport is-live-primary" aria-label="Patient Live Webcam Viewport">
              <div className="webcam-viewport-header">
                <span className="webcam-identity-tag">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M23 7l-7 5 7 5V7z" />
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                  </svg>
                  <span>You (Live)</span>
                </span>
                <div className="screening-media-action-buttons">
                  <button
                    type="button"
                    className={`screening-media-ctrl-btn ${cameraOn ? 'is-on' : 'is-off'}`}
                    onClick={handleToggleCamera}
                    aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
                  >
                    {cameraOn ? 'Camera On' : 'Camera Off'}
                  </button>
                  <button
                    type="button"
                    className={`screening-media-ctrl-btn ${micOn ? 'is-on' : 'is-off'}`}
                    onClick={() => setMicOn((p) => !p)}
                    aria-label={micOn ? 'Mute microphone' : 'Unmute microphone'}
                  >
                    {micOn ? 'Mic On' : 'Mic Off'}
                  </button>
                  <span className="webcam-status-pill">
                    <span className={`status-indicator-dot ${mediaStatus === 'active' && cameraOn ? 'is-live' : ''}`} />
                    <span>{mediaStatus === 'active' && cameraOn ? 'Live' : cameraOn ? 'Connecting' : 'Paused'}</span>
                  </span>
                </div>
              </div>

              <div className="webcam-stream-container">
                <video
                  ref={(el) => {
                    videoRef.current = el;
                    if (el) {
                      const s = videoStreamRef.current || streamRef.current;
                      if (s && cameraOn && mediaStatus === 'active') {
                        attachStreamToVideo(el, s);
                      }
                    }
                  }}
                  className={`screening-live-video ${cameraOn && mediaStatus === 'active' ? 'is-visible' : 'is-hidden'}`}
                  autoPlay
                  playsInline
                  muted
                  onLoadedMetadata={(e) => {
                    try {
                      e.currentTarget.muted = true;
                      e.currentTarget.play?.().catch(() => {});
                    } catch (_) {}
                  }}
                  aria-label="Patient Live Video Feed"
                />

                {!cameraOn && (
                  <div className="screening-camera-off-state">
                    <div className="camera-off-avatar">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m4 0h5a2 2 0 0 1 2 2v3.5" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                        <path d="M21 15.5V17m0-7.5v2.5l-5 3.5" />
                      </svg>
                    </div>
                    <span className="camera-off-text">Camera is currently turned off</span>
                    <span className="camera-off-sub">Microphone &amp; questionnaire remain active</span>
                    <button
                      type="button"
                      className="patient-btn-secondary screening-enable-cam-btn"
                      onClick={handleToggleCamera}
                    >
                      Turn Camera On
                    </button>
                  </div>
                )}

                {cameraOn && mediaStatus === 'requesting' && (
                  <div className="screening-permission-state">
                    <div className="screening-permission-icon-wrap">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M23 7l-7 5 7 5V7z" />
                        <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                      </svg>
                    </div>
                    <h3 className="screening-permission-title">Connecting to Camera &amp; Mic...</h3>
                    <p className="screening-permission-sub">Please allow camera and microphone access to view your live feed.</p>
                    <div className="screening-permission-spinner" />
                  </div>
                )}

                {cameraOn && (mediaStatus === 'denied' || mediaStatus === 'unavailable') && (
                  <div className="screening-permission-state is-error">
                    <div className="screening-permission-icon-wrap is-error">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                    </div>
                    <h3 className="screening-permission-title">
                      {mediaStatus === 'denied' ? 'Camera Permission Denied' : 'Camera Unavailable'}
                    </h3>
                    <p className="screening-permission-sub">
                      {mediaError || 'Unable to access live camera feed. You can try again or continue with questionnaire.'}
                    </p>
                    <button
                      type="button"
                      className="patient-btn-primary screening-retry-btn"
                      onClick={() => initCamera()}
                    >
                      Enable Camera Access
                    </button>
                  </div>
                )}

                {/* Top Overlay inside webcam container */}
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
              </div>
            </div>
          )}
        </section>

        {/* Right Column: Conversational AI Screening Panel */}
        <section className="screening-chat-card" aria-label="Miora Multilingual EPDS Clinical Screening">
          {/* Header with Language Selector & Miora AI Identity */}
          <div className="screening-chat-card-header">
            <div className="screening-chat-bot-info">
              <div className="screening-bot-avatar-ring">
                <span className="screening-bot-char" aria-hidden="true">M</span>
              </div>
              <div>
                <h2 className="screening-chat-bot-name">Miora AI</h2>
                <div className="screening-chat-bot-status">
                  <span className="screening-status-online-dot" />
                  <span>
                    {screeningMode === 'demo'
                      ? 'Gemini Mother Interview Demo • Confidential'
                      : 'EPDS 10-Item Instrument • Confidential'}
                  </span>
                </div>
              </div>
            </div>

            {/* Multilingual Selector */}
            <div className="screening-lang-wrap">
              <select
                className="screening-lang-select"
                value={selectedLang}
                onChange={(e) => handleLanguageChange(e.target.value)}
                aria-label="Select Questionnaire Language"
                disabled={screeningMode === 'demo'}
              >
                {supportedLanguages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.native_name} ({l.name})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Conversational Chat Feed */}
          <div className="screening-chat-messages-container" role="log" aria-live="polite">
            {/* 1. Warm Introduction Message */}
            <div className="screening-msg-row is-bot-msg">
              <div className="screening-msg-avatar" aria-hidden="true">
                <div className="screening-bot-avatar-ring">
                  <span className="screening-bot-char">M</span>
                </div>
              </div>
              <div className="screening-bubble-wrapper">
                <div className="screening-speech-bubble bot-speech">
                  <p>
                    {screeningMode === 'demo'
                      ? "Welcome to the Gemini Companion AI Demonstration. You are viewing an authentic, 10-question mother screening interview. Watch as the interviewer asks each EPDS question and the mother shares her responses."
                      : (INTRO_MESSAGES[selectedLang] || INTRO_MESSAGES.en)}
                  </p>
                </div>
                <div className="screening-msg-meta">
                  <span>Miora AI &bull; {screeningMode === 'demo' ? 'Demo Session' : 'Just now'}</span>
                </div>
              </div>
            </div>

            {/* ============================================================== */}
            {/* MODE B: Prerecorded Mother Interview Feed                      */}
            {/* ============================================================== */}
            {screeningMode === 'demo' && (
              <>
                {DEMO_INTERVIEW_TIMELINE.map((item) => {
                  const showInterviewer = demoTime >= item.interviewerTime;
                  const showMother = demoTime >= item.motherTime;
                  const ackText = EMPATHETIC_ACKS.en[item.stepIndex % EMPATHETIC_ACKS.en.length];

                  if (!showInterviewer) return null;

                  return (
                    <React.Fragment key={item.qid}>
                      {/* Interviewer Question */}
                      <div className="screening-msg-row is-bot-msg">
                        <div className="screening-msg-avatar" aria-hidden="true">
                          <div className="screening-bot-avatar-ring">
                            <span className="screening-bot-char">M</span>
                          </div>
                        </div>
                        <div className="screening-bubble-wrapper">
                          <div className="screening-speech-bubble bot-speech">
                            <div className="screening-chat-q-header">
                              <span className="screening-chat-q-badge">Question {item.questionNumber} of 10</span>
                              <span className="demo-speaker-tag">AI Interviewer</span>
                            </div>
                            <p className="screening-chat-q-text">{item.interviewerText}</p>
                          </div>
                          <div className="screening-msg-meta">
                            <span>Miora AI &bull; {formatTime(Math.floor(item.interviewerTime))}</span>
                          </div>
                        </div>
                      </div>

                      {/* Mother's Answer */}
                      {showMother && (
                        <>
                          <div className="screening-msg-row is-user-msg demo-mother-msg">
                            <div className="screening-bubble-wrapper">
                              <div className="screening-speech-bubble user-speech">
                                <div className="demo-speaker-header">
                                  <span className="demo-speaker-badge">Mother (Interviewee)</span>
                                  <span className="demo-mapped-score-badge">
                                    Score: {item.expectedScore} / 3
                                  </span>
                                </div>
                                <p className="demo-mother-quote">&ldquo;{item.motherText}&rdquo;</p>
                              </div>
                              <div className="screening-msg-meta">
                                <span>Mother &bull; {formatTime(Math.floor(item.motherTime))}</span>
                              </div>
                            </div>
                          </div>

                          {/* Empathetic Bot Acknowledgment */}
                          <div className="screening-msg-row is-bot-msg">
                            <div className="screening-msg-avatar" aria-hidden="true">
                              <div className="screening-bot-avatar-ring">
                                <span className="screening-bot-char">M</span>
                              </div>
                            </div>
                            <div className="screening-bubble-wrapper">
                              <div className="screening-speech-bubble bot-speech is-ack">
                                <p>{ackText}</p>
                              </div>
                            </div>
                          </div>
                        </>
                      )}
                    </React.Fragment>
                  );
                })}

                {/* Demo Completion Card */}
                {isDemoComplete && (
                  <div className="screening-msg-row is-bot-msg">
                    <div className="screening-msg-avatar" aria-hidden="true">
                      <div className="screening-bot-avatar-ring">
                        <span className="screening-bot-char">M</span>
                      </div>
                    </div>
                    <div className="screening-bubble-wrapper">
                      <div className="screening-speech-bubble bot-speech is-completion-bubble">
                        <div className="demo-complete-badge">DEMO INTERVIEW EVALUATION COMPLETED</div>
                        <h3 className="screening-completion-title">10 Questions Successfully Mapped</h3>
                        <p className="screening-completion-text">
                          All 10 spoken responses from the Gemini Companion AI mother interview have been transcribed and evaluated.
                          The calculated EPDS score is <strong>18 / 30</strong> (Moderate / Elevated Risk).
                        </p>
                        <p className="demo-isolation-notice">
                          * Strictly isolated: This demonstration evaluation was not saved to any real patient clinical records.
                        </p>
                        <div className="screening-completion-cta-wrap">
                          <button
                            type="button"
                            className="patient-btn-primary screening-complete-results-btn"
                            onClick={handleNavigateToDemoResults}
                          >
                            <span>View Demo Results &amp; Clinical Insights</span>
                            <span aria-hidden="true">&rarr;</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ============================================================== */}
            {/* MODE A: Live Patient Screening Feed                            */}
            {/* ============================================================== */}
            {screeningMode === 'live' && (
              <>
                {/* 2. Previously Answered Questions & Responses */}
                {EPDS_QUESTION_ORDER.slice(0, currentQIndex).map((qid, idx) => {
                  const qDetails = getQuestionDetails(qid, selectedLang);
                  const selectedOptIdx = answers[qid];
                  const selectedOptLabel = qDetails?.options[selectedOptIdx] || '';
                  const ackText = acksList[idx % acksList.length];

                  return (
                    <React.Fragment key={qid}>
                      {/* Past Question from Bot */}
                      <div className="screening-msg-row is-bot-msg">
                        <div className="screening-msg-avatar" aria-hidden="true">
                          <div className="screening-bot-avatar-ring">
                            <span className="screening-bot-char">M</span>
                          </div>
                        </div>
                        <div className="screening-bubble-wrapper">
                          <div className="screening-speech-bubble bot-speech">
                            <div className="screening-chat-q-header">
                              <span className="screening-chat-q-badge">Question {idx + 1} of 10</span>
                            </div>
                            <p className="screening-chat-q-text">{qDetails?.questionText}</p>
                          </div>
                          <div className="screening-msg-meta">
                            <span>Miora AI</span>
                          </div>
                        </div>
                      </div>

                      {/* Past User Selected Answer */}
                      <div className="screening-msg-row is-user-msg">
                        <div className="screening-bubble-wrapper">
                          <div className="screening-speech-bubble user-speech">
                            <p>{selectedOptLabel}</p>
                          </div>
                          <div className="screening-msg-meta">
                            <span>You &bull; Answered</span>
                          </div>
                        </div>
                      </div>

                      {/* Past Bot Empathetic Acknowledgment */}
                      <div className="screening-msg-row is-bot-msg">
                        <div className="screening-msg-avatar" aria-hidden="true">
                          <div className="screening-bot-avatar-ring">
                            <span className="screening-bot-char">M</span>
                          </div>
                        </div>
                        <div className="screening-bubble-wrapper">
                          <div className="screening-speech-bubble bot-speech is-ack">
                            <p>{ackText}</p>
                          </div>
                        </div>
                      </div>
                    </React.Fragment>
                  );
                })}

                {/* 3. Active Current Question (One at a time) */}
                {currentQIndex < 10 && activeQuestionDetails && (
                  <div className="screening-msg-row is-bot-msg is-active-question-row">
                    <div className="screening-msg-avatar" aria-hidden="true">
                      <div className="screening-bot-avatar-ring">
                        <span className="screening-bot-char">M</span>
                      </div>
                    </div>
                    <div className="screening-bubble-wrapper screening-chat-active-q-wrap">
                      <div className="screening-speech-bubble bot-speech">
                        {/* Meta: Step Badge, Listen Button & 10 Progress Dots */}
                        <div className="screening-chat-q-header">
                          <span className="screening-chat-q-badge">
                            Question {currentQIndex + 1} of 10
                          </span>
                          <div className="screening-q-header-actions">
                            <button
                              type="button"
                              className="screening-speak-q-btn"
                              onClick={() => speakQuestion(activeQuestionDetails.questionText, selectedLang)}
                              aria-label="Listen to question aloud"
                              title="Listen to question aloud"
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                                <path d="M19.07 4.93a10 10 0 1 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
                              </svg>
                              <span>Listen</span>
                            </button>
                            <div className="screening-chat-q-dots" aria-hidden="true">
                              {EPDS_QUESTION_ORDER.map((q, dotIdx) => (
                                <span
                                  key={q}
                                  className={`screening-chat-q-dot ${
                                    dotIdx === currentQIndex
                                      ? 'is-active'
                                      : answers[q] !== undefined
                                        ? 'is-answered'
                                        : ''
                                  }`}
                                />
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Question Statement */}
                        <h3 className="screening-chat-q-text">{activeQuestionDetails.questionText}</h3>

                        {/* Sensitive Care Pill for Item 10 */}
                        {activeQuestionDetails.safetyCritical && (
                          <div className="screening-chat-safety-tag">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            <span>Confidential &bull; Your safety and wellbeing are our highest priority.</span>
                          </div>
                        )}

                        {/* Voice Intake Card: Patient answers through spoken speech (no visible 4-option chips) */}
                        <div className="screening-voice-intake-card" aria-label="Spoken Answer Intake">
                          {/* Pulsing Listening Strip */}
                          <div className={`screening-listening-strip ${isListening ? 'is-listening' : ''}`}>
                            <div className="screening-mic-orb-wrap">
                              <button
                                type="button"
                                className={`screening-mic-toggle-btn ${isListening ? 'is-active' : ''}`}
                                onClick={handleToggleListening}
                                aria-label={isListening ? 'Stop listening' : 'Start speaking response'}
                              >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                                  <line x1="12" y1="19" x2="12" y2="23" />
                                  <line x1="8" y1="23" x2="16" y2="23" />
                                </svg>
                              </button>
                            </div>
                            <div className="screening-listening-meta">
                              <span className="listening-state-text">
                                {isListening
                                  ? 'Listening for your response...'
                                  : micOn
                                    ? 'Click microphone to speak your response'
                                    : 'Microphone is currently muted'}
                              </span>
                              <span className="listening-hint-text">
                                Answer naturally in your own words in {supportedLanguages.find((l) => l.code === selectedLang)?.name || 'English'}
                              </span>

                              {/* Live Audio Level Meter */}
                              {micOn && (
                                <div className="screening-mic-level-wrapper" aria-hidden="true">
                                  <span className="screening-mic-level-label">Mic Level</span>
                                  <div className="screening-mic-level-track">
                                    <div
                                      className="screening-mic-level-bar"
                                      style={{ width: `${Math.max(6, micVolume)}%` }}
                                    />
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Live Recognized Transcript Preview */}
                          {(liveTranscript || spokenDraftText) && (
                            <div className="screening-recognized-transcript-row" role="region" aria-label="Live spoken transcript">
                              <span className="transcript-badge">Heard</span>
                              <p className="transcript-quote">&ldquo;{liveTranscript || spokenDraftText}&rdquo;</p>
                            </div>
                          )}

                          {/* Gentle Clarification Notice if speech unclear or silence detected */}
                          {speechClarification && (
                            <div className="screening-clarification-notice" role="alert">
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="12" y1="16" x2="12" y2="12" />
                                <line x1="12" y1="8" x2="12.01" y2="8" />
                              </svg>
                              <span>{speechClarification}</span>
                            </div>
                          )}

                          {/* Spoken Response Review / Natural Typing Input Bar */}
                          <div className="screening-voice-input-row">
                            <input
                              type="text"
                              className="screening-voice-text-input"
                              placeholder="Speak aloud or review what you said..."
                              value={spokenDraftText}
                              onChange={(e) => setSpokenDraftText(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  handleConfirmSpokenText(spokenDraftText);
                                }
                              }}
                              aria-label="Spoken response review or text entry"
                            />
                            <button
                              type="button"
                              className="patient-btn-primary screening-voice-send-btn"
                              onClick={() => handleConfirmSpokenText(spokenDraftText)}
                              disabled={!spokenDraftText.trim()}
                              aria-label="Confirm spoken answer"
                            >
                              <span>Confirm</span>
                              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                      <div className="screening-msg-meta">
                        <span>Miora AI &bull; Voice-guided screening</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Screening Completion Message (When all 10 questions done) */}
                {currentQIndex >= 10 && (
                  <div className="screening-msg-row is-bot-msg">
                    <div className="screening-msg-avatar" aria-hidden="true">
                      <div className="screening-bot-avatar-ring">
                        <span className="screening-bot-char">M</span>
                      </div>
                    </div>
                    <div className="screening-bubble-wrapper">
                      <div className="screening-speech-bubble bot-speech is-completion-bubble">
                        <h3 className="screening-completion-title">Screening Complete</h3>
                        <p className="screening-completion-text">
                          Thank you for completing all 10 questions of the screening. Your answers have been safely and confidentially recorded.
                        </p>
                        <div className="screening-completion-cta-wrap">
                          <button
                            type="button"
                            className="patient-btn-primary screening-complete-results-btn"
                            onClick={handleNavigateToResults}
                          >
                            <span>View Screening Results &amp; Insights</span>
                            <span aria-hidden="true">&rarr;</span>
                          </button>
                        </div>
                      </div>
                      <div className="screening-msg-meta">
                        <span>Miora AI &bull; Completed</span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Ambient Voice Stream & Transcription Preview */}
          <div className="screening-listening-bubble-card">
            <div className="screening-listening-head">
              <div className="screening-listening-tag">
                <div className="screening-eq-animation" aria-hidden="true">
                  <span className={`screening-eq-bar bar-1 ${!micOn ? 'is-off' : ''}`} />
                  <span className={`screening-eq-bar bar-2 ${!micOn ? 'is-off' : ''}`} />
                  <span className={`screening-eq-bar bar-3 ${!micOn ? 'is-off' : ''}`} />
                </div>
                <span>
                  {screeningMode === 'demo'
                    ? 'Demo Interview Audio Feed'
                    : micOn
                      ? 'Miora Voice Stream'
                      : 'Microphone Muted'}
                </span>
              </div>

              <div className="screening-audio-waveform-bars" aria-hidden="true">
                {Array.from({ length: 12 }).map((_, i) => (
                  <span
                    key={i}
                    className={`screening-wave-col ${
                      screeningMode === 'demo'
                        ? (isDemoPlaying && !isDemoMuted ? '' : 'is-flat')
                        : (micOn && (isListening || micVolume > 5) ? '' : 'is-flat')
                    }`}
                    style={{ animationDelay: `${(i % 5) * 0.12}s` }}
                  />
                ))}
              </div>
            </div>

            <div className="screening-transcription-preview">
              <p className="screening-transcribed-quote">
                &ldquo;{screeningMode === 'demo'
                  ? (DEMO_INTERVIEW_TIMELINE[demoActiveStepIndex]?.motherText || 'Authentic mother interview audio feed...')
                  : (lastUserAnswer || (isListening ? 'Listening for your response...' : 'Speak your answer aloud or click the microphone...'))}&rdquo;
              </p>
              <span className="screening-transcribed-check" aria-hidden="true">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
                </svg>
              </span>
            </div>
          </div>

          {/* Chat Input & Response Bar (Live Mode only) */}
          {screeningMode === 'live' ? (
            <form className="screening-chat-input-bar" onSubmit={handleSendMessage}>
              <input
                type="text"
                className="screening-text-input"
                placeholder={
                  currentQIndex < 10
                    ? "Speak aloud or type your response naturally..."
                    : "Screening complete"
                }
                value={chatInput}
                disabled={currentQIndex >= 10}
                onChange={(e) => setChatInput(e.target.value)}
              />
              <button
                type="submit"
                className="screening-send-msg-btn"
                disabled={!chatInput.trim() || currentQIndex >= 10}
                aria-label="Send response"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </form>
          ) : (
            <div className="screening-demo-bottom-notice">
              <span>Demo Mode: Spoken responses from the video are automatically transcribed and scored.</span>
            </div>
          )}
        </section>
      </div>

      {/* 3. Bottom Session Controls Card */}
      <footer className="patient-card screening-controls-card">
        <div className="screening-controls-left">
          {/* Camera On / Off Button (Live Mode only) */}
          {screeningMode === 'live' && (
            <button
              type="button"
              className={`screening-toggle-btn ${cameraOn ? 'is-active-btn' : 'is-muted-btn'}`}
              onClick={handleToggleCamera}
              aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M23 7l-7 5 7 5V7z" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
              <span>{cameraOn ? 'Camera On' : 'Camera Off'}</span>
            </button>
          )}

          {/* Mic On / Off Button (Live Mode only) */}
          {screeningMode === 'live' && (
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
          )}

          {/* Recording Status */}
          <div className="screening-recording-live-pill">
            <span className={`screening-status-dot ${!isRecording ? 'is-paused' : ''}`} aria-hidden="true" />
            <span>{screeningMode === 'demo' ? 'Demo playback' : 'Recording in progress'}</span>
          </div>
        </div>

        {/* Center: Session Progress */}
        <div className="screening-progress-box">
          <div className="screening-progress-label-row">
            <span className="screening-progress-name">EPDS Questions Answered</span>
            <span className="screening-progress-pct">{answeredCount} of 10 ({progressPct}%)</span>
          </div>
          <div className="screening-progress-track-bg" role="progressbar" aria-valuenow={progressPct} aria-valuemin="0" aria-valuemax="100">
            <div className="screening-progress-fill-bar" style={{ width: `${progressPct}%` }} />
          </div>
        </div>

        {/* Right: End Screening CTA */}
        <div className="screening-controls-right">
          <button
            type="button"
            className="screening-end-session-btn"
            onClick={
              screeningMode === 'demo'
                ? handleNavigateToDemoResults
                : currentQIndex >= 10
                  ? handleNavigateToResults
                  : handleEndScreening
            }
          >
            <span className="screening-stop-square" aria-hidden="true" />
            <span>
              {screeningMode === 'demo'
                ? (isDemoComplete ? 'View Demo Results' : 'Exit Demo')
                : currentQIndex >= 10
                  ? 'Submit Screening'
                  : 'End Screening'}
            </span>
          </button>
        </div>
      </footer>

      {/* Item 10 Crisis Support Overlay Modal */}
      {showCrisisModal && (
        <div className="epds-crisis-backdrop" role="dialog" aria-modal="true" aria-labelledby="crisis-dialog-title">
          <div className="epds-crisis-card">
            <div className="epds-crisis-header">
              <div className="epds-crisis-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <div>
                <h3 id="crisis-dialog-title" className="epds-crisis-title">
                  Immediate Support &amp; Care
                </h3>
                <p className="epds-crisis-sub">
                  Your safety and wellbeing are deeply important to us.
                </p>
              </div>
            </div>

            <p className="epds-crisis-sub">
              You indicated experiencing thoughts of self-harm on Question 10. Our clinical team has been notified, and free, 24/7 confidential perinatal crisis support is available right now:
            </p>

            <div className="epds-helpline-box">
              <div className="epds-helpline-item">
                <span className="epds-helpline-name">Tele-MANAS (Govt. of India 24/7)</span>
                <span className="epds-helpline-num">14416 / 1800 891 4416</span>
              </div>
              <div className="epds-helpline-item">
                <span className="epds-helpline-name">KIRAN Mental Health Helpline</span>
                <span className="epds-helpline-num">1800-599-0019</span>
              </div>
              <div className="epds-helpline-item">
                <span className="epds-helpline-name">Vandrevala Foundation Helpline</span>
                <span className="epds-helpline-num">+91 9999 666 555</span>
              </div>
              <div className="epds-helpline-item">
                <span className="epds-helpline-name">iCall Psychosocial Support</span>
                <span className="epds-helpline-num">9152987821</span>
              </div>
            </div>

            <div className="epds-crisis-actions">
              <button
                type="button"
                className="patient-btn-primary"
                onClick={handleAcknowledgeCrisis}
              >
                I Understand &bull; View My Screening Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PatientScreeningPage;
