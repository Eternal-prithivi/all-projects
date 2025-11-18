import React from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { useNavigate } from 'react-router-dom';

function Header({ user }) { // Accept user as a prop
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="dashboard-header">
      {/* Add a check here: only show the welcome message if the user exists */}
      <h1 className="header-title">Welcome, {user ? user.username : 'User'}!</h1>
      <button onClick={handleLogout} className="logout-button">
        Logout
      </button>
    </header>
  );
}

export default Header;
