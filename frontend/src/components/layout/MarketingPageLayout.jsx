import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import Footer from './Footer.jsx';
import AnimatedBackground from '../AnimatedBackground.jsx';
import { useLandingNav } from '../../hooks/useLandingNav.js';
import { useLandingReveal } from '../../hooks/useLandingReveal.js';
import '../../styles/marketing-shell.css';

/**
 * Shared premium shell for public marketing pages (features, about, contact, help).
 * Matches landing page: backdrop, nav, scroll progress, scroll reveals.
 */
export default function MarketingPageLayout({ children, showFooter = true }) {
  const { user } = useAuth();
  const navScrolled = useLandingNav(16);
  useLandingReveal();

  return (
    <div className="marketing-page">
      <div className="landing-scroll-progress" aria-hidden="true" />
      <AnimatedBackground />

      <nav className={`landing-nav ${navScrolled ? 'landing-nav--scrolled' : ''}`}>
        <div className="nav-container">
          <Link to="/" className="nav-logo">
            <h2>Zenith</h2>
          </Link>
          <div className="nav-links">
            <Link to="/features">Features</Link>
            <Link to="/about">About</Link>
            <Link to="/contact">Contact</Link>
            <Link to="/help">Help</Link>
            {user ? (
              <Link to="/dashboard" className="btn-nav-signup">
                Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-nav-login">
                  Login
                </Link>
                <Link to="/register" className="btn-nav-signup">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <main className="marketing-page__main">{children}</main>

      {showFooter && (
        <div className="reveal-item marketing-page__footer">
          <Footer />
        </div>
      )}
    </div>
  );
}
