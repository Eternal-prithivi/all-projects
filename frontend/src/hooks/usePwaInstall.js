// =============================================================================
// HOOK: usePwaInstall.js
// PURPOSE: Captures the browser's beforeinstallprompt event so we can show a
//          custom "Add to Home Screen" banner at the right time.
//
// Usage:
//   const { canInstall, isInstalled, triggerInstall, dismissInstall } = usePwaInstall();
//
// Returns:
//   canInstall      – true when the browser has a pending install prompt
//   isInstalled     – true when the app is already running as a standalone PWA
//   triggerInstall  – call this to show the native install dialog
//   dismissInstall  – call this to hide our custom banner (persisted for 30 days)
// =============================================================================

import { useCallback, useEffect, useState } from 'react';

const DISMISS_KEY = 'zenith-pwa-banner-dismissed';
const DISMISS_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

function isAlreadyInstalled() {
  // Standalone display mode (Android + iOS Safari after "Add to Home Screen")
  if (window.matchMedia('(display-mode: standalone)').matches) return true;
  // iOS Safari legacy property
  if (window.navigator.standalone === true) return true;
  return false;
}

function wasBannerDismissed() {
  try {
    const raw = sessionStorage.getItem(DISMISS_KEY) || localStorage.getItem(DISMISS_KEY);
    if (!raw) return false;
    const { until } = JSON.parse(raw);
    return Date.now() < until;
  } catch {
    return false;
  }
}

export function usePwaInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(isAlreadyInstalled);
  const [dismissed, setDismissed] = useState(wasBannerDismissed);

  // Capture beforeinstallprompt event (Chrome, Edge, Samsung Internet)
  useEffect(() => {
    const handler = (e) => {
      e.preventDefault(); // Stop the mini-infobar from appearing
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  // Detect when the app is installed via the appinstalled event
  useEffect(() => {
    const handler = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
    };
    window.addEventListener('appinstalled', handler);
    return () => window.removeEventListener('appinstalled', handler);
  }, []);

  // Watch for display-mode change (covers iOS/Android after install)
  useEffect(() => {
    const mq = window.matchMedia('(display-mode: standalone)');
    const handler = (e) => { if (e.matches) setIsInstalled(true); };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const triggerInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setIsInstalled(true);
    }
    setDeferredPrompt(null);
  }, [deferredPrompt]);

  const dismissInstall = useCallback(() => {
    setDismissed(true);
    try {
      const payload = JSON.stringify({ until: Date.now() + DISMISS_TTL_MS });
      localStorage.setItem(DISMISS_KEY, payload);
    } catch {
      // ignore storage errors
    }
  }, []);

  return {
    // Show the banner when: browser supports install, app isn't already installed, user hasn't dismissed
    canInstall: !!deferredPrompt && !isInstalled && !dismissed,
    isInstalled,
    triggerInstall,
    dismissInstall,
  };
}
