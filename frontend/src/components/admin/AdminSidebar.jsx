import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { FaChartLine, FaUsers, FaDollarSign, FaServer, FaHome, FaQuestionCircle, FaShieldAlt } from 'react-icons/fa';
import '../../styles/admin-layout.css';

const AdminSidebar = ({ user }) => {
  const userInitial = user?.username?.charAt(0).toUpperCase() || 'A';

  return (
    <aside className="admin-sidebar nav-rail admin-rail" role="navigation" aria-label="Admin navigation">
      <div className="rail-logo admin-rail-logo">
        <Link to="/admin" aria-label="Go to admin overview">
          <span className="rail-logo-mark">A</span>
        </Link>
      </div>

      <nav className="rail-nav admin-rail-nav">
        <ul role="menu">
          <li role="none">
            <NavLink to="/admin" end role="menuitem" aria-label="Overview" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaChartLine className="rail-icon" /></span>
              <span className="rail-link-label">Overview</span>
            </NavLink>
          </li>
          <li role="none">
            <NavLink to="/admin/users" role="menuitem" aria-label="User Management" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaUsers className="rail-icon" /></span>
              <span className="rail-link-label">Users</span>
            </NavLink>
          </li>
          <li role="none">
            <NavLink to="/admin/analytics" role="menuitem" aria-label="Analytics" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaChartLine className="rail-icon" /></span>
              <span className="rail-link-label">Analytics</span>
            </NavLink>
          </li>
          <li role="none">
            <NavLink to="/admin/payments" role="menuitem" aria-label="Payments" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaDollarSign className="rail-icon" /></span>
              <span className="rail-link-label">Payments</span>
            </NavLink>
          </li>
          <li role="none">
            <NavLink to="/admin/system" role="menuitem" aria-label="System Health" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaServer className="rail-icon" /></span>
              <span className="rail-link-label">System</span>
            </NavLink>
          </li>
          <li role="none">
            <NavLink to="/admin/provision-roles" role="menuitem" aria-label="Provision roles" className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}>
              <span className="rail-link-icon"><FaShieldAlt className="rail-icon" /></span>
              <span className="rail-link-label">Provision roles</span>
            </NavLink>
          </li>
        </ul>
      </nav>

      <div className="rail-bottom admin-rail-bottom">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}
          aria-label="Back to Dashboard"
        >
          <span className="rail-link-icon"><FaHome className="rail-icon" /></span>
          <span className="rail-link-label">Dashboard</span>
        </NavLink>

        <NavLink
          to="/admin/settings"
          className={({ isActive }) => `rail-link rail-link-user ${isActive ? 'active' : ''}`}
          aria-label="Admin Settings"
        >
          <span className="rail-avatar">{userInitial}</span>
          <span className="rail-link-label">Admin Settings</span>
        </NavLink>

        <Link to="/help" className="rail-link" aria-label="Help Center">
          <span className="rail-link-icon"><FaQuestionCircle className="rail-icon" /></span>
          <span className="rail-link-label">Help</span>
        </Link>
      </div>
    </aside>
  );
};

export default AdminSidebar;
