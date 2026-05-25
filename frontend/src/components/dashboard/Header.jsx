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

function Header() {
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
