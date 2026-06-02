// =============================================================================
// COMPONENT: Sidebar.jsx
// PURPOSE: Left navigation rail for dashboard (desktop). Mobile uses MobileBottomNav.
// =============================================================================
import React from 'react';
import { NavLink } from 'react-router-dom';
import { FaQuestionCircle, FaUserShield } from 'react-icons/fa';
import { DASHBOARD_NAV_ITEMS } from '../../config/dashboardNavConfig.jsx';
import '../../styles/sidebar.css';
import ZenithLogo from '../brand/ZenithLogo.jsx';

function Sidebar({ user }) {
  const userInitial = user && user.username ? user.username.charAt(0).toUpperCase() : '?';

  return (
    <aside className="nav-rail nav-rail--desktop" role="navigation" aria-label="Main navigation">
      <div className="rail-logo" data-tour="sidebar-logo">
        <ZenithLogo size={32} linkTo="/" />
      </div>

      <nav className="rail-nav" data-tour="sidebar-nav">
        <ul role="menu">
          {DASHBOARD_NAV_ITEMS.map((item) => (
            <li key={item.to} role="none">
              <NavLink
                to={item.to}
                end={item.end}
                role="menuitem"
                aria-label={item.label}
                className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}
              >
                <span className="rail-link-icon">{item.icon}</span>
                <span className="rail-link-label">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="rail-bottom">
        {user?.role === 'admin' && (
          <NavLink
            to="/admin"
            className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}
            aria-label="Admin portal"
          >
            <span className="rail-link-icon">
              <FaUserShield className="rail-icon" />
            </span>
            <span className="rail-link-label">Admin</span>
          </NavLink>
        )}
        <NavLink
          to="/help"
          className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}
          aria-label="Help Center"
          data-tour="sidebar-help"
        >
          <span className="rail-link-icon">
            <FaQuestionCircle className="rail-icon" />
          </span>
          <span className="rail-link-label">Help</span>
        </NavLink>

        <NavLink
          to="/dashboard/settings"
          className={({ isActive }) => `rail-link rail-link-user ${isActive ? 'active' : ''}`}
          aria-label="Settings"
        >
          <span className="rail-avatar">{userInitial}</span>
          <span className="rail-link-label">{user?.username || 'User'}</span>
        </NavLink>
      </div>
    </aside>
  );
}

export default Sidebar;
