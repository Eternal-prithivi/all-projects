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
import React, { useCallback, useState } from "react";
import { Outlet } from "react-router-dom";
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
import SupportWsBridge from "../support/SupportWsBridge.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useAppKeyboardShortcuts } from "../../hooks/useAppKeyboardShortcuts.js";
import { DASHBOARD_GO_ROUTES } from "../../utils/keyboardShortcuts.js";
import { PlanEntitlementsProvider } from "../../context/PlanEntitlementsContext.jsx";
import { CloudAvailabilityProvider } from "../../context/CloudAvailabilityContext.jsx";
import "../../styles/plan-upgrade.css";
import "../../styles/dashboard.css";
import "../../styles/mobile-nav.css";
import "../../styles/cards.css";
import "../../styles/dashboard-polish.css";
import "react-toastify/dist/ReactToastify.css";
import "../../styles/toast-custom.css";

function DashboardLayout() {
  const { user } = useAuth();
  const { effectiveTheme } = useTheme();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  const openSearch = useCallback(() => setShowSearch(true), []);
  const openShortcuts = useCallback(() => setShowShortcuts(true), []);

  useAppKeyboardShortcuts({
    goRoutes: DASHBOARD_GO_ROUTES,
    onOpenSearch: openSearch,
    onOpenShortcuts: openShortcuts,
    overlaysOpen: showSearch || showShortcuts,
  });

  return (
    <NotificationProvider>
      <PlanEntitlementsProvider>
      <CloudAvailabilityProvider>
      <SupportWsBridge notifyOnAgentReply />
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
            <div className="dashboard-content-stack">
              <div className="dashboard-content__body">
                <Outlet />
              </div>
              <Footer />
            </div>
          </main>
        </div>
        <QuickActions />
        <KeyboardShortcuts
          isOpen={showShortcuts}
          onClose={() => setShowShortcuts(false)}
          variant="dashboard"
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
      </CloudAvailabilityProvider>
      </PlanEntitlementsProvider>
    </NotificationProvider>
  );
}

export default DashboardLayout;
