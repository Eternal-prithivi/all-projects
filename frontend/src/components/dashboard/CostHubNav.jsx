import React from 'react';
import { NavLink } from 'react-router-dom';

/** Sub-nav for Cost Analysis hub only — related tools linked from sidebar elsewhere */
export default function CostHubNav() {
  return (
    <nav className="zenith-cost-hub" aria-label="Cost tools">
      <NavLink to="/dashboard/costs" end>
        Analysis
      </NavLink>
      <NavLink to="/dashboard/simulator">Simulator</NavLink>
      <NavLink to="/dashboard/optimization">Optimization</NavLink>
      <NavLink to="/dashboard/pricing">Pricing</NavLink>
    </nav>
  );
}
