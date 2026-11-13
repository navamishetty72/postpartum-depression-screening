export const AmbientBackdrop = () => `
  <div class="page-ambient" aria-hidden="true">
    <div class="ambient-wash ambient-wash-1"></div>
    <div class="ambient-wash ambient-wash-2"></div>
    <div class="ambient-wash ambient-wash-3"></div>
    <div class="ambient-wash ambient-wash-4"></div>
    <div class="ambient-dots"></div>
    <svg class="ambient-petal ambient-petal-left" viewBox="0 0 320 420" fill="none">
      <defs>
        <linearGradient id="petalLeftGrad" x1="0" y1="0" x2="320" y2="420" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#f7d5db" stop-opacity="0.45" />
          <stop offset="100%" stop-color="#fdf8f4" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path d="M-20 40C95 28 215 95 245 205C272 302 205 395 85 405C15 410 -30 355 -35 265C-40 175 -55 44 -20 40Z" fill="url(#petalLeftGrad)" />
    </svg>
    <svg class="ambient-petal ambient-petal-right" viewBox="0 0 340 440" fill="none">
      <defs>
        <linearGradient id="petalRightGrad" x1="340" y1="0" x2="0" y2="440" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#f6cfd7" stop-opacity="0.42" />
          <stop offset="100%" stop-color="#fdf8f4" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path d="M350 60C220 38 110 118 85 232C62 335 135 415 245 422C325 427 370 365 372 272C374 185 385 66 350 60Z" fill="url(#petalRightGrad)" />
    </svg>
  </div>
`;

