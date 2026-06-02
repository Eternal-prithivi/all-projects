import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { FaBars, FaTimes } from 'react-icons/fa';
import '../../styles/mobile-marketing-nav.css';

/**
 * Hamburger + drawer for marketing/landing nav on small screens.
 * Drawer renders in a portal so it is not clipped by nav overflow/stacking.
 */
export default function MobileMarketingNav({ userLoggedIn, links }) {
  const [open, setOpen] = useState(false);
  const menuBtnRef = useRef(null);

  const close = () => {
    setOpen(false);
    menuBtnRef.current?.focus();
  };

  const toggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOpen((v) => !v);
  };

  useEffect(() => {
    if (!open) return undefined;
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  /* Ensure scroll lock never sticks if the component unmounts while open */
  useEffect(
    () => () => {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    },
    []
  );

  const drawer =
    open &&
    createPortal(
      <>
        <button
          type="button"
          className="mobile-marketing-nav__backdrop"
          aria-label="Close menu"
          onClick={close}
        />
        <nav
          id="mobile-marketing-nav-drawer"
          className="mobile-marketing-nav__drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Site navigation"
        >
          <div className="mobile-marketing-nav__drawer-head">
            <span className="mobile-marketing-nav__drawer-title">Menu</span>
            <button
              type="button"
              className="mobile-marketing-nav__close"
              aria-label="Close menu"
              onClick={close}
            >
              <FaTimes aria-hidden />
            </button>
          </div>
          <ul className="mobile-marketing-nav__list">
            {links.map((link) => {
              const className = ['mobile-marketing-nav__link', link.className]
                .filter(Boolean)
                .join(' ');
              if (link.href) {
                return (
                  <li key={link.href}>
                    <a href={link.href} className={className} onClick={close}>
                      {link.label}
                    </a>
                  </li>
                );
              }
              return (
                <li key={link.to}>
                  <Link to={link.to} className={className} onClick={close}>
                    {link.label}
                  </Link>
                </li>
              );
            })}
            {userLoggedIn ? (
              <li>
                <Link
                  to="/dashboard"
                  className="mobile-marketing-nav__link btn-nav-signup"
                  onClick={close}
                >
                  Dashboard
                </Link>
              </li>
            ) : (
              <>
                <li>
                  <Link to="/login" className="mobile-marketing-nav__link btn-nav-login" onClick={close}>
                    Login
                  </Link>
                </li>
                <li>
                  <Link
                    to="/register"
                    className="mobile-marketing-nav__link btn-nav-signup"
                    onClick={close}
                  >
                    Sign Up
                  </Link>
                </li>
              </>
            )}
          </ul>
        </nav>
      </>,
      document.body
    );

  return (
    <div className="mobile-marketing-nav">
      <button
        ref={menuBtnRef}
        type="button"
        className="mobile-marketing-nav__toggle"
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
        aria-controls="mobile-marketing-nav-drawer"
        onClick={toggle}
      >
        {open ? <FaTimes aria-hidden /> : <FaBars aria-hidden />}
      </button>
      {drawer}
    </div>
  );
}
