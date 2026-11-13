import React from 'react';
import { useNavigate } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from '../components/PatientIcons.jsx';
import './patientHome.css';

export function PatientHomePage() {
  const navigate = useNavigate();
  const { patient, screening, consultations } = usePatient();

  const patientName = patient?.name || 'Amara';
  const riskScore = screening?.riskScore ?? 64;
  const riskLabel = screening?.riskLevel ?? 'Moderate Attention';

  // Gauge calculations for 54px circle (radius 22, circumference ~138.23)
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (riskScore / 100) * circumference;

  return (
    <div className="patient-home-container">
      {/* Breadcrumb Bar */}
      <div className="medhist-breadcrumb-bar">
        <span className="medhist-breadcrumb-current">Dashboard</span>
      </div>

      {/* Hero Welcome Banner */}
      <div className="patient-card patient-home-hero-card">
        <div className="patient-home-hero-text">
          <div className="patient-home-greeting-badge">
            <PatientIcon name="heart" size={13} />
            <span>Maternal Emotional Wellness</span>
          </div>

          <h1 className="patient-home-title">
            Welcome back, {patientName}
          </h1>

          <p className="patient-home-subtitle">
            Your personalized companion for postpartum recovery and emotional intelligence.
            Track your well-being trajectory, start guided screening check-ins, and connect with your clinical support team.
          </p>

          <div className="patient-home-hero-actions">
            <button
              type="button"
              className="patient-btn-primary"
              onClick={() => navigate('/patient/screening')}
            >
              <PatientIcon name="ai-screening" size={15} />
              <span>Start AI Screening</span>
            </button>

            <button
              type="button"
              className="patient-btn-secondary"
              onClick={() => navigate('/patient/ai-assistant')}
            >
              <PatientIcon name="ai-assistant" size={15} />
              <span>Talk with AI Assistant</span>
            </button>
          </div>
        </div>

        <div className="patient-home-hero-illu-wrap" aria-hidden="true">
          <img
            src="/assets/care-mother-feathered.png"
            alt=""
            className="patient-home-hero-illustration"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      </div>

      {/* 6-Card Dashboard Grid */}
      <div className="patient-home-grid">
        {/* Card 1: Wellness Index */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="reports" size={18} />
              </div>
              <span className="patient-home-status-tag">Active Index</span>
            </div>

            <h2 className="patient-home-card-title">Postpartum Wellness Index</h2>
            <p className="patient-home-card-desc">
              Multimodal synthesis from your latest screening and clinical indicators.
            </p>

            <div className="patient-home-gauge-row">
              <svg className="patient-home-gauge-svg" viewBox="0 0 54 54">
                <circle
                  cx="27"
                  cy="27"
                  r={radius}
                  fill="none"
                  stroke="#fbeaf0"
                  strokeWidth="5"
                />
                <circle
                  cx="27"
                  cy="27"
                  r={radius}
                  fill="none"
                  stroke="var(--patient-brand-rose)"
                  strokeWidth="5"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                />
              </svg>

              <div className="patient-home-gauge-info">
                <span className="patient-home-gauge-val">{riskScore}%</span>
                <span className="patient-home-gauge-sub">{riskLabel}</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-secondary patient-home-card-btn"
            onClick={() => navigate('/patient/reports')}
          >
            <span>View Full Reports &amp; Analytics</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>

        {/* Card 2: AI Screening */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="ai-screening" size={18} />
              </div>
              <span className="patient-home-status-tag">Check-In Due</span>
            </div>

            <h2 className="patient-home-card-title">AI Screening Check-In</h2>
            <p className="patient-home-card-desc">
              A 3-minute confidential multimodal check-in assessing facial sentiment, voice acoustics, and conversational cues.
            </p>

            <div className="patient-home-chips-list">
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Camera &amp; mic live preview</span>
              </div>
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Immediate objective score</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-primary patient-home-card-btn"
            onClick={() => navigate('/patient/screening')}
          >
            <span>Begin Screening Session</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>

        {/* Card 3: AI Assistant */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="ai-assistant" size={18} />
              </div>
              <span className="patient-home-status-tag">24/7 Companion</span>
            </div>

            <h2 className="patient-home-card-title">AI Assistant Companion</h2>
            <p className="patient-home-card-desc">
              Non-judgmental, compassionate maternal emotional support anytime you need to reflect or ask questions.
            </p>

            <div className="patient-home-chips-list">
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Voice &amp; speech synthesis</span>
              </div>
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Mood tracking check-ins</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-secondary patient-home-card-btn"
            onClick={() => navigate('/patient/ai-assistant')}
          >
            <span>Open AI Assistant</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>

        {/* Card 4: Care Suggestions */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="care-suggestions" size={18} />
              </div>
              <span className="patient-home-status-tag">Restorative Plan</span>
            </div>

            <h2 className="patient-home-card-title">Care Suggestions</h2>
            <p className="patient-home-card-desc">
              Evidence-based restorative practices including 4-7-8 breathing, sleep consolidation, and journaling.
            </p>

            <div className="patient-home-chips-list">
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>4-7-8 Parasympathetic breathing</span>
              </div>
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Postpartum sleep restoration tips</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-secondary patient-home-card-btn"
            onClick={() => navigate('/patient/care-suggestions')}
          >
            <span>Explore Care Practices</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>

        {/* Card 5: Medical History */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="medical-history" size={18} />
              </div>
              <span className="patient-home-status-tag">Encrypted</span>
            </div>

            <h2 className="patient-home-card-title">Medical History &amp; Records</h2>
            <p className="patient-home-card-desc">
              Manage your baseline clinical health background, depression history, and uploaded diagnostic files.
            </p>

            <div className="patient-home-chips-list">
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>PPD diagnosis question recorded</span>
              </div>
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>256-bit encrypted documents</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-secondary patient-home-card-btn"
            onClick={() => navigate('/patient/medical-history')}
          >
            <span>Review Medical History</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>

        {/* Card 6: Connected Clinician */}
        <div className="patient-home-card">
          <div>
            <div className="patient-home-card-header">
              <div className="patient-home-card-icon-wrap">
                <PatientIcon name="connect-doctor" size={18} />
              </div>
              <span className="patient-home-status-tag">Connected</span>
            </div>

            <h2 className="patient-home-card-title">Connect to a Doctor</h2>
            <p className="patient-home-card-desc">
              Direct consultation channel with your assigned maternal mental health specialist.
            </p>

            <div className="patient-home-chips-list">
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Dr. Elena Rostova &bull; OB/GYN</span>
              </div>
              <div className="patient-home-chip-item">
                <span className="patient-home-chip-dot" />
                <span>Next consult: Nov 24, 2026</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="patient-btn-secondary patient-home-card-btn"
            onClick={() => navigate('/patient/connect-doctor')}
          >
            <span>Book / View Consultations</span>
            <PatientIcon name="arrow-right" size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

