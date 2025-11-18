import React, { useState, useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import Sidebar from "./Sidebar.jsx";
import Header from "./Header.jsx";
import Footer from "../Footer.jsx";
import Breadcrumbs from "../Breadcrumbs.jsx";
import QuickActions from "../QuickActions.jsx";
import KeyboardShortcuts from "../KeyboardShortcuts.jsx";
import GlobalSearch from "../GlobalSearch.jsx";
import "../../styles/dashboard.css";
import "../../styles/cards.css";
import "../../styles/toast-custom.css";

function DashboardLayout() {
  const { user } = useAuth();
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
      
      // Quick actions
      if (e.key === 'n' || e.key === 'N') {
        if (!showSearch && !showShortcuts) {
          e.preventDefault();
          navigate('/dashboard/vmcluster');
        }
      }
      if (e.key === 'u' || e.key === 'U') {
        if (!showSearch && !showShortcuts) {
          e.preventDefault();
          navigate('/dashboard/storage');
        }
      }
      if (e.key === 'c' || e.key === 'C') {
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
    <div className="dashboard-page">
      <Sidebar user={user} />
      <div className="dashboard-main">
        <Header user={user} />
        <div className="dashboard-breadcrumbs-wrapper">
          <Breadcrumbs />
        </div>
        <main className="dashboard-content">
          <Outlet />
        </main>
        <Footer />
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
    </div>
  );
}

export default DashboardLayout;
