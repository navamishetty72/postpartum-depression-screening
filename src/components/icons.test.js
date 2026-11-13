import { describe, it, expect, vi } from 'vitest';
import { icon, iconPaths } from './icons.js';

describe('icon helper', () => {
  it('renders known icon SVG with custom size and aria-hidden', () => {
    const svg = icon('leaf', 32);
    expect(svg).toContain('width="32"');
    expect(svg).toContain('height="32"');
    expect(svg).toContain('aria-hidden="true"');
    expect(svg).toContain('<svg');
  });

  it('warns when an unknown icon is requested and falls back to arrow (C3)', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const svg = icon('non_existent_icon');
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('[Miora] Icon "non_existent_icon" does not exist')
    );
    expect(svg).toContain(iconPaths.arrow);
    warnSpy.mockRestore();
  });
});

