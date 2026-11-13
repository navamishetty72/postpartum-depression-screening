import React, { useState } from 'react';
import { usePatient } from '../context/PatientContext.jsx';
import { PatientIcon } from '../components/PatientIcons.jsx';

export function PatientSettingsPage() {
  const [cameraPermission, setCameraPermission] = useState('prompt');
  const [micPermission, setMicPermission] = useState('prompt');
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [consultationAlerts, setConsultationAlerts] = useState(true);
  const [confidentialMode, setConfidentialMode] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: 860 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, margin: '0 0 6px 0', color: 'var(--patient-text-primary)' }}>
          Account &amp; Privacy Settings
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--patient-text-muted)' }}>
          Configure confidential screening permissions, alerts, and account security.
        </p>
      </div>

      {saveSuccess && (
        <div style={{ background: 'var(--patient-success-bg)', color: 'var(--patient-success)', padding: '10px 16px', borderRadius: 8, marginBottom: 16, fontSize: 13 }}>
          ✓ Settings saved successfully.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Screening Privacy & Permissions */}
        <section style={{ background: '#ffffff', border: '1px solid var(--patient-border)', borderRadius: 12, padding: 20, boxShadow: 'var(--patient-shadow-card)' }}>
          <h2 style={{ fontSize: 15, margin: '0 0 12px 0', color: 'var(--patient-text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <PatientIcon name="video" size={17} color="var(--patient-primary)" />
            <span>Screening Device Permissions</span>
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ display: 'block', fontSize: 13, color: 'var(--patient-text-body)' }}>Camera Access</strong>
                <small style={{ color: 'var(--patient-text-muted)', fontSize: 11.5 }}>Allow conversational video analysis during AI screening</small>
              </div>
              <input type="checkbox" checked={cameraPermission !== 'denied'} onChange={(e) => setCameraPermission(e.target.checked ? 'granted' : 'denied')} />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ display: 'block', fontSize: 13, color: 'var(--patient-text-body)' }}>Microphone Access</strong>
                <small style={{ color: 'var(--patient-text-muted)', fontSize: 11.5 }}>Allow vocal biomarker and speech dictation</small>
              </div>
              <input type="checkbox" checked={micPermission !== 'denied'} onChange={(e) => setMicPermission(e.target.checked ? 'granted' : 'denied')} />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ display: 'block', fontSize: 13, color: 'var(--patient-text-body)' }}>Strict Patient Confidentiality</strong>
                <small style={{ color: 'var(--patient-text-muted)', fontSize: 11.5 }}>Only authorized clinical care team can access screening reports</small>
              </div>
              <input type="checkbox" checked={confidentialMode} onChange={(e) => setConfidentialMode(e.target.checked)} />
            </label>
          </div>
        </section>

        {/* Notifications & Reminders */}
        <section style={{ background: '#ffffff', border: '1px solid var(--patient-border)', borderRadius: 12, padding: 20, boxShadow: 'var(--patient-shadow-card)' }}>
          <h2 style={{ fontSize: 15, margin: '0 0 12px 0', color: 'var(--patient-text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <PatientIcon name="bell" size={17} color="var(--patient-primary)" />
            <span>Notification Preferences</span>
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ display: 'block', fontSize: 13, color: 'var(--patient-text-body)' }}>Screening Report Ready Alerts</strong>
                <small style={{ color: 'var(--patient-text-muted)', fontSize: 11.5 }}>Receive in-app and email updates when reports finish processing</small>
              </div>
              <input type="checkbox" checked={emailNotifs} onChange={(e) => setEmailNotifs(e.target.checked)} />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
              <div>
                <strong style={{ display: 'block', fontSize: 13, color: 'var(--patient-text-body)' }}>Consultation Reminders</strong>
                <small style={{ color: 'var(--patient-text-muted)', fontSize: 11.5 }}>Reminder alerts 24 hours prior to scheduled doctor telehealth calls</small>
              </div>
              <input type="checkbox" checked={consultationAlerts} onChange={(e) => setConsultationAlerts(e.target.checked)} />
            </label>
          </div>
        </section>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={handleSave}
            style={{
              background: 'var(--patient-primary)',
              color: '#ffffff',
              border: 'none',
              padding: '9px 22px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
}
export default PatientSettingsPage;
