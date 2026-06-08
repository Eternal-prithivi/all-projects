// =============================================================================
// MODULE: main.jsx  (entry point)
// PURPOSE: React app bootstrap — defines ALL routes via createBrowserRouter,
//          wraps providers (AuthContext, ThemeContext, PreferencesContext, NotificationContext)
// ROUTES:
//   /                → LandingPage
//   /login /register → Auth pages
//   /dashboard/*     → DashboardLayout (ProtectedRoute) + all page children
//   /admin/*         → AdminLayout + pages/admin/* (admin role required)
// LAZY LOADING: All dashboard pages are lazy-loaded for performance (React.lazy + Suspense)
// DO NOT:
//   - Add routes without wrapping in ProtectedRoute (if auth required)
//   - Change provider order — AuthContext must wrap PreferencesContext (it depends on token)
//   - Import heavy components eagerly here — use React.lazy for all page-level components
// =============================================================================
import React, { Suspense } from "react";
import { lazyWithRetry } from "./utils/lazyLoad.js";
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
const DashboardLayout = lazyWithRetry(() => import("./components/dashboard/DashboardLayout.jsx"));
const DashboardPage = lazyWithRetry(() => import("./pages/DashboardPage.jsx"));
const StoragePage = lazyWithRetry(() => import("./pages/StoragePage.jsx"));
const VMClusterPage = lazyWithRetry(() => import("./pages/VMClusterPage.jsx"));
const CostAnalysisPage = lazyWithRetry(() => import("./pages/CostAnalysisEnhancedPage.jsx"));
const CostSimulatorPage = lazyWithRetry(() => import("./pages/CostSimulatorPage.jsx"));
const CostOptimizationPage = lazyWithRetry(() => import("./pages/CostOptimizationPage.jsx"));
const SecurityPage = lazyWithRetry(() => import("./pages/SecurityPage.jsx"));
const SecuritySettingsPage = lazyWithRetry(() => import("./pages/SecuritySettingsPage.jsx"));
const ProfilePage = lazyWithRetry(() => import("./pages/ProfilePage.jsx"));
const SettingsPage = lazyWithRetry(() => import("./pages/SettingsPage.jsx"));
const BillingPage = lazyWithRetry(() => import("./pages/BillingPage.jsx"));
const PricingPage = lazyWithRetry(() => import("./pages/PricingPage.jsx"));
const ContactPage = lazyWithRetry(() => import("./pages/ContactPage.jsx"));
const AboutPage = lazyWithRetry(() => import("./pages/AboutPage.jsx"));
const FeaturesPage = lazyWithRetry(() => import("./pages/FeaturesPage.jsx"));
const HelpCenterPage = lazyWithRetry(() => import("./pages/HelpCenterPage.jsx"));
const TermsOfServicePage = lazyWithRetry(() => import("./pages/TermsOfServicePage.jsx"));
const PrivacyPolicyPage = lazyWithRetry(() => import("./pages/PrivacyPolicyPage.jsx"));
const AccessDeniedPage = lazyWithRetry(() => import("./pages/AccessDeniedPage.jsx"));
const NotFoundPage = lazyWithRetry(() => import("./pages/NotFoundPage.jsx"));
const ServerErrorPage = lazyWithRetry(() => import("./pages/ServerErrorPage.jsx"));
const ServiceUnavailablePage = lazyWithRetry(() => import("./pages/ServiceUnavailablePage.jsx"));
const ProvisionPage = lazyWithRetry(() => import("./pages/ProvisionPage.jsx"));

// Admin pages (lazy loaded - only for admins)
const AdminLayout = lazyWithRetry(() => import("./components/admin/AdminLayout.jsx"));
const AdminOverviewPage = lazyWithRetry(() => import("./pages/admin/AdminOverviewPage.jsx"));
const AdminUsersPage = lazyWithRetry(() => import("./pages/admin/AdminUsersPage.jsx"));
const AdminAnalyticsPage = lazyWithRetry(() => import("./pages/admin/AdminAnalyticsPage.jsx"));
const AdminPaymentsPage = lazyWithRetry(() => import("./pages/admin/AdminPaymentsPage.jsx"));
const AdminSystemPage = lazyWithRetry(() => import("./pages/admin/AdminSystemPage.jsx"));
const AdminSettingsPage = lazyWithRetry(() => import("./pages/admin/AdminSettingsPage.jsx"));
const AdminTestPage = lazyWithRetry(() => import("./pages/admin/AdminTestPage.jsx"));
const TrustCenterPage = lazyWithRetry(() => import("./pages/TrustCenterPage.jsx"));
const CookiePolicyPage = lazyWithRetry(() => import("./pages/CookiePolicyPage.jsx"));
const DpaPage = lazyWithRetry(() => import("./pages/DpaPage.jsx"));
const StatusPage = lazyWithRetry(() => import("./pages/StatusPage.jsx"));
const VerifyEmailPage = lazyWithRetry(() => import("./pages/VerifyEmailPage.jsx"));
const PublicPricingPage = lazyWithRetry(() => import("./pages/PublicPricingPage.jsx"));
const SessionExpiredPage = lazyWithRetry(() => import("./pages/SessionExpiredPage.jsx"));
const BillingSuccessPage = lazyWithRetry(() => import("./pages/BillingSuccessPage.jsx"));
const BillingCancelPage = lazyWithRetry(() => import("./pages/BillingCancelPage.jsx"));
const DocsHubPage = lazyWithRetry(() => import("./pages/DocsHubPage.jsx"));
const NotificationsPage = lazyWithRetry(() => import("./pages/NotificationsPage.jsx"));
const TeamPage = lazyWithRetry(() => import("./pages/TeamPage.jsx"));
const AcceptInvitePage = lazyWithRetry(() => import("./pages/AcceptInvitePage.jsx"));
const SsoCallbackPage = lazyWithRetry(() => import("./pages/SsoCallbackPage.jsx"));
const SupportTicketPage = lazyWithRetry(() => import("./pages/SupportTicketPage.jsx"));
const SupportPage = lazyWithRetry(() => import("./pages/SupportPage.jsx"));
const AdminSupportPage = lazyWithRetry(() => import("./pages/admin/AdminSupportPage.jsx"));

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
      { path: "/support/ticket", element: <Suspense fallback={<LazyLoadFallback />}><SupportTicketPage /></Suspense> },
      { path: "/support/ticket/:referenceCode", element: <Suspense fallback={<LazyLoadFallback />}><SupportTicketPage /></Suspense> },
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
              { path: "support", element: <Suspense fallback={<LazyLoadFallback />}><SupportPage /></Suspense> },
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
              { path: "notifications", element: <Suspense fallback={<LazyLoadFallback />}><NotificationsPage /></Suspense> },
              { path: "test", element: <Suspense fallback={<LazyLoadFallback />}><AdminTestPage /></Suspense> },
              { path: "support", element: <Suspense fallback={<LazyLoadFallback />}><AdminSupportPage /></Suspense> },
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
