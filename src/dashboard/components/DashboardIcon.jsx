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
  clipboardCheck: (
    <>
      <rect x="5" y="4.5" width="14" height="16" rx="2.2" />
      <path d="M9 4.5a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 4.5v1.2H9V4.5Z" />
      <path d="m9 13 2 2 4-4" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  shieldCheck: (
    <>
      <path d="M12 3.2 19 6v5.2c0 4.6-2.9 8.1-7 9.6-4.1-1.5-7-5-7-9.6V6l7-2.8Z" />
      <path d="m9.2 12.2 1.9 1.9 3.8-4" />
    </>
  ),
  filter: (
    <path d="M4 5.5h16l-6.2 7.2v5.1l-3.6 1.7v-6.8L4 5.5Z" />
  ),
  eye: (
    <>
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.6" />
    </>
  ),
  refresh: (
    <>
      <path d="M4.5 12a7.5 7.5 0 0 1 12.9-5.2L19.5 9" />
      <path d="M19.5 4.8V9h-4.2" />
      <path d="M19.5 12a7.5 7.5 0 0 1-12.9 5.2L4.5 15" />
      <path d="M4.5 19.2V15h4.2" />
    </>
  ),
  chevronLeft: <path d="m14.5 6.5-5.5 5.5 5.5 5.5" />,
  video: (
    <>
      <rect x="3" y="6.5" width="13" height="11" rx="2.2" />
      <path d="m16 10 5-2.8v9.6L16 14" />
    </>
  ),
  videoOff: (
    <>
      <path d="M10.5 6.5H14a2 2 0 0 1 2 2v2.2l5-2.7v8l-3.2-1.8" />
      <path d="M14.5 17.5H5a2 2 0 0 1-2-2V8.5a2 2 0 0 1 2-2h1.5" />
      <path d="m3.5 3.5 17 17" />
    </>
  ),
  micOff: (
    <>
      <path d="M15.4 10.5V6.4a3.4 3.4 0 0 0-6.2-1.9" />
      <path d="M8.6 8.6v2.5a3.4 3.4 0 0 0 5.4 2.7" />
      <path d="M5.2 11.2v.6a6.8 6.8 0 0 0 11.1 5.2M12 18.6V22M8.8 22h6.4M3.5 3.5l17 17" />
    </>
  ),
  upload: (
    <>
      <path d="M12 15.5V4.5M7.5 8.5 12 4l4.5 4.5" />
      <path d="M4.5 15.5v2.8a1.7 1.7 0 0 0 1.7 1.7h11.6a1.7 1.7 0 0 0 1.7-1.7v-2.8" />
    </>
  ),
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.2" />
      <path d="M8 3.2v3.2M16 3.2v3.2M3.5 9.5h17" />
    </>
  ),
  messageCircle: (
    <>
      <path d="M20 11.5a7.8 7.8 0 0 1-11.2 7L4 20l1.4-4.3A7.8 7.8 0 1 1 20 11.5Z" />
      <circle cx="9" cy="11.5" r="0.7" fill="currentColor" stroke="none" />
      <circle cx="12" cy="11.5" r="0.7" fill="currentColor" stroke="none" />
      <circle cx="15" cy="11.5" r="0.7" fill="currentColor" stroke="none" />
    </>
  ),
  smile: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 14.2a4.5 4.5 0 0 0 7 0" />
      <circle cx="9.2" cy="9.8" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="14.8" cy="9.8" r="0.8" fill="currentColor" stroke="none" />
    </>
  ),
  faceScan: (
    <>
      <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
      <path d="M9 14.2a3.8 3.8 0 0 0 6 0" />
      <circle cx="9.5" cy="10" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="14.5" cy="10" r="0.8" fill="currentColor" stroke="none" />
    </>
  ),
  checkSquare: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2.5" />
      <path d="m8.5 12.2 2.4 2.4 4.6-4.8" />
    </>
  ),
  maximize: (
    <path d="M15 4h5v5M9 20H4v-5M20 4l-6 6M4 20l6-6" />
  ),
  arrowLeft: <path d="M19.5 12h-14M10.5 7l-5 5 5 5" />,
  stopSquare: (
    <rect x="7" y="7" width="10" height="10" rx="1.8" fill="currentColor" stroke="none" />
  ),
  uploadCloud: (
    <>
      <path d="M16.5 16.5a3.5 3.5 0 0 0 .6-6.9A5.2 5.2 0 0 0 7 8.4a4 4 0 0 0-.5 7.9" />
      <path d="M12 19.5v-7M9.2 15.2 12 12.5l2.8 2.7" />
    </>
  ),
  fileText: (
    <>
      <path d="M14 3.5H7.2A1.7 1.7 0 0 0 5.5 5.2v13.6a1.7 1.7 0 0 0 1.7 1.7h9.6a1.7 1.7 0 0 0 1.7-1.7V8L14 3.5Z" />
      <path d="M14 3.5V8h4.5M9 12h6M9 15.5h4.5" />
    </>
  ),
  trash: (
    <>
      <path d="M4.5 6.5h15M9.5 4h5M7 6.5l.8 12a1.5 1.5 0 0 0 1.5 1.4h5.4a1.5 1.5 0 0 0 1.5-1.4l.8-12" />
      <path d="M10.2 10.5v5.5M13.8 10.5v5.5" />
    </>
  ),
  play: (
    <polygon points="8 6 18 12 8 18 8 6" />
  ),
  download: (
    <>
      <path d="M12 4.5v10.5M8 11.5l4 4 4-4" />
      <path d="M4.5 16.5v2a1.7 1.7 0 0 0 1.7 1.7h11.6a1.7 1.7 0 0 0 1.7-1.7v-2" />
    </>
  ),
  share: (
    <>
      <circle cx="17.5" cy="5.5" r="2.3" />
      <circle cx="6.5" cy="12" r="2.3" />
      <circle cx="17.5" cy="18.5" r="2.3" />
      <path d="m8.6 10.8 6.8-4.1M8.6 13.2l6.8 4.1" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none" />
    </>
  ),
  brain: (
    <>
      <path d="M9.5 4.5a3 3 0 0 0-3 3c-1.4.4-2.3 1.7-2.2 3.1a3 3 0 0 0 .9 5.5 2.8 2.8 0 0 0 4.8 2V5.2a3 3 0 0 0-.5-.7Z" />
      <path d="M14.5 4.5a3 3 0 0 1 3 3c1.4.4 2.3 1.7 2.2 3.1a3 3 0 0 1-.9 5.5 2.8 2.8 0 0 1-4.8 2V5.2c.2-.3.3-.5.5-.7Z" />
    </>
  ),
  trendingUp: (
    <>
      <path d="m3.5 16.5 6-6 4 4 7-7" />
      <path d="M15.5 7.5h5v5" />
    </>
  ),
  leaf: (
    <>
      <path d="M19.5 4.5C12.5 4.2 7 6.6 4.7 10.8c-1.1 2-.6 4.4 1.6 5.3 2.4.9 5.2-.2 6.8-2.1 2.9-3.3 3.7-7 6.4-9.5Z" />
      <path d="M4 20c1.9-4.7 5.5-7.9 10-9.8" />
    </>
  ),
  heart: (
    <path d="M20.2 8.8c0 5.1-8.2 10.4-8.2 10.4S3.8 13.9 3.8 8.8A4.4 4.4 0 0 1 12 6.4a4.4 4.4 0 0 1 8.2 2.4Z" />
  ),
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.8 12.2 2.2 2.2 4.3-4.5" />
    </>
  ),
  dumbbell: (
    <>
      <path d="M6.5 7.5v9M17.5 7.5v9M4 9.5v5M20 9.5v5M6.5 12h11" />
    </>
  ),
  bookOpen: (
    <>
      <path d="M12 6.5c-2.2-1.4-4.8-1.6-7.5-.7v12.5c2.7-.9 5.3-.7 7.5.7 2.2-1.4 4.8-1.6 7.5-.7V5.8c-2.7-.9-5.3-.7-7.5.7Z" />
      <path d="M12 6.5V19" />
    </>
  ),
  lotus: (
    <>
      <path d="M12 5c2.1 2.7 2.8 5.4 2 8.2-.6 2-1.4 3.2-2 3.8-.6-.6-1.4-1.8-2-3.8-.8-2.8-.1-5.5 2-8.2Z" />
      <path d="M9.6 15.8C6.9 15 5 12.9 4.5 9.8c2.4.4 4.2 1.6 5.2 3.4" />
      <path d="M14.4 15.8c2.7-.8 4.6-2.9 5.1-6-2.4.4-4.2 1.6-5.2 3.4" />
      <path d="M5 18.5h14" />
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
  scale: (
    <>
      <path d="M12 3.5v16.5M7 20h10" />
      <path d="M5 7h14" />
      <path d="M5 7 3 12.5a2.6 2.6 0 0 0 4 0L5 7Z" />
      <path d="M19 7l-2 5.5a2.6 2.6 0 0 0 4 0L19 7Z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11.2v4.3" />
      <circle cx="12" cy="8.2" r="0.7" fill="currentColor" stroke="none" />
    </>
  ),
  externalLink: (
    <>
      <path d="M14 4.5h5.5V10" />
      <path d="M10.5 13.5 19.5 4.5" />
      <path d="M18.5 13.5v4.3a1.7 1.7 0 0 1-1.7 1.7H6.2a1.7 1.7 0 0 1-1.7-1.7V7.2a1.7 1.7 0 0 1 1.7-1.7h4.3" />
    </>
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

