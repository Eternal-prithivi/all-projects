import React from 'react';
import { NavLink, Link } from 'react-router-dom';
// Corrected import from our new local file
import { IconDashboard, IconBarChart, IconHardDrive, IconServer, IconShield } from './Icons.jsx';
import { FaQuestionCircle } from 'react-icons/fa';
import '../../styles/sidebar.css';

function Sidebar({ user }) {
  const userInitial = user && user.username ? user.username.charAt(0).toUpperCase() : '?';
  const username = user ? user.username : 'Loading...';

  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      <div className="sidebar-header">
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }} aria-label="Go to homepage">
          <h3>Zenith</h3>
        </Link>
      </div>
      <nav className="sidebar-nav">
        <ul role="menu">
          <li role="none"><NavLink to="/dashboard" end role="menuitem" aria-label="Dashboard overview"><IconDashboard className="sidebar-icon" aria-hidden="true" />Overview</NavLink></li>
          <li role="none"><NavLink to="/dashboard/storage" role="menuitem" aria-label="Storage management"><IconHardDrive className="sidebar-icon" aria-hidden="true" />Storage</NavLink></li>
          <li role="none"><NavLink to="/dashboard/vmcluster" role="menuitem" aria-label="VM cluster management"><IconServer className="sidebar-icon" aria-hidden="true" />VM Cluster</NavLink></li>
          <li role="none"><NavLink to="/dashboard/security" role="menuitem" aria-label="Security settings"><IconShield className="sidebar-icon" aria-hidden="true" />Security</NavLink></li>
          <li role="none"><NavLink to="/dashboard/costs" role="menuitem" aria-label="Cost analysis"><IconBarChart className="sidebar-icon" aria-hidden="true" />Cost Analysis</NavLink></li>
          <li role="none"><NavLink to="/dashboard/billing" role="menuitem" aria-label="Billing information">
            <svg className="sidebar-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
              <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
            </svg>
            Billing
          </NavLink></li>
          <li role="none"><NavLink to="/help" role="menuitem" aria-label="Help center">
            <FaQuestionCircle className="sidebar-icon" aria-hidden="true" />
            Help Center
          </NavLink></li>
        </ul>
      </nav>
      <div className="user-profile" role="complementary" aria-label="User information">
        <div className="user-avatar" aria-hidden="true">{userInitial}</div>
        <div className="user-info">
          <h4>{username}</h4>
          <p>User</p>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
