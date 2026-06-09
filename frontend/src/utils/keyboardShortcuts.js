/** @returns {boolean} True when the user is typing in a field — skip global shortcuts. */
export function isTypingTarget(target) {
  if (!target || typeof target !== 'object') return false;
  const el = target;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  return Boolean(el.closest?.('[contenteditable="true"]'));
}

export function isMacPlatform() {
  return /Mac|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function commandKeyLabel() {
  return isMacPlatform() ? '⌘' : 'Ctrl';
}

export const GO_NAV_TIMEOUT_MS = 1200;

export const DASHBOARD_GO_ROUTES = {
  d: '/dashboard',
  v: '/dashboard/vmcluster',
  s: '/dashboard/storage',
  c: '/dashboard/costs',
  y: '/dashboard/security',
};

export const ADMIN_GO_ROUTES = {
  d: '/admin',
  u: '/admin/users',
  a: '/admin/analytics',
  s: '/admin/system',
};
