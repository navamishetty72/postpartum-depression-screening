import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { ResultsPage } from './pages/ResultsPage.jsx';
import { DiscordancePage } from './pages/DiscordancePage.jsx';

function renderResults(initialEntry = '/results') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:motherId" element={<ResultsPage />} />
            <Route path="/clinical-review" element={<DiscordancePage />} />
            <Route path="/mothers" element={<div>Mothers Registry</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 05: Maternal Screening Results', () => {
  it('renders header, patient strip, 3-column assessment row, trend/factors/interpretation row, and next steps', () => {
    renderResults();

    expect(screen.getByRole('link', { name: 'Results' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByText('SCREENING RESULTS')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Maternal Screening Results'
    );
    expect(screen.getByRole('button', { name: /Export Report/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Share Case/i })).toBeInTheDocument();

    // Patient Strip defaults to M-108
    expect(screen.getByLabelText('Select screening session')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();
    expect(screen.getByText('Apr 16, 2026 · 10:24 AM')).toBeInTheDocument();
    expect(screen.getByText('Screening Completed')).toBeInTheDocument();

    // Row 1: Overall Risk, Modality-wise Analysis, Multimodal Summary
    expect(screen.getByRole('heading', { name: 'Overall Risk Assessment' })).toBeInTheDocument();
    expect(screen.getAllByText('0.62')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'Modality-wise Analysis' })).toBeInTheDocument();
    expect(screen.getByText('0.58')).toBeInTheDocument();
    expect(screen.getByText('0.66')).toBeInTheDocument();
    expect(screen.getByText('0.60')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Multimodal Summary' })).toBeInTheDocument();
    expect(screen.getByText('3 of 3 modalities processed')).toBeInTheDocument();

    // Row 2: Risk Trend, Key Contributing Factors, Interpretation
    expect(screen.getByRole('heading', { name: 'Risk Trend' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Key Contributing Factors' })).toBeInTheDocument();
    expect(screen.getByText('Elevated negative sentiment in text')).toBeInTheDocument();
    expect(screen.getByText('Higher vocal strain and lower energy')).toBeInTheDocument();
    expect(screen.getByText('Reduced positive facial expressiveness')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Interpretation' })).toBeInTheDocument();

    // Recommended Next Steps
    expect(screen.getByRole('heading', { name: 'Recommended Next Steps' })).toBeInTheDocument();
    expect(screen.getByText('Schedule follow-up in 7 days')).toBeInTheDocument();
    expect(screen.getByText('Consider brief clinical review')).toBeInTheDocument();
    expect(screen.getByText('Provide support resources')).toBeInTheDocument();
  });

  it('supports Export Report, Share Case with consent, Support Resources, and Follow-up action', () => {
    const createObjectUrlSpy = vi.fn(() => 'blob:mock-report');
    const revokeObjectUrlSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrlSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrlSpy,
    });

    renderResults();

    // Export Report modal
    fireEvent.click(screen.getByRole('button', { name: /Export Report/i }));
    expect(screen.getByRole('dialog', { name: /Export Screening Report/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Download Report/i }));
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('status')).toHaveTextContent('Report downloaded successfully.');
    fireEvent.click(screen.getByRole('button', { name: 'Close export modal' }));

    // Share Case requires consent
    fireEvent.click(screen.getByRole('button', { name: /Share Case/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Send Internal Handoff' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/consent/i);
    fireEvent.click(screen.getByLabelText(/Confirm patient consent/i));
    fireEvent.click(screen.getByRole('button', { name: 'Send Internal Handoff' }));
    expect(screen.getByText(/Shared with Perinatal Psychiatry Team/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Done' }));

    // Schedule Follow-up & Support Resources
    fireEvent.click(screen.getByRole('button', { name: /Schedule follow-up in 7 days/i }));
    expect(screen.getByRole('status')).toHaveTextContent(
      '7-day follow-up scheduled for M-108'
    );

    fireEvent.click(screen.getByRole('button', { name: /Provide support resources/i }));
    expect(screen.getByRole('dialog', { name: /Maternal Support Resources/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close support resources modal' }));

    // Clinical Review navigation
    fireEvent.click(screen.getByRole('button', { name: /Consider brief clinical review/i }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Voice–Text Discordance Review'
    );
  });

  it('handles partial modality availability, missing historical trend, and missing mother record', () => {
    renderResults('/results/M-112');

    expect(screen.getByText('Screening Pending')).toBeInTheDocument();
    expect(screen.getByText('1 of 3 modalities processed')).toBeInTheDocument();
    expect(screen.getAllByText('Unavailable').length).toBe(2);
    expect(
      screen.getByText('No historical screening trend available yet for this mother.')
    ).toBeInTheDocument();

    renderResults('/results/M-999');
    expect(screen.getByText('Screening Record Not Found')).toBeInTheDocument();
  });
});
