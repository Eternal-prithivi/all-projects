import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('apiBase', () => {
  beforeEach(() => {
    vi.stubEnv('MODE', 'production');
    vi.stubEnv('VITE_API_URL', 'https://zenith-backend-707i.onrender.com');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    delete global.window;
  });

  it('uses same origin on rajverse.me to avoid ad-blocked Render host (HTTP only)', async () => {
    global.window = {
      location: {
        origin: 'https://rajverse.me',
        hostname: 'rajverse.me',
      },
    };
    const { getApiRoot, getApiBaseUrl, getWsRoot } = await import('./apiBase.js');
    expect(getApiRoot()).toBe('https://rajverse.me');
    expect(getApiBaseUrl()).toBe('https://rajverse.me/api');
    // WebSockets must bypass Vercel (no WS proxy support) — go directly to Render.
    expect(getWsRoot()).toBe('wss://zenith-backend-707i.onrender.com');
  });

  it('falls back to Render when not on rajverse.me', async () => {
    global.window = {
      location: {
        origin: 'https://zenith-frontend.vercel.app',
        hostname: 'zenith-frontend.vercel.app',
      },
    };
    const { getApiRoot } = await import('./apiBase.js');
    expect(getApiRoot()).toBe('https://zenith-backend-707i.onrender.com');
  });
});
