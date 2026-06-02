import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { FaEllipsisH } from 'react-icons/fa';
import MobileNavMoreSheet from '../dashboard/MobileNavMoreSheet.jsx';
import { ADMIN_MOBILE_PRIMARY, getAdminMobileMoreItems } from '../../config/adminNavConfig.jsx';
import '../../styles/mobile-nav.css';

function AdminMobileBottomNav({ user }) {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreItems = getAdminMobileMoreItems(user);

  return (
    <>
      <nav className="mobile-bottom-nav" role="navigation" aria-label="Admin navigation">
        <ul className="mobile-bottom-nav__tabs">
          {ADMIN_MOBILE_PRIMARY.map((item) => (
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

export default AdminMobileBottomNav;
