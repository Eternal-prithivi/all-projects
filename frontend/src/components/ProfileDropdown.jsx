import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/profile-dropdown.css';

const ProfileDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <div className="profile-dropdown" ref={dropdownRef}>
      <button 
        className="profile-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
      >
        <div className="profile-avatar">
          {getInitials(user?.username || 'User')}
        </div>
        <span className="profile-name">{user?.username || 'User'}</span>
        <svg 
          className={`dropdown-arrow ${isOpen ? 'open' : ''}`}
          width="12" 
          height="8" 
          viewBox="0 0 12 8"
        >
          <path d="M1 1L6 6L11 1" stroke="currentColor" strokeWidth="2" fill="none"/>
        </svg>
      </button>

      {isOpen && (
        <div className="profile-menu">
          <div className="profile-menu-header">
            <div className="profile-menu-avatar">
              {getInitials(user?.username || 'User')}
            </div>
            <div className="profile-menu-info">
              <div className="profile-menu-name">{user?.username || 'User'}</div>
              <div className="profile-menu-email">{user?.email || 'user@example.com'}</div>
            </div>
          </div>

          <div className="profile-menu-divider"></div>

          <button className="profile-menu-item" onClick={() => {
            setIsOpen(false);
            navigate('/dashboard/profile');
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm2 2H6c-2.2 0-4 1.8-4 4v1h12v-1c0-2.2-1.8-4-4-4z"/>
            </svg>
            Profile
          </button>

          <button className="profile-menu-item" onClick={() => {
            setIsOpen(false);
            navigate('/dashboard/settings');
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 12.5A5.5 5.5 0 1113.5 8 5.51 5.51 0 018 13.5zM8 4a4 4 0 100 8 4 4 0 000-8z"/>
            </svg>
            Settings
          </button>

          <button className="profile-menu-item" onClick={() => {
            setIsOpen(false);
            navigate('/dashboard/security-settings');
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1L2 4v5c0 3.5 2.5 6.5 6 7 3.5-.5 6-3.5 6-7V4l-6-3zm0 2.2L12 5v4c0 2.5-1.8 4.8-4 5.2-2.2-.4-4-2.7-4-5.2V5l4-1.8z"/>
            </svg>
            Security
          </button>

          <div className="profile-menu-divider"></div>

          <button className="profile-menu-item danger" onClick={handleLogout}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M6 2H4v12h2V2zm6 0h-2v12h2V2zM8 8l4-3v6l-4-3z"/>
            </svg>
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

export default ProfileDropdown;
