import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { getDashboardStats } from "../api.js";
import StatCard from "../components/dashboard/StatCard.jsx";
import {
  IconDollarSign,
  IconServer,
  IconHardDrive,
  IconShieldCheck,
} from "../components/dashboard/Icons.jsx";

function DashboardPage() {
  const { token, user } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      if (token) {
        try {
          const statsData = await getDashboardStats(token);
          setStats(statsData);
        } catch (error) {
          console.error("Failed to fetch dashboard stats:", error);
        }
      }
    };
    fetchStats();
  }, [token]);

  if (!user || !stats) {
    return (
      <div style={{ color: "white", textAlign: "center", paddingTop: "5rem" }}>
        Loading...
      </div>
    );
  }

  return (
    // This component now ONLY renders the page-specific content
    <>
      <div className="welcome-message">
        <h2>Dashboard Overview</h2>
        <p>
          Welcome back, {user.username}! Here's a snapshot of your cloud
          environment.
        </p>
      </div>
      <div className="stats-grid">
        <StatCard
          title="Monthly Costs"
          value={`$${stats.monthly_costs.toLocaleString()}`}
          icon={<IconDollarSign />}
        />
        <StatCard
          title="Active VMs"
          value={stats.active_vms}
          icon={<IconServer />}
        />
        <StatCard
          title="Storage Used"
          value={`${stats.storage_used_tb} TB`}
          icon={<IconHardDrive />}
        />
        <StatCard
          title="Security Alerts"
          value={stats.security_alerts}
          icon={<IconShieldCheck />}
        />
      </div>
    </>
  );
}

export default DashboardPage;
