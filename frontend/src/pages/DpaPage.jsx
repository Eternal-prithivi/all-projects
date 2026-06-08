import React from 'react';
import { Link } from 'react-router-dom';
import { FaFileContract } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/legal-pages.css';

export default function DpaPage() {
  const lastUpdated = 'May 29, 2026';

  return (
    <MarketingPageLayout>
      <div className="legal-page">
        <div className="legal-header">
          <div className="legal-header-content">
            <span className="legal-icon" aria-hidden="true">
              <FaFileContract />
            </span>
            <h1>Data Processing Agreement</h1>
            <p className="last-updated">Last Updated: {lastUpdated}</p>
          </div>
        </div>

        <div className="legal-content">
          <div className="legal-intro">
            <p>
              This Data Processing Agreement (&quot;DPA&quot;) forms part of the agreement between the
              customer (&quot;Controller&quot;) and Zenith, operated by Rajverse (&quot;Processor&quot;),
              when the Controller uses Zenith&apos;s multi-cloud resource optimization platform — including
              cost analysis, storage orchestration, VM management, secure vault, and BYOC (bring your own cloud)
              integrations.
            </p>
            <p>
              This DPA supplements our{' '}
              <Link to="/legal/terms">Terms of Service</Link> and{' '}
              <Link to="/legal/privacy">Privacy Policy</Link>. By using paid or enterprise features of
              Zenith, Controller agrees to the data processing terms below.
            </p>
          </div>

          <section className="legal-section">
            <h2>1. Definitions</h2>
            <p>
              &quot;Personal Data&quot; means any information relating to an identified or identifiable
              natural person processed by Processor on behalf of Controller through the Service.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Scope and roles</h2>
            <ul>
              <li>Controller determines purposes and means of processing account and usage data.</li>
              <li>Processor processes Personal Data only on documented instructions from Controller.</li>
              <li>
                BYOC configurations may cause Controller data to reside in Controller-owned cloud
                accounts; Processor access is limited to operations required to deliver the Service.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Processor obligations</h2>
            <ul>
              <li>Process Personal Data only to provide, secure, and improve the Service</li>
              <li>Ensure personnel with access are bound by confidentiality</li>
              <li>Implement appropriate technical and organizational security measures</li>
              <li>Assist Controller with data subject requests where feasible</li>
              <li>Notify Controller without undue delay of confirmed Personal Data breaches</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>4. Subprocessors</h2>
            <p>
              Controller authorizes Processor to engage subprocessors required to operate the Service.
              Processor will impose equivalent data protection obligations on subprocessors and will
              notify Controller of material changes where required by law.
            </p>
            <p>Current subprocessors include, as applicable to your deployment:</p>
            <ul>
              <li>MongoDB Atlas — application database and user account data</li>
              <li>Render — API hosting (staging/production)</li>
              <li>Vercel — frontend hosting and CDN</li>
              <li>Razorpay — payment processing (billing data only)</li>
              <li>AWS, GCP, or Azure — per your BYOC configuration for storage, VMs, and cost data</li>
              <li>Transactional email provider — account notifications and security alerts</li>
            </ul>
            <p>
              See the <Link to="/trust">Trust Center</Link> for an overview and the{' '}
              <Link to="/legal/privacy">Privacy Policy</Link> for details on data categories processed.
            </p>
          </section>

          <section className="legal-section">
            <h2>5. International transfers</h2>
            <p>
              Where Personal Data is transferred outside the Controller&apos;s jurisdiction, Processor
              will use appropriate safeguards (such as standard contractual clauses) where required by
              applicable law.
            </p>
          </section>

          <section className="legal-section">
            <h2>6. Retention and deletion</h2>
            <p>
              Upon termination, Processor will delete or return Personal Data per Controller instructions,
              subject to legal retention requirements. Account deletion flows are available in Profile
              settings.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Security measures</h2>
            <p>Processor implements appropriate technical and organizational measures, including:</p>
            <ul>
              <li>TLS encryption for data in transit</li>
              <li>Role-based access control and optional two-factor authentication</li>
              <li>Audit logging for security-sensitive actions</li>
              <li>Client-side encryption options for secure vault uploads</li>
              <li>Rate limiting and session management</li>
              <li>BYOC architecture so cloud credentials remain in Controller-owned accounts where configured</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>8. Audits and cooperation</h2>
            <p>
              Upon reasonable written request, Processor will provide information necessary to demonstrate
              compliance with this DPA. Processor may satisfy audit requests through third-party
              certifications or summaries where available, subject to confidentiality obligations.
            </p>
          </section>

          <section className="legal-section">
            <h2>9. Executed agreements</h2>
            <p>
              Enterprise customers requiring a countersigned DPA should contact us via{' '}
              <Link to="/contact">Contact</Link> or email{' '}
              <a href="mailto:support@rajverse.me">support@rajverse.me</a>.
            </p>
          </section>

          <section className="legal-section">
            <h2>Related documents</h2>
            <ul>
              <li>
                <Link to="/legal/privacy">Privacy Policy</Link>
              </li>
              <li>
                <Link to="/legal/terms">Terms of Service</Link>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
