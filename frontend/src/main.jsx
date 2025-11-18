import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App.jsx";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import DashboardLayout from "./components/dashboard/DashboardLayout.jsx"; // Import the new layout
import DashboardPage from "./pages/DashboardPage.jsx";
import StoragePage from "./pages/StoragePage.jsx";
import VMClusterPage from "./pages/VMClusterPage.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import "./index.css";
import SecurityPage from "./pages/SecurityPage.jsx";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      // --- Public Routes ---
      { index: true, element: <HomePage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },

      // --- Protected Routes ---
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: "dashboard",
            element: <DashboardLayout />, // The layout is applied here
            children: [
              { index: true, element: <DashboardPage /> },
              { path: "storage", element: <StoragePage /> },
              { path: "vmcluster", element: <VMClusterPage /> },
              { path: "security", element: <SecurityPage /> }, // Add this route
            ],
          },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </React.StrictMode>
);
