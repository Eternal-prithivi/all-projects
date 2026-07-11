import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ACCOUNT_HUB_LINKS } from '../../config/accountHubNavConfig.js';

export default function AccountHubNav() {
  const location = useLocation();
  const inAdminArea = location.pathname.startsWith('/admin');

  if (inAdminArea) {
    return (
      <nav className="zenith-account-hub" aria-label="Account settings">
        {ACCOUNT_HUB_LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} end={link.end}>
            {link.label}
          </NavLink>
        ))}
        <NavLink to="/admin/settings" end>
          Platform settings
        </NavLink>
      </nav>
    );
  }

  return (
    <nav className="zenith-account-hub" aria-label="Account settings">
      {ACCOUNT_HUB_LINKS.map((link) => (
        <NavLink key={link.to} to={link.to} end={link.end}>
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
