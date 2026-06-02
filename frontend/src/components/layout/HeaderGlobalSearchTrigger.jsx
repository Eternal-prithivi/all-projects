import React from 'react';

function openGlobalSearch() {
  document.dispatchEvent(
    new KeyboardEvent('keydown', {
      key: 'k',
      metaKey: true,
      bubbles: true,
    })
  );
}

/**
 * Global search bar trigger (⌘K). Used in dashboard header center and admin header center.
 */
export default function HeaderGlobalSearchTrigger({
  className = '',
  placeholder = 'Search...',
  showKbd = true,
}) {
  return (
    <button
      className={['header-search-trigger', className].filter(Boolean).join(' ')}
      type="button"
      aria-label="Open global search"
      data-tour="header-search"
      onClick={openGlobalSearch}
      title="Search (⌘K)"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden>
        <circle cx="7" cy="7" r="5" />
        <line x1="11" y1="11" x2="14" y2="14" />
      </svg>
      <span className="header-search-trigger-placeholder">{placeholder}</span>
      {showKbd ? <kbd>⌘K</kbd> : null}
    </button>
  );
}
