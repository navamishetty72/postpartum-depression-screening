import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { UploadAnalyzePage } from './pages/UploadAnalyzePage.jsx';
import { LiveScreeningPage } from './pages/LiveScreeningPage.jsx';
import { ResultsPage } from './pages/ResultsPage.jsx';

function renderUploadPage(analyzerOverride) {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={['/upload-analyze']}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route
              path="/upload-analyze"
              element={<UploadAnalyzePage analyzer={analyzerOverride} />}
            />
            <Route path="/live-screening" element={<LiveScreeningPage />} />
            <Route path="/results/:motherId" element={<ResultsPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 04: Upload & Analyze', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders Screening nav active, header, patient strip, 3 upload cards, and empty analysis preview', () => {
    renderUploadPage();

    expect(screen.getByRole('link', { name: 'Screening' })).toHaveClass('is-active');
    expect(screen.getByText('UPLOAD & ANALYZE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Upload & Analyze');

    // Patient Strip
    expect(screen.getByLabelText('Select mother for screening')).toHaveValue('M-108');
    expect(screen.getByText('N. R.')).toBeInTheDocument();
    expect(screen.getByText('Week 2')).toBeInTheDocument();

    // 3 Upload Cards
    expect(screen.getByLabelText('Upload Text files')).toBeInTheDocument();
    expect(screen.getByLabelText('Upload Voice / Audio files')).toBeInTheDocument();
    expect(screen.getByLabelText('Upload Video files')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Uploaded Files (0)' })).toBeInTheDocument();

    // Honest empty state with no fabricated scores
    expect(
      screen.getByText('Your analysis preview will appear here after processing.')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Analysis/i })).toBeDisabled();
  });

  it('validates file types, updates Uploaded Files & Selected Modalities, and supports removal and Clear All', async () => {
    renderUploadPage();

    const textInput = screen.getByLabelText('Upload Text files');
    const badFile = new File(['binary'], 'malware.exe', { type: 'application/octet-stream' });
    fireEvent.change(textInput, { target: { files: [badFile] } });
    expect(screen.getByRole('alert')).toHaveTextContent(/not a supported Text file/i);
    expect(screen.getByRole('heading', { name: 'Uploaded Files (0)' })).toBeInTheDocument();

    const goodText = new File(['Feeling exhausted this week.'], 'ppd_response.txt', {
      type: 'text/plain',
    });
    const goodAudio = new File(['audio-bytes'], 'session_voice.mp3', { type: 'audio/mpeg' });
    fireEvent.change(textInput, { target: { files: [goodText] } });
    fireEvent.change(screen.getByLabelText('Upload Voice / Audio files'), {
      target: { files: [goodAudio] },
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Uploaded Files (2)' })).toBeInTheDocument();
    });
    expect(screen.getByText('ppd_response.txt')).toBeInTheDocument();
    expect(screen.getByText('session_voice.mp3')).toBeInTheDocument();

    // Selected Modalities auto-enabled for Text & Voice, disabled for Video
    const textToggle = screen.getByRole('button', { name: /^Text$/i });
    const voiceToggle = screen.getByRole('button', { name: /^Voice$/i });
    const videoToggle = screen.getByRole('button', { name: /Video/i });
    expect(textToggle).toHaveAttribute('aria-pressed', 'true');
    expect(voiceToggle).toHaveAttribute('aria-pressed', 'true');
    expect(videoToggle).toBeDisabled();

    // Run Analysis enabled now
    expect(screen.getByRole('button', { name: /Run Analysis/i })).toBeEnabled();

    // Deselecting both disables Run Analysis
    fireEvent.click(textToggle);
    fireEvent.click(voiceToggle);
    expect(screen.getByRole('button', { name: /Run Analysis/i })).toBeDisabled();
    fireEvent.click(textToggle);

    // Remove single file & Clear All
    fireEvent.click(screen.getByRole('button', { name: 'Remove ppd_response.txt' }));
    expect(screen.getByRole('heading', { name: 'Uploaded Files (1)' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Clear All/i }));
    expect(screen.getByRole('heading', { name: 'Uploaded Files (0)' })).toBeInTheDocument();
  });

  it('handles Save Draft, backend failure with Retry without navigating, and successful analysis navigation to Results', async () => {
    const mockAnalyzer = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        reason: 'backend-unavailable',
        message: 'Backend analysis service unreachable.',
      })
      .mockResolvedValueOnce({
        ok: true,
        result: {
          combinedScore: 0.58,
          riskCategory: 'Moderate Risk',
          modalityContributions: { text: 0.54, voice: 0.62 },
          indicators: ['Text signal: mild fatigue cues', 'Voice signal: lower affect'],
          nextSteps: ['Schedule follow-up in 7 days'],
        },
      });

    renderUploadPage(mockAnalyzer);

    const goodText = new File(['Mild exhaustion'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByLabelText('Upload Text files'), {
      target: { files: [goodText] },
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Uploaded Files (1)' })).toBeInTheDocument();
    });

    // Save Draft
    fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
    expect(screen.getByRole('status')).toHaveTextContent(/Draft saved at/i);

    // Confirm consent & run analysis -> first call fails honestly, stays on page & shows Retry
    fireEvent.click(
      screen.getByLabelText(/Mother consent confirmed for asynchronous multimodal analysis/i)
    );
    fireEvent.click(screen.getByRole('button', { name: /Run Analysis/i }));

    await waitFor(() => {
      expect(screen.getByText('Analysis Could Not Complete')).toBeInTheDocument();
    });
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Upload & Analyze');

    // Retry succeeds and navigates to Results (Screen 05)
    fireEvent.click(screen.getByRole('button', { name: /Retry Analysis/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Maternal Screening Results'
      );
    });
  });

  it('Back to Screening navigates to Screen 03', () => {
    renderUploadPage();
    fireEvent.click(screen.getByRole('button', { name: /Back to Screening/i }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Maternal Screening Session'
    );
  });
});

