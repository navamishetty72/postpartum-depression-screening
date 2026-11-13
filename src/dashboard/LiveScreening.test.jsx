import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { LiveScreeningPage } from './pages/LiveScreeningPage.jsx';
import { UploadAnalyzePage } from './pages/UploadAnalyzePage.jsx';
import { ResultsPage } from './pages/ResultsPage.jsx';

function renderLiveScreening(initialEntry = '/live-screening') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/live-screening" element={<LiveScreeningPage />} />
            <Route path="/upload-analyze" element={<UploadAnalyzePage />} />
            <Route path="/results/:motherId" element={<ResultsPage />} />
            <Route path="/dashboard" element={<div>Dashboard View</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 03: Live Screening', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('renders header, live elapsed timer, mode switch, patient strip, 3-column workspace, and preliminary empty state', () => {
    vi.useFakeTimers();
    renderLiveScreening();

    expect(screen.getByRole('link', { name: 'Live Screening' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByText('LIVE SCREENING')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Maternal Screening Session'
    );
    expect(screen.getByText('Live Session Active')).toBeInTheDocument();
    expect(screen.getByLabelText('Elapsed session time')).toHaveTextContent('00:00');

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.getByLabelText('Elapsed session time')).toHaveTextContent('00:03');

    // Patient Strip defaults to M-108
    expect(screen.getByLabelText('Select mother for screening')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();
    expect(screen.getByText('Multimodal (Text · Voice · Video)')).toBeInTheDocument();

    // Workspace panels & pending preliminary state (no fake scores)
    expect(screen.getByRole('heading', { name: 'Live Session' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Conversation' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Real-time Signals' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Session Progress' })).toBeInTheDocument();
    expect(screen.getByText('0 / 3 Modalities')).toBeInTheDocument();
    expect(screen.getByText('Awaiting session completion')).toBeInTheDocument();
  });

  it('switches to Upload & Analyze screen as a separate workflow', () => {
    renderLiveScreening();
    fireEvent.click(screen.getByRole('tab', { name: /Upload & Analyze/i }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Asynchronous Screening Upload'
    );
  });

  it('requires media consent, handles permission denial gracefully, and supports guided conversation & completion', async () => {
    const getUserMediaMock = vi.fn().mockRejectedValue(
      Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' })
    );
    Object.defineProperty(window.navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: getUserMediaMock },
    });

    renderLiveScreening();

    // Try completing with zero captured modalities -> blocked with validation alert
    fireEvent.click(screen.getByRole('button', { name: /Complete Screening/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      /Please record at least one conversation response or media capture/i
    );

    // Attempt to enable media with consent -> permission error displayed clearly
    fireEvent.click(screen.getByRole('button', { name: /Consent & Start Media/i }));
    await waitFor(() => {
      expect(getUserMediaMock).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText(/permission was denied/i)).toBeInTheDocument();

    // Continue screening via Conversation
    const input = screen.getByLabelText('Mother response text');
    fireEvent.change(input, { target: { value: 'Feeling tired but supported today.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send response' }));

    expect(screen.getByText('Feeling tired but supported today.')).toBeInTheDocument();
    expect(screen.getByText('1 / 3 Modalities')).toBeInTheDocument();
    expect(screen.getByText('Captured (1)')).toBeInTheDocument();

    // Save Draft
    fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
    expect(screen.getByRole('status')).toHaveTextContent(/Draft saved at/i);

    // Cancel Screening asks for confirmation when session has progress
    fireEvent.click(screen.getByRole('button', { name: /Cancel Screening/i }));
    expect(
      screen.getByRole('dialog', { name: /Discard Screening Session/i })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Keep Session' }));

    // Complete Screening navigates to Results for M-108
    fireEvent.click(screen.getByRole('button', { name: /Complete Screening/i }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Wellbeing Results Archive'
    );
  });
});

