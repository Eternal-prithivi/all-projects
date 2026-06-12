// =============================================================================
// COMPONENT: Sidebar.jsx
// PURPOSE: Left navigation rail for dashboard (desktop). Mobile uses MobileBottomNav.
// =============================================================================
import React from 'react';
import { NavLink } from 'react-router-dom';
import { FaLock, FaQuestionCircle, FaUserShield } from 'react-icons/fa';
import { DASHBOARD_NAV_ITEMS } from '../../config/dashboardNavConfig.jsx';
import { usePlanEntitlementsContext } from '../../context/PlanEntitlementsContext.jsx';
import '../../styles/sidebar.css';
import ZenithLogo from '../brand/ZenithLogo.jsx';

function Sidebar({ user }) {
  const { isNavLocked, openUpgradeDrawer } = usePlanEntitlementsContext();
  const userInitial = user && user.username ? user.username.charAt(0).toUpperCase() : '?';

  const handleNavClick = (event, item) => {
    const lockId = item.navLockId || item.navId;
    if (!lockId || !item.lockNavBlock || !isNavLocked(lockId)) {
      return;
    }
    event.preventDefault();
    openUpgradeDrawer(lockId);
  };

  return (
    <aside className="nav-rail nav-rail--desktop" role="navigation" aria-label="Main navigation">
      <div className="rail-logo" data-tour="sidebar-logo">
        <ZenithLogo size={32} linkTo="/" animateOnMount />
      </div>

      <nav className="rail-nav" data-tour="sidebar-nav">
        <ul role="menu">
          {DASHBOARD_NAV_ITEMS.map((item) => {
            const lockId = item.navLockId || item.navId;
            const locked = lockId ? isNavLocked(lockId) : false;
            const showLockBadge = locked && !item.lockNavBlock;

            return (
              <li key={item.to} role="none">
                <NavLink
                  to={item.to}
                  end={item.end}
                  role="menuitem"
                  aria-label={item.label}
                  className={({ isActive }) =>
                    `rail-link ${isActive ? 'active' : ''} ${locked && item.lockNavBlock ? 'rail-link--locked' : ''}`
                  }
                  onClick={(e) => handleNavClick(e, item)}
                >
                  <span className="rail-link-icon">{item.icon}</span>
                  <span className="rail-link-label">{item.label}</span>
                  {showLockBadge && (
                    <span className="rail-link-lock" title="Upgrade for full access">
                      <FaLock aria-hidden />
                    </span>
                  )}
                </NavLink>
              </li>
            );
          })}
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
