/**
 * Stable device fingerprint for session integrity (hashed before send — raw signals not stored).
 */
export async function getDeviceFingerprint() {
  const parts = [
    navigator.userAgent || '',
    navigator.language || '',
    Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    String(screen.width),
    String(screen.height),
    String(screen.colorDepth),
    String(navigator.hardwareConcurrency || 0),
  ].join('|');

  const data = new TextEncoder().encode(parts);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
