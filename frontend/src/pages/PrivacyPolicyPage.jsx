import React from 'react';
import { FaShieldAlt } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/legal-pages.css';

const PrivacyPolicyPage = () => {
  const lastUpdated = "November 30, 2025";

  return (
    <MarketingPageLayout>
    <div className="legal-page">
      <div className="legal-header reveal-group">
        <div className="legal-header-content reveal-item">
          <FaShieldAlt className="legal-icon" />
          <h1>Privacy Policy</h1>
          <p className="last-updated">Last Updated: {lastUpdated}</p>
        </div>
      </div>

      <div className="legal-content reveal-item">
        <div className="legal-intro">
          <p>
            At Zenith, we take your privacy seriously. This Privacy Policy explains how we collect, use, disclose, 
            and safeguard your information when you use our cloud resource optimization platform. Please read this 
            policy carefully to understand our practices regarding your data.
          </p>
          <p>
            By using Zenith, you agree to the collection and use of information in accordance with this Privacy Policy.
          </p>
        </div>

        <section className="legal-section">
          <h2>1. Information We Collect</h2>
          
          <h3>1.1 Information You Provide</h3>
          <p>We collect information that you voluntarily provide to us, including:</p>
          <ul>
            <li><strong>Account Information:</strong> Username, email address, password (encrypted)</li>
            <li><strong>Profile Information:</strong> Name, profile picture, preferences, settings</li>
            <li><strong>Billing Information:</strong> Payment method details (processed securely through Razorpay)</li>
            <li><strong>Support Communications:</strong> Messages, feedback, and correspondence with our support team</li>
            <li><strong>User Content:</strong> Files, data, and configurations you upload to our Service</li>
          </ul>

          <h3>1.2 Automatically Collected Information</h3>
          <p>When you use our Service, we automatically collect certain information:</p>
          <ul>
            <li><strong>Usage Data:</strong> Pages visited, features used, time spent, actions taken</li>
            <li><strong>Device Information:</strong> Browser type, device type, operating system, IP address</li>
            <li><strong>Location Data:</strong> General geographic location based on IP address</li>
            <li><strong>Session Data:</strong> Login times, session duration, active sessions</li>
            <li><strong>Performance Data:</strong> VM metrics, storage usage, resource consumption</li>
            <li><strong>Cookies and Tracking:</strong> Authentication tokens, preferences, analytics data</li>
          </ul>

          <h3>1.3 Third-Party Information</h3>
          <p>We may receive information from third-party services:</p>
          <ul>
            <li><strong>Cloud Providers:</strong> AWS, Google Cloud Platform, Microsoft Azure (usage metrics, costs)</li>
            <li><strong>Payment Processor:</strong> Razorpay (transaction status, payment confirmation)</li>
            <li><strong>Authentication Services:</strong> OAuth providers if you use social login</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>2. How We Use Your Information</h2>
          <p>We use the collected information for the following purposes:</p>

          <h3>2.1 Service Provision</h3>
          <ul>
            <li>Create and manage your account</li>
            <li>Provide access to virtual machines and storage</li>
            <li>Process payments and manage subscriptions</li>
            <li>Optimize cloud resource allocation and costs</li>
            <li>Generate usage reports and analytics</li>
          </ul>

          <h3>2.2 Service Improvement</h3>
          <ul>
            <li>Analyze usage patterns to improve features</li>
            <li>Develop new features and services</li>
            <li>Train machine learning models for optimization</li>
            <li>Monitor and improve platform performance</li>
          </ul>

          <h3>2.3 Communication</h3>
          <ul>
            <li>Send service notifications and updates</li>
            <li>Respond to your inquiries and support requests</li>
            <li>Send billing information and invoices</li>
            <li>Deliver security alerts and important announcements</li>
            <li>Send marketing communications (with your consent, opt-out available)</li>
          </ul>

          <h3>2.4 Security and Compliance</h3>
          <ul>
            <li>Detect and prevent fraud and unauthorized access</li>
            <li>Monitor for security threats and vulnerabilities</li>
            <li>Comply with legal obligations and regulations</li>
            <li>Enforce our Terms of Service</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>3. How We Share Your Information</h2>
          <p>We do not sell your personal information. We may share your information in the following circumstances:</p>

          <h3>3.1 Service Providers</h3>
          <p>We share information with third-party service providers who assist us in operating our Service:</p>
          <ul>
            <li><strong>Cloud Infrastructure:</strong> AWS, Google Cloud, Azure (to host your data and VMs)</li>
            <li><strong>Payment Processing:</strong> Razorpay (to process payments securely)</li>
            <li><strong>Email Services:</strong> Gmail API (to send notifications and support emails)</li>
            <li><strong>Analytics:</strong> Service analytics providers (aggregated, anonymized data)</li>
          </ul>

          <h3>3.2 Legal Requirements</h3>
          <p>We may disclose your information if required by law or to:</p>
          <ul>
            <li>Comply with legal processes, court orders, or government requests</li>
            <li>Enforce our Terms of Service and policies</li>
            <li>Protect the rights, property, or safety of Zenith, our users, or others</li>
            <li>Prevent fraud, security threats, or illegal activities</li>
          </ul>

          <h3>3.3 Business Transfers</h3>
          <p>
            In the event of a merger, acquisition, or sale of assets, your information may be transferred to the 
            acquiring entity. We will notify you before your information is transferred and becomes subject to a 
            different privacy policy.
          </p>

          <h3>3.4 With Your Consent</h3>
          <p>We may share your information with your explicit consent for specific purposes not covered above.</p>
        </section>

        <section className="legal-section">
          <h2>4. Data Security</h2>
          <p>We implement industry-standard security measures to protect your information:</p>

          <h3>4.1 Encryption</h3>
          <ul>
            <li><strong>In Transit:</strong> All data transmitted between you and our servers is encrypted using TLS 1.3</li>
            <li><strong>At Rest:</strong> All stored data is encrypted using AES-256 encryption</li>
            <li><strong>Optional Manual Encryption:</strong> Additional encryption available for sensitive files</li>
          </ul>

          <h3>4.2 Access Controls</h3>
          <ul>
            <li>Strong password requirements and hashing (bcrypt)</li>
            <li>Two-factor authentication (2FA) support</li>
            <li>Session management with automatic timeout</li>
            <li>Role-based access control (admin vs. user permissions)</li>
            <li>SSH key-based authentication for VM access</li>
          </ul>

          <h3>4.3 Monitoring and Auditing</h3>
          <ul>
            <li>Activity logging for all security-related events</li>
            <li>Regular security audits and vulnerability assessments</li>
            <li>Intrusion detection and prevention systems</li>
            <li>Automated backup and disaster recovery procedures</li>
          </ul>

          <h3>4.4 Limitations</h3>
          <p>
            While we strive to protect your information, no method of transmission or storage is 100% secure. 
            You are responsible for maintaining the security of your account credentials.
          </p>
        </section>

        <section className="legal-section">
          <h2>5. Data Retention</h2>
          <p>We retain your information for as long as necessary to provide our Service and comply with legal obligations:</p>
          <ul>
            <li><strong>Active Accounts:</strong> Data retained while your account is active</li>
            <li><strong>Inactive Accounts:</strong> Data may be deleted after 12 months of inactivity (with notice)</li>
            <li><strong>Deleted Accounts:</strong> Data deleted within 30 days of account deletion (backups within 90 days)</li>
            <li><strong>Billing Records:</strong> Retained for 7 years for tax and accounting purposes</li>
            <li><strong>Activity Logs:</strong> Retained for 90 days for security monitoring</li>
          </ul>
          <p>
            You can request data deletion at any time by contacting support. Some information may be retained in 
            anonymized form for analytics purposes.
          </p>
        </section>

        <section className="legal-section">
          <h2>6. Your Privacy Rights</h2>
          <p>You have the following rights regarding your personal information:</p>

          <h3>6.1 Access and Portability</h3>
          <ul>
            <li>Request a copy of your personal data</li>
            <li>Export your data in a machine-readable format</li>
            <li>View your activity history and session information</li>
          </ul>

          <h3>6.2 Correction and Update</h3>
          <ul>
            <li>Update your profile information at any time</li>
            <li>Correct inaccurate or incomplete data</li>
            <li>Modify your communication preferences</li>
          </ul>

          <h3>6.3 Deletion</h3>
          <ul>
            <li>Request deletion of your account and associated data</li>
            <li>Delete specific files or content you've uploaded</li>
            <li>Revoke API keys and access tokens</li>
          </ul>

          <h3>6.4 Restriction and Objection</h3>
          <ul>
            <li>Opt out of marketing communications</li>
            <li>Disable optional data collection (e.g., analytics)</li>
            <li>Object to automated decision-making</li>
          </ul>

          <p>To exercise these rights, contact us at aangatla957@gmail.com or use your account settings.</p>
        </section>

        <section className="legal-section">
          <h2>7. Cookies and Tracking Technologies</h2>
          <p>We use cookies and similar technologies to enhance your experience:</p>

          <h3>7.1 Essential Cookies</h3>
          <ul>
            <li>Authentication tokens (JWT) to maintain your login session</li>
            <li>Security tokens for CSRF protection</li>
            <li>Session management and preferences</li>
          </ul>

          <h3>7.2 Analytics Cookies</h3>
          <ul>
            <li>Usage statistics and performance monitoring</li>
            <li>Feature adoption tracking</li>
            <li>Error reporting and debugging</li>
          </ul>

          <h3>7.3 Cookie Control</h3>
          <p>
            You can control cookies through your browser settings. Note that disabling essential cookies may affect 
            the functionality of our Service.
          </p>
        </section>

        <section className="legal-section">
          <h2>8. Children's Privacy</h2>
          <p>
            Our Service is not intended for individuals under 18 years of age. We do not knowingly collect personal 
            information from children. If we become aware that we have collected information from a child without 
            parental consent, we will take steps to delete that information.
          </p>
        </section>

        <section className="legal-section">
          <h2>9. International Data Transfers</h2>
          <p>
            Your information may be processed and stored in different countries where our cloud providers operate 
            (including the United States, Europe, and Asia). We ensure that appropriate safeguards are in place to 
            protect your data when transferred internationally, including:
          </p>
          <ul>
            <li>Standard Contractual Clauses (SCCs) with cloud providers</li>
            <li>Compliance with GDPR for European users</li>
            <li>Encryption during transfer and storage</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>10. Third-Party Links</h2>
          <p>
            Our Service may contain links to third-party websites or services (e.g., AWS Console, GCP Console). 
            We are not responsible for the privacy practices of these third parties. We encourage you to read their 
            privacy policies before providing any personal information.
          </p>
        </section>

        <section className="legal-section">
          <h2>11. Changes to This Privacy Policy</h2>
          <p>
            We may update this Privacy Policy from time to time to reflect changes in our practices or legal requirements. 
            We will notify you of material changes via email or through a prominent notice on our Service. The "Last Updated" 
            date at the top of this policy indicates when it was last revised.
          </p>
          <p>
            Your continued use of the Service after changes to this Privacy Policy constitutes acceptance of the updated policy.
          </p>
        </section>

        <section className="legal-section">
          <h2>12. Compliance with Regulations</h2>
          <p>We comply with applicable data protection regulations, including:</p>
          <ul>
            <li><strong>GDPR:</strong> General Data Protection Regulation (European users)</li>
            <li><strong>IT Act, 2000:</strong> Information Technology Act (Indian users)</li>
            <li><strong>SPDI Rules:</strong> Sensitive Personal Data or Information Rules (India)</li>
          </ul>
          <p>If you are in the European Union, you have additional rights under GDPR, including the right to lodge a complaint with a supervisory authority.</p>
        </section>

        <section className="legal-section">
          <h2>13. Contact Us</h2>
          <p>
            If you have questions, concerns, or requests regarding this Privacy Policy or our data practices, 
            please contact us:
          </p>
          <div className="contact-info">
            <p><strong>Email:</strong> aangatla957@gmail.com</p>
            <p><strong>Website:</strong> <a href="http://localhost:5173/contact">Contact Us</a></p>
            <p><strong>Data Protection Officer:</strong> Available upon request</p>
          </div>
        </section>

        <div className="legal-footer">
          <p>
            By using Zenith, you acknowledge that you have read and understood this Privacy Policy and agree to 
            our collection, use, and disclosure of your information as described herein.
          </p>
        </div>
      </div>
    </div>
    </MarketingPageLayout>
  );
};

export default PrivacyPolicyPage;
