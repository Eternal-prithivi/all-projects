/**
 * Detect client OS for download CTAs.
 * @returns {'mac' | 'win' | 'linux' | 'unknown'}
 */
export function detectPlatform() {
  if (typeof navigator === 'undefined') return 'unknown';

  const ua = navigator.userAgent || '';
  const platform = navigator.userAgentData?.platform || navigator.platform || '';

  if (/Mac|macOS|Macintosh/i.test(platform) || /Mac OS X/i.test(ua)) {
    return 'mac';
  }
  if (/Win/i.test(platform) || /Windows/i.test(ua)) {
    return 'win';
  }
  if (/Linux/i.test(platform) || /Linux/i.test(ua)) {
    return 'linux';
  }
  return 'unknown';
}

export const PLATFORM_LABELS = {
  mac: 'macOS',
  win: 'Windows',
  linux: 'Linux',
  unknown: 'your platform',
};
