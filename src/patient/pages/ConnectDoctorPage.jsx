import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from '../components/PatientIcons.jsx';
import './reports.css'; // shares report and consultation styles

export function ConnectDoctorPage() {
  const { consultations: contextConsultations, patient } = usePatient();

  const [consultationsList, setConsultationsList] = useState(
    contextConsultations || [
      {
        id: 'c-101',
        doctorName: 'Dr. Elena Rostova',
        role: 'Perinatal Psychiatry Lead',
        date: '20 Nov 2026',
        time: '11:00 AM',
        status: 'Scheduled',
        type: 'Telehealth Video',
        clinic: 'Miora Maternal Care Unit',
      },
      {
        id: 'c-100',
        doctorName: 'Dr. Elena Rostova',
        role: 'Perinatal Psychiatry Lead',
        date: '03 Nov 2026',
        time: '02:30 PM',
        status: 'Completed',
        type: 'Audio Consult',
        clinic: 'Miora Maternal Care Unit',
      },
    ]
  );

  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState('Telehealth Video');
  const [bookingDate, setBookingDate] = useState('2026-11-25');
  const [bookingTime, setBookingTime] = useState('11:00 AM');
  const [bookingReason, setBookingReason] = useState('');
  const [bookingNotice, setBookingNotice] = useState('');
  const [activeSummaryModal, setActiveSummaryModal] = useState(null);
  const [joiningRoomNotice, setJoiningRoomNotice] = useState(false);

  const handleBookConsultation = (e) => {
    e.preventDefault();
    const newConsultation = {
      id: `c-${Date.now()}`,
      doctorName: 'Dr. Elena Rostova',
      role: 'Perinatal Psychiatry Lead',
      date: new Date(bookingDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
      time: bookingTime,
      status: 'Scheduled',
      type: selectedType,
      clinic: 'Miora Maternal Care Unit',
    };

    setConsultationsList((prev) => [newConsultation, ...prev]);
    setBookingModalOpen(false);
    setBookingNotice('Consultation successfully scheduled with Dr. Elena Rostova!');
    setTimeout(() => setBookingNotice(''), 5000);
  };

  const handleJoinRoom = () => {
    setJoiningRoomNotice(true);
    setTimeout(() => setJoiningRoomNotice(false), 3000);
  };

  return (
    <div className="patient-consultations-container">
      {/* Breadcrumb */}
      <div className="medhist-breadcrumb-bar">
        <NavLink to="/patient/reports" className="medhist-breadcrumb-link">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
            <path d="M9.5 21v-7h5v7" />
          </svg>
          <span>Home</span>
        </NavLink>
        <span className="medhist-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
        <span className="medhist-breadcrumb-current">Connect to a Doctor</span>
      </div>

      {/* Page Banner */}
      <div className="patient-page-banner">
        <h1 className="patient-page-heading">Connect to a Doctor</h1>
        <p className="patient-page-subheading">
          Confidential telehealth consultations, clinical evaluations, and ongoing postpartum emotional guidance coordinated with Dr. Elena Rostova.
        </p>
      </div>

      {/* Telehealth Simulation Notice Banner */}
      <div className="patient-card connect-disclaimer-card" role="note">
        <div className="connect-disclaimer-icon-wrap" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div className="connect-disclaimer-content">
          <strong className="connect-disclaimer-title">Telehealth Simulation Notice</strong>
          <p className="connect-disclaimer-text">
            All virtual consultations, video feeds, and clinical session notes within Miora are end-to-end encrypted and HIPAA-compliant. Scheduled sessions are securely mirrored to your clinical care plan.
          </p>
        </div>
      </div>

      {/* Success Notice if booked */}
      {bookingNotice && (
        <div className="connect-success-toast" role="status">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{bookingNotice}</span>
        </div>
      )}

      {/* Joining Room Simulation Notice */}
      {joiningRoomNotice && (
        <div className="connect-joining-banner" role="status">
          <span className="connect-joining-spinner" aria-hidden="true" />
          <span>Connecting to Dr. Elena Rostova's private telehealth room...</span>
        </div>
      )}

      {/* Doctor Profile Card */}
      <section className="patient-card connect-doctor-card" aria-labelledby="doctor-profile-title">
        <div className="connect-doctor-main">
          <div className="connect-doctor-avatar-wrap">
            <div className="connect-doctor-avatar-circle">
              ER
            </div>
            <span className="connect-doctor-online-pill">
              <span className="connect-online-dot" />
              Available for Consult
            </span>
          </div>

          <div className="connect-doctor-details">
            <div className="connect-doctor-header-row">
              <div>
                <h2 id="doctor-profile-title" className="connect-doctor-name">
                  Dr. Elena Rostova, MD
                </h2>
                <p className="connect-doctor-designation">
                  Perinatal Psychiatry Lead &bull; Miora Maternal Care Unit
                </p>
              </div>

              <button
                type="button"
                className="patient-btn-primary connect-schedule-btn"
                onClick={() => setBookingModalOpen(true)}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                  <line x1="12" y1="14" x2="12" y2="18" />
                  <line x1="10" y1="16" x2="14" y2="16" />
                </svg>
                <span>Schedule Consultation</span>
              </button>
            </div>

            <p className="connect-doctor-bio">
              Specializing in perinatal depression, anxiety disorders, and maternal emotional wellbeing. Dr. Rostova works collaboratively with mothers through compassionate clinical evaluation and evidence-based recovery regimens.
            </p>

            <div className="connect-doctor-tags-row">
              <span className="connect-tag">Postpartum Mood Care</span>
              <span className="connect-tag">PPD Clinical Screening</span>
              <span className="connect-tag">Telehealth Support</span>
              <span className="connect-tag">Mindfulness Therapy</span>
            </div>
          </div>
        </div>
      </section>

      {/* Consultation Records Section */}
      <section className="patient-card connect-records-card" aria-labelledby="consultations-title">
        <div className="connect-records-header">
          <div>
            <h3 id="consultations-title" className="connect-records-title">
              Consultation Records &amp; Care Notes
            </h3>
            <p className="connect-records-sub">
              Your scheduled sessions and past clinical summaries with Dr. Rostova.
            </p>
          </div>

          <span className="connect-records-count">
            {consultationsList.length} Sessions Total
          </span>
        </div>

        <div className="connect-consultations-list">
          {consultationsList.map((c) => {
            const isScheduled = c.status.toLowerCase() === 'scheduled';
            return (
              <div key={c.id} className={`connect-consultation-row ${isScheduled ? 'is-scheduled' : 'is-completed'}`}>
                <div className="connect-row-icon-col" aria-hidden="true">
                  <div className={`connect-row-icon-pill ${isScheduled ? 'is-active-pill' : ''}`}>
                    <PatientIcon name="connect-doctor" size={18} />
                  </div>
                </div>

                <div className="connect-row-info-col">
                  <div className="connect-row-top">
                    <strong className="connect-row-type">{c.type}</strong>
                    <span className={`connect-status-badge ${isScheduled ? 'status-scheduled' : 'status-completed'}`}>
                      {c.status}
                    </span>
                  </div>

                  <p className="connect-row-doctor-info">
                    With {c.doctorName} &bull; {c.role}
                  </p>

                  <div className="connect-row-meta">
                    <span className="connect-meta-item">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                        <line x1="16" y1="2" x2="16" y2="6" />
                        <line x1="8" y1="2" x2="8" y2="6" />
                        <line x1="3" y1="10" x2="21" y2="10" />
                      </svg>
                      {c.date}
                    </span>
                    <span className="connect-meta-item">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      {c.time}
                    </span>
                    <span className="connect-meta-item clinic-name">
                      {c.clinic}
                    </span>
                  </div>
                </div>

                <div className="connect-row-action-col">
                  {isScheduled ? (
                    <button
                      type="button"
                      className="patient-btn-primary connect-join-btn"
                      onClick={handleJoinRoom}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M23 7l-7 5 7 5V7z" />
                        <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                      </svg>
                      <span>Join Room</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="patient-btn-secondary connect-summary-btn"
                      onClick={() => setActiveSummaryModal(c)}
                    >
                      <span>View Care Summary</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Booking Modal */}
      {bookingModalOpen && (
        <div className="companion-modal-backdrop" onClick={() => setBookingModalOpen(false)} role="dialog" aria-modal="true">
          <div className="patient-card connect-booking-modal" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h3 className="companion-modal-title">Schedule New Consultation</h3>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setBookingModalOpen(false)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleBookConsultation} className="connect-booking-form">
              <div className="booking-form-field">
                <label className="booking-label">Consultation Mode</label>
                <div className="booking-modes-grid">
                  <button
                    type="button"
                    className={`booking-mode-pill ${selectedType === 'Telehealth Video' ? 'is-selected' : ''}`}
                    onClick={() => setSelectedType('Telehealth Video')}
                  >
                    <span>Telehealth Video</span>
                  </button>
                  <button
                    type="button"
                    className={`booking-mode-pill ${selectedType === 'Audio Consult' ? 'is-selected' : ''}`}
                    onClick={() => setSelectedType('Audio Consult')}
                  >
                    <span>Audio Consult</span>
                  </button>
                </div>
              </div>

              <div className="booking-form-row">
                <div className="booking-form-field">
                  <label className="booking-label" htmlFor="booking-date">Preferred Date</label>
                  <input
                    id="booking-date"
                    type="date"
                    className="booking-input"
                    value={bookingDate}
                    onChange={(e) => setBookingDate(e.target.value)}
                    required
                  />
                </div>

                <div className="booking-form-field">
                  <label className="booking-label" htmlFor="booking-time">Preferred Time Slot</label>
                  <select
                    id="booking-time"
                    className="booking-input"
                    value={bookingTime}
                    onChange={(e) => setBookingTime(e.target.value)}
                  >
                    <option value="09:00 AM">09:00 AM</option>
                    <option value="11:00 AM">11:00 AM</option>
                    <option value="02:30 PM">02:30 PM</option>
                    <option value="04:00 PM">04:00 PM</option>
                  </select>
                </div>
              </div>

              <div className="booking-form-field">
                <label className="booking-label" htmlFor="booking-notes">Notes or Symptoms (Optional)</label>
                <textarea
                  id="booking-notes"
                  className="booking-textarea"
                  rows={3}
                  placeholder="Share anything you'd like Dr. Rostova to focus on during your session..."
                  value={bookingReason}
                  onChange={(e) => setBookingReason(e.target.value)}
                />
              </div>

              <div className="booking-modal-actions">
                <button
                  type="button"
                  className="patient-btn-secondary"
                  onClick={() => setBookingModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="patient-btn-primary">
                  Confirm Consultation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Care Summary Modal */}
      {activeSummaryModal && (
        <div className="companion-modal-backdrop" onClick={() => setActiveSummaryModal(null)} role="dialog" aria-modal="true">
          <div className="patient-card connect-summary-modal" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h3 className="companion-modal-title">Clinical Care Note Summary</h3>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setActiveSummaryModal(null)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <div className="connect-summary-modal-body">
              <div className="summary-meta-header">
                <strong>{activeSummaryModal.doctorName} &bull; {activeSummaryModal.role}</strong>
                <span>Completed on {activeSummaryModal.date} at {activeSummaryModal.time}</span>
              </div>
              <p className="summary-p">
                <strong>Assessment:</strong> Patient presented with moderate postpartum fatigue and sleep fragmentation. Edinburgh screening score 14/30 discussed in detail.
              </p>
              <p className="summary-p">
                <strong>Recommendations:</strong>
              </p>
              <ul className="summary-ul">
                <li>Continue 4-7-8 grounding and gentle parasympathetic breathing twice daily.</li>
                <li>Coordinate overnight feeds with support network to ensure at least one 4-hour consolidated sleep block.</li>
                <li>Follow-up virtual check-in scheduled for late November.</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ConnectDoctorPage;

