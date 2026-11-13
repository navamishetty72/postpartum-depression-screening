import React from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';
import { RiskBadge } from './Badges.jsx';

export function PatientInfoStrip({
  mothers,
  activeMother,
  onSelectMother,
  selectId = 'patient-strip-mother-select',
}) {
  return (
    <section className="miora-card miora-patient-strip" aria-label="Selected mother summary">
      <div className="miora-patient-item">
        <span className="miora-patient-icon" aria-hidden="true">
          <DashboardIcon name="user" size={18} />
        </span>
        <div className="miora-patient-meta">
          <div className="miora-patient-select-row">
            <label htmlFor={selectId} className="sr-only">
              Select mother for screening
            </label>
            <select
              id={selectId}
              className="miora-patient-id-select"
              value={activeMother.id}
              onChange={(e) => onSelectMother(e.target.value)}
            >
              {mothers.slice(0, 25).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
          </div>
          <span className="miora-patient-sub">{activeMother.initials}</span>
        </div>
      </div>

      <span className="miora-patient-divider" aria-hidden="true" />

      <div className="miora-patient-item">
        <span className="miora-patient-icon is-plain" aria-hidden="true">
          <DashboardIcon name="calendar" size={18} />
        </span>
        <div className="miora-patient-meta">
          <span className="miora-patient-label">Postpartum Week</span>
          <strong>Week {activeMother.postpartumWeek}</strong>
        </div>
      </div>

      <span className="miora-patient-divider" aria-hidden="true" />

      <div className="miora-patient-item">
        <span className="miora-patient-icon is-plain" aria-hidden="true">
          <DashboardIcon name="layers" size={18} />
        </span>
        <div className="miora-patient-meta">
          <span className="miora-patient-label">Previous Risk</span>
          <RiskBadge risk={activeMother.risk} />
        </div>
      </div>

      <span className="miora-patient-divider" aria-hidden="true" />

      <div className="miora-patient-item">
        <span className="miora-patient-icon is-plain" aria-hidden="true">
          <DashboardIcon name="clock" size={18} />
        </span>
        <div className="miora-patient-meta">
          <span className="miora-patient-label">Last Screening</span>
          <strong>{activeMother.lastScreeningDate}</strong>
        </div>
      </div>

      <span className="miora-patient-divider" aria-hidden="true" />

      <div className="miora-patient-item">
        <span className="miora-patient-icon is-plain" aria-hidden="true">
          <DashboardIcon name="barChart" size={18} />
        </span>
        <div className="miora-patient-meta">
          <span className="miora-patient-label">Screening Type</span>
          <strong>Multimodal (Text · Voice · Video)</strong>
        </div>
      </div>
    </section>
  );
}

