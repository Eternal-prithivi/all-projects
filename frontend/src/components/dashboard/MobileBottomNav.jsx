import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { FaEllipsisH } from 'react-icons/fa';
import MobileNavMoreSheet from './MobileNavMoreSheet.jsx';
import {
  DASHBOARD_MOBILE_PRIMARY,
  getDashboardMobileMoreItems,
} from '../../config/dashboardNavConfig.jsx';
import '../../styles/mobile-nav.css';

function MobileBottomNav({ user }) {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreItems = getDashboardMobileMoreItems(user);

  return (
    <>
      <nav className="mobile-bottom-nav" role="navigation" aria-label="Main navigation">
        <ul className="mobile-bottom-nav__tabs" data-tour="sidebar-nav">
          {DASHBOARD_MOBILE_PRIMARY.map((item) => (
            <li key={item.to} className="mobile-bottom-nav__tab">
              <NavLink
                to={item.to}
                end={item.end}
                aria-label={item.label}
                className={({ isActive }) =>
                  `mobile-bottom-nav__link ${isActive ? 'active' : ''}`
                }
              >
                <span className="mobile-bottom-nav__icon">{item.icon}</span>
                <span className="mobile-bottom-nav__label">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="mobile-bottom-nav__more"
          aria-label="More navigation"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen(true)}
        >
          <span className="mobile-bottom-nav__icon">
            <FaEllipsisH aria-hidden />
          </span>
          <span className="mobile-bottom-nav__label">More</span>
        </button>
      </nav>
      <MobileNavMoreSheet
        isOpen={moreOpen}
        onClose={() => setMoreOpen(false)}
        items={moreItems}
        user={user}
      />
    </>
  );
}

export default MobileBottomNav;
