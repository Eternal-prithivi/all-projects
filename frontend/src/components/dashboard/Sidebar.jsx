import React from 'react';
import { NavLink, Link } from 'react-router-dom';
// Corrected import from our new local file
import { IconDashboard, IconBarChart, IconHardDrive, IconServer, IconShield } from './Icons.jsx';
import '../../styles/sidebar.css';

function Sidebar({ user }) {
  const userInitial = user && user.username ? user.username.charAt(0).toUpperCase() : '?';
  const username = user ? user.username : 'Loading...';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Zenith</h3>
        </Link>
      </div>
      <nav className="sidebar-nav">
        <ul>
          <li><NavLink to="/dashboard" end><IconDashboard className="sidebar-icon" />Overview</NavLink></li>
          <li><NavLink to="/dashboard/storage"><IconHardDrive className="sidebar-icon" />Storage</NavLink></li>
          <li><NavLink to="/dashboard/vmcluster"><IconServer className="sidebar-icon" />VM Cluster</NavLink></li>
          <li><NavLink to="/dashboard/security"><IconShield className="sidebar-icon" />Security</NavLink></li>
          <li><NavLink to="/dashboard/costs"><IconBarChart className="sidebar-icon" />Cost Analysis</NavLink></li>
          <li><NavLink to="/dashboard/billing">
            <svg className="sidebar-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
              <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
            </svg>
            Billing
          </NavLink></li>
        </ul>
      </nav>
      <div className="user-profile">
        <div className="user-avatar">{userInitial}</div>
        <div className="user-info">
          <h4>{username}</h4>
          <p>Admin</p>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
