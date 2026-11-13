import React from 'react';
import { Outlet } from 'react-router-dom';
import { TopNav } from './components/TopNav.jsx';
import { AddMotherModal } from './components/AddMotherModal.jsx';

export function DashboardLayout() {
  return (
    <div className="miora-app-shell">
      <a className="skip-link" href="#dashboard-main">
        Skip to dashboard content
      </a>
      <TopNav />
      <main id="dashboard-main">
        <Outlet />
      </main>
      <AddMotherModal />
    </div>
  );
}

