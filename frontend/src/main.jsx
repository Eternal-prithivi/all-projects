// =============================================================================
// MODULE: main.jsx  (entry point)
// PURPOSE: React app bootstrap — defines ALL routes via createBrowserRouter,
//          wraps providers (AuthContext, ThemeContext, PreferencesContext, NotificationContext)
// ROUTES:
//   /                → LandingPage
//   /login /register → Auth pages
//   /dashboard/*     → DashboardLayout (ProtectedRoute) + all page children
//   /admin/*         → AdminDashboardPage (admin role required)
// LAZY LOADING: All dashboard pages are lazy-loaded for performance (React.lazy + Suspense)
// DO NOT:
//   - Add routes without wrapping in ProtectedRoute (if auth required)
//   - Change provider order — AuthContext must wrap PreferencesContext (it depends on token)
//   - Import heavy components eagerly here — use React.lazy for all page-level components
// =============================================================================
import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import { PreferencesProvider } from "./context/PreferencesContext.jsx";
import ThemeSync from "./components/ThemeSync.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import LazyLoadFallback from "./components/LazyLoadFallback.jsx";
import "./index.css";

// Optional Sentry — only load the chunk when DSN is configured (avoids dev errors without npm install)
if (import.meta.env.VITE_SENTRY_DSN) {
  import("./lib/sentry-init.js");
}

// Eager load: Critical pages needed immediately
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";

