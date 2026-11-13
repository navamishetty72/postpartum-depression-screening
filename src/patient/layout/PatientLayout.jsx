import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { PatientSidebar } from '../components/PatientSidebar.jsx';
import { PatientHeader } from '../components/PatientHeader.jsx';
import '../styles/patientLayout.css';

export function PatientLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="patient-app-shell">
      <div
        className={`patient-mobile-backdrop ${mobileOpen ? 'is-active' : ''}`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />
      <PatientSidebar
        isMobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="patient-main-container">
        <PatientHeader onToggleMobile={() => setMobileOpen((prev) => !prev)} />
        <main className="patient-content-area" id="patient-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default PatientLayout;

