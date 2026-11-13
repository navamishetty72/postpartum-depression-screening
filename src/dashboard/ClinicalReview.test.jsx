import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { ClinicalReviewPage } from './pages/ClinicalReviewPage.jsx';

function renderClinicalReview(initialEntry = '/clinical-review', reviewSubmitter) {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route
              path="/clinical-review"
              element={<ClinicalReviewPage reviewSubmitter={reviewSubmitter} />}
            />
            <Route
              path="/clinical-review/:motherId"
              element={<ClinicalReviewPage reviewSubmitter={reviewSubmitter} />}
            />
            <Route path="/insights/:motherId" element={<div>Insights Care Target</div>} />
            <Route path="/results/:motherId" element={<div>Results Target</div>} />
            <Route path="/mothers/:motherId" element={<div>Mother Record Target</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 08: Clinical Review & Assessment', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders navigation, header, patient strip, Row 1 cards, Row 2 cards, and bottom finalization bar', () => {
    renderClinicalReview();

    expect(screen.getByRole('link', { name: 'Clinical Review' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByRole('link', { name: 'Screening' })).toBeInTheDocument();
    expect(screen.getByText('CLINICAL REVIEW')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Clinical Review & Assessment'
    );
    expect(screen.getByRole('button', { name: /Previous Results/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Export Clinical Note/i })).toBeInTheDocument();

    // Patient Strip (M-108 default)
    expect(screen.getByLabelText('Select mother for clinical review')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();
    expect(screen.getByText('Apr 16, 2026')).toBeInTheDocument();
    expect(screen.getByText('Under Clinical Review')).toBeInTheDocument();

    // Row 1A: AI Screening Summary
    expect(screen.getByRole('heading', { name: 'AI Screening Summary' })).toBeInTheDocument();
    expect(screen.getByText('0.62 (Moderate)')).toBeInTheDocument();
    expect(screen.getByText('0.81 (High)')).toBeInTheDocument();
    expect(screen.getByText('0.66')).toBeInTheDocument();
    expect(screen.getByText('0.60')).toBeInTheDocument();
    expect(screen.getByText('0.58')).toBeInTheDocument();

    // Row 1B: Key Evidence
    expect(screen.getByRole('heading', { name: 'Key Evidence' })).toBeInTheDocument();
    expect(screen.getByText('Voice:')).toBeInTheDocument();
    expect(screen.getByText('Facial:')).toBeInTheDocument();
    expect(screen.getByText('Text:')).toBeInTheDocument();

    // Row 1C: Clinical Assessment
    expect(screen.getByRole('heading', { name: 'Clinical Assessment' })).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Record your clinical impression, key observations and context/i)
    ).toBeInTheDocument();
    expect(screen.getByText('0 / 500')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Low' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Moderate' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'High' })).toBeInTheDocument();

    // Row 2A, 2B, 2C & Bottom bar
    expect(screen.getByRole('heading', { name: 'Comparison: AI vs Clinician' })).toBeInTheDocument();
    expect(screen.getByText('Pending Clinician Assessment')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Clinical Decision' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Follow-up & Care Plan/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back to Insights & Care/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Finalize & Save/i })).toBeInTheDocument();
  });

  it('validates required inputs, updates AI vs Clinician comparison, handles disagreement rationale, backend failure retry, and confirmation save', async () => {
    const mockSubmitter = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        message: 'Could not reach EHR API. Your notes remain intact.',
      })
      .mockResolvedValueOnce({
        ok: true,
        persistenceMode: 'remote',
      });

    renderClinicalReview('/clinical-review', mockSubmitter);

    // Attempt empty finalize -> shows inline validation errors, does not open confirm dialog
    fireEvent.click(screen.getByRole('button', { name: /Finalize & Save/i }));
    expect(
      screen.getByText(/Please enter clinician review notes before finalizing/i)
    ).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    // Fill clinician notes & live counter
    fireEvent.change(
      screen.getByPlaceholderText(/Record your clinical impression, key observations and context/i),
      { target: { value: 'Mother exhibited pronounced fatigue and requested support check-in.' } }
    );
    expect(screen.getByText('67 / 500')).toBeInTheDocument();

    // Select High clinical risk -> triggers Different Assessment vs AI Moderate Risk
    fireEvent.click(screen.getByRole('radio', { name: 'High' }));
    expect(screen.getByText('Different Assessment')).toBeInTheDocument();
    expect(screen.getByText('Moderate Risk')).toBeInTheDocument();
    expect(screen.getByText('High Risk')).toBeInTheDocument();

    // Select Do not agree -> requires rationale
    fireEvent.click(screen.getByRole('radio', { name: /Do not agree/i }));
    fireEvent.click(screen.getByRole('button', { name: /Finalize & Save/i }));
    expect(
      screen.getByText(/Please specify a reason for disagreeing with the AI assessment/i)
    ).toBeInTheDocument();

    // Provide rationale + update follow-up selectors
    fireEvent.change(
      screen.getByPlaceholderText(/Specify why your independent clinical decision differs/i),
      { target: { value: 'Clinical interview revealed acute sleep deprivation not captured in text.' } }
    );
    fireEvent.change(screen.getByLabelText('Next Screening'), {
      target: { value: 'Within 48 hours' },
    });

    // Click Finalize & Save -> opens confirmation modal
    fireEvent.click(screen.getByRole('button', { name: /Finalize & Save/i }));
    const confirmDialog = screen.getByRole('dialog', {
      name: /Confirm Clinical Review Finalization/i,
    });
    expect(within(confirmDialog).getByText('Moderate Risk')).toBeInTheDocument();
    expect(within(confirmDialog).getByText('High Risk')).toBeInTheDocument();

    // First attempt fails -> preserves input & offers Retry Save (AI Moderate preserved!)
    fireEvent.click(within(confirmDialog).getByRole('button', { name: /Confirm Finalize & Save/i }));
    await waitFor(() => {
      expect(within(confirmDialog).getByRole('alert')).toHaveTextContent(
        /Could not reach EHR API/i
      );
    });
    expect(within(confirmDialog).getByRole('button', { name: 'Retry Save' })).toBeInTheDocument();

    // Retry succeeds -> shows completion status & keeps original AI assessment 0.62 (Moderate)
    fireEvent.click(within(confirmDialog).getByRole('button', { name: 'Retry Save' }));
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/Clinical review finalized for M-108/i);
    });
    expect(screen.getByText('Clinical Review Finalized')).toBeInTheDocument();
    expect(screen.getByText('0.62 (Moderate)')).toBeInTheDocument();
  });

  it('supports Previous Results modal, Export Clinical Note PDF download, and honest partial modality states', () => {
    const createObjectUrlSpy = vi.fn(() => 'blob:mock-clinical-note');
    const revokeObjectUrlSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrlSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrlSpy,
    });

    renderClinicalReview('/clinical-review');

    // Previous Results modal
    fireEvent.click(screen.getByRole('button', { name: /Previous Results/i }));
    const prevDialog = screen.getByRole('dialog', { name: /Previous Results & Review History/i });
    expect(within(prevDialog).getByText(/SCR-243/i)).toBeInTheDocument();
    expect(within(prevDialog).getByText(/Longitudinal AI Risk Trend/i)).toBeInTheDocument();
    fireEvent.click(within(prevDialog).getByRole('button', { name: 'Back to Review' }));

    // Export Clinical Note PDF
    fireEvent.click(screen.getByRole('button', { name: /Export Clinical Note/i }));
    const exportDialog = screen.getByRole('dialog', { name: /Export Clinical Note/i });
    expect(within(exportDialog).getByText(/AI SCREENING SUMMARY/i)).toBeInTheDocument();
    fireEvent.click(within(exportDialog).getByRole('button', { name: 'Download PDF Note' }));
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(createObjectUrlSpy.mock.calls[0][0].type).toBe('application/pdf');
    expect(within(exportDialog).getByRole('status')).toHaveTextContent(
      'Clinical note PDF downloaded successfully.'
    );
    fireEvent.click(
      within(exportDialog).getByRole('button', { name: 'Close export clinical note modal' })
    );

    // Partial modality state on M-112 (no fabricated Voice / Facial / Discordance scores)
    fireEvent.change(screen.getByLabelText('Select mother for clinical review'), {
      target: { value: 'M-112' },
    });
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThanOrEqual(3);
  });
});

