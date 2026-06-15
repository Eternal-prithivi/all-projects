// =============================================================================
// COMPONENT: OnboardingTour.jsx  (294 lines)
// PURPOSE: 7-step guided first-time user tour using react-joyride v3
//   - Shows welcome modal + tour only ONCE per user (localStorage: zenith_onboarding_complete)
//   - Steps target: sidebar-nav, global-search, cost-card, storage-card, vm-card, quick-actions, help
//   - Uses UNCONTROLLED mode (no stepIndex prop) — required for react-joyride v3
//   - disableBeacon: true on all steps — prevents manual click-to-start requirement
// MOUNTED IN: DashboardLayout.jsx (persists across all dashboard navigation)
// RESTART: SettingsPage.jsx "Restart Tour" button → deletes localStorage key
// DO NOT:
//   - Add stepIndex prop — breaks go()/next() in joyride v3 (uncontrolled mode required)
//   - Import Joyride as default — use named import: { Joyride } from 'react-joyride'
//   - Move out of DashboardLayout — must mount once, not inside individual pages
//   - Add location.pathname to useEffect deps — causes re-trigger on navigation
// =============================================================================
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useMediaQuery, MOBILE_MEDIA_QUERY } from '../hooks/useMediaQuery.js';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/onboarding.css';

/** Build per-user localStorage keys so each account gets its own tour state. */
function tourKeys(username) {
  const suffix = username ? `_${username}` : '';
  return {
    complete: `zenith_onboarding_complete${suffix}`,
    dismissed: `zenith_onboarding_dismissed${suffix}`,
  };
}

/** Session flag — Settings → Restart Tour sets this before navigating to /dashboard. */
const ONBOARDING_RESTART_KEY = 'zenith_onboarding_restart';

/**
 * OnboardingTour — Guided first-time walkthrough using react-joyride v3.
 * 
 * Shows a 7-step tour on the dashboard for first-time users.
 * Tracks completion/dismissal in localStorage so it only shows once.
 * Styled to match Zenith's glassmorphism + gold accent design system.
 * 
 * Uses UNCONTROLLED mode (no stepIndex prop) — joyride manages step
 * progression internally. This is required for v3 compatibility.
 */
