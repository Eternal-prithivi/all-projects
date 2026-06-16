import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  canAttemptSessionRefresh,
  clearAuthTokens,
  getStoredAccessToken,
  getStoredRefreshToken,
  shouldProbeSessionOnLoad,
  storeAuthTokens,
} from './authTokens.js';

describe('authTokens', () => {
  afterEach(() => {
    clearAuthTokens();
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it('stores and reads bearer tokens', () => {
    storeAuthTokens({ access_token: 'access', refresh_token: 'refresh' });
    expect(getStoredAccessToken()).toBe('access');
    expect(getStoredRefreshToken()).toBe('refresh');
  });

  it('clears stored tokens', () => {
    storeAuthTokens({ access_token: 'access', refresh_token: 'refresh' });
    clearAuthTokens();
    expect(getStoredAccessToken()).toBeNull();
    expect(getStoredRefreshToken()).toBeNull();
  });

  it('does not probe session when anonymous on cross-origin API', () => {
    vi.stubGlobal('window', { location: { hostname: 'rajverse.me' } });
    expect(shouldProbeSessionOnLoad()).toBe(false);
    expect(canAttemptSessionRefresh()).toBe(false);
  });

  it('clears orphaned cached user without probing API', () => {
    sessionStorage.setItem('cachedUser', JSON.stringify({ username: 'stale' }));
    vi.stubGlobal('window', { location: { hostname: 'rajverse.me' } });
    expect(shouldProbeSessionOnLoad()).toBe(false);
    expect(sessionStorage.getItem('cachedUser')).toBeNull();
    expect(canAttemptSessionRefresh()).toBe(false);
  });

  it('probes session when bearer token exists', () => {
    storeAuthTokens({ access_token: 'access' });
    expect(shouldProbeSessionOnLoad()).toBe(true);
  });
});
