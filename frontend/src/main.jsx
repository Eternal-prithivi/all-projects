import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import LazyLoadFallback from "./components/LazyLoadFallback.jsx";
import "./index.css";

// Eager load: Critical pages needed immediately
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

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
const HelpCenterPage = lazy(() => import("./pages/HelpCenterPage.jsx"));
const TermsOfServicePage = lazy(() => import("./pages/TermsOfServicePage.jsx"));
const PrivacyPolicyPage = lazy(() => import("./pages/PrivacyPolicyPage.jsx"));
const AccessDeniedPage = lazy(() => import("./pages/AccessDeniedPage.jsx"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage.jsx"));
const ServerErrorPage = lazy(() => import("./pages/ServerErrorPage.jsx"));

// Admin pages (lazy loaded - only for admins)
const AdminLayout = lazy(() => import("./components/admin/AdminLayout.jsx"));
const AdminOverviewPage = lazy(() => import("./pages/admin/AdminOverviewPage.jsx"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage.jsx"));
const AdminAnalyticsPage = lazy(() => import("./pages/admin/AdminAnalyticsPage.jsx"));
const AdminPaymentsPage = lazy(() => import("./pages/admin/AdminPaymentsPage.jsx"));
const AdminSystemPage = lazy(() => import("./pages/admin/AdminSystemPage.jsx"));
const AdminSettingsPage = lazy(() => import("./pages/admin/AdminSettingsPage.jsx"));
const AdminTestPage = lazy(() => import("./pages/admin/AdminTestPage.jsx"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      // --- Public Routes (eager loaded) ---
      { index: true, element: <HomePage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      
      // --- Public Routes (lazy loaded) ---
      { path: "/contact", element: <Suspense fallback={<LazyLoadFallback />}><ContactPage /></Suspense> },
      { path: "/about", element: <Suspense fallback={<LazyLoadFallback />}><AboutPage /></Suspense> },
      { path: "/access-denied", element: <Suspense fallback={<LazyLoadFallback />}><AccessDeniedPage /></Suspense> },
      { path: "/help", element: <Suspense fallback={<LazyLoadFallback />}><HelpCenterPage /></Suspense> },
      { path: "/legal/terms", element: <Suspense fallback={<LazyLoadFallback />}><TermsOfServicePage /></Suspense> },
      { path: "/legal/privacy", element: <Suspense fallback={<LazyLoadFallback />}><PrivacyPolicyPage /></Suspense> },

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
      { path: "*", element: <Suspense fallback={<LazyLoadFallback />}><NotFoundPage /></Suspense> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
