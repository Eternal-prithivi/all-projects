import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { NotificationProvider } from '../../context/NotificationContext.jsx';
import AdminSidebar from './AdminSidebar';
import AdminHeader from './AdminHeader';
import Breadcrumbs from '../Breadcrumbs.jsx';
import GlobalSearch from '../GlobalSearch.jsx';
import KeyboardShortcuts from '../KeyboardShortcuts.jsx';
import '../../styles/header-toolbar.css';
import '../../styles/admin-layout.css';
import '../../styles/dashboard-polish.css';
import '../../styles/breadcrumbs.css';
import '../../styles/notification-bell.css';
import '../../styles/profile-dropdown.css';
import 'react-toastify/dist/ReactToastify.css';
import '../../styles/toast-custom.css';

const AdminLayout = () => {
  const { user, token, loading } = useAuth();
  const { effectiveTheme } = useTheme();
  const navigate = useNavigate();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  React.useEffect(() => {
    if (loading) return;
    if (!token) {
      navigate('/login', { replace: true, state: { from: window.location.pathname } });
      return;
    }
    if (user && user.role !== 'admin') {
      navigate('/access-denied', { replace: true });
    }
  }, [user, token, loading, navigate]);

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === '?' && !e.shiftKey) {
        e.preventDefault();
        setShowShortcuts(true);
      }
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShowSearch(true);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(true);
      }
    };
    const handleShowShortcuts = () => setShowShortcuts(true);

    document.addEventListener('keydown', handleKeyPress);
    window.addEventListener('show-shortcuts', handleShowShortcuts);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
      window.removeEventListener('show-shortcuts', handleShowShortcuts);
    };
  }, []);

  if (loading) {
    return (
      <div className="admin-loading-screen">
        <div className="spinner" />
        <p>Loading admin portal...</p>
      </div>
    );
  }

  if (!token || !user || user.role !== 'admin') {
    return null;
  }

  return (
    <NotificationProvider>
      <div className="admin-layout">
        <AdminSidebar user={user} />
        <div className="admin-main">
          <AdminHeader />
          <div className="dashboard-breadcrumbs-wrapper admin-breadcrumbs-wrapper">
            <Breadcrumbs />
          </div>
          <div className="admin-content">
            <Outlet />
          </div>
        </div>
        <GlobalSearch isOpen={showSearch} onClose={() => setShowSearch(false)} />
        <KeyboardShortcuts isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
        <ToastContainer
          position="top-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnFocusLoss={false}
          draggable={false}
          pauseOnHover
          theme={effectiveTheme === 'light' ? 'light' : 'dark'}
          limit={5}
          enableMultiContainer={false}
          containerId="admin-toast-container"
          role="alert"
          aria-live="polite"
          style={{ zIndex: 99999 }}
        />
      </div>
    </NotificationProvider>
  );
};

export default AdminLayout;
