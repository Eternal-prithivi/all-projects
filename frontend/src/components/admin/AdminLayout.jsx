import React, { useCallback, useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { ConfirmProvider } from '../../context/ConfirmContext.jsx';
import SupportWsBridge from '../support/SupportWsBridge.jsx';
import AdminSidebar from './AdminSidebar';
import AdminMobileBottomNav from './AdminMobileBottomNav';
import AdminHeader from './AdminHeader';
import Breadcrumbs from '../Breadcrumbs.jsx';
import GlobalSearch from '../GlobalSearch.jsx';
import KeyboardShortcuts from '../KeyboardShortcuts.jsx';
import { useAppKeyboardShortcuts } from '../../hooks/useAppKeyboardShortcuts.js';
import { ADMIN_GO_ROUTES } from '../../utils/keyboardShortcuts.js';
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

  const openSearch = useCallback(() => setShowSearch(true), []);
  const openShortcuts = useCallback(() => setShowShortcuts(true), []);

  useAppKeyboardShortcuts({
    goRoutes: ADMIN_GO_ROUTES,
    onOpenSearch: openSearch,
    onOpenShortcuts: openShortcuts,
    overlaysOpen: showSearch || showShortcuts,
  });

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
      <ConfirmProvider>
      <SupportWsBridge />
      <div className="admin-layout">
        <AdminSidebar user={user} />
        <AdminMobileBottomNav user={user} />
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
        <KeyboardShortcuts
          isOpen={showShortcuts}
          onClose={() => setShowShortcuts(false)}
          variant="admin"
        />
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
      </ConfirmProvider>
    </NotificationProvider>
  );
};

export default AdminLayout;
