import React from 'react';
import HeaderToolbarActions from '../layout/HeaderToolbarActions.jsx';

function Header() {
  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <span className="header-brand-text">Zenith</span>
        <span className="header-brand-badge">Cloud</span>
      </div>

      <button
        className="header-search-trigger"
        type="button"
        aria-label="Open global search"
        data-tour="header-search"
        onClick={() => {
          document.dispatchEvent(
            new KeyboardEvent('keydown', {
              key: 'k',
              metaKey: true,
              bubbles: true,
            })
          );
        }}
        title="Search (⌘K)"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden>
          <circle cx="7" cy="7" r="5" />
          <line x1="11" y1="11" x2="14" y2="14" />
        </svg>
        <span>Search...</span>
        <kbd>⌘K</kbd>
      </button>

      <HeaderToolbarActions
        notificationViewAllPath="/dashboard/notifications"
        showSearchTrigger={false}
      />
    </header>
  );
}

export default Header;
