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

  it('Screen 2 — AI Screening: renders 2-column workspace with video controls, conversation panel, and session controls', () => {
    renderPatientApp('/patient/screening');

    // Progress tracker stages
    expect(screen.getAllByText('Medical History').length).toBeGreaterThan(0);
    expect(screen.getByText('Screening')).toBeInTheDocument();
    expect(screen.getByText('Analysis')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();

    // Video area & badges
    expect(screen.getByLabelText('Patient Video Feed')).toBeInTheDocument();
    expect(screen.getByText('You (Live)')).toBeInTheDocument();

    // Conversational panel
    expect(screen.getByText('Miora AI')).toBeInTheDocument();
    expect(screen.getByText(/In the past two weeks, how often have you felt low, sad, or hopeless\?/i)).toBeInTheDocument();
    expect(screen.getByText(/I've been feeling a bit low almost every day/i)).toBeInTheDocument();

    // Media toggle controls
    const camBtn = screen.getByRole('button', { name: /Turn camera off/i });
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

