import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { KpiCard } from '../components/KpiCard.jsx';
import { RiskBadge, StatusBadge } from '../components/Badges.jsx';
import { FiltersSidebar } from '../components/FiltersSidebar.jsx';
import { Pagination } from '../components/Pagination.jsx';
import { MotherProfileDrawer } from '../components/MotherProfileDrawer.jsx';

const PAGE_SIZE = 6;

const RISK_PRIORITY_WEIGHT = {
  High: 4,
  'Requires Review': 3,
  Moderate: 2,
  Low: 1,
};

export function MothersCasesPage() {
  const {
    mothers,
    screenings,
    metrics,
    setIsAddMotherOpen,
    updateMotherStatus,
  } = useClinicalData();
  const { motherId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const urlFilter = searchParams.get('filter') || '';

  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [selectedRisks, setSelectedRisks] = useState(() =>
    urlFilter === 'priority' ? ['High', 'Requires Review'] : []
  );
  const [selectedStatuses, setSelectedStatuses] = useState(() =>
    urlFilter === 'review' ? ['Follow-up'] : []
  );
  const [weekRange, setWeekRange] = useState([0, 24]);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    if (urlFilter === 'priority') {
      setSelectedRisks(['High', 'Requires Review']);
      setSelectedStatuses([]);
      setCurrentPage(1);
    } else if (urlFilter === 'review') {
      setSelectedStatuses(['Follow-up']);
      setSelectedRisks([]);
      setCurrentPage(1);
    }
  }, [urlFilter]);

  const toggleRisk = (risk) => {
    setSelectedRisks((prev) =>
      prev.includes(risk) ? prev.filter((item) => item !== risk) : [...prev, risk]
    );
    setCurrentPage(1);
  };

  const toggleStatus = (status) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((item) => item !== status) : [...prev, status]
    );
    setCurrentPage(1);
  };

  const handleWeekRangeChange = (nextRange) => {
    setWeekRange(nextRange);
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setSelectedRisks([]);
    setSelectedStatuses([]);
    setWeekRange([0, 24]);
    setQuery('');
    setSortBy('recent');
    setCurrentPage(1);
    if (urlFilter) {
      setSearchParams({});
    }
  };

  const filteredAndSortedMothers = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    const [minWeek, maxWeek] = weekRange;

    const filtered = mothers.filter((m) => {
      if (selectedRisks.length > 0) {
        const matchesRisk = selectedRisks.some((r) => {
          if (r === 'Requires Review') {
            return m.risk === 'Requires Review' || m.status === 'Review';
          }
          return m.risk === r;
        });
        if (!matchesRisk) return false;
      }

      if (selectedStatuses.length > 0 && !selectedStatuses.includes(m.status)) {
        return false;
      }

      if (m.postpartumWeek < minWeek || m.postpartumWeek > maxWeek) {
        return false;
      }

      if (trimmed) {
        const searchable = [
          m.id,
          m.name,
          m.initials,
          m.reasonForReview,
          m.status,
          m.risk,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!searchable.includes(trimmed)) return false;
      }

      return true;
    });

    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === 'oldest') {
        return new Date(a.lastScreeningIso).getTime() - new Date(b.lastScreeningIso).getTime();
      }
      if (sortBy === 'risk') {
        const diff =
          (RISK_PRIORITY_WEIGHT[b.risk] || 0) - (RISK_PRIORITY_WEIGHT[a.risk] || 0);
        if (diff !== 0) return diff;
      }
      return new Date(b.lastScreeningIso).getTime() - new Date(a.lastScreeningIso).getTime();
    });

    return sorted;
  }, [mothers, query, selectedRisks, selectedStatuses, weekRange, sortBy]);

  const totalItems = filteredAndSortedMothers.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);

  const paginatedMothers = useMemo(() => {
    const startIdx = (safePage - 1) * PAGE_SIZE;
    return filteredAndSortedMothers.slice(startIdx, startIdx + PAGE_SIZE);
  }, [filteredAndSortedMothers, safePage]);

  const activeFilterCount =
    selectedRisks.length +
    selectedStatuses.length +
    (weekRange[0] > 0 || weekRange[1] < 24 ? 1 : 0);

  const selectedMother = motherId
    ? mothers.find((m) => m.id.toLowerCase() === motherId.toLowerCase()) || null
    : null;

  const relatedScreenings = useMemo(() => {
    if (!selectedMother) return [];
    return screenings.filter((s) => s.motherId === selectedMother.id);
  }, [screenings, selectedMother]);

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Flowing Blush Header Waves */}
        <svg
          className="miora-header-ribbon miora-mothers-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="mothersWaveGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#mothersWaveGrad1)"
          />
          <path
            d="M70 155 C 210 110, 320 120, 445 70 C 535 34, 595 40, 640 15"
            stroke="#f4b9c8"
            strokeOpacity="0.45"
            strokeWidth="1.5"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="mothers-cases-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>MOTHERS &amp; CASES</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="mothers-cases-heading" className="miora-dash-title">
              Mother Registry &amp; <em>Case Management</em>
            </h1>
            <p className="miora-dash-subtitle">
              View, search and manage all registered mothers and their screening cases.
            </p>
          </div>

          <div className="miora-dash-header-actions">
            <button
              type="button"
              className="miora-cta-primary"
              onClick={() => setIsAddMotherOpen(true)}
            >
              <DashboardIcon name="plus" size={16} strokeWidth={2.2} />
              <span>Add Mother</span>
            </button>
          </div>
        </section>

        {/* 4 Overview Statistics KPI Cards */}
        <section className="miora-kpi-grid" aria-label="Registry overview statistics">
          <KpiCard
            icon="users"
            value={metrics.registeredMothers}
            trend={metrics.trends.registeredMothers}
            trendTone="positive"
            label="Total Mothers"
            onClick={handleClearFilters}
          />
          <KpiCard
            icon="clipboardCheck"
            value={metrics.activeCases}
            trend={metrics.trends.screeningsCompleted}
            trendTone="positive"
            label="Active Cases"
            onClick={() => {
              setSelectedRisks([]);
              setSelectedStatuses(['Active']);
              setCurrentPage(1);
            }}
          />
          <KpiCard
            icon="clock"
            value={metrics.casesForReview}
            trend={metrics.trends.casesForReview}
            trendTone="attention"
            label="Follow-ups Due"
            onClick={() => {
              setSelectedRisks([]);
              setSelectedStatuses(['Follow-up']);
              setCurrentPage(1);
            }}
          />
          <KpiCard
            icon="shieldCheck"
            value={metrics.highRiskCases}
            trend={metrics.trends.highRiskCases}
            trendTone="positive"
            trendDirection="down"
            label="High-Risk Cases"
            onClick={() => {
              setSelectedStatuses([]);
              setSelectedRisks(['High']);
              setCurrentPage(1);
            }}
          />
        </section>

        {/* Two-column Workspace: Left Filters (255px) + Right Mother Registry */}
        <div className="miora-registry-layout">
          <FiltersSidebar
            selectedRisks={selectedRisks}
            onToggleRisk={toggleRisk}
            weekRange={weekRange}
            onWeekRangeChange={handleWeekRangeChange}
            selectedStatuses={selectedStatuses}
            onToggleStatus={toggleStatus}
            onClearFilters={handleClearFilters}
            activeFilterCount={activeFilterCount}
          />

          <section className="miora-card miora-registry-card" aria-labelledby="registry-table-title">
            <div className="miora-registry-toolbar">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="users" size={22} strokeWidth={1.65} />
                </span>
                <h2 id="registry-table-title" className="miora-card-title">
                  Mothers &amp; Cases ({totalItems})
                </h2>
              </div>

              <div className="miora-registry-controls">
                <div className="miora-registry-search">
                  <DashboardIcon name="search" size={15} strokeWidth={1.8} />
                  <input
                    type="search"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setCurrentPage(1);
                    }}
                    placeholder="Search by Mother ID, name or case..."
                    aria-label="Search by Mother ID, name or case"
                  />
                </div>

                <div className="miora-select-wrap">
                  <label htmlFor="registry-sort" className="sr-only">
                    Sort mother registry
                  </label>
                  <select
                    id="registry-sort"
                    className="miora-pill-select"
                    value={sortBy}
                    onChange={(e) => {
                      setSortBy(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="recent">Sort: Recent</option>
                    <option value="oldest">Sort: Oldest</option>
                    <option value="risk">Sort: Risk Level</option>
                  </select>
                  <span className="miora-select-chevron" aria-hidden="true">
                    <DashboardIcon name="chevronDown" size={14} strokeWidth={2} />
                  </span>
                </div>
              </div>
            </div>

            <div className="miora-table-scroll">
              <table className="miora-registry-table">
                <thead>
                  <tr>
                    <th scope="col">Mother ID</th>
                    <th scope="col">Mother (Initials)</th>
                    <th scope="col">Postpartum Week</th>
                    <th scope="col">Last Screening</th>
                    <th scope="col">Risk Level</th>
                    <th scope="col">Case Status</th>
                    <th scope="col" className="miora-registry-actions-col">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedMothers.length > 0 ? (
                    paginatedMothers.map((item) => (
                      <tr
                        key={item.id}
                        className="miora-registry-row"
                        onClick={() => navigate(`/mothers/${item.id}`)}
                      >
                        <td className="miora-cell-id">{item.id}</td>
                        <td>
                          <div className="miora-mother-cell">
                            <span className="miora-initials-avatar" aria-hidden="true">
                              {item.avatarInitials}
                            </span>
                            <span className="miora-mother-initials">{item.initials}</span>
                          </div>
                        </td>
                        <td className="miora-cell-week">Week {item.postpartumWeek}</td>
                        <td className="miora-cell-date">{item.lastScreeningDate}</td>
                        <td>
                          <RiskBadge risk={item.risk} showDot />
                        </td>
                        <td>
                          <StatusBadge status={item.status} showDot={false} />
                        </td>
                        <td className="miora-registry-actions-cell">
                          <button
                            type="button"
                            className="miora-eye-btn"
                            aria-label={`View profile for ${item.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/mothers/${item.id}`);
                            }}
                          >
                            <DashboardIcon name="eye" size={16} strokeWidth={1.7} />
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="miora-registry-empty">
                        No mothers match the current search or filters.{' '}
                        <button
                          type="button"
                          className="miora-inline-reset"
                          onClick={handleClearFilters}
                        >
                          Clear Filters
                        </button>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <Pagination
              currentPage={safePage}
              totalPages={totalPages}
              totalItems={totalItems}
              pageSize={PAGE_SIZE}
              onPageChange={(nextPage) => setCurrentPage(nextPage)}
            />
          </section>
        </div>
      </div>

      {selectedMother && (
        <MotherProfileDrawer
          mother={selectedMother}
          relatedScreenings={relatedScreenings}
          onClose={() => navigate('/mothers')}
          onUpdateStatus={updateMotherStatus}
          onOpenResults={(id) => navigate(`/results/${id}`)}
          onStartScreening={(id) => navigate(`/live-screening?mother=${id}`)}
        />
      )}
    </div>
  );
}
