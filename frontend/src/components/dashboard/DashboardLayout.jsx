import React from "react";
import { Outlet } from "react-router-dom";
// This is the corrected import path (../.. goes up two levels)
import { useAuth } from "../../context/AuthContext.jsx";
import Sidebar from "./Sidebar.jsx";
import Header from "./Header.jsx";
import "../../styles/dashboard.css";
import "../../styles/cards.css";

function DashboardLayout() {
  const { user } = useAuth();

  return (
    <div className="dashboard-page">
      <Sidebar user={user} />
      <div className="dashboard-main">
        <Header user={user} />
        <main className="dashboard-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
