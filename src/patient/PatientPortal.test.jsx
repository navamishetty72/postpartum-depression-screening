import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PatientProvider } from './context/PatientContext.jsx';
import { ClinicalProvider } from '../dashboard/context/ClinicalContext.jsx';
import { PatientLayout } from './layout/PatientLayout.jsx';
import { MedicalHistoryScreen } from './pages/MedicalHistoryScreen.jsx';
import { PatientScreeningPage } from './pages/PatientScreeningPage.jsx';
import { AiAssistantScreen } from './pages/AiAssistantScreen.jsx';
import { ConnectDoctorPage } from './pages/ConnectDoctorPage.jsx';
import { PatientHomePage } from './pages/PatientHomePage.jsx';
import { PatientReportsPage } from './pages/PatientReportsPage.jsx';
import { CareSuggestionsPage } from './pages/CareSuggestionsPage.jsx';
import { ScreeningResultsPage } from './pages/ScreeningResultsPage.jsx';

function renderPatientApp(initialRoute = '/patient/reports') {
  return render(
    <ClinicalProvider>
      <PatientProvider>
        <MemoryRouter initialEntries={[initialRoute]}>
          <Routes>
            <Route element={<PatientLayout />}>
              <Route path="/patient/dashboard" element={<PatientHomePage />} />
              <Route path="/patient/home" element={<PatientHomePage />} />
              <Route path="/patient/reports" element={<PatientReportsPage />} />
              <Route path="/patient/medical-history" element={<MedicalHistoryScreen />} />
              <Route path="/medical-history" element={<MedicalHistoryScreen />} />
              <Route path="/patient/screening" element={<PatientScreeningPage />} />
              <Route path="/screening" element={<PatientScreeningPage />} />
              <Route path="/screening-results" element={<ScreeningResultsPage />} />
              <Route path="/patient/ai-assistant" element={<AiAssistantScreen />} />
              <Route path="/ai-assistant" element={<AiAssistantScreen />} />
              <Route path="/patient/connect-doctor" element={<ConnectDoctorPage />} />
              <Route path="/patient/care-suggestions" element={<CareSuggestionsPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </PatientProvider>
    </ClinicalProvider>
  );
}

describe('Miora Patient Portal Visual Refinement & Six Screens', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    if (!window.HTMLElement.prototype.scrollIntoView) {
      window.HTMLElement.prototype.scrollIntoView = vi.fn();
    }
    if (!window.URL.createObjectURL) {
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    }
    if (!window.URL.revokeObjectURL) {
      window.URL.revokeObjectURL = vi.fn();
    }
    if (!window.HTMLMediaElement.prototype.play) {
      window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue();
    }
    if (!window.HTMLMediaElement.prototype.pause) {
      window.HTMLMediaElement.prototype.pause = vi.fn();
    }
    if (!navigator.mediaDevices) {
      navigator.mediaDevices = {};
    }
    navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue({
      getTracks: () => [
        { kind: 'video', stop: vi.fn(), enabled: true },
        { kind: 'audio', stop: vi.fn(), enabled: true },
      ],
      getVideoTracks: () => [{ kind: 'video', stop: vi.fn(), enabled: true }],
      getAudioTracks: () => [{ kind: 'audio', stop: vi.fn(), enabled: true }],
    });
    window.speechSynthesis = {
      speak: vi.fn((utterance) => {
        utterance?.onstart?.();
      }),
      cancel: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      getVoices: vi.fn(() => [
        { name: 'Samantha', lang: 'en-US', default: true },
        { name: 'Google हिन्दी', lang: 'hi-IN', default: false },
      ]),
      speaking: false,
    };
    window.SpeechSynthesisUtterance = class {
      constructor(text) {
        this.text = text;
        this.rate = 1;
        this.pitch = 1;
        this.lang = 'en-US';
        this.voice = null;
        this.onstart = null;
        this.onend = null;
        this.onerror = null;
      }
    };
    window.SpeechRecognition = class MockSpeechRecognition {
      constructor() {
        this.continuous = false;
        this.interimResults = false;
        this.lang = 'en-US';
        this.onstart = null;
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
      }
      start() {
        this.onstart?.();
      }
      stop() {
        this.onend?.();
      }
    };
    window.webkitSpeechRecognition = window.SpeechRecognition;
    window.AudioContext = class MockAudioContext {
      constructor() {
        this.state = 'running';
      }
      createAnalyser() {
        return {
          fftSize: 256,
          smoothingTimeConstant: 0.6,
          frequencyBinCount: 128,
          getByteFrequencyData: vi.fn((arr) => arr.fill(40)),
        };
      }
      createMediaStreamSource() {
        return { connect: vi.fn() };
      }
      close() {
        this.state = 'closed';
        return Promise.resolve();
      }
    };
    window.webkitAudioContext = window.AudioContext;
  });

  it('renders the shared patient portal shell with sidebar navigation and top header', () => {
    renderPatientApp('/patient/reports');

    // Sidebar branding & tagline
    const sidebar = screen.getByRole('complementary', { name: /Patient Portal Navigation/i });
    expect(sidebar).toBeInTheDocument();
    expect(sidebar).toHaveTextContent(/Maternal Emotional/i);
    expect(sidebar).toHaveTextContent(/Intelligence/i);

    // Brand logo navigates to landing page
    const brandLink = screen.getByRole('link', { name: /Miora Home/i });
    expect(brandLink).toBeInTheDocument();
    expect(brandLink).toHaveAttribute('href', '/');

    // All navigation links in sidebar
    expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Medical History/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /AI Screening/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /AI Assistant/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Connect to a Doctor/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /My Reports/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Care Suggestions/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Profile/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Settings/i })).toBeInTheDocument();

    // Top Header
    expect(screen.getByText('Confidential Maternal Emotional Care')).toBeInTheDocument();
    expect(screen.getByLabelText(/Patient profile menu/i)).toBeInTheDocument();
    expect(screen.getByText('Amara')).toBeInTheDocument();
  });

  it('Screen 1 — Medical History: renders PPD diagnosis question, radio options, records upload, and Save action', () => {
    renderPatientApp('/patient/medical-history');

    // Heading
    expect(screen.getByRole('heading', { level: 1, name: /Medical History/i })).toBeInTheDocument();

    // Question
    expect(screen.getByText(/Have you ever been diagnosed with Postpartum Depression/i)).toBeInTheDocument();

    // Radio options: Yes, No, Not Sure
    const yesBtn = screen.getByRole('radio', { name: /Yes/i });
    const noBtn = screen.getByRole('radio', { name: /^No$/i });
    const notSureBtn = screen.getByRole('radio', { name: /Not Sure/i });

    expect(yesBtn).toBeInTheDocument();
    expect(noBtn).toBeInTheDocument();
    expect(notSureBtn).toBeInTheDocument();

    // Select 'No' option
    fireEvent.click(noBtn);
    expect(noBtn).toHaveAttribute('aria-checked', 'true');
    expect(yesBtn).toHaveAttribute('aria-checked', 'false');

    // Upload records section
    expect(screen.getByText(/Upload Relevant Records/i)).toBeInTheDocument();
    expect(screen.getByText(/PPD_Diagnosis_Report\.pdf/i)).toBeInTheDocument();

    // Save & Continue button
    const saveBtn = screen.getByRole('button', { name: /Save & Continue/i });
    expect(saveBtn).toBeInTheDocument();
    fireEvent.click(saveBtn);

    // Navigates to AI Screening
    expect(screen.getByRole('heading', { level: 1, name: /AI Screening Session/i })).toBeInTheDocument();
  });

  it('Screen 2 — AI Screening: renders 2-column workspace with dual video controls, conversation panel, and session controls', () => {
    renderPatientApp('/patient/screening');

    // Progress tracker stages
    expect(screen.getAllByText('Medical History').length).toBeGreaterThan(0);
    expect(screen.getByText('Screening')).toBeInTheDocument();
    expect(screen.getByText('Analysis')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();

    // Live video workspace viewport
    expect(screen.getByLabelText(/Patient Live Webcam Viewport/i)).toBeInTheDocument();
    expect(screen.getByText('You (Live)')).toBeInTheDocument();

    // Conversational panel
    expect(screen.getByText('Miora AI')).toBeInTheDocument();
    expect(screen.getByText(/Have you been able to laugh and see the funny side of things\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Speak your answer aloud or click the microphone/i)).toBeInTheDocument();

    // Media toggle controls
    const camBtn = screen.getAllByRole('button', { name: /Turn camera off/i })[0];
    expect(camBtn).toBeInTheDocument();
    fireEvent.click(camBtn);
    expect(screen.getByText(/Camera is currently turned off/i)).toBeInTheDocument();

    // End Screening button navigates to results
    const endBtn = screen.getByRole('button', { name: /End Screening/i });
    expect(endBtn).toBeInTheDocument();
    fireEvent.click(endBtn);

    expect(screen.getByRole('heading', { level: 1, name: /Screening Results/i })).toBeInTheDocument();
    expect(screen.getByText('64%')).toBeInTheDocument();
  });

  it('Screen 2 — Voice-Based EPDS: answers through speech without visible option chips, displays live transcript, and advances sequentially', () => {
    renderPatientApp('/patient/screening');

    // Assert clickable 4 options and radio buttons are NOT present in the question bubble
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(document.querySelector('.screening-chat-option-chip')).toBeNull();

    // Voice intake card is present with microphone button
    expect(screen.getByLabelText(/Spoken Answer Intake/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start speaking response/i })).toBeInTheDocument();

    // Question 1 is visible
    expect(screen.getByText(/Have you been able to laugh and see the funny side of things\?/i)).toBeInTheDocument();
    expect(screen.getByText('Question 1 of 10')).toBeInTheDocument();

    // Spoken response for Q1
    const spokenInput = screen.getByLabelText(/Spoken response review or text entry/i);
    const confirmBtn = screen.getByRole('button', { name: /Confirm spoken answer/i });
    fireEvent.change(spokenInput, { target: { value: 'As much as I always could' } });
    fireEvent.click(confirmBtn);

    // Advances to Question 2
    expect(screen.getByText(/Have you looked forward with enjoyment to things\?/i)).toBeInTheDocument();
    expect(screen.getByText('Question 2 of 10')).toBeInTheDocument();

    // Previously selected answer is preserved in chat history
    expect(screen.getAllByText(/As much as I always could/i).length).toBeGreaterThan(0);

    // Spoken response for Q2
    fireEvent.change(spokenInput, { target: { value: 'As much as I ever did' } });
    fireEvent.click(confirmBtn);

    // Advances to Question 3
    expect(screen.getByText(/Have you blamed yourself unnecessarily when things went wrong\?/i)).toBeInTheDocument();
    expect(screen.getByText('Question 3 of 10')).toBeInTheDocument();
  });

  it('Screen 2 — Voice-Based EPDS: multilingual switching and Hindi speech mapping without losing answers', () => {
    renderPatientApp('/patient/screening');

    // Initially in English
    expect(screen.getByText(/Have you been able to laugh and see the funny side of things\?/i)).toBeInTheDocument();

    // Answer Q1 in English
    const spokenInput = screen.getByLabelText(/Spoken response review or text entry/i);
    const confirmBtn = screen.getByRole('button', { name: /Confirm spoken answer/i });
    fireEvent.change(spokenInput, { target: { value: 'As much as I always could' } });
    fireEvent.click(confirmBtn);

    // Q2 in English
    expect(screen.getByText(/Have you looked forward with enjoyment to things\?/i)).toBeInTheDocument();

    // Switch language to Hindi
    const langSelect = screen.getByLabelText(/Select Questionnaire Language/i);
    fireEvent.change(langSelect, { target: { value: 'hi' } });

    // Q2 is now in Hindi
    expect(screen.getByText(/मैंने आने वाले दिनों और चीजों का आनंद के साथ इंतजार किया है/i)).toBeInTheDocument();

    // Spoken answer in Hindi for Q2
    fireEvent.change(spokenInput, { target: { value: 'उतना ही जितना मैं हमेशा कर सकती थी' } });
    fireEvent.click(confirmBtn);

    // Advances to Q3 in Hindi
    expect(screen.getByText('Question 3 of 10')).toBeInTheDocument();

    // Switch language to Bengali
    fireEvent.change(langSelect, { target: { value: 'bn' } });
    expect(screen.getByText(/কোনো কিছু ভুল হলে আমি অকারণেই নিজেকে দোষ দিয়েছি/i)).toBeInTheDocument();
  });

  it('Screen 2 — Voice-Based EPDS: Question 10 self-harm spoken response triggers immediate crisis helpline modal', () => {
    renderPatientApp('/patient/screening');

    const spokenInput = screen.getByLabelText(/Spoken response review or text entry/i);
    const confirmBtn = screen.getByRole('button', { name: /Confirm spoken answer/i });

    // Answer questions 1 to 9
    const answers1to9 = [
      'As much as I always could',
      'As much as I ever did',
      'No, never',
      'No, not at all',
      'No, not at all',
      'No, I have been coping as well as ever',
      'No, not at all',
      'No, not at all',
      'No, never',
    ];

    for (let i = 0; i < 9; i++) {
      fireEvent.change(spokenInput, { target: { value: answers1to9[i] } });
      fireEvent.click(confirmBtn);
    }

    // Now on Question 10
    expect(screen.getByText(/Has the thought of harming yourself occurred to you\?/i)).toBeInTheDocument();
    expect(screen.getByText('Question 10 of 10')).toBeInTheDocument();
    expect(screen.getByText(/Confidential • Your safety and wellbeing are our highest priority/i)).toBeInTheDocument();

    // Spoken response for Q10 indicating self-harm: "Yes, quite often"
    fireEvent.change(spokenInput, { target: { value: 'Yes, quite often' } });
    fireEvent.click(confirmBtn);

    // Immediate crisis modal appears
    expect(screen.getByText('Immediate Support & Care')).toBeInTheDocument();
    expect(screen.getByText(/Tele-MANAS \(Govt\. of India 24\/7\)/i)).toBeInTheDocument();
    expect(screen.getByText(/14416 \/ 1800 891 4416/i)).toBeInTheDocument();
    expect(screen.getByText(/KIRAN Mental Health Helpline/i)).toBeInTheDocument();
    expect(screen.getByText(/1800-599-0019/i)).toBeInTheDocument();

    // Acknowledge crisis modal
    const ackBtn = screen.getByRole('button', { name: /I Understand • View My Screening Report/i });
    expect(ackBtn).toBeInTheDocument();
    fireEvent.click(ackBtn);

    expect(screen.getByRole('heading', { level: 1, name: /Screening Results/i })).toBeInTheDocument();
  });

  it('Screen 2 — Voice-Based EPDS: unclear response displays gentle clarification notice without question advance', () => {
    renderPatientApp('/patient/screening');

    const spokenInput = screen.getByLabelText(/Spoken response review or text entry/i);
    const confirmBtn = screen.getByRole('button', { name: /Confirm spoken answer/i });

    // Submit ambiguous/unclear phrase
    fireEvent.change(spokenInput, { target: { value: 'uh maybe stuff whatever' } });
    fireEvent.click(confirmBtn);

    // Still on Question 1
    expect(screen.getByText('Question 1 of 10')).toBeInTheDocument();

    // Clarification notice is rendered
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/I didn't quite catch that/i)).toBeInTheDocument();

    // Providing clear answer resolves clarification and advances
    fireEvent.change(spokenInput, { target: { value: 'As much as I always could' } });
    fireEvent.click(confirmBtn);

    expect(screen.getByText('Question 2 of 10')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('Screen 2 — Demo Video Workspace: Gemini companion video controls operate in Demo Mode', () => {
    renderPatientApp('/patient/screening?mode=demo');

    // Gemini play/pause toggle
    const pauseGeminiBtn = screen.getByRole('button', { name: /Pause AI Companion Video/i });
    expect(pauseGeminiBtn).toBeInTheDocument();
    fireEvent.click(pauseGeminiBtn);
    expect(screen.getByRole('button', { name: /Play AI Companion Video/i })).toBeInTheDocument();

    // Gemini mute/unmute toggle
    const muteGeminiBtn = screen.getByRole('button', { name: /Mute AI Companion Audio|Unmute AI Companion Audio/i });
    expect(muteGeminiBtn).toBeInTheDocument();
    fireEvent.click(muteGeminiBtn);

    // Gemini video viewport present
    expect(screen.getByLabelText(/Miora AI Companion Video Viewport/i)).toBeInTheDocument();
  });

  it('Screen 2 — Camera Permissions: handles permission denial and provides retry button', async () => {
    navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue({ name: 'NotAllowedError' });

    renderPatientApp('/patient/screening');

    await waitFor(() => {
      expect(screen.getByText(/Camera Permission Denied/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: /Enable Camera Access/i });
    expect(retryBtn).toBeInTheDocument();

    // Clicking retry attempts to re-acquire media
    fireEvent.click(retryBtn);
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
  });

  it('Screen 3 — AI Assistant: renders hero banner, mood selector, prompt chips, and supports chat interactions', async () => {
    renderPatientApp('/patient/ai-assistant');

    // Heading
    expect(screen.getByRole('heading', { level: 1, name: /Your AI Companion/i })).toBeInTheDocument();

    // Mood today row
    expect(screen.getByText('Your Mood Today')).toBeInTheDocument();
    const okayMood = screen.getByRole('radio', { name: /Okay/i });
    expect(okayMood).toBeInTheDocument();

    // Prompt chips
    const copingChip = screen.getByRole('button', { name: /Coping Strategies/i });
    expect(copingChip).toBeInTheDocument();

    // Click prompt chip
    fireEvent.click(copingChip);
    expect(screen.getByText(/Could you share some simple coping strategies\?/i)).toBeInTheDocument();

    // Resources cards & Modal
    const audioCard = screen.getByRole('button', { name: /Open Relaxation Audio/i });
    expect(audioCard).toBeInTheDocument();
    fireEvent.click(audioCard);

    expect(screen.getByText('Relaxation Audio')).toBeInTheDocument();
    expect(screen.getByText(/Playing: Gentle Ocean Waves/i)).toBeInTheDocument();
  });

  it('Screen 3 — Voice-First AI Assistant: renders glowing orb, voice toolbar, speech input, interruption, and seamless mode switching with history preservation', async () => {
    renderPatientApp('/patient/ai-assistant');

    // 1. Voice Mode is Default View
    expect(screen.getByRole('tab', { name: /Voice Mode/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText("I'm here whenever you want to talk.")).toBeInTheDocument();
    expect(screen.getByText("M")).toBeInTheDocument(); // Central orb initial

    // 2. Toolbar controls
    const tapToTalkBtn = screen.getByRole('button', { name: /Start speaking/i });
    expect(tapToTalkBtn).toBeInTheDocument();
    const replayBtn = screen.getByRole('button', { name: /Replay last response/i });
    expect(replayBtn).toBeInTheDocument();

    // 3. Audio input & Listening state
    fireEvent.click(tapToTalkBtn);
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(await screen.findByText(/Miora is listening/i)).toBeInTheDocument();
    expect(await screen.findByText(/Listening for your voice/i)).toBeInTheDocument();

    // 4. Mute / Stop listening
    const muteBtn = screen.getByRole('button', { name: /Stop listening/i });
    fireEvent.click(muteBtn);
    expect(await screen.findByText("I'm here whenever you want to talk.")).toBeInTheDocument();

    // 5. Replay last response triggers speech synthesis
    fireEvent.click(replayBtn);
    expect(window.speechSynthesis.speak).toHaveBeenCalled();

    // 6. When Miora is speaking, Interrupt button appears and cancels speech synthesis
    expect(await screen.findByRole('button', { name: /Interrupt Miora and speak/i })).toBeInTheDocument();
    const interruptBtn = screen.getByRole('button', { name: /Interrupt Miora and speak/i });
    fireEvent.click(interruptBtn);
    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
    expect(await screen.findByText(/Miora is listening/i)).toBeInTheDocument();

    // Clean up listening state
    fireEvent.click(screen.getByRole('button', { name: /Stop listening/i }));

    // 7. Language switching updates speech & synthesis language
    const langSelect = screen.getByRole('combobox', { name: /Select conversational language/i });
    expect(langSelect).toBeInTheDocument();
    fireEvent.change(langSelect, { target: { value: 'hi' } });
    expect(langSelect.value).toBe('hi');

    // 8. Seamless Mode Switching to Text Mode: preserves conversation history
    const textModeTab = screen.getByRole('tab', { name: /Text Mode/i });
    fireEvent.click(textModeTab);
    expect(textModeTab).toHaveAttribute('aria-selected', 'true');

    // Message bubbles are present from shared history
    expect(screen.getByText(/I've been feeling a bit anxious and overwhelmed lately/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /Message Miora AI/i })).toBeInTheDocument();

    // Send a message in Text Mode
    const textInput = screen.getByRole('textbox', { name: /Message Miora AI/i });
    fireEvent.change(textInput, { target: { value: 'How can I get more rest?' } });
    const sendBtn = screen.getByRole('button', { name: /Send message/i });
    fireEvent.click(sendBtn);

    expect(screen.getByText('How can I get more rest?')).toBeInTheDocument();

    // 9. Switch back to Voice Mode: history is completely preserved
    const voiceModeTab = screen.getByRole('tab', { name: /Voice Mode/i });
    fireEvent.click(voiceModeTab);
    expect(voiceModeTab).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByText("I'm here whenever you want to talk.")).toBeInTheDocument();
  });

  it('Screen 4 — Connect to a Doctor: displays Dr. Elena Rostova profile, notice, records, and supports consultation booking', () => {
    renderPatientApp('/patient/connect-doctor');

    // Heading
    expect(screen.getByRole('heading', { level: 1, name: /Connect to a Doctor/i })).toBeInTheDocument();

    // Telehealth Simulation Notice
    expect(screen.getByText(/Telehealth Simulation Notice/i)).toBeInTheDocument();

    // Doctor profile card
    expect(screen.getByText('Dr. Elena Rostova, MD')).toBeInTheDocument();
    expect(screen.getAllByText(/Perinatal Psychiatry Lead/i).length).toBeGreaterThan(0);

    // Consultations list
    expect(screen.getByText('20 Nov 2026')).toBeInTheDocument();
    expect(screen.getByText('Telehealth Video')).toBeInTheDocument();

    // Open booking modal
    const scheduleBtn = screen.getByRole('button', { name: /Schedule Consultation/i });
    fireEvent.click(scheduleBtn);

    expect(screen.getByText('Schedule New Consultation')).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /Confirm Consultation/i });
    fireEvent.click(confirmBtn);

    expect(screen.getByText(/Consultation successfully scheduled with Dr. Elena Rostova!/i)).toBeInTheDocument();
  });

  it('Screen 5 — My Reports: renders overview metrics, risk score gauge, trend chart, and tab switching', async () => {
    renderPatientApp('/patient/reports');

    // Title
    expect(screen.getByRole('heading', { level: 1, name: /My Reports & Analytics/i })).toBeInTheDocument();

    // Cards in Overview
    expect(screen.getByText('Latest Screening Result')).toBeInTheDocument();
    expect(screen.getByText('64%')).toBeInTheDocument();
    expect(screen.getByText('Moderate Risk for PPD')).toBeInTheDocument();
    expect(screen.getByText('Emotional Well-being Trend')).toBeInTheDocument();
    expect(screen.getByText('Download Reports')).toBeInTheDocument();
    expect(screen.getByText('Key Insights & Clinical Signals')).toBeInTheDocument();

    // Download action
    const downloadBtn = screen.getAllByRole('button', { name: /Download/i })[0];
    fireEvent.click(downloadBtn);
    expect(await screen.findByText(/Downloaded/i)).toBeInTheDocument();

    // Tab switching to Screening Reports
    const screeningTab = screen.getByRole('tab', { name: /Screening Reports/i });
    fireEvent.click(screeningTab);
    expect(screen.getByText('Detailed AI Screening Assessment')).toBeInTheDocument();
    expect(screen.getByText('14 / 30')).toBeInTheDocument();
  });

  it('Screen 6 — Care Suggestions: renders recovery plan, exercise cards, and interactive progress checklist', () => {
    renderPatientApp('/patient/care-suggestions');

    // Title
    expect(screen.getByRole('heading', { level: 1, name: /Personalised Care Suggestions/i })).toBeInTheDocument();

    // 4-Week plan
    expect(screen.getByText(/Your 4-Week Postpartum Recovery Plan/i)).toBeInTheDocument();

    // Exercise cards
    expect(screen.getByText('4-7-8 Breathing')).toBeInTheDocument();
    expect(screen.getByText('Sleep Restoration')).toBeInTheDocument();
    expect(screen.getByText('Daily Reflection')).toBeInTheDocument();

    // Daily Checklist & task toggling
    expect(screen.getByText('Daily Checklist')).toBeInTheDocument();
    const journalTask = screen.getByText('Journaling');
    expect(journalTask).toBeInTheDocument();

    // Toggle task
    fireEvent.click(journalTask);

    // Interactive modal for breathing exercise
    const startBreathingBtn = screen.getByRole('button', { name: /Start \(5 min\)/i });
    fireEvent.click(startBreathingBtn);
    expect(screen.getByText('4-7-8 Breathing Exercise')).toBeInTheDocument();
    const completeModalBtn = screen.getByRole('button', { name: /Complete Exercise & Mark Done/i });
    fireEvent.click(completeModalBtn);
  });

  it('Patient Dashboard default route: renders Patient Home at /patient/dashboard while My Reports remains at /patient/reports', () => {
    renderPatientApp('/patient/dashboard');

    // Heading for Patient Home
    expect(screen.getByRole('heading', { level: 1, name: /Welcome back, Amara/i })).toBeInTheDocument();
    expect(screen.getByText(/Your personalized companion for postpartum recovery/i)).toBeInTheDocument();

    // Dashboard quick action cards
    expect(screen.getByRole('heading', { level: 2, name: /Postpartum Wellness Index/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /AI Screening Check-In/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /AI Assistant Companion/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /Care Suggestions/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /Medical History & Records/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /Connect to a Doctor/i })).toBeInTheDocument();

    // Action button to navigate to My Reports
    expect(screen.getByRole('button', { name: /View Full Reports & Analytics/i })).toBeInTheDocument();
  });
});

