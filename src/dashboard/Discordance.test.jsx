import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { DiscordancePage } from './pages/DiscordancePage.jsx';

function renderDiscordance(initialEntry = '/discordance') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/discordance" element={<DiscordancePage />} />
            <Route path="/discordance/:motherId" element={<DiscordancePage />} />
            <Route path="/clinical-review" element={<DiscordancePage />} />
            <Route path="/mothers/:motherId" element={<div>Mother Record View</div>} />
            <Route path="/insights" element={<div>Insights &amp; Care View</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 06: Cross-Modal Discordance', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders header, patient strip, 3-column Row 1, 3-column Row 2, and Recommended Actions with non-judgmental copy', () => {
    renderDiscordance();

    expect(screen.getByRole('link', { name: 'Discordance' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByRole('link', { name: 'Screening' })).toBeInTheDocument();
    expect(screen.getByText('DISCORDANCE ANALYSIS')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Cross-Modal Discordance'
    );
    expect(screen.getByRole('button', { name: /Export Report/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add Note/i })).toBeInTheDocument();

    // Patient Strip defaults to M-108
    expect(screen.getByLabelText('Select mother for discordance analysis')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();
    expect(screen.getByText('Multimodal (Text · Voice · Video)')).toBeInTheDocument();
    expect(screen.getByText('Apr 16, 2026 · 10:24 AM')).toBeInTheDocument();
    expect(screen.getByText('Analysis Completed')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Record/i })).toHaveAttribute(
      'href',
      '/mothers/M-108'
    );

    // Row 1A: Modality Comparison table
    const comparisonTable = screen.getByRole('table');
    expect(within(comparisonTable).getByText('Text')).toBeInTheDocument();
    expect(within(comparisonTable).getByText('0.58')).toBeInTheDocument();
    expect(within(comparisonTable).getByText('Voice')).toBeInTheDocument();
    expect(within(comparisonTable).getByText('0.66')).toBeInTheDocument();
    expect(within(comparisonTable).getByText('Video')).toBeInTheDocument();
    expect(within(comparisonTable).getByText('0.60')).toBeInTheDocument();

    // Row 1B: Risk by Modality chart + hover tooltip interaction
    expect(screen.getByRole('heading', { name: 'Risk by Modality' })).toBeInTheDocument();
    const voiceBarCol = screen.getByLabelText(/Voice \(Acoustic\): 0\.66/i);
    fireEvent.mouseEnter(voiceBarCol);
    expect(screen.getByRole('status')).toHaveTextContent('Voice: 0.66 (Moderate)');

    // Row 1C: Discordance Result separate from Overall Risk
    expect(screen.getByRole('heading', { name: 'Discordance Result' })).toBeInTheDocument();
    expect(screen.getByText('0.81')).toBeInTheDocument();
    expect(screen.getByText('Notable Difference')).toBeInTheDocument();
    expect(screen.getByText('Overall Postpartum Risk (Separate):')).toBeInTheDocument();
    expect(screen.getByText('Moderate (0.62)')).toBeInTheDocument();

    // Row 2A: Signal Alignment
    expect(screen.getByRole('heading', { name: 'Signal Alignment' })).toBeInTheDocument();
    expect(screen.getByText(/Pairwise alignment score/i)).toBeInTheDocument();
    expect(screen.getByText('Text ↔ Voice')).toBeInTheDocument();
    expect(screen.getByText('0.92')).toBeInTheDocument();
    expect(screen.getByText('Text ↔ Video')).toBeInTheDocument();
    expect(screen.getByText('0.98')).toBeInTheDocument();
    expect(screen.getByText('Voice ↔ Video')).toBeInTheDocument();
    expect(screen.getByText('0.94')).toBeInTheDocument();

    // Row 2B: Key Observations
    expect(screen.getByRole('heading', { name: 'Key Observations' })).toBeInTheDocument();
    expect(screen.getByText('Elevated negative sentiment in text')).toBeInTheDocument();
    expect(screen.getByText('Higher vocal strain and lower energy')).toBeInTheDocument();

    // Row 2C: Clinical Interpretation (no deception / underreporting wording)
    expect(screen.getByRole('heading', { name: 'Clinical Interpretation' })).toBeInTheDocument();
    expect(document.body.textContent.toLowerCase()).not.toContain('underreporting');
    expect(document.body.textContent.toLowerCase()).not.toContain('concealing');

    // Bottom: Recommended Actions
    expect(screen.getByRole('heading', { name: 'Recommended Actions' })).toBeInTheDocument();
    expect(screen.getByText('Conduct follow-up screening in 7 days')).toBeInTheDocument();
    expect(screen.getByText('Schedule brief clinical review')).toBeInTheDocument();
    expect(screen.getByText('Discuss support resources')).toBeInTheDocument();
  });

  it('withholds pairwise & discordance calculations when required modalities are missing', () => {
    renderDiscordance('/discordance/M-112');

    expect(screen.getByLabelText('Select mother for discordance analysis')).toHaveValue('M-112');
    expect(screen.getByText('Analysis Pending')).toBeInTheDocument();
    expect(screen.getByText('Insufficient Modalities')).toBeInTheDocument();
    expect(screen.getAllByText(/Voice & Video unavailable|Text & Video unavailable|Voice unavailable/i).length).toBeGreaterThanOrEqual(2);

    renderDiscordance('/discordance/M-999');
    expect(screen.getByText('Discordance Record Not Found')).toBeInTheDocument();
  });

  it('supports Add Note, Export PDF Report, patient switching, and Recommended Actions workflows', () => {
    const createObjectUrlSpy = vi.fn(() => 'blob:mock-discordance-pdf');
    const revokeObjectUrlSpy = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrlSpy,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrlSpy,
    });

    renderDiscordance();

    // Switch patient via dropdown to M-104
    fireEvent.change(screen.getByLabelText('Select mother for discordance analysis'), {
      target: { value: 'M-104' },
    });
    expect(screen.getByText('A. S.')).toBeInTheDocument();
    expect(screen.getByText('0.74')).toBeInTheDocument();

    // Add Contextual Note (validates empty state then saves)
    fireEvent.click(screen.getByRole('button', { name: /Add Note/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      /Please enter a contextual clinical observation/i
    );
    fireEvent.change(
      screen.getByPlaceholderText(/Document sleep context, psychosocial factors/i),
      { target: { value: 'Mother reported disrupted nighttime sleep during intake.' } }
    );
    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }));
    expect(screen.getByRole('status')).toHaveTextContent(/Contextual note saved for M-104/i);
    expect(
      screen.getByText('Mother reported disrupted nighttime sleep during intake.')
    ).toBeInTheDocument();

    // Export PDF Report includes saved note & triggers Blob download
    fireEvent.click(screen.getByRole('button', { name: /Export Report/i }));
    const exportDialog = screen.getByRole('dialog', { name: /Export Discordance Report/i });
    expect(within(exportDialog).getByText(/SEPARATE ASSESSMENT METRICS/i)).toBeInTheDocument();
    fireEvent.click(within(exportDialog).getByRole('button', { name: 'Export PDF' }));
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(createObjectUrlSpy.mock.calls[0][0].type).toBe('application/pdf');
    expect(within(exportDialog).getByRole('status')).toHaveTextContent(
      'Discordance PDF report downloaded successfully.'
    );
    fireEvent.click(
      within(exportDialog).getByRole('button', { name: 'Close discordance export modal' })
    );

    // Recommended Action 1: 7-day follow-up scheduling
    fireEvent.click(
      screen.getByRole('button', { name: /Conduct follow-up screening in 7 days/i })
    );
    expect(screen.getByRole('status')).toHaveTextContent(
      '7-day follow-up screening scheduled for M-104.'
    );

    // Recommended Action 2: Clinical Review workflow
    fireEvent.click(screen.getByRole('button', { name: /Schedule brief clinical review/i }));
    expect(screen.getByRole('status')).toHaveTextContent(
      'Brief clinical review queued for M-104 (SCR-244).'
    );

    // Recommended Action 3: Support resources -> Insights & Care
    fireEvent.click(screen.getByRole('button', { name: /Discuss support resources/i }));
    expect(screen.getByText('Insights & Care View')).toBeInTheDocument();
  });
});
