// =============================================================================
// COMPONENT: Sidebar.jsx  (80 lines)
// PURPOSE: Left navigation rail for all dashboard pages
//   - Collapsed: 56px icon-only rail | Expanded: 220px with labels (hover or toggle)
//   - Mobile: transforms to bottom tab bar (CSS media query handles this)
//   - Links: Dashboard, Cost Analysis, Storage, VM Cluster, Security (+ admin if role=admin)
//   - data-tour="sidebar-nav" — onboarding tour step 1 targets this
// USED BY: DashboardLayout.jsx
// DO NOT:
//   - Change nav link paths without updating GlobalSearch.jsx route map
//   - Remove data-tour="sidebar-nav" attribute — breaks onboarding tour step 1
//   - Add inline widths — collapsed/expanded is controlled via CSS class toggle
// =============================================================================
import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { IconDashboard, IconBarChart, IconHardDrive, IconServer, IconShield } from './Icons.jsx';
import { FaQuestionCircle } from 'react-icons/fa';
import '../../styles/sidebar.css';

function Sidebar({ user }) {
  const userInitial = user && user.username ? user.username.charAt(0).toUpperCase() : '?';

  const navItems = [
    { to: '/dashboard', icon: <IconDashboard className="rail-icon" />, label: 'Overview', end: true },
    { to: '/dashboard/storage', icon: <IconHardDrive className="rail-icon" />, label: 'Storage' },
    { to: '/dashboard/vmcluster', icon: <IconServer className="rail-icon" />, label: 'VM Cluster' },
    { to: '/dashboard/security', icon: <IconShield className="rail-icon" />, label: 'Security' },
    { to: '/dashboard/provision', icon: (
      <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M5.5 16a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.977A4.5 4.5 0 1113.5 16h-8z"/>
        <path d="M10 9l3 3m0 0l-3 3m3-3H7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      </svg>
    ), label: 'Provision' },
    { to: '/dashboard/costs', icon: <IconBarChart className="rail-icon" />, label: 'Cost Analysis' },
    { to: '/dashboard/billing', icon: (
      <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
        <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
      </svg>
    ), label: 'Billing' },
  ];

  return (
    <aside className="nav-rail" role="navigation" aria-label="Main navigation">
      {/* Logo mark */}
      <div className="rail-logo" data-tour="sidebar-logo">
        <Link to="/" aria-label="Go to homepage">
          <span className="rail-logo-mark">Z</span>
        </Link>
      </div>

      {/* Navigation items */}
      <nav className="rail-nav" data-tour="sidebar-nav">
        <ul role="menu">
          {navItems.map((item) => (
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

      {/* Bottom section */}
      <div className="rail-bottom">
        <NavLink
          to="/help"
          className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}
          aria-label="Help Center"
          data-tour="sidebar-help"
        >
          <span className="rail-link-icon"><FaQuestionCircle className="rail-icon" /></span>
          <span className="rail-link-label">Help</span>
        </NavLink>

        <NavLink
          to="/dashboard/settings"
          className={({ isActive }) => `rail-link rail-link-user ${isActive ? 'active' : ''}`}
          aria-label="Settings"
        >
          <span className="rail-avatar">{userInitial}</span>
          <span className="rail-link-label">
            {user?.username || 'User'}
          </span>
        </NavLink>
      </div>
    </aside>
  );
}

export default Sidebar;
