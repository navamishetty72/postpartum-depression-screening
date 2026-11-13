import React from 'react';
import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ClinicalProvider } from './context/ClinicalContext.jsx';
import { DashboardLayout } from './DashboardLayout.jsx';
import { MothersCasesPage } from './pages/MothersCasesPage.jsx';
import { DiscordancePage } from './pages/DiscordancePage.jsx';

function renderMothersPage(initialEntry = '/mothers') {
  return render(
    <ClinicalProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/mothers" element={<MothersCasesPage />} />
            <Route path="/mothers/:motherId" element={<MothersCasesPage />} />
            <Route path="/clinical-review" element={<DiscordancePage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ClinicalProvider>
  );
}

describe('Miora Screen 02: Mothers & Cases', () => {
  it('renders navigation, header, 4 KPI cards, filters sidebar, 6 initial rows, and pagination', () => {
    renderMothersPage();

    expect(screen.getByRole('link', { name: 'Mothers & Cases' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Clinical Review' })).toBeInTheDocument();

    expect(screen.getByText('MOTHERS & CASES')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Mother Registry & Case Management'
    );
    expect(screen.getByRole('button', { name: /Add Mother/i })).toBeInTheDocument();

    // 4 KPI cards
    expect(screen.getByText('328')).toBeInTheDocument();
    expect(screen.getByText('Total Mothers')).toBeInTheDocument();
    expect(screen.getByText('247')).toBeInTheDocument();
    expect(screen.getByText('Active Cases')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
    expect(screen.getByText('Follow-ups Due')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('High-Risk Cases')).toBeInTheDocument();

    // Registry header & 6 sample rows
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (328)' })).toBeInTheDocument();
    expect(screen.getByText('M-104')).toBeInTheDocument();
    expect(screen.getByText('A. S.')).toBeInTheDocument();
    expect(screen.getByText('M-108')).toBeInTheDocument();
    expect(screen.getByText('M-112')).toBeInTheDocument();
    expect(screen.getByText('M-115')).toBeInTheDocument();
    expect(screen.getByText('M-117')).toBeInTheDocument();
    expect(screen.getByText('M-120')).toBeInTheDocument();

    // Pagination
    expect(screen.getByText('Showing 1 – 6 of 328 mothers')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Page 55' })).toBeInTheDocument();
  });

  it('supports pagination, search, sorting, simultaneous filters, and clearing filters', () => {
    renderMothersPage();

    // Pagination to page 2
    fireEvent.click(screen.getByRole('button', { name: 'Page 2' }));
    expect(screen.getByText('Showing 7 – 12 of 328 mothers')).toBeInTheDocument();
    expect(screen.getByText('M-116')).toBeInTheDocument();

    // Search resets to page 1 and finds M-104
    const searchInput = screen.getByPlaceholderText('Search by Mother ID, name or case...');
    fireEvent.change(searchInput, { target: { value: 'M-104' } });
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (1)' })).toBeInTheDocument();
    expect(screen.getByText('Showing 1 – 1 of 1 mothers')).toBeInTheDocument();

    // Clear filters/search
    fireEvent.click(screen.getAllByRole('button', { name: /Clear Filters/i })[0]);
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (328)' })).toBeInTheDocument();

    // Filter by High Risk (7 high-risk mothers total)
    const highCheckbox = screen.getAllByLabelText('High')[0];
    fireEvent.click(highCheckbox);
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (7)' })).toBeInTheDocument();

    // Narrow postpartum week range to Week 0 - Week 8 (excludes M-120 at Week 10)
    const maxWeekInput = screen.getAllByLabelText('Maximum postpartum week')[0];
    fireEvent.change(maxWeekInput, { target: { value: '8' } });
    expect(screen.queryByText('M-120')).not.toBeInTheDocument();
    expect(screen.getByText('M-104')).toBeInTheDocument();

    // Sort by Risk Level & Oldest without errors
    fireEvent.change(screen.getByLabelText('Sort mother registry'), {
      target: { value: 'oldest' },
    });
    expect(screen.getByText('M-104')).toBeInTheDocument();

    // Clear filters restores all 328
    fireEvent.click(screen.getAllByRole('button', { name: /Clear Filters/i })[0]);
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (328)' })).toBeInTheDocument();
  });

  it('opens mother profile drawer on eye action and adds a new mother via Add Mother button', () => {
    renderMothersPage();

    fireEvent.click(screen.getByRole('button', { name: 'View profile for M-104' }));
    expect(screen.getByRole('dialog', { name: 'Mother profile M-104' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Amara K.' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Close mother profile' }));
    expect(screen.queryByRole('dialog', { name: 'Mother profile M-104' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Add Mother/i }));
    fireEvent.change(screen.getByPlaceholderText('e.g. Nadia P.'), {
      target: { value: 'Zoya A.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Complete Registration' }));
    fireEvent.click(screen.getByRole('button', { name: 'Done' }));

    expect(screen.getByText('329')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Mothers & Cases (329)' })).toBeInTheDocument();
  });
});

