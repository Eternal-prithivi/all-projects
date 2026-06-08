/** Browser event bus for support WebSocket payloads (one WS connection per layout). */

export const SUPPORT_WS_EVENT = 'zenith:support-ws';

export function dispatchSupportWsEvent(payload) {
  if (!payload || typeof payload !== 'object') return;
  window.dispatchEvent(new CustomEvent(SUPPORT_WS_EVENT, { detail: payload }));
}

export function subscribeSupportWsEvent(handler) {
  const listener = (e) => handler(e.detail);
  window.addEventListener(SUPPORT_WS_EVENT, listener);
  return () => window.removeEventListener(SUPPORT_WS_EVENT, listener);
}

export function matchesSupportTarget(payload, { referenceCode, ticketId } = {}) {
  if (!payload) return false;
  if (referenceCode && payload.reference_code === referenceCode) return true;
  if (ticketId && payload.ticket_id === ticketId) return true;
  return false;
}
