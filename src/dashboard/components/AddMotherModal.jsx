import React, { useEffect, useState } from 'react';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from './DashboardIcon.jsx';

export function AddMotherModal() {
  const { isAddMotherOpen, setIsAddMotherOpen, addMother } = useClinicalData();
  const [name, setName] = useState('');
  const [postpartumWeek, setPostpartumWeek] = useState('4');
  const [risk, setRisk] = useState('Low');
  const [reasonForReview, setReasonForReview] = useState('');
  const [createdId, setCreatedId] = useState(null);

  useEffect(() => {
    const onEsc = (e) => {
      if (e.key === 'Escape' && isAddMotherOpen) {
        setIsAddMotherOpen(false);
      }
    };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isAddMotherOpen, setIsAddMotherOpen]);

  if (!isAddMotherOpen) return null;

  const handleClose = () => {
    setCreatedId(null);
    setIsAddMotherOpen(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    const created = addMother({ name, postpartumWeek, risk, reasonForReview });
    setCreatedId(created?.id || 'M-118');
    setName('');
    setReasonForReview('');
  };

  return (
    <div className="miora-modal-backdrop" role="presentation" onClick={handleClose}>
      <div
        className="miora-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-mother-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="miora-modal-head">
          <div className="miora-modal-head-left">
            <span className="miora-kpi-icon-wrap miora-modal-icon" aria-hidden="true">
              <DashboardIcon name="userPlus" size={20} />
            </span>
            <div>
              <h2 id="add-mother-modal-title">Register Mother</h2>
              <p>Enroll a mother into postpartum emotional wellbeing monitoring.</p>
            </div>
          </div>
          <button
            type="button"
            className="dash-icon-btn"
            aria-label="Close registration modal"
            onClick={handleClose}
          >
            <DashboardIcon name="close" size={18} />
          </button>
        </div>

        {createdId ? (
          <div className="miora-modal-success">
            <div className="miora-success-pill">
              <DashboardIcon name="check" size={16} />
              <span>Registered as {createdId}</span>
            </div>
            <p>
              The mother profile has been added to the active clinical registry and KPI totals.
            </p>
            <div className="miora-modal-actions">
              <button type="button" className="miora-btn-secondary" onClick={() => setCreatedId(null)}>
                Register Another
              </button>
              <button type="button" className="miora-btn-primary" onClick={handleClose}>
                Done
              </button>
            </div>
          </div>
        ) : (
          <form className="miora-modal-form" onSubmit={handleSubmit}>
            <label className="miora-field">
              <span>Mother Name or Initials *</span>
              <input
                type="text"
                required
                placeholder="e.g. Nadia P."
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>

            <div className="miora-field-row">
              <label className="miora-field">
                <span>Postpartum Week</span>
                <input
                  type="number"
                  min="0"
                  max="52"
                  value={postpartumWeek}
                  onChange={(e) => setPostpartumWeek(e.target.value)}
                />
              </label>

              <label className="miora-field">
                <span>Initial Triage Risk</span>
                <select value={risk} onChange={(e) => setRisk(e.target.value)}>
                  <option value="Low">Low</option>
                  <option value="Moderate">Moderate</option>
                  <option value="High">High</option>
                </select>
              </label>
            </div>

            <label className="miora-field">
              <span>Intake Notes / Reason for Monitoring</span>
              <textarea
                rows="3"
                placeholder="e.g. Baseline Week 4 check-in; reported interrupted sleep."
                value={reasonForReview}
                onChange={(e) => setReasonForReview(e.target.value)}
              />
            </label>

            <div className="miora-modal-actions">
              <button type="button" className="miora-btn-secondary" onClick={handleClose}>
                Cancel
              </button>
              <button type="submit" className="miora-btn-primary">
                Complete Registration
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

