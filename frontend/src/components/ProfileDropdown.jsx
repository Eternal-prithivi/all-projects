import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FaLock } from 'react-icons/fa';
import { useAuth } from '../context/AuthContext';
import { usePlanEntitlementsContext } from '../context/PlanEntitlementsContext.jsx';
import { PATHS } from '../data/productFacts.js';
import '../styles/profile-dropdown.css';

const ProfileDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();
  const { planName, isNavLocked, openUpgradeDrawer } = usePlanEntitlementsContext();
  const navigate = useNavigate();
  const location = useLocation();
  const dropdownRef = useRef(null);
  const inAdminArea = location.pathname.startsWith('/admin');
  const isAdmin = user?.role === 'admin';
  const settingsPath = inAdminArea ? '/admin/settings' : PATHS.settings;
  const teamLocked = isNavLocked('team_seat_billing');

  const displayName = user?.full_name?.trim() || user?.username || 'User';
  const planLabel = planName ? `${planName} plan` : 'Free plan';

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const closeMenu = () => setIsOpen(false);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const navigateTo = (path) => {
    closeMenu();
    navigate(path);
  };

  const handleTeamClick = () => {
    if (teamLocked) {
      closeMenu();
      openUpgradeDrawer('team_seat_billing');
      return;
    }
    navigateTo(PATHS.team);
  };

  const handleShortcuts = () => {
    closeMenu();
    window.dispatchEvent(new CustomEvent('show-shortcuts'));
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.substring(0, 2).toUpperCase();
  };

  const renderAvatar = () => {
    if (user?.profile_picture) {
      return (
        <img
          src={user.profile_picture}
          alt=""
          className="profile-avatar-img"
        />
      );
    }
    return getInitials(displayName);
  };

  const MenuItem = ({ onClick, children, className = '', icon }) => (
    <button className={`profile-menu-item ${className}`.trim()} type="button" onClick={onClick}>
      {icon}
      {children}
    </button>
  );

  const SectionLabel = ({ children }) => (
    <div className="profile-menu-section-label" role="presentation">{children}</div>
  );

  return (
    <div className="profile-dropdown" ref={dropdownRef}>
      <button
        className="profile-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <div className="profile-avatar">
          {renderAvatar()}
        </div>
        <span className="profile-name">{displayName}</span>
        <svg
          className={`dropdown-arrow ${isOpen ? 'open' : ''}`}
          width="12"
          height="8"
          viewBox="0 0 12 8"
          aria-hidden
        >
          <path d="M1 1L6 6L11 1" stroke="currentColor" strokeWidth="2" fill="none" />
        </svg>
      </button>

      {isOpen && (
        <div className="profile-menu" role="menu">
          <div className="profile-menu-header">
            <div className="profile-menu-avatar">
              {renderAvatar()}
            </div>
            <div className="profile-menu-info">
              <div className="profile-menu-name">{displayName}</div>
              {user?.full_name && user?.username && (
                <div className="profile-menu-username">@{user.username}</div>
              )}
              <div className="profile-menu-email">{user?.email || 'user@example.com'}</div>
              <span className={`profile-menu-plan-badge ${planName?.toLowerCase() === 'free' || !planName ? 'profile-menu-plan-badge--free' : ''}`}>
                {planLabel}
              </span>
            </div>
          </div>

          {isAdmin && inAdminArea && (
            <>
              <MenuItem
                onClick={() => navigateTo(PATHS.dashboard)}
                icon={(
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                    <path d="M8 1l7 6v8H1V7l7-6zm0 1.5L2 8v6h12V8L8 2.5z" />
                  </svg>
                )}
              >
                User dashboard
              </MenuItem>
              <div className="profile-menu-divider" />
            </>
          )}

          {isAdmin && !inAdminArea && (
            <>
              <MenuItem
                onClick={() => navigateTo('/admin')}
                icon={(
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                    <path d="M2 2h5l2 3h5v8H2V2zm2 2v2h2V4H4zm8 8H6V9h6v3z" />
                  </svg>
                )}
              >
                Admin portal
              </MenuItem>
              <div className="profile-menu-divider" />
            </>
          )}

          <SectionLabel>Account</SectionLabel>

          <MenuItem
            onClick={() => navigateTo(PATHS.profile)}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm2 2H6c-2.2 0-4 1.8-4 4v1h12v-1c0-2.2-1.8-4-4-4z" />
              </svg>
            )}
          >
            Profile
          </MenuItem>

          <MenuItem
            onClick={() => navigateTo(PATHS.securitySettings)}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 1L2 4v5c0 3.5 2.5 6.5 6 7 3.5-.5 6-3.5 6-7V4l-6-3zm0 2.2L12 5v4c0 2.5-1.8 4.8-4 5.2-2.2-.4-4-2.7-4-5.2V5l4-1.8z" />
              </svg>
            )}
          >
            Security
          </MenuItem>

          <MenuItem
            onClick={() => navigateTo(settingsPath)}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 12.5A5.5 5.5 0 1113.5 8 5.51 5.51 0 018 13.5zM8 4a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            )}
          >
            Settings
          </MenuItem>

          <div className="profile-menu-divider" />
          <SectionLabel>Workspace</SectionLabel>

          <MenuItem
            onClick={() => navigateTo(PATHS.billing)}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v1h14V4a1 1 0 0 0-1-1H2zm13 4H1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7z" />
              </svg>
            )}
          >
            Billing
          </MenuItem>

          <button
            className={`profile-menu-item ${teamLocked ? 'profile-menu-item--locked' : ''}`}
            type="button"
            onClick={handleTeamClick}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
              <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4 1 1 1 1-1-1-4-5-4-5-3-5-4-1-1-1-1 1 1 4 5 4 5 3 5 4 1 1 1 1-1z" />
              <path d="M4 4a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm7 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0z" transform="translate(-1 0)" />
            </svg>
            Team
            {teamLocked && <FaLock className="profile-menu-lock" aria-hidden />}
          </button>

          <div className="profile-menu-divider" />
          <SectionLabel>Help</SectionLabel>

          <MenuItem
            onClick={() => navigateTo(PATHS.help)}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z" />
                <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z" />
              </svg>
            )}
          >
            Help &amp; support
          </MenuItem>

          <MenuItem
            onClick={handleShortcuts}
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M2 3h12v2H2V3zm0 4h3v2H2V7zm0 4h3v2H2v-2zm5-4h7v2H7V7zm0 4h7v2H7v-2z" />
              </svg>
            )}
          >
            Keyboard shortcuts
          </MenuItem>

          <div className="profile-menu-divider" />

          <MenuItem
            onClick={handleLogout}
            className="danger"
            icon={(
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M6 2H4v12h2V2zm6 0h-2v12h2V2zM8 8l4-3v6l-4-3z" />
              </svg>
            )}
          >
            Logout
          </MenuItem>
        </div>
      )}
    </div>
  );
};

export default ProfileDropdown;
