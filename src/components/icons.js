export const iconPaths = {
  leaf: '<path d="M20.4 3.6C12.8 3.3 6.8 5.8 4.3 10.3c-1.2 2.2-.7 4.8 1.7 5.8 2.6 1 5.7-.2 7.5-2.3 3.2-3.6 4.1-7.7 6.9-10.2Z"/><path d="M3.5 20.4c2.1-5.1 6.1-8.6 11-10.7"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
  heart: '<path d="M20.8 8.9c0 5.4-8.8 11-8.8 11s-8.8-5.6-8.8-11A4.8 4.8 0 0 1 12 6.3a4.8 4.8 0 0 1 8.8 2.6Z"/>',
  mic: '<rect x="8.3" y="3" width="7.4" height="12" rx="3.7"/><path d="M5 11.4v.6a7 7 0 0 0 14 0v-.6M12 19v3M8.5 22h7"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  shield: '<path d="M12 3 19 6v5.2c0 4.8-3 8.4-7 9.8-4-1.4-7-5-7-9.8V6l7-3Z"/><path d="m9.2 12.2 1.8 1.8 3.9-4.1"/>',
  flask: '<path d="M9 3h6M10 3v5.4L4.8 18a2 2 0 0 0 1.7 3h11a2 2 0 0 0 1.7-3L14 8.4V3"/><path d="M7.4 16h9.2"/>',
  medal: '<circle cx="12" cy="14" r="6"/><path d="m8.6 9.7-1.2-6.2L12 5.9l4.6-2.4-1.2 6.2M9.7 14.2l1.5 1.5 3.1-3.1"/>',
  arrow: '<path d="M4 12h15M13 6l6 6-6 6"/>',
  play: '<path d="m9 6 9 6-9 6V6Z"/>',
  sparkles: '<path d="m12 3-1.1 3.9L7 8l3.9 1.1L12 13l1.1-3.9L17 8l-3.9-1.1L12 3ZM19 13l-.7 2.3L16 16l2.3.7L19 19l.7-2.3L22 16l-2.3-.7L19 13ZM5 14l-.7 2.3L2 17l2.3.7L5 20l.7-2.3L8 17l-2.3-.7L5 14Z"/>',
  hand: '<path d="M5.5 12.5V7.6a1.5 1.5 0 0 1 3 0v4.1-7a1.5 1.5 0 0 1 3 0v7-6a1.5 1.5 0 0 1 3 0v6.5-4.1a1.5 1.5 0 0 1 3 0v7.2c0 3.8-2.3 6.7-6.4 6.7h-.8c-3.1 0-4.7-1.7-6.2-3.9L3.2 15a1.7 1.7 0 0 1 2.3-2.5Z"/>',
  phone: '<path d="M7.1 3.2 9.3 7 7.7 9.2a14.4 14.4 0 0 0 7.1 7.1l2.2-1.6 3.8 2.2-1 3.2c-.3.9-1.2 1.5-2.1 1.4C9.6 20.4 3.6 14.4 2.5 6.3c-.1-.9.5-1.8 1.4-2.1l3.2-1Z"/>',
  close: '<path d="M18 6 6 18M6 6l12 12"/>'
};

export const icon = (name, size = 24) => {
  if (!iconPaths[name]) {
    console.warn(`[Miora] Icon "${name}" does not exist; falling back to "arrow".`);
  }
  const common = `width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"`;
  return `<svg ${common}>${iconPaths[name] || iconPaths.arrow}</svg>`;
};
