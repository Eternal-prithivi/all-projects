// =============================================================================
// COMPONENT: Header.jsx  (58 lines)
// PURPOSE: Top bar for all dashboard pages
//   - Left: sidebar toggle button + page breadcrumb
//   - Center: Global Search trigger (⌘K shortcut, opens GlobalSearch modal)
//   - Right: NotificationBell + ProfileDropdown (logout, profile link)
//   - data-tour="global-search" — onboarding tour step 2 targets the search button
// USED BY: DashboardLayout.jsx
// DO NOT:
//   - Remove data-tour="global-search" attribute — breaks onboarding tour step 2
//   - Add page-specific content here — Header is shared across all dashboard pages
//   - Move NotificationBell logic into Header — it lives in NotificationBell.jsx component
// =============================================================================
import React from 'react';
import ProfileDropdown from '../ProfileDropdown.jsx';
import NotificationBell from '../NotificationBell.jsx';
import { useTheme } from '../../context/ThemeContext.jsx';

function Header() {
  const { effectiveTheme, toggleTheme } = useTheme();
  return (
    <header className="dashboard-header">
      {/* Left: Brand text */}
      <div className="header-brand">
        <span className="header-brand-text">Zenith</span>
        <span className="header-brand-badge">Cloud</span>
      </div>

      {/* Center: Search trigger */}
      <button 
        className="header-search-trigger"
        type="button"
        aria-label="Open global search"
        data-tour="header-search"
        onClick={() => {
          // Trigger the existing GlobalSearch modal
          document.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'k',
            metaKey: true,
            bubbles: true,
          }));
        }}
        title="Search (⌘K)"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="7" cy="7" r="5" />
          <line x1="11" y1="11" x2="14" y2="14" />
        </svg>
        <span>Search...</span>
        <kbd>⌘K</kbd>
      </button>

      {/* Right: Actions */}
      <div className="header-actions">
        <button
          className="header-theme-btn"
          type="button"
          aria-label={effectiveTheme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          title={effectiveTheme === 'light' ? 'Dark mode' : 'Light mode'}
          onClick={toggleTheme}
        >
          {effectiveTheme === 'light' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          )}
        </button>
        <button 
          className="header-help-btn" 
          type="button"
          aria-label="Open keyboard shortcuts"
          title="Press ? for keyboard shortcuts"
          onClick={() => {
            window.dispatchEvent(new CustomEvent('show-shortcuts'));
          }}
        >
          ?
        </button>
        <NotificationBell />
        <ProfileDropdown />
      </div>
    </header>
  );
}

export default Header;
