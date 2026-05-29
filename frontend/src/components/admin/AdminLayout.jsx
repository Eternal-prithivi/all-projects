import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AdminSidebar from './AdminSidebar';
import AdminHeader from './AdminHeader';
import '../../styles/admin-layout.css';
import '../../styles/dashboard-polish.css';
import { FaShieldAlt, FaExclamationTriangle } from 'react-icons/fa';

const AdminLayout = () => {
  const { user, token, loading } = useAuth();
  const navigate = useNavigate();

  // Check authentication and authorization
  React.useEffect(() => {
    console.log('🔍 AdminLayout check:', { 
      loading,
      hasToken: !!token, 
      hasUser: !!user, 
      userRole: user?.role
    });

    // Wait for auth loading to complete
    if (loading) {
      console.log('⏳ Waiting for auth to load...');
      return;
    }

    // No token means not logged in - redirect to login with current path
    if (!token) {
      console.log('❌ No token found, redirecting to login');
      navigate('/login', { replace: true, state: { from: window.location.pathname } });
      return;
    }

    // Check if user is loaded and has admin role
    if (user) {
      console.log('✅ User loaded:', user.username, 'Role:', user.role);
      if (user.role !== 'admin') {
        console.log('⛔ Not an admin, redirecting to access denied page');
        navigate('/access-denied', { replace: true });
      } else {
        console.log('🎉 Admin verified, showing admin portal');
      }
    }
  }, [user, token, loading, navigate]);

  // Show loading while auth is being checked
  if (loading) {
    return (
      <div className="admin-loading-screen">
        <div className="spinner"></div>
        <p>Loading admin portal...</p>
      </div>
    );
  }

  // Block rendering for non-authenticated users
  if (!token || !user) {
    return null; // Will redirect via useEffect
  }

  // Block rendering for non-admin users
  if (user.role !== 'admin') {
    return null; // Will redirect via useEffect
  }

  // Render admin portal for authorized users
  return (
    <div className="admin-layout">
      <AdminSidebar user={user} />
      <div className="admin-main">
        <AdminHeader user={user} />
        <div className="admin-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default AdminLayout;
