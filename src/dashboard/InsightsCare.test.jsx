import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { InsightsCarePage } from './pages/InsightsCarePage.jsx';

function renderInsights(initialEntry = '/insights') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/insights" element={<InsightsCarePage />} />
            <Route path="/insights/:motherId" element={<InsightsCarePage />} />
            <Route path="/mothers/:motherId" element={<div>Mother Case View</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 07: Personalized Insights & Care', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders header, patient strip, insights, recommendations, timeline, trend, resources, notes, and summary', () => {
    renderInsights();

    expect(screen.getByRole('link', { name: 'Insights & Care' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByText('INSIGHTS & CARE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Personalized Insights & Care'
    );
    expect(screen.getByRole('button', { name: /Schedule Follow-up/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Care Plan \(PDF\)/i })).toBeInTheDocument();

    // Patient Strip defaults to M-108
    expect(screen.getByLabelText('Select mother for care plan')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();
    expect(screen.getByText('Apr 16, 2026')).toBeInTheDocument();
    expect(screen.getByText('Care Plan Ready')).toBeInTheDocument();

    // Row 1
    expect(screen.getByRole('heading', { name: 'Key Insights' })).toBeInTheDocument();
    expect(screen.getByText(/Moderate risk of postpartum distress \(Score: 0.62\)/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Care Recommendations' })).toBeInTheDocument();
    expect(screen.getByText('Emotional Support')).toBeInTheDocument();
    expect(screen.getByText('Counselling Referral')).toBeInTheDocument();
    expect(screen.getByText('Wellbeing Practices')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Follow-up Plan' })).toBeInTheDocument();
    expect(screen.getByText('In 7 days')).toBeInTheDocument();
    expect(screen.getByText('In 2 weeks')).toBeInTheDocument();
    expect(screen.getByText('In 4 weeks')).toBeInTheDocument();

    // Row 2
    expect(screen.getByRole('heading', { name: 'Wellbeing Trend' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Support Resources' })).toBeInTheDocument();
    expect(screen.getByText('Coping Strategies')).toBeInTheDocument();
    expect(screen.getByText('Support Groups')).toBeInTheDocument();
    expect(screen.getByText('Educational Resources')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Care Team Notes' })).toBeInTheDocument();
    expect(screen.getByText('0 / 500')).toBeInTheDocument();

    // Summary
    expect(screen.getByRole('heading', { name: 'Care Plan Summary' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Finalize Care Plan/i })).toBeInTheDocument();
  });

  it('supports scheduling follow-up, editing milestone, saving notes, PDF download, and finalizing plan', () => {
    const createObjectUrlSpy = vi.fn(() => 'blob:mock-pdf');
    const revokeObjectUrlSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrlSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrlSpy,
    });

    renderInsights();

    // Schedule Follow-up
    fireEvent.click(screen.getByRole('button', { name: /Schedule Follow-up/i }));
    expect(screen.getByRole('dialog', { name: /Schedule Follow-up/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Follow-up Focus / Description'), {
      target: { value: 'Check sleep schedule and partner support.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save Appointment' }));
    expect(screen.getByText('Check sleep schedule and partner support.')).toBeInTheDocument();

    // Mark a milestone completed
    fireEvent.click(screen.getByRole('button', { name: 'Mark Clinical review completed' }));
    expect(
      screen.getByRole('button', { name: 'Mark Clinical review incomplete' })
    ).toHaveTextContent('Done');

    // Save Care Team Notes
    const notesInput = screen.getByLabelText('Care team clinical notes');
    fireEvent.change(notesInput, { target: { value: 'Discussed sleep rotation plan.' } });
    expect(screen.getByText('30 / 500')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save Notes' }));
    expect(screen.getByText(/Notes saved at/i)).toBeInTheDocument();

    // Care Plan PDF export
    fireEvent.click(screen.getByRole('button', { name: /Care Plan \(PDF\)/i }));
    expect(screen.getByRole('dialog', { name: /Care Plan PDF Export/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Download Care Plan \(\.pdf\)/i }));
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Care Plan PDF downloaded.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close Care Plan PDF modal' }));

    // Finalize Care Plan
    fireEvent.click(screen.getByRole('button', { name: /Finalize Care Plan/i }));
    expect(screen.getByText('Care Plan Finalized')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      /Care plan finalized for M-108/i
    );
  });

  it('shows honest empty trend state when historical records are unavailable', () => {
    renderInsights('/insights/M-112');

    expect(
      screen.getByText('No historical wellbeing trend available yet for this mother.')
    ).toBeInTheDocument();
  });
});
