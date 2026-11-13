import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { LandingPageRoute } from './LandingPageRoute.jsx';
import { ClinicalProvider } from './dashboard/context/ClinicalContext.jsx';
import { DashboardLayout } from './dashboard/DashboardLayout.jsx';
import { CommandCenterPage } from './dashboard/pages/CommandCenterPage.jsx';
import { MothersCasesPage } from './dashboard/pages/MothersCasesPage.jsx';
import { LiveScreeningPage } from './dashboard/pages/LiveScreeningPage.jsx';
import { ResultsPage } from './dashboard/pages/ResultsPage.jsx';
import { DiscordancePage } from './dashboard/pages/DiscordancePage.jsx';
import { InsightsCarePage } from './dashboard/pages/InsightsCarePage.jsx';

export function App() {
  return (
    <ClinicalProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPageRoute />} />
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<CommandCenterPage />} />
            <Route path="/command-center" element={<Navigate to="/dashboard" replace />} />
            <Route path="/mothers" element={<MothersCasesPage />} />
            <Route path="/mothers/:motherId" element={<MothersCasesPage />} />
            <Route path="/live-screening" element={<LiveScreeningPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:motherId" element={<ResultsPage />} />
            <Route path="/discordance" element={<DiscordancePage />} />
            <Route path="/clinical-review" element={<DiscordancePage />} />
            <Route path="/insights" element={<InsightsCarePage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ClinicalProvider>
  );
}
export default App;

