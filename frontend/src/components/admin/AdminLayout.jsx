import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { NotificationProvider } from '../../context/NotificationContext.jsx';
import AdminSidebar from './AdminSidebar';
import AdminHeader from './AdminHeader';
import '../../styles/admin-layout.css';
import '../../styles/dashboard-polish.css';
import '../../styles/notification-bell.css';
import 'react-toastify/dist/ReactToastify.css';
import '../../styles/toast-custom.css';

const AdminLayout = () => {
  const { user, token, loading } = useAuth();
  const { effectiveTheme } = useTheme();
  const navigate = useNavigate();

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
          <AdminHeader user={user} />
          <div className="admin-content">
            <Outlet />
          </div>
        </div>
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
