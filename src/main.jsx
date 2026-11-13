import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import './dashboard/dashboard.css';
import { App } from './App.jsx';

const rootEl = document.querySelector('#app');
createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

