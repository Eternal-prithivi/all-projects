import React from 'react';
import { Link } from 'react-router-dom';
import { FaCookieBite } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/legal-pages.css';

export default function CookiePolicyPage() {
  const lastUpdated = 'May 29, 2026';

  return (
    <MarketingPageLayout>
      <div className="legal-page">
        <div className="legal-header">
          <div className="legal-header-content">
            <span className="legal-icon" aria-hidden="true">
              <FaCookieBite />
            </span>
            <h1>Cookie Policy</h1>
            <p className="last-updated">Last Updated: {lastUpdated}</p>
          </div>
        </div>

        <div className="legal-content">
          <div className="legal-intro">
            <p>
              This Cookie Policy explains how Zenith uses cookies and similar technologies when you
              visit our website or use our application. It should be read together with our{' '}
              <Link to="/legal/privacy">Privacy Policy</Link>.
            </p>
          </div>

          <section className="legal-section">
            <h2>1. What are cookies?</h2>
            <p>
              Cookies are small text files stored on your device. They help us remember preferences,
              keep you signed in, and understand how the product is used.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Cookies we use</h2>
            <h3>2.1 Strictly necessary</h3>
            <ul>
              <li>Authentication session (e.g. access token storage for logged-in users)</li>
              <li>Security and load-balancing cookies</li>
              <li>Cookie consent preference (`zenith_cookie_consent`)</li>
            </ul>
            <h3>2.2 Functional</h3>
            <ul>
              <li>Theme preference (light / dark / auto)</li>
              <li>Onboarding and UI tour completion flags</li>
            </ul>
            <h3>2.3 Analytics (optional)</h3>
            <p>
              We may use privacy-respecting analytics to improve the product. Non-essential analytics
              are only enabled when you accept cookies via our consent banner.
            </p>
          </section>

          <section className="legal-section">
            <h2>3. Managing cookies</h2>
            <p>
              You can clear or block cookies in your browser settings. Blocking essential cookies may
              prevent login or certain features from working.
            </p>
            <p>
              To reset your consent choice, clear site data for Zenith or remove the
              `zenith_cookie_consent` entry in local storage, then reload the page.
            </p>
          </section>

          <section className="legal-section">
            <h2>4. Contact</h2>
            <p>
              Questions about this policy: <a href="mailto:support@rajverse.me">support@rajverse.me</a>
            </p>
          </section>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
