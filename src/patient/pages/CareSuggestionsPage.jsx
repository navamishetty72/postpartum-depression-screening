import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from '../components/PatientIcons.jsx';
import './care-suggestions.css';

export function CareSuggestionsPage() {
  const navigate = useNavigate();
  const {
    patient,
    screening,
    carePlan,
    toggleCareTask,
  } = usePatient();

  const [activeTab, setActiveTab] = useState('care-plan');

  // Modals for interactive actions
  const [activeModal, setActiveModal] = useState(null); // 'breathing' | 'sleep' | 'journaling'
  const [journalEntry, setJournalEntry] = useState('');

  // Tasks from patient context
  const tasks = carePlan?.tasks || [
    { id: 'task-1', title: 'Breathing exercise', completed: true },
    { id: 'task-2', title: 'Mood check-in', completed: true },
    { id: 'task-3', title: 'Sleep routine', completed: true },
    { id: 'task-4', title: 'Journaling', completed: false },
    { id: 'task-5', title: 'Light activity', completed: false },
    { id: 'task-6', title: 'Self-care time', completed: false },
    { id: 'task-7', title: 'Reflection', completed: false },
  ];

  const completedCount = tasks.filter((t) => t.completed).length;
  const totalTasks = tasks.length;

  // Circular gauge calculations
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const progressRatio = totalTasks > 0 ? completedCount / totalTasks : 0;
  const strokeDashoffset = circumference - progressRatio * circumference;

  // Tabs configuration
  const tabs = [
    { id: 'care-plan', label: 'My Care Plan', icon: 'feather-leaf' },
    { id: 'self-care', label: 'Self-Care', icon: 'lotus' },
    { id: 'mood-support', label: 'Mood Support', icon: 'smile-face' },
    { id: 'lifestyle', label: 'Lifestyle', icon: 'apple' },
    { id: 'resources', label: 'Resources', icon: 'book-open' },
  ];

  const handleStartBreathing = () => {
    setActiveModal('breathing');
  };

  const handleCompleteBreathing = () => {
    const breathingTask = tasks.find((t) => t.id === 'task-1');
    if (breathingTask && !breathingTask.completed) {
      toggleCareTask('task-1');
    }
    setActiveModal(null);
  };

  const handleSaveJournal = () => {
    if (journalEntry.trim()) {
      const journalTask = tasks.find((t) => t.id === 'task-4');
      if (journalTask && !journalTask.completed) {
        toggleCareTask('task-4');
      }
    }
    setActiveModal(null);
    setJournalEntry('');
  };

  const riskDisplay = screening?.riskLabel
    ? screening.riskLabel.replace(' for PPD', '')
    : 'Moderate Risk';

  return (
    <div className="care-page-container">
      {/* Breadcrumb Bar */}
      <div className="medhist-breadcrumb-bar">
        <NavLink to="/patient/dashboard" className="medhist-breadcrumb-link">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
            <path d="M9.5 21v-7h5v7" />
          </svg>
          <span>Home</span>
        </NavLink>
        <span className="medhist-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
        <span className="medhist-breadcrumb-current">Care Suggestions</span>
      </div>

      {/* Hero Header Banner */}
      <div className="patient-card care-hero-card">
        <div className="care-hero-text">
          <h1 className="patient-page-heading care-title">Personalised Care Suggestions</h1>
          <p className="patient-page-subheading care-subtitle">
            Evidence-based recovery plans, mindful restorative practices, and clinical guidance tailored to your postpartum journey.
          </p>
        </div>

        <div className="care-hero-illu-wrap" aria-hidden="true">
          <img
            src="/assets/care-mother-feathered.png"
            alt=""
            className="care-hero-illustration"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      </div>

      {/* Categories Tabs Navigation */}
      <nav className="care-tabs-nav" aria-label="Care Suggestion Categories">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              className={`care-tab-btn ${isActive ? 'is-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="care-tab-icon">
                <PatientIcon name={tab.icon} size={15} />
              </span>
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Main Two-Column Content Grid */}
      <div className="care-main-grid">
        {/* Left Column: Plan & Daily Suggestions */}
        <div className="care-main-left">
          {/* Personalised Care Plan Hero Card */}
          <section className="patient-card care-plan-card" aria-label="Personalised Care Plan Overview">
            <div className="plan-info-left">
              <div className="plan-badge-icon" aria-hidden="true">
                <PatientIcon name="clipboard" size={20} />
              </div>
              <div className="plan-text-content">
                <h2 className="plan-title">Your 4-Week Postpartum Recovery Plan</h2>
                <p className="plan-desc">
                  Calibrated to your screening indicators ({riskDisplay}), focused on nervous system grounding, emotional nourishment, and sleep restoration.
                </p>
              </div>
            </div>

            <div className="plan-info-right">
              <div className="plan-meta-box">
                <span className="plan-meta-label">Plan Duration</span>
                <span className="plan-meta-value">{carePlan?.duration || '4 Weeks'}</span>
              </div>

              <div className="plan-meta-box">
                <span className="plan-meta-label">Focus Areas</span>
                <span className="plan-meta-value">
                  {(carePlan?.focusAreas || ['Rest', 'Grounding', 'Nourishment', 'Support']).join(' • ')}
                </span>
              </div>
            </div>
          </section>

          {/* Today's Care Suggestions Cards Section */}
          <section className="care-suggestions-section" aria-label="Today's Care Suggestions">
            <div className="suggestions-header-row">
              <h2 className="suggestions-section-title">Today's Restorative Practices</h2>
              <div className="day-progress-badge">
                <PatientIcon name="calendar" size={13} />
                <span>Day {carePlan?.currentDay || 3} of {carePlan?.totalDays || 28}</span>
              </div>
            </div>

            <div className="suggestions-cards-grid">
              {/* Card 1: Breathing Exercise */}
              <article className="patient-card suggestion-card">
                <div className="suggestion-img-wrap">
                  <img
                    src="/assets/care-breathing.png"
                    alt="Breathing Exercise"
                    className="suggestion-img"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
                <h3 className="suggestion-card-title">4-7-8 Breathing</h3>
                <p className="suggestion-card-desc">A 5-minute parasympathetic exercise to calm maternal anxiety.</p>
                <button
                  type="button"
                  className="patient-btn-primary suggestion-action-btn"
                  onClick={handleStartBreathing}
                >
                  <PatientIcon name="play-circle" size={14} />
                  <span>Start (5 min)</span>
                </button>
              </article>

              {/* Card 2: Better Sleep */}
              <article className="patient-card suggestion-card">
                <div className="suggestion-img-wrap">
                  <img
                    src="/assets/care-sleep.png"
                    alt="Better Sleep"
                    className="suggestion-img"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
                <h3 className="suggestion-card-title">Sleep Restoration</h3>
                <p className="suggestion-card-desc">Evidence-based steps to consolidate postpartum sleep cycles.</p>
                <button
                  type="button"
                  className="patient-btn-secondary suggestion-action-btn"
                  onClick={() => setActiveModal('sleep')}
                >
                  <span>View Sleep Tips</span>
                  <PatientIcon name="arrow-right" size={12} />
                </button>
              </article>

              {/* Card 3: Mood Journaling */}
              <article className="patient-card suggestion-card">
                <div className="suggestion-img-wrap">
                  <img
                    src="/assets/care-journaling.png"
                    alt="Mood Journaling"
                    className="suggestion-img"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
                <h3 className="suggestion-card-title">Daily Reflection</h3>
                <p className="suggestion-card-desc">Safe emotional release and non-judgmental prompt journaling.</p>
                <button
                  type="button"
                  className="patient-btn-secondary suggestion-action-btn"
                  onClick={() => setActiveModal('journaling')}
                >
                  <span>Start Journaling</span>
                  <PatientIcon name="arrow-right" size={12} />
                </button>
              </article>
            </div>
          </section>
        </div>

        {/* Right Column: Progress Tracker & Doctor Connection */}
        <div className="care-main-right">
          {/* Progress Tracker Card */}
          <section className="patient-card care-progress-card" aria-label="Care Plan Progress">
            <h2 className="progress-card-title">Daily Checklist</h2>
            <div className="progress-body-row">
              {/* Circular Gauge */}
              <div className="progress-gauge-wrap">
                <svg className="progress-gauge-svg" viewBox="0 0 90 90" aria-hidden="true">
                  <circle
                    className="progress-gauge-track"
                    cx="45"
                    cy="45"
                    r={radius}
                  />
                  <circle
                    className="progress-gauge-bar"
                    cx="45"
                    cy="45"
                    r={radius}
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                  />
                </svg>
                <div className="progress-gauge-text">
                  <span className="gauge-fraction">
                    {completedCount}/{totalTasks}
                  </span>
                  <span className="gauge-subtext">Tasks<br />Done</span>
                </div>
              </div>

              {/* Checklist */}
              <ul className="progress-tasks-list">
                {tasks.map((task) => (
                  <li
                    key={task.id}
                    className={`progress-task-item ${task.completed ? 'is-completed' : ''}`}
                    onClick={() => toggleCareTask(task.id)}
                    role="checkbox"
                    aria-checked={task.completed}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === ' ' || e.key === 'Enter') {
                        toggleCareTask(task.id);
                      }
                    }}
                    title="Click to toggle completion"
                  >
                    <span className={`task-check-circle ${task.completed ? 'completed' : 'pending'}`}>
                      {task.completed && (
                        <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="2.5 6 4.8 8.5 9.5 3.5" />
                        </svg>
                      )}
                    </span>
                    <span className="task-name">{task.title}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Need More Support? Card */}
          <section className="patient-card care-support-card" aria-label="Clinical Support">
            <div className="support-header-row">
              <div className="support-icon-wrap" aria-hidden="true">
                <PatientIcon name="connect-doctor" size={18} />
              </div>
              <div className="support-text-wrap">
                <h2 className="support-title">Need Clinical Support?</h2>
                <p className="support-desc">
                  Connect directly with Dr. Elena Rostova for personalized psychiatric evaluations and guided care adjustments.
                </p>
              </div>
            </div>

            <NavLink to="/patient/connect-doctor" className="patient-btn-primary support-action-btn">
              <span>Connect to a Doctor</span>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </NavLink>
          </section>
        </div>
      </div>

      {/* Interactive Modals */}
      {/* 1. Breathing Exercise Modal */}
      {activeModal === 'breathing' && (
        <div className="companion-modal-backdrop" onClick={() => setActiveModal(null)} role="dialog" aria-modal="true">
          <div className="patient-card care-interactive-modal" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h3 className="companion-modal-title">4-7-8 Breathing Exercise</h3>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <p className="care-modal-desc">
              Take a slow, gentle breath in through your nose for 4 seconds, hold softly for 7 seconds, and exhale completely through your mouth for 8 seconds.
            </p>
            <div className="breathing-circle-wrap">
              <div className="breathing-bubble">Breathe</div>
            </div>
            <button
              type="button"
              className="patient-btn-primary modal-action-btn"
              onClick={handleCompleteBreathing}
            >
              Complete Exercise &amp; Mark Done
            </button>
          </div>
        </div>
      )}

      {/* 2. Better Sleep Tips Modal */}
      {activeModal === 'sleep' && (
        <div className="companion-modal-backdrop" onClick={() => setActiveModal(null)} role="dialog" aria-modal="true">
          <div className="patient-card care-interactive-modal" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h3 className="companion-modal-title">Postpartum Sleep Hygiene</h3>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <p className="care-modal-desc">
              Sleep is essential for maternal emotional recovery. Gentle, evidence-based recommendations:
            </p>
            <ul className="care-tips-ul">
              <li><strong>Consolidated sleep block:</strong> Coordinate night feedings with your partner to preserve at least one 4-hour stretch of deep sleep.</li>
              <li><strong>Circadian lighting:</strong> Keep room lighting amber and dim 45 minutes prior to sleep.</li>
              <li><strong>Nervous system offloading:</strong> Practice 3 minutes of mindful sensory grounding before laying down.</li>
              <li><strong>Nap with flexibility:</strong> A 20-minute restorative rest during midday replenishes daytime mental energy.</li>
            </ul>
            <button
              type="button"
              className="patient-btn-secondary modal-action-btn"
              onClick={() => setActiveModal(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* 3. Mood Journaling Modal */}
      {activeModal === 'journaling' && (
        <div className="companion-modal-backdrop" onClick={() => setActiveModal(null)} role="dialog" aria-modal="true">
          <div className="patient-card care-interactive-modal" onClick={(e) => e.stopPropagation()}>
            <div className="companion-modal-head">
              <h3 className="companion-modal-title">Daily Mood Reflection</h3>
              <button
                type="button"
                className="companion-modal-close-btn"
                onClick={() => setActiveModal(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <p className="care-modal-desc">
              Write down whatever thoughts or feelings are present right now. There are no expectations or judgments.
            </p>
            <textarea
              className="journal-textarea"
              placeholder="How are you feeling today? What is one thing that brought a small moment of comfort?..."
              rows={4}
              value={journalEntry}
              onChange={(e) => setJournalEntry(e.target.value)}
            />
            <button
              type="button"
              className="patient-btn-primary modal-action-btn"
              onClick={handleSaveJournal}
            >
              Save Reflection &amp; Mark Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default CareSuggestionsPage;
