import React from 'react';

const ICON_PATHS = {
  users: (
    <>
      <circle cx="12" cy="8.5" r="2.8" />
      <path d="M6.8 18.5c0-2.6 2.3-4.5 5.2-4.5s5.2 1.9 5.2 4.5" />
      <circle cx="6.2" cy="10.2" r="2" />
      <path d="M2.6 18c.1-1.9 1.6-3.3 3.6-3.5" />
      <circle cx="17.8" cy="10.2" r="2" />
      <path d="M21.4 18c-.1-1.9-1.6-3.3-3.6-3.5" />
    </>
  ),
  mic: (
    <>
      <rect x="8.6" y="3" width="6.8" height="11.5" rx="3.4" />
      <path d="M5.2 11.2v.6a6.8 6.8 0 0 0 13.6 0v-.6M12 18.6V22M8.8 22h6.4" />
    </>
  ),
  alertTriangle: (
    <>
      <path d="M10.4 4.4 3.1 17.2a1.8 1.8 0 0 0 1.6 2.7h14.6a1.8 1.8 0 0 0 1.6-2.7L13.6 4.4a1.8 1.8 0 0 0-3.2 0Z" />
      <path d="M12 9.4v4.4" />
      <circle cx="12" cy="16.4" r="0.6" fill="currentColor" stroke="none" />
    </>
  ),
  layers: (
    <>
      <path d="m12 3.5 8.8 4.6-8.8 4.6-8.8-4.6L12 3.5Z" />
      <path d="m3.2 12 8.8 4.6 8.8-4.6" />
      <path d="m3.2 16 8.8 4.6 8.8-4.6" />
    </>
  ),
  barChart: (
    <>
      <rect x="4" y="13.5" width="3.5" height="6.5" rx="0.8" />
      <rect x="10.2" y="9" width="3.5" height="11" rx="0.8" />
      <rect x="16.5" y="4.5" width="3.5" height="15.5" rx="0.8" />
    </>
  ),
  pieChart: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 3.5V12h8.5" />
    </>
  ),
  flag: (
    <>
      <path d="M5.5 21V4.5" />
      <path d="M5.5 4.8c2.6-1.4 4.8.8 7.5.5 2-.2 3.6-1 5-.4v8.2c-1.4-.6-3 .2-5 .4-2.7.3-4.9-1.9-7.5-.5" />
    </>
  ),
  waveform: (
    <>
      <path d="M3.5 10.5v3" />
      <path d="M6.8 8v8" />
      <path d="M10.1 4.5v15" />
      <path d="M13.4 7v10" />
      <path d="M16.7 5.5v13" />
      <path d="M20 9.5v5" />
    </>
  ),
  bolt: <path d="M13.2 2.8 5.2 13h6l-1 8.2 8-10.2h-6l1-8.2Z" />,
  userPlus: (
    <>
      <circle cx="9.5" cy="8" r="3.2" />
      <path d="M3.5 19.5c0-3 2.7-5 6-5s6 2 6 5" />
      <path d="M19 8.5v5M16.5 11h5" />
    </>
  ),
  clipboardList: (
    <>
      <rect x="5" y="4" width="14" height="16.5" rx="2.2" />
      <path d="M9 8.5h6M9 12.2h6M9 15.8h4" />
    </>
  ),
  stethoscope: (
    <>
      <path d="M6.5 4.5v5a4.5 4.5 0 0 0 9 0v-5" />
      <path d="M5 4.5h3M14 4.5h3" />
      <path d="M11 14v2.5a4 4 0 0 0 8 0v-2" />
      <circle cx="19" cy="12.5" r="1.8" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8.4" r="3.3" />
      <path d="M5.5 19.5c0-3.1 2.9-5.2 6.5-5.2s6.5 2.1 6.5 5.2" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.2 4.2" />
    </>
  ),
  bell: (
    <>
      <path d="M6.2 15.8c1-1.1 1.5-2.6 1.5-4.3v-1a4.3 4.3 0 1 1 8.6 0v1c0 1.7.5 3.2 1.5 4.3H6.2Z" />
      <path d="M10 18.6a2.2 2.2 0 0 0 4 0" />
    </>
  ),
  chevronDown: <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />,
  chevronRight: <path d="m9.5 6.5 5.5 5.5-5.5 5.5" />,
  arrowRight: <path d="M4.5 12h14M13.5 7l5 5-5 5" />,
  plus: <path d="M12 5v14M5 12h14" />,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  sparkle: (
    <path d="m12 3-1.2 4.2L6.5 8.5l4.3 1.3L12 14l1.2-4.2 4.3-1.3-4.3-1.3L12 3Z" />
  ),
};

export function DashboardIcon({ name, size = 20, className = '', strokeWidth = 1.7 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {ICON_PATHS[name] || ICON_PATHS.arrowRight}
    </svg>
  );
}

