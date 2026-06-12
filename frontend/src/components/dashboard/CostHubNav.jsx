import React from 'react';
import { NavLink } from 'react-router-dom';
import { FaLock } from 'react-icons/fa';
import { COST_HUB_LINKS } from '../../config/dashboardNavConfig.jsx';
import { usePlanEntitlementsContext } from '../../context/PlanEntitlementsContext.jsx';

export default function CostHubNav() {
  const { isNavLocked, openUpgradeDrawer } = usePlanEntitlementsContext();

  return (
    <nav className="zenith-cost-hub" aria-label="Cost tools">
      {COST_HUB_LINKS.map((link) => {
        const locked = link.navId ? isNavLocked(link.navId) : false;
        if (locked && link.lockNavBlock) {
          return (
            <button
              key={link.to}
              type="button"
              className="zenith-cost-hub__locked"
              onClick={() => openUpgradeDrawer(link.navId)}
            >
              {link.label}
              <FaLock className="zenith-cost-hub__lock" aria-hidden />
            </button>
          );
        }
        return (
          <NavLink key={link.to} to={link.to} end={link.end}>
            {link.label}
            {locked && <FaLock className="zenith-cost-hub__lock" aria-hidden />}
          </NavLink>
        );
      })}
    </nav>
  );
}
