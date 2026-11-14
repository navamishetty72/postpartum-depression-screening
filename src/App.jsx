import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { LandingPageRoute } from './LandingPageRoute.jsx';
import { LoginScreen } from './LoginScreen.jsx';
import { CreateAccountScreen } from './CreateAccountScreen.jsx';
import { PatientLayout } from './patient/layout/PatientLayout.jsx';
import { PatientScreeningPage } from './patient/pages/PatientScreeningPage.jsx';
import { ScreeningResultsPage } from './patient/pages/ScreeningResultsPage.jsx';
import { MedicalHistoryScreen } from './patient/pages/MedicalHistoryScreen.jsx';
import { AiAssistantScreen } from './patient/pages/AiAssistantScreen.jsx';
import { ConnectDoctorPage } from './patient/pages/ConnectDoctorPage.jsx';
import { PatientHomePage } from './patient/pages/PatientHomePage.jsx';
import { PatientReportsPage } from './patient/pages/PatientReportsPage.jsx';
import { CareSuggestionsPage } from './patient/pages/CareSuggestionsPage.jsx';
import { PatientProvider } from './patient/context/PatientContext.jsx';
import { ClinicalProvider } from './dashboard/context/ClinicalContext.jsx';
import { DashboardLayout } from './dashboard/DashboardLayout.jsx';
import { CommandCenterPage } from './dashboard/pages/CommandCenterPage.jsx';
import { MothersCasesPage } from './dashboard/pages/MothersCasesPage.jsx';
import { LiveScreeningPage } from './dashboard/pages/LiveScreeningPage.jsx';
import { UploadAnalyzePage } from './dashboard/pages/UploadAnalyzePage.jsx';
import { ResultsPage } from './dashboard/pages/ResultsPage.jsx';
import { DiscordancePage } from './dashboard/pages/DiscordancePage.jsx';
import { InsightsCarePage } from './dashboard/pages/InsightsCarePage.jsx';
import { ClinicalReviewPage } from './dashboard/pages/ClinicalReviewPage.jsx';

export function App() {
  return (
    <ClinicalProvider>
      <PatientProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPageRoute />} />
            <Route path="/login" element={<LoginScreen />} />
            <Route path="/signin" element={<Navigate to="/login" replace />} />
            <Route path="/create-account" element={<CreateAccountScreen />} />
            <Route path="/register" element={<CreateAccountScreen />} />
            <Route path="/signup" element={<Navigate to="/create-account" replace />} />

            {/* Patient Portal Routes with Unified Patient Shell */}
            <Route element={<PatientLayout />}>
              <Route path="/patient/dashboard" element={<PatientHomePage />} />
              <Route path="/patient/home" element={<PatientHomePage />} />
              <Route path="/patient" element={<Navigate to="/patient/dashboard" replace />} />
              <Route path="/patient/reports" element={<PatientReportsPage />} />
              <Route path="/patient/my-reports" element={<Navigate to="/patient/reports" replace />} />
              <Route path="/reports" element={<Navigate to="/patient/reports" replace />} />
              <Route path="/my-reports" element={<Navigate to="/patient/reports" replace />} />
              <Route path="/patient/profile" element={<PatientHomePage />} />
              <Route path="/patient/settings" element={<PatientHomePage />} />

              {/* AI Assistant / Companion */}
              <Route path="/ai-assistant" element={<AiAssistantScreen />} />
              <Route path="/patient/ai-assistant" element={<AiAssistantScreen />} />
              <Route path="/patient/companion" element={<Navigate to="/patient/ai-assistant" replace />} />
              <Route path="/assistant" element={<Navigate to="/patient/ai-assistant" replace />} />
              <Route path="/voice-assistant" element={<Navigate to="/patient/ai-assistant" replace />} />

              {/* Screening Journey (Stages 1-4) */}
              <Route path="/medical-history" element={<MedicalHistoryScreen />} />
              <Route path="/patient/medical-history" element={<MedicalHistoryScreen />} />
              <Route path="/patient/history" element={<Navigate to="/patient/medical-history" replace />} />

              <Route path="/screening" element={<PatientScreeningPage />} />
              <Route path="/ai-screening" element={<PatientScreeningPage />} />
              <Route path="/patient/screening" element={<PatientScreeningPage />} />
              <Route path="/patient-screening" element={<PatientScreeningPage />} />
              <Route path="/patient/ai-screening" element={<PatientScreeningPage />} />
              <Route path="/patient/live-screening" element={<Navigate to="/patient/screening" replace />} />

              <Route path="/screening-results" element={<ScreeningResultsPage />} />
              <Route path="/screening/results" element={<ScreeningResultsPage />} />
              <Route path="/patient/screening/results" element={<ScreeningResultsPage />} />
              <Route path="/patient/results" element={<ScreeningResultsPage />} />

              {/* Care Suggestions & Doctor Consultations */}
              <Route path="/patient/care-suggestions" element={<CareSuggestionsPage />} />
              <Route path="/care-suggestions" element={<CareSuggestionsPage />} />
              <Route path="/patient/suggestions" element={<Navigate to="/patient/care-suggestions" replace />} />

              <Route path="/patient/connect-doctor" element={<ConnectDoctorPage />} />
              <Route path="/connect-doctor" element={<ConnectDoctorPage />} />
              <Route path="/patient/connect" element={<Navigate to="/patient/connect-doctor" replace />} />
            </Route>

            {/* Clinician Dashboard */}
            <Route element={<DashboardLayout />}>
              <Route path="/dashboard" element={<CommandCenterPage />} />
              <Route path="/command-center" element={<Navigate to="/dashboard" replace />} />
              <Route path="/mothers" element={<MothersCasesPage />} />
              <Route path="/mothers/:motherId" element={<MothersCasesPage />} />
              <Route path="/live-screening" element={<LiveScreeningPage />} />
              <Route path="/upload-analyze" element={<UploadAnalyzePage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/results/:motherId" element={<ResultsPage />} />
              <Route path="/discordance" element={<DiscordancePage />} />
              <Route path="/discordance/:motherId" element={<DiscordancePage />} />
              <Route path="/clinical-review" element={<ClinicalReviewPage />} />
              <Route path="/clinical-review/:motherId" element={<ClinicalReviewPage />} />
              <Route path="/insights" element={<InsightsCarePage />} />
              <Route path="/insights/:motherId" element={<InsightsCarePage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </PatientProvider>
    </ClinicalProvider>
  );
}

export default App;
