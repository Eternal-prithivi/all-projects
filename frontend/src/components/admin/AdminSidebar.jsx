import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { 
  FaShieldAlt, FaChartLine, FaUsers, FaDollarSign, 
  FaServer, FaCog, FaHome
} from 'react-icons/fa';
import '../../styles/admin-layout.css';

const AdminSidebar = ({ user }) => {
  const userInitial = user?.username?.charAt(0).toUpperCase() || 'A';

  return (
    <aside className="admin-sidebar">
      <div className="admin-sidebar-header">
        <Link to="/admin" className="admin-brand">
          <FaShieldAlt className="admin-brand-icon" />
          <div className="admin-brand-text">
            <h3>Platform Admin</h3>
            <span>Zenith Cloud</span>
          </div>
        </Link>
      </div>

      <nav className="admin-sidebar-nav">
        <ul>
          <li>
            <NavLink to="/admin" end>
              <FaChartLine />
              <span>Overview</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/users">
              <FaUsers />
              <span>User Management</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/analytics">
              <FaChartLine />
              <span>Analytics</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/payments">
              <FaDollarSign />
              <span>Payments</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/system">
              <FaServer />
              <span>System Health</span>
            </NavLink>
          </li>
        </ul>

        <div className="admin-sidebar-divider"></div>

        <ul className="admin-sidebar-secondary">
          <li>
            <Link to="/dashboard" className="admin-sidebar-link">
              <FaHome />
              <span>Back to Dashboard</span>
            </Link>
          </li>
          <li>
            <NavLink to="/admin/settings">
              <FaCog />
              <span>Admin Settings</span>
            </NavLink>
          </li>
        </ul>
      </nav>

      <div className="admin-user-profile">
        <div className="admin-user-avatar">{userInitial}</div>
        <div className="admin-user-info">
          <h4>{user?.username}</h4>
          <p className="admin-badge">Administrator</p>
        </div>
      </div>
    </aside>
  );
};

export default AdminSidebar;
