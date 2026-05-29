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
        <div className="legal-header reveal-group">
          <div className="legal-header-content reveal-item">
            <FaFileContract className="legal-icon" />
            <h1>Data Processing Agreement</h1>
            <p className="last-updated">Last Updated: {lastUpdated}</p>
          </div>
        </div>

        <div className="legal-content reveal-item">
          <div className="legal-intro">
            <p>
              This Data Processing Agreement (&quot;DPA&quot;) forms part of the agreement between the
              customer (&quot;Controller&quot;) and Zenith (&quot;Processor&quot;) when the Controller
              uses Zenith&apos;s cloud optimization platform and related services.
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
              Controller authorizes Processor to engage subprocessors listed in the{' '}
              <Link to="/trust">Trust Center</Link> and Privacy Policy. Processor will impose equivalent
              data protection obligations on subprocessors.
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
            <h2>7. Executed agreements</h2>
            <p>
              Enterprise customers requiring a countersigned DPA should contact{' '}
              <Link to="/contact">sales</Link> or email{' '}
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
