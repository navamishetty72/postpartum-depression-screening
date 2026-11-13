import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

function buildPageTokens(currentPage, totalPages) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (currentPage <= 3) {
    return [1, 2, 3, 'ellipsis-end', totalPages];
  }
  if (currentPage >= totalPages - 2) {
    return [1, 'ellipsis-start', totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, 'ellipsis-start', currentPage - 1, currentPage, currentPage + 1, 'ellipsis-end', totalPages];
}

export function Pagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
}) {
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);
  const tokens = buildPageTokens(currentPage, Math.max(totalPages, 1));

  return (
    <div className="miora-pagination-bar">
      <div className="miora-pagination-summary">
        {totalItems === 0
          ? 'Showing 0 mothers'
          : `Showing ${startItem} – ${endItem} of ${totalItems} mothers`}
      </div>

      <nav className="miora-pagination-controls" aria-label="Registry pagination">
        <button
          type="button"
          className="miora-page-btn miora-page-nav"
          aria-label="Previous page"
          disabled={currentPage <= 1 || totalItems === 0}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <DashboardIcon name="chevronLeft" size={15} strokeWidth={1.9} />
        </button>

        {tokens.map((token) =>
          typeof token === 'string' ? (
            <span key={token} className="miora-page-ellipsis" aria-hidden="true">
              ···
            </span>
          ) : (
            <button
              key={token}
              type="button"
              className={`miora-page-btn ${currentPage === token ? 'is-active' : ''}`}
              aria-label={`Page ${token}`}
              aria-current={currentPage === token ? 'page' : undefined}
              onClick={() => onPageChange(token)}
            >
              {token}
            </button>
          )
        )}

        <button
          type="button"
          className="miora-page-btn miora-page-nav"
          aria-label="Next page"
          disabled={currentPage >= totalPages || totalItems === 0}
          onClick={() => onPageChange(currentPage + 1)}
        >
          <DashboardIcon name="chevronRight" size={15} strokeWidth={1.9} />
        </button>
      </nav>
    </div>
  );
}

