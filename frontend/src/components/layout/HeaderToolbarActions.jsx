import React from 'react';
import { useTheme } from '../../context/ThemeContext.jsx';
import NotificationBell from '../NotificationBell.jsx';
import ProfileDropdown from '../ProfileDropdown.jsx';

/**
 * Shared header actions (dashboard + admin): theme, search, shortcuts, notifications, profile.
 */
export default function HeaderToolbarActions({
  notificationViewAllPath = '/dashboard/notifications',
  showSearchTrigger = true,
  className = 'header-actions',
}) {
  const { effectiveTheme, toggleTheme } = useTheme();

  const openGlobalSearch = () => {
    document.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
      })
    );
  };

  return (
    <div className={className}>
      {showSearchTrigger && (
        <button
          className="header-search-trigger header-search-trigger--compact"
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
          <span className="header-search-trigger-label">Search</span>
          <kbd>⌘K</kbd>
        </button>
      )}

      <button
        className="header-theme-btn"
        type="button"
        aria-label={effectiveTheme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        title={effectiveTheme === 'light' ? 'Dark mode' : 'Light mode'}
        onClick={toggleTheme}
      >
        {effectiveTheme === 'light' ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
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
        onClick={() => window.dispatchEvent(new CustomEvent('show-shortcuts'))}
      >
        ?
      </button>

      <NotificationBell viewAllPath={notificationViewAllPath} />
      <ProfileDropdown />
    </div>
  );
}
