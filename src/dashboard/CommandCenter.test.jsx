import React from 'react';
import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { LandingPageRoute } from '../LandingPageRoute.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { CommandCenterPage } from './pages/CommandCenterPage.jsx';
import { MothersCasesPage } from './pages/MothersCasesPage.jsx';
import { LiveScreeningPage } from './pages/LiveScreeningPage.jsx';
import { ResultsPage } from './pages/ResultsPage.jsx';
import { DiscordancePage } from './pages/DiscordancePage.jsx';
import { InsightsCarePage } from './pages/InsightsCarePage.jsx';

function renderDashboard(initialEntry = '/dashboard') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<CommandCenterPage />} />
            <Route path="/mothers" element={<MothersCasesPage />} />
            <Route path="/mothers/:motherId" element={<MothersCasesPage />} />
            <Route path="/live-screening" element={<LiveScreeningPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:motherId" element={<ResultsPage />} />
            <Route path="/discordance" element={<DiscordancePage />} />
            <Route path="/insights" element={<InsightsCarePage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 01: Dashboard', () => {
  it('renders top navigation, header, KPI cards, charts, priority cases, recent screenings, and quick actions', () => {
    renderDashboard();

    // Top Navigation
    expect(screen.getByRole('link', { name: 'Miora Dashboard' })).toBeInTheDocument();
    expect(screen.queryByText('Maternal Emotional')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Mothers & Cases' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Screening' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Results' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Discordance' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Insights & Care' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clinician profile menu' })).toHaveTextContent('DR');

    // Dashboard Header
    expect(screen.getByText('DASHBOARD')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Postpartum Health Intelligence');
    expect(screen.getByRole('button', { name: /Start Screening/i })).toBeInTheDocument();

    // 4 KPI Cards
    expect(screen.getByText('328')).toBeInTheDocument();
    expect(screen.getByText('Registered Mothers')).toBeInTheDocument();
    expect(screen.getByText('Screenings Completed')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
    expect(screen.getByText('Cases for Review')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Potential Discordance')).toBeInTheDocument();

    // Risk Distribution
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
    expect(screen.getByText('58% (143)')).toBeInTheDocument();
    expect(screen.getByText('Moderate Risk')).toBeInTheDocument();
    expect(screen.getByText('20% (49)')).toBeInTheDocument();
    expect(screen.getByText('High Risk')).toBeInTheDocument();
    expect(screen.getByText('14% (35)')).toBeInTheDocument();
    expect(screen.getByText('Requires Review')).toBeInTheDocument();
    expect(screen.getByText('8% (20)')).toBeInTheDocument();

    // Priority Cases
    expect(screen.getByText('M-104')).toBeInTheDocument();
    expect(screen.getByText('Elevated distress cues')).toBeInTheDocument();
    expect(screen.getByText('M-108')).toBeInTheDocument();
    expect(screen.getByText('Voice-text mismatch')).toBeInTheDocument();
    expect(screen.getByText('M-112')).toBeInTheDocument();
    expect(screen.getByText('Incomplete screening')).toBeInTheDocument();

    // Recent Screenings
    expect(screen.getByText('M-117')).toBeInTheDocument();
    expect(screen.getByText('Completed · 10 min ago')).toBeInTheDocument();
    expect(screen.getByText('M-116')).toBeInTheDocument();
    expect(screen.getByText('Completed · 24 min ago')).toBeInTheDocument();
    expect(screen.getByText('M-115')).toBeInTheDocument();
    expect(screen.getByText('Completed · 36 min ago')).toBeInTheDocument();

    // Quick Actions
    expect(screen.getByRole('button', { name: 'Add Mother' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Review Cases' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View Insights' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clinical Review' })).toBeInTheDocument();
  });

  it('registers a new mother via Quick Actions Add Mother modal and updates KPI count', () => {
    renderDashboard();

    fireEvent.click(screen.getByRole('button', { name: 'Add Mother' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('e.g. Nadia P.'), {
      target: { value: 'Layla S.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Complete Registration' }));
    expect(screen.getByText(/Registered as M-118/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Done' }));
    expect(screen.getByText('329')).toBeInTheDocument();
  });

  it('navigates from Priority Cases row to Mother profile and from Start Screening to Live Screening', () => {
    renderDashboard();

    fireEvent.click(screen.getByRole('button', { name: 'Open case profile for M-104' }));
    expect(screen.getByRole('heading', { name: 'Amara K.' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Dashboard' }));
    fireEvent.click(screen.getByRole('button', { name: /Start Screening/i }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Maternal Screening Session/i);
    expect(screen.getByRole('button', { name: /Complete Screening/i })).toBeInTheDocument();
  });

  it('navigates from Landing Page Get Started button to Login', () => {
    render(
      <ClinicalProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<LandingPageRoute />} />
            <Route path="/login" element={<div><h1>Welcome Back</h1></div>} />
          </Routes>
        </MemoryRouter>
      </ClinicalProvider>
    );

    const getStartedLink = screen.getAllByRole('link', { name: /Get Started/i })[0];
    expect(getStartedLink).toHaveAttribute('href', '/login');
    fireEvent.click(getStartedLink);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome Back'
    );
  });
});

