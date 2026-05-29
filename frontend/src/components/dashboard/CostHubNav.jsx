import { NavLink } from 'react-router-dom';

/** Shared sub-nav for all /dashboard cost-related pages */
export default function CostHubNav() {
  return (
    <nav className="zenith-cost-hub" aria-label="Cost tools">
      <NavLink to="/dashboard/costs" end>
        Analysis
      </NavLink>
      <NavLink to="/dashboard/simulator">Simulator</NavLink>
      <NavLink to="/dashboard/optimization">Optimization</NavLink>
      <NavLink to="/dashboard/billing">Billing</NavLink>
      <NavLink to="/dashboard/pricing">Pricing</NavLink>
    </nav>
  );
}
