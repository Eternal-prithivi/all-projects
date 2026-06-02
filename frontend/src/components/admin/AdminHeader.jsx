import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FaUserCircle, FaSignOutAlt } from 'react-icons/fa';
import NotificationBell from '../NotificationBell.jsx';
import '../../styles/admin-layout.css';

const AdminHeader = ({ user }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = React.useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="admin-header">
      <div className="admin-header-left">
        <h1>Platform Administration</h1>
      </div>

      <div className="admin-header-right">
        <NotificationBell viewAllPath="/admin/notifications" />

        <div className="admin-user-menu">
          <button
            type="button"
            className="admin-user-btn"
            onClick={() => setShowDropdown(!showDropdown)}
            aria-expanded={showDropdown}
          >
            <FaUserCircle />
            <span>{user?.username}</span>
          </button>

          {showDropdown && (
            <div className="admin-user-dropdown">
              <div className="dropdown-header">
                <p className="dropdown-name">{user?.username}</p>
                <p className="dropdown-email">{user?.email}</p>
              </div>
              <div className="dropdown-divider" />
              <button type="button" onClick={handleLogout} className="dropdown-item logout">
                <FaSignOutAlt />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default AdminHeader;
