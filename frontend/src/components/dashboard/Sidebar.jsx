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
          <li><NavLink to="/dashboard/costs"><IconBarChart className="sidebar-icon" />Cost Analysis</NavLink></li>
          <li><NavLink to="/dashboard/storage"><IconHardDrive className="sidebar-icon" />Storage</NavLink></li>
          <li><NavLink to="/dashboard/vmcluster"><IconServer className="sidebar-icon" />VM Cluster</NavLink></li>
          <li><NavLink to="/dashboard/security"><IconShield className="sidebar-icon" />Security</NavLink></li>
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