function OnboardingTour() {
  const location = useLocation();
  const { user } = useAuth();
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY);
  const [run, setRun] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [joyrideLib, setJoyrideLib] = useState(null);
  const joyrideRef = useRef(null);
  const checkedUsernameRef = useRef(null);
  const pendingRunRef = useRef(false);

  const loadJoyride = useCallback(async () => {
    if (joyrideRef.current) return joyrideRef.current;
    const mod = await import('react-joyride');
    joyrideRef.current = mod;
    setJoyrideLib(mod);
    return mod;
  }, []);

  // Tour steps targeting data-tour attributes and data-type selectors
  const steps = [
    {
      target: '[data-tour="sidebar-nav"]',
      content: (
        <div className="tour-step-content">
          <h3>Navigation Sidebar</h3>
          <p>
            This is your command center. Use the sidebar on desktop, or the bottom tabs and
            <strong> More </strong> menu on mobile. Reach <strong>Storage</strong>,{' '}
            <strong>VM Clusters</strong>, <strong>Security</strong>, <strong>Cost Analysis</strong>,
            and <strong>Billing</strong> from here.
          </p>
        </div>
      ),
      placement: 'right',
      disableBeacon: true,
    },
    {
      target: '[data-tour="header-search"]',
      content: (
        <div className="tour-step-content">
          <h3>Global Search</h3>
          <p>
            Quickly find anything — files, VMs, settings, or pages.
            You can also press <kbd>⌘K</kbd> or <kbd>/</kbd> to open it instantly.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
    },
    {
      target: '[data-tour="card-costs"]',
      content: (
        <div className="tour-step-content">
          <h3>Cost Overview</h3>
          <p>
            Your <strong>30-day multi-cloud spend</strong> and 7-day trend live here.
            Connect AWS, GCP, or Azure in Settings, then hit <strong>Refresh</strong> to pull
            live billing data into this card.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
    },
    {
      target: '[data-tour="card-storage"]',
      content: (
        <div className="tour-step-content">
          <h3>Storage Management</h3>
          <p>
            Track how much of your plan capacity you&apos;re using. Upload files from the
            <strong> Storage </strong> page — our <strong>ML engine</strong> recommends the
            cheapest cloud tier for each file.
          </p>
        </div>
      ),
      placement: 'left',
      disableBeacon: true,
    },
    {
      target: '[data-tour="card-vms"]',
      content: (
        <div className="tour-step-content">
          <h3>VM Cluster Health</h3>
          <p>
            See healthy, warning, and critical VMs at a glance. On the
            <strong> VM Cluster </strong> page, describe your workload in plain English —
            our <strong>NLP classifier</strong> assigns the right cluster for you.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
    },
    {
      target: '[data-tour="quick-actions"]',
      content: (
        <div className="tour-step-content">
          <h3>Quick Actions</h3>
          <p>
            Jump straight to the most common tasks — manage VMs, upload files,
            analyze costs, or check security. No hunting through menus.
          </p>
        </div>
      ),
      placement: 'top',
      disableBeacon: true,
    },
    {
      target: '[data-tour="sidebar-help"]',
      content: (
        <div className="tour-step-content">
          <h3>Help Center</h3>
          <p>
            Got questions? The Help Center has <strong>26 FAQ articles</strong> across
            6 categories — from getting started to advanced security settings.
            You can also reach support from the <strong>Contact</strong> page.
          </p>
          <p className="tour-step-final">
            🎉 You're all set! Explore Zenith at your own pace.
          </p>
        </div>
      ),
      placement: 'right',
      disableBeacon: true,
    },
  ];

  // Show welcome when auth is ready; honour Settings → Restart Tour in the same session.
  useEffect(() => {
    if (!user?.username || location.pathname !== '/dashboard') return undefined;

    const keys = tourKeys(user.username);
    const forceRestart = sessionStorage.getItem(ONBOARDING_RESTART_KEY) === '1';

    if (forceRestart) {
      sessionStorage.removeItem(ONBOARDING_RESTART_KEY);
      setRun(false);
      setMobileTipIndex(0);
      const timer = setTimeout(() => setShowWelcome(true), 400);
      return () => clearTimeout(timer);
    }

    if (checkedUsernameRef.current === user.username) return undefined;
    checkedUsernameRef.current = user.username;

    const isComplete = localStorage.getItem(keys.complete);
    const isDismissed = localStorage.getItem(keys.dismissed);
    if (isComplete || isDismissed) return undefined;

    const timer = setTimeout(() => setShowWelcome(true), 1500);
    return () => clearTimeout(timer);
  }, [user?.username, location.pathname]);

  const [mobileTipIndex, setMobileTipIndex] = useState(0);

  const mobileTips = [
    {
      title: 'Welcome to Zenith',
      body: 'This short orientation replaces the desktop tour. Zenith unifies AWS, GCP, and Azure costs, storage, and VMs in one place.',
    },
    {
      title: 'Bottom navigation',
      body: 'Use the tabs at the bottom for Overview, Storage, Infrastructure, and Cost. Tap More for Security, Billing, Settings, and Help.',
    },
    {
      title: 'Your first tasks',
      body: 'Connect a cloud in Settings, upload a file in Storage, or open Cost Analysis. The Getting Started checklist on the dashboard tracks your progress.',
    },
    {
      title: 'Need help?',
      body: 'Tap More → Help for FAQs, or open Support from the profile menu. You can replay these tips from Settings → Restart Tour.',
    },
  ];

  const completeMobileTips = useCallback(() => {
    const keys = tourKeys(user?.username);
    setShowWelcome(false);
    localStorage.setItem(keys.complete, 'true');
  }, [user?.username]);

  const dismissMobileTips = useCallback(() => {
    const keys = tourKeys(user?.username);
    setShowWelcome(false);
    localStorage.setItem(keys.dismissed, 'true');
  }, [user?.username]);

  const startTour = useCallback(async () => {
    setShowWelcome(false);
    pendingRunRef.current = true;
    await loadJoyride();
  }, [loadJoyride]);

  useEffect(() => {
    if (!joyrideLib || !pendingRunRef.current || isMobile) return undefined;
    pendingRunRef.current = false;
    const outer = requestAnimationFrame(() => {
      requestAnimationFrame(() => setRun(true));
    });
    return () => cancelAnimationFrame(outer);
  }, [joyrideLib, isMobile]);

  const dismissTour = useCallback(() => {
    const keys = tourKeys(user?.username);
    setShowWelcome(false);
    localStorage.setItem(keys.dismissed, 'true');
  }, [user?.username]);

  const handleJoyrideCallback = useCallback((data) => {
    const { STATUS, ACTIONS } = joyrideRef.current || {};
    if (!STATUS || !ACTIONS) return;

    const keys = tourKeys(user?.username);
    const { status, action } = data;

    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRun(false);
      localStorage.setItem(keys.complete, 'true');
    }

    if (action === ACTIONS.CLOSE) {
      setRun(false);
      localStorage.setItem(keys.dismissed, 'true');
    }
  }, [user?.username]);

  // Custom tooltip component matching Zenith design
  const ZenithTooltip = ({
    continuous,
    index,
    step,
    backProps,
    closeProps,
    primaryProps,
    tooltipProps,
    size,
    isLastStep,
    skipProps,
  }) => (
    <div className="zenith-tour-tooltip" {...tooltipProps}>
      <button className="tour-close-btn" {...closeProps} aria-label="Close tour">
        ✕
      </button>
      <div className="tour-tooltip-content">
        {step.content}
      </div>
      <div className="tour-tooltip-footer">
        <div className="tour-progress">
          {Array.from({ length: size }, (_, i) => (
            <span
              key={i}
              className={`tour-dot ${i === index ? 'active' : ''} ${i < index ? 'completed' : ''}`}
            />
          ))}
        </div>
        <div className="tour-actions">
          {index > 0 && (
            <button className="tour-btn tour-btn-back" {...backProps}>
              Back
            </button>
          )}
          {!isLastStep && index === 0 && (
            <button className="tour-btn tour-btn-skip" {...skipProps}>
              Skip Tour
            </button>
          )}
          {continuous && (
            <button className="tour-btn tour-btn-next" {...primaryProps}>
              {isLastStep ? 'Finish Tour' : 'Next'}
            </button>
          )}
        </div>
      </div>
      <div className="tour-step-counter">
        {index + 1} of {size}
      </div>
    </div>
  );

  return (
    <>
      {/* Welcome modal — appears before tour starts */}
      {showWelcome && isMobile && (
        <div className="tour-welcome-overlay mobile-tips-overlay" onClick={dismissMobileTips}>
          <div className="tour-welcome-card mobile-tips-card" onClick={(e) => e.stopPropagation()}>
            <div className="tour-welcome-glow" />
            <p className="mobile-tips-kicker">Quick orientation</p>
            <h2>{mobileTips[mobileTipIndex].title}</h2>
            <p>{mobileTips[mobileTipIndex].body}</p>
            <div className="mobile-tips-dots" aria-hidden="true">
              {mobileTips.map((_, i) => (
                <span key={i} className={`tour-dot ${i === mobileTipIndex ? 'active' : ''}`} />
              ))}
            </div>
            <div className="tour-welcome-actions">
              {mobileTipIndex < mobileTips.length - 1 ? (
                <button
                  type="button"
                  className="tour-btn tour-btn-next"
                  onClick={() => setMobileTipIndex((i) => i + 1)}
                >
                  Next
                </button>
              ) : (
                <button type="button" className="tour-btn tour-btn-next" onClick={completeMobileTips}>
                  Got it
                </button>
              )}
              <button type="button" className="tour-btn tour-btn-skip" onClick={dismissMobileTips}>
                Skip
              </button>
            </div>
          </div>
        </div>
      )}

      {showWelcome && !isMobile && (
        <div className="tour-welcome-overlay" onClick={dismissTour}>
          <div className="tour-welcome-card" onClick={(e) => e.stopPropagation()}>
            <div className="tour-welcome-glow" />
            <div className="tour-welcome-icon">
              <span>Z</span>
            </div>
            <h2>Welcome to Zenith</h2>
            <p>
              Zenith brings your <strong>AWS, GCP, and Azure</strong> costs, storage, and VMs
              into one dashboard.
            </p>
            <p className="tour-welcome-detail">
              This 7-step tour (~2 min) shows where to connect clouds, read your live widgets,
              jump to common tasks, and find help. You&apos;ll also see a <strong>Getting Started</strong>{' '}
              checklist below the tour for hands-on setup.
            </p>
            <div className="tour-welcome-actions">
              <button type="button" className="tour-btn tour-btn-next" onClick={startTour}>
                Start Tour
              </button>
              <button type="button" className="tour-btn tour-btn-skip" onClick={dismissTour}>
                Skip — I&apos;ll use the checklist
              </button>
            </div>
            <p className="tour-welcome-hint">
              Replay anytime from Settings → Preferences → Restart Tour
            </p>
          </div>
        </div>
      )}

      {/* Joyride tour — desktop/tablet only; library loaded on demand */}
      {!isMobile && joyrideLib && (
      <joyrideLib.Joyride
        steps={steps}
        run={run}
        continuous
        showSkipButton
        showProgress
        disableOverlayClose={false}
        disableScrolling={false}
        spotlightClicks={false}
        callback={handleJoyrideCallback}
        tooltipComponent={ZenithTooltip}
        floaterProps={{
          disableAnimation: false,
        }}
        styles={{
          options: {
            arrowColor: 'rgba(15, 15, 25, 0.95)',
            overlayColor: 'rgba(0, 0, 0, 0.75)',
            zIndex: 10000,
          },
          spotlight: {
            borderRadius: '14px',
          },
        }}
      />
      )}
    </>
  );
}

export default OnboardingTour;