// Lazy load: All other pages (loaded on-demand)
const DashboardLayout = lazy(() => import("./components/dashboard/DashboardLayout.jsx"));
const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"));
const StoragePage = lazy(() => import("./pages/StoragePage.jsx"));
const VMClusterPage = lazy(() => import("./pages/VMClusterPage.jsx"));
const CostAnalysisPage = lazy(() => import("./pages/CostAnalysisEnhancedPage.jsx"));
const CostSimulatorPage = lazy(() => import("./pages/CostSimulatorPage.jsx"));
const CostOptimizationPage = lazy(() => import("./pages/CostOptimizationPage.jsx"));
const SecurityPage = lazy(() => import("./pages/SecurityPage.jsx"));
const SecuritySettingsPage = lazy(() => import("./pages/SecuritySettingsPage.jsx"));
const ProfilePage = lazy(() => import("./pages/ProfilePage.jsx"));
const SettingsPage = lazy(() => import("./pages/SettingsPage.jsx"));
const BillingPage = lazy(() => import("./pages/BillingPage.jsx"));
const PricingPage = lazy(() => import("./pages/PricingPage.jsx"));
const ContactPage = lazy(() => import("./pages/ContactPage.jsx"));
const AboutPage = lazy(() => import("./pages/AboutPage.jsx"));
const FeaturesPage = lazy(() => import("./pages/FeaturesPage.jsx"));
const HelpCenterPage = lazy(() => import("./pages/HelpCenterPage.jsx"));
const TermsOfServicePage = lazy(() => import("./pages/TermsOfServicePage.jsx"));
const PrivacyPolicyPage = lazy(() => import("./pages/PrivacyPolicyPage.jsx"));
const AccessDeniedPage = lazy(() => import("./pages/AccessDeniedPage.jsx"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage.jsx"));
const ServerErrorPage = lazy(() => import("./pages/ServerErrorPage.jsx"));
const ServiceUnavailablePage = lazy(() => import("./pages/ServiceUnavailablePage.jsx"));
const ProvisionPage = lazy(() => import("./pages/ProvisionPage.jsx"));

// Admin pages (lazy loaded - only for admins)
const AdminLayout = lazy(() => import("./components/admin/AdminLayout.jsx"));
const AdminOverviewPage = lazy(() => import("./pages/admin/AdminOverviewPage.jsx"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage.jsx"));
const AdminAnalyticsPage = lazy(() => import("./pages/admin/AdminAnalyticsPage.jsx"));
const AdminPaymentsPage = lazy(() => import("./pages/admin/AdminPaymentsPage.jsx"));
const AdminSystemPage = lazy(() => import("./pages/admin/AdminSystemPage.jsx"));
const AdminSettingsPage = lazy(() => import("./pages/admin/AdminSettingsPage.jsx"));
const AdminTestPage = lazy(() => import("./pages/admin/AdminTestPage.jsx"));
const TrustCenterPage = lazy(() => import("./pages/TrustCenterPage.jsx"));
const CookiePolicyPage = lazy(() => import("./pages/CookiePolicyPage.jsx"));
const DpaPage = lazy(() => import("./pages/DpaPage.jsx"));
const StatusPage = lazy(() => import("./pages/StatusPage.jsx"));
const VerifyEmailPage = lazy(() => import("./pages/VerifyEmailPage.jsx"));
const PublicPricingPage = lazy(() => import("./pages/PublicPricingPage.jsx"));
const SessionExpiredPage = lazy(() => import("./pages/SessionExpiredPage.jsx"));
const BillingSuccessPage = lazy(() => import("./pages/BillingSuccessPage.jsx"));
const BillingCancelPage = lazy(() => import("./pages/BillingCancelPage.jsx"));
const DocsHubPage = lazy(() => import("./pages/DocsHubPage.jsx"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage.jsx"));
const TeamPage = lazy(() => import("./pages/TeamPage.jsx"));
const AcceptInvitePage = lazy(() => import("./pages/AcceptInvitePage.jsx"));
const SsoCallbackPage = lazy(() => import("./pages/SsoCallbackPage.jsx"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      // --- Public Routes (eager loaded) ---
      { index: true, element: <HomePage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      { path: "/forgot-password", element: <ForgotPasswordPage /> },
      { path: "/reset-password", element: <ResetPasswordPage /> },
      
      // --- Public Routes (lazy loaded) ---
      { path: "/contact", element: <Suspense fallback={<LazyLoadFallback />}><ContactPage /></Suspense> },
      { path: "/about", element: <Suspense fallback={<LazyLoadFallback />}><AboutPage /></Suspense> },
      { path: "/features", element: <Suspense fallback={<LazyLoadFallback />}><FeaturesPage /></Suspense> },
      { path: "/access-denied", element: <Suspense fallback={<LazyLoadFallback />}><AccessDeniedPage /></Suspense> },
      { path: "/help", element: <Suspense fallback={<LazyLoadFallback />}><HelpCenterPage /></Suspense> },
      { path: "/legal/terms", element: <Suspense fallback={<LazyLoadFallback />}><TermsOfServicePage /></Suspense> },
      { path: "/legal/privacy", element: <Suspense fallback={<LazyLoadFallback />}><PrivacyPolicyPage /></Suspense> },
      { path: "/legal/cookies", element: <Suspense fallback={<LazyLoadFallback />}><CookiePolicyPage /></Suspense> },
      { path: "/legal/dpa", element: <Suspense fallback={<LazyLoadFallback />}><DpaPage /></Suspense> },
      { path: "/trust", element: <Suspense fallback={<LazyLoadFallback />}><TrustCenterPage /></Suspense> },
      { path: "/status", element: <Suspense fallback={<LazyLoadFallback />}><StatusPage /></Suspense> },
      { path: "/verify-email", element: <Suspense fallback={<LazyLoadFallback />}><VerifyEmailPage /></Suspense> },
      { path: "/pricing", element: <Suspense fallback={<LazyLoadFallback />}><PublicPricingPage /></Suspense> },
      { path: "/docs", element: <Suspense fallback={<LazyLoadFallback />}><DocsHubPage /></Suspense> },
      { path: "/session-expired", element: <Suspense fallback={<LazyLoadFallback />}><SessionExpiredPage /></Suspense> },
      { path: "/billing/success", element: <Suspense fallback={<LazyLoadFallback />}><BillingSuccessPage /></Suspense> },
      { path: "/billing/cancel", element: <Suspense fallback={<LazyLoadFallback />}><BillingCancelPage /></Suspense> },
      { path: "/auth/sso/callback", element: <Suspense fallback={<LazyLoadFallback />}><SsoCallbackPage /></Suspense> },
      { path: "/invite/:token", element: <Suspense fallback={<LazyLoadFallback />}><AcceptInvitePage /></Suspense> },

      // --- Protected Routes (lazy loaded) ---
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: "dashboard",
            element: <Suspense fallback={<LazyLoadFallback />}><DashboardLayout /></Suspense>,
            children: [
              { index: true, element: <Suspense fallback={<LazyLoadFallback />}><DashboardPage /></Suspense> },
              { path: "costs", element: <Suspense fallback={<LazyLoadFallback />}><CostAnalysisPage /></Suspense> },
              { path: "billing", element: <Suspense fallback={<LazyLoadFallback />}><BillingPage /></Suspense> },
              { path: "pricing", element: <Suspense fallback={<LazyLoadFallback />}><PricingPage /></Suspense> },
              { path: "simulator", element: <Suspense fallback={<LazyLoadFallback />}><CostSimulatorPage /></Suspense> },
              { path: "optimization", element: <Suspense fallback={<LazyLoadFallback />}><CostOptimizationPage /></Suspense> },
              { path: "storage", element: <Suspense fallback={<LazyLoadFallback />}><StoragePage /></Suspense> },
              { path: "vmcluster", element: <Suspense fallback={<LazyLoadFallback />}><VMClusterPage /></Suspense> },
              { path: "security", element: <Suspense fallback={<LazyLoadFallback />}><SecurityPage /></Suspense> },
              { path: "security-settings", element: <Suspense fallback={<LazyLoadFallback />}><SecuritySettingsPage /></Suspense> },
              { path: "profile", element: <Suspense fallback={<LazyLoadFallback />}><ProfilePage /></Suspense> },
              { path: "settings", element: <Suspense fallback={<LazyLoadFallback />}><SettingsPage /></Suspense> },
              { path: "provision", element: <Suspense fallback={<LazyLoadFallback />}><ProvisionPage /></Suspense> },
              { path: "notifications", element: <Suspense fallback={<LazyLoadFallback />}><NotificationsPage /></Suspense> },
              { path: "team", element: <Suspense fallback={<LazyLoadFallback />}><TeamPage /></Suspense> },
            ],
          },
          {
            path: "admin",
            element: <Suspense fallback={<LazyLoadFallback />}><AdminLayout /></Suspense>,
            children: [
              { index: true, element: <Suspense fallback={<LazyLoadFallback />}><AdminOverviewPage /></Suspense> },
              { path: "users", element: <Suspense fallback={<LazyLoadFallback />}><AdminUsersPage /></Suspense> },
              { path: "analytics", element: <Suspense fallback={<LazyLoadFallback />}><AdminAnalyticsPage /></Suspense> },
              { path: "payments", element: <Suspense fallback={<LazyLoadFallback />}><AdminPaymentsPage /></Suspense> },
              { path: "system", element: <Suspense fallback={<LazyLoadFallback />}><AdminSystemPage /></Suspense> },
              { path: "settings", element: <Suspense fallback={<LazyLoadFallback />}><AdminSettingsPage /></Suspense> },
              { path: "test", element: <Suspense fallback={<LazyLoadFallback />}><AdminTestPage /></Suspense> },
            ],
          },
        ],
      },

      // --- Error Routes (lazy loaded) ---
      { path: "/500", element: <Suspense fallback={<LazyLoadFallback />}><ServerErrorPage /></Suspense> },
      { path: "/503", element: <Suspense fallback={<LazyLoadFallback />}><ServiceUnavailablePage /></Suspense> },
      { path: "*", element: <Suspense fallback={<LazyLoadFallback />}><NotFoundPage /></Suspense> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider>
          <ThemeSync />
          <PreferencesProvider>
            <RouterProvider router={router} />
          </PreferencesProvider>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
