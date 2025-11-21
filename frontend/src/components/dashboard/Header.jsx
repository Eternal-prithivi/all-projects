import React from 'react';
import ProfileDropdown from '../ProfileDropdown.jsx';
import NotificationBell from '../NotificationBell.jsx';

function Header({ user, onShowShortcuts }) {
  return (
    <header className="dashboard-header">
      <h1 className="header-title">Welcome, {user ? user.username : 'User'}!</h1>
      <div className="header-actions">
        <button 
          className="header-help-btn" 
          title="Press ? for keyboard shortcuts"
          onClick={() => {
            // Dispatch custom event to trigger shortcuts modal
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
