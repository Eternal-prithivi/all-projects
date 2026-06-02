import React, { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { FaQuestionCircle, FaUserShield } from 'react-icons/fa';

function MobileNavMoreSheet({ isOpen, onClose, items, user }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
      document.removeEventListener('keydown', onKey);
    };
  }, [isOpen, onClose]);

  useEffect(
    () => () => {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    },
    []
  );

  if (!isOpen) return null;

  const userInitial = user?.username?.charAt(0).toUpperCase() || '?';

  return (
    <>
      <button type="button" className="mobile-nav-sheet-backdrop" aria-label="Close menu" onClick={onClose} />
      <div className="mobile-nav-sheet" role="dialog" aria-modal="true" aria-labelledby="mobile-nav-more-title">
        <div className="mobile-nav-sheet__header">
          <h2 id="mobile-nav-more-title" className="mobile-nav-sheet__title">
            More
          </h2>
          <button
            ref={closeRef}
            type="button"
            className="mobile-nav-sheet__close"
            aria-label="Close"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <ul className="mobile-nav-sheet__list" role="menu">
          {items.map((item) => {
            const key = item.to;
            let icon = item.icon;
            if (item.isHelp) icon = <FaQuestionCircle className="rail-icon" />;
            if (item.isAdmin) icon = <FaUserShield className="rail-icon" />;
            if (item.isSettings) {
              icon = <span className="mobile-nav-sheet__avatar">{item.userInitial ?? userInitial}</span>;
            }

            return (
              <li key={key} role="none">
                <NavLink
                  to={item.to}
                  end={item.end}
                  role="menuitem"
                  className={({ isActive }) =>
                    `mobile-nav-sheet__link ${isActive ? 'active' : ''}`
                  }
                  onClick={onClose}
                >
                  {icon ? <span className="mobile-bottom-nav__icon">{icon}</span> : null}
                  <span>{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );
}

export default MobileNavMoreSheet;
