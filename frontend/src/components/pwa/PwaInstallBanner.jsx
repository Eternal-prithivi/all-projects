// =============================================================================
// COMPONENT: PwaInstallBanner.jsx
// PURPOSE: A premium "Add to Home Screen" install prompt banner.
//          Appears at the bottom of the screen after a short delay.
//          Dismissed state is persisted in localStorage for 30 days.
//
// Used in: App.jsx (rendered once globally)
// Hook:    usePwaInstall
// =============================================================================

import React, { useEffect, useState } from 'react';
import { usePwaInstall } from '../../hooks/usePwaInstall.js';
import './PwaInstallBanner.css';

// Delay before showing the banner (gives the user time to engage first)
const SHOW_DELAY_MS = 8000;

export default function PwaInstallBanner() {
  const { canInstall, isInstalled, triggerInstall, dismissInstall } = usePwaInstall();
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);

  // Show after a short delay so it doesn't interrupt the first impression
  useEffect(() => {
    if (!canInstall) return undefined;
    const timer = setTimeout(() => setVisible(true), SHOW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [canInstall]);

  // Hide immediately if installed mid-session
  useEffect(() => {
    if (isInstalled && visible) handleDismiss();
  }, [isInstalled]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleDismiss() {
    setExiting(true);
    setTimeout(() => {
      setVisible(false);
      setExiting(false);
      dismissInstall();
    }, 320);
  }

  async function handleInstall() {
    await triggerInstall();
    handleDismiss();
  }

  if (!visible) return null;

  return (
    <div
      className={`pwa-banner${exiting ? ' pwa-banner--exit' : ''}`}
      role="dialog"
      aria-modal="false"
      aria-label="Install Zenith as an app"
    >
      <div className="pwa-banner__glow" aria-hidden="true" />

      <div className="pwa-banner__icon-wrap" aria-hidden="true">
        <img src="/icon-192.png" alt="" className="pwa-banner__icon" width={40} height={40} />
      </div>

      <div className="pwa-banner__body">
        <p className="pwa-banner__title">Install Zenith</p>
        <p className="pwa-banner__desc">
          Add to your home screen — opens like a native app, no browser bar.
        </p>
      </div>

      <div className="pwa-banner__actions">
        <button
          id="pwa-install-btn"
          type="button"
          className="pwa-banner__install"
          onClick={handleInstall}
        >
          Install
        </button>
        <button
          id="pwa-dismiss-btn"
          type="button"
          className="pwa-banner__dismiss"
          aria-label="Dismiss install prompt"
          onClick={handleDismiss}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
