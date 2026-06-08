import React from 'react';
import { Link } from 'react-router-dom';
import { FaShieldAlt, FaLock, FaServer, FaUserShield } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/legal-pages.css';
import '../styles/trust-center.css';

const TRUST_PILLARS = [
  {
    icon: <FaLock />,
    title: 'Encryption',
    text: 'Data in transit uses TLS. Secure vault files support client-side encryption and SSE options for object storage.',
  },
  {
    icon: <FaUserShield />,
    title: 'Access control',
    text: 'Role-based admin portal, session management, optional 2FA, and audit logging for security-sensitive actions.',
  },
  {
    icon: <FaServer />,
    title: 'BYOC architecture',
    text: 'Bring your own cloud credentials and buckets. Zenith orchestrates optimization without requiring blanket root keys in UI.',
  },
  {
    icon: <FaShieldAlt />,
    title: 'Operational security',
    text: 'Platform maintenance mode, health monitoring, and documented subprocessors in our privacy and DPA materials.',
  },
];

export default function TrustCenterPage() {
  return (
    <MarketingPageLayout>
      <div className="legal-page trust-center-page">
        <div className="legal-header">
          <div className="legal-header-content">
            <span className="legal-icon" aria-hidden="true">
              <FaShieldAlt />
            </span>
            <h1>Trust Center</h1>
            <p className="last-updated">Security & compliance overview for Zenith</p>
          </div>
        </div>

        <div className="legal-content">
          <div className="legal-intro">
            <p>
              Zenith is built for teams that need visibility into cloud spend, storage, and security
              without sacrificing control. This page summarizes how we approach security — for full
              legal terms see our policies linked below.
            </p>
          </div>

          <div className="trust-pillars">
            {TRUST_PILLARS.map((p) => (
              <article key={p.title} className="trust-pillar">
                <div className="trust-pillar__icon">{p.icon}</div>
                <h2>{p.title}</h2>
                <p>{p.text}</p>
              </article>
            ))}
          </div>

          <section className="legal-section">
            <h2>Compliance & policies</h2>
            <ul>
              <li>
                <Link to="/legal/privacy">Privacy Policy</Link> — data collection, retention, and rights
              </li>
              <li>
                <Link to="/legal/dpa">Data Processing Agreement (DPA)</Link> — processor obligations for
                enterprise customers
              </li>
              <li>
                <Link to="/legal/cookies">Cookie Policy</Link> — how we use cookies and similar technologies
              </li>
              <li>
                <Link to="/legal/terms">Terms of Service</Link> — acceptable use and liability
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>Subprocessors</h2>
            <p>We rely on vetted providers to operate the platform, including:</p>
            <ul>
              <li>Cloud infrastructure (AWS, GCP, Azure — per your BYOC configuration)</li>
              <li>MongoDB Atlas (application database)</li>
              <li>Razorpay (payments)</li>
              <li>Email delivery (transactional notifications)</li>
            </ul>
            <p>
              Details and updates are reflected in the Privacy Policy. Enterprise customers may request
              a subprocessor list via <Link to="/contact">Contact</Link>.
            </p>
          </section>

          <section className="legal-section">
            <h2>Report a security issue</h2>
            <p>
              If you discover a vulnerability, contact us at{' '}
              <a href="mailto:support@rajverse.me">support@rajverse.me</a> with steps to reproduce.
              Please avoid public disclosure until we acknowledge receipt.
            </p>
          </section>

          <section className="legal-section">
            <h2>System status</h2>
            <p>
              Check platform availability on our <Link to="/status">status page</Link>.
            </p>
          </section>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
