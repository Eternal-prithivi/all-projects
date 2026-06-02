// =============================================================================
// COMPONENT: DashboardLayout.jsx  (133 lines)
// PURPOSE: Root layout wrapper for ALL /dashboard/* and /admin/* routes
//   - Renders: Sidebar + Header + <Outlet> (child page) + ToastContainer + OnboardingTour
//   - Handles sidebar open/close toggle state passed down to Sidebar
//   - Mounts OnboardingTour here so it persists across page navigation
// USED BY: React Router — wraps every ProtectedRoute in createBrowserRouter
// DO NOT:
//   - Move OnboardingTour out of this component — it must mount once at layout level
//   - Add page-specific logic here — keep this as a pure layout shell
//   - Remove ToastContainer — it's the global toast host for react-toastify
// =============================================================================
import React, { useState, useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import { useAuth } from "../../context/AuthContext.jsx";
import { NotificationProvider } from "../../context/NotificationContext.jsx";
import Sidebar from "./Sidebar.jsx";
import MobileBottomNav from "./MobileBottomNav.jsx";
import Header from "./Header.jsx";
import Footer from "../layout/Footer.jsx";
import Breadcrumbs from "../Breadcrumbs.jsx";
import QuickActions from "../QuickActions.jsx";
import KeyboardShortcuts from "../KeyboardShortcuts.jsx";
import GlobalSearch from "../GlobalSearch.jsx";
import OnboardingTour from "../OnboardingTour.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import "../../styles/dashboard.css";
import "../../styles/mobile-nav.css";
import "../../styles/cards.css";
import "../../styles/dashboard-polish.css";
import "react-toastify/dist/ReactToastify.css";
import "../../styles/toast-custom.css";

function DashboardLayout() {
  const { user } = useAuth();
  const { effectiveTheme } = useTheme();
  const navigate = useNavigate();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    const handleKeyPress = (e) => {
      // Show keyboard shortcuts
      if (e.key === '?' && !e.shiftKey) {
        e.preventDefault();
        setShowShortcuts(true);
      }
      
      // Show search
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShowSearch(true);
      }

      // Command palette (Cmd/Ctrl + K)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(true);
      }
      
      // Quick actions - Alt/Option + Shift + key
      // altKey works for both Mac (Option) and Windows (Alt)
      if (e.altKey && e.shiftKey && (e.key === 'n' || e.key === 'N')) {
        if (!showSearch && !showShortcuts) {
          e.preventDefault();
          navigate('/dashboard/vmcluster');
        }
      }
      if (e.altKey && e.shiftKey && (e.key === 'u' || e.key === 'U')) {
        if (!showSearch && !showShortcuts) {
          e.preventDefault();
          navigate('/dashboard/storage');
        }
      }
      if (e.altKey && e.shiftKey && (e.key === 'c' || e.key === 'C')) {
        if (!showSearch && !showShortcuts) {
          e.preventDefault();
          navigate('/dashboard/costs');
        }
      }
    };

    const handleShowShortcuts = () => {
      setShowShortcuts(true);
    };

    document.addEventListener('keydown', handleKeyPress);
    window.addEventListener('show-shortcuts', handleShowShortcuts);
    
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
      window.removeEventListener('show-shortcuts', handleShowShortcuts);
    };
  }, [navigate, showSearch, showShortcuts]);

  return (
    <NotificationProvider>
      <div className="dashboard-page">
        {/* Skip to main content link for keyboard navigation */}
        <a href="#main-content" className="skip-to-main" tabIndex={0}>
          Skip to main content
        </a>
        <Sidebar user={user} />
        <MobileBottomNav user={user} />
        <div className="dashboard-main">
          <Header user={user} />
          <div className="dashboard-breadcrumbs-wrapper">
            <Breadcrumbs />
          </div>
          <main id="main-content" className="dashboard-content" role="main" aria-label="Main dashboard content">
            <div className="dashboard-content__body">
              <Outlet />
            </div>
            <Footer />
          </main>
        </div>
        <QuickActions />
        <KeyboardShortcuts 
          isOpen={showShortcuts} 
          onClose={() => setShowShortcuts(false)} 
        />
        <GlobalSearch 
          isOpen={showSearch} 
          onClose={() => setShowSearch(false)} 
        />
        <OnboardingTour />
        <ToastContainer
          position="top-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop={true}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss={false}
          draggable={false}
          pauseOnHover
          theme={effectiveTheme === 'light' ? 'light' : 'dark'}
          limit={5}
          enableMultiContainer={false}
          containerId="main-toast-container"
          role="alert"
          aria-live="polite"
          style={{ 
            zIndex: 99999,
          }}
        />
      </div>
    </NotificationProvider>
  );
}

export default DashboardLayout;
