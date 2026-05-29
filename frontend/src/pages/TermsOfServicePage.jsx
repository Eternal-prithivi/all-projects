import React from 'react';
import { FaFileContract } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/legal-pages.css';

const TermsOfServicePage = () => {
  const lastUpdated = "November 30, 2025";

  return (
    <MarketingPageLayout>
    <div className="legal-page">
      <div className="legal-header reveal-group">
        <div className="legal-header-content reveal-item">
          <FaFileContract className="legal-icon" />
          <h1>Terms of Service</h1>
          <p className="last-updated">Last Updated: {lastUpdated}</p>
        </div>
      </div>

      <div className="legal-content reveal-item">
        <div className="legal-intro">
          <p>
            Welcome to Zenith. These Terms of Service ("Terms") govern your access to and use of Zenith's 
            cloud resource optimization platform, including our website, services, and applications 
            (collectively, the "Service"). By accessing or using the Service, you agree to be bound by these Terms.
          </p>
          <p>
            Please read these Terms carefully. If you do not agree to these Terms, you may not access or use the Service.
          </p>
        </div>

        <section className="legal-section">
          <h2>1. Acceptance of Terms</h2>
          <p>
            By creating an account, accessing, or using Zenith's services, you acknowledge that you have read, 
            understood, and agree to be bound by these Terms and our Privacy Policy. If you are using the Service 
            on behalf of an organization, you represent and warrant that you have the authority to bind that 
            organization to these Terms.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Account Registration</h2>
          <h3>2.1 Account Creation</h3>
          <p>
            To use certain features of the Service, you must register for an account. You agree to provide accurate, 
            current, and complete information during registration and to update such information to keep it accurate, 
            current, and complete.
          </p>
          
          <h3>2.2 Account Security</h3>
          <p>
            You are responsible for maintaining the confidentiality of your account credentials and for all activities 
            that occur under your account. You agree to:
          </p>
          <ul>
            <li>Use a strong, unique password</li>
            <li>Enable two-factor authentication when available</li>
            <li>Notify us immediately of any unauthorized use of your account</li>
            <li>Not share your account credentials with others</li>
          </ul>

          <h3>2.3 Account Eligibility</h3>
          <p>
            You must be at least 18 years old to use the Service. By using the Service, you represent and warrant 
            that you meet this age requirement.
          </p>
        </section>

        <section className="legal-section">
          <h2>3. Service Plans and Billing</h2>
          <h3>3.1 Subscription Plans</h3>
          <p>
            Zenith offers multiple subscription plans (Free, Basic, and Pro) with varying features and limits. 
            Plan details, pricing, and features are described on our Pricing page and may be updated from time to time.
          </p>

          <h3>3.2 Payment Terms</h3>
          <p>
            Paid subscriptions are billed monthly in advance. By subscribing to a paid plan, you authorize us to charge 
            your payment method on a recurring basis. All fees are non-refundable except as required by law or as 
            explicitly stated in these Terms.
          </p>

          <h3>3.3 Plan Changes</h3>
          <p>
            You may upgrade or downgrade your plan at any time. Upgrades take effect immediately, and you will be 
            charged a prorated amount for the remainder of the billing cycle. Downgrades take effect at the start 
            of your next billing cycle.
          </p>

          <h3>3.4 Free Trial</h3>
          <p>
            We may offer a free trial period for new users. At the end of the trial period, you will be charged 
            for the selected plan unless you cancel before the trial ends. We reserve the right to modify or 
            discontinue free trials at any time.
          </p>

          <h3>3.5 Price Changes</h3>
          <p>
            We reserve the right to change our pricing at any time. We will provide at least 30 days' notice of 
            any price increases to existing subscribers. Continued use of the Service after the price change 
            constitutes acceptance of the new pricing.
          </p>
        </section>

        <section className="legal-section">
          <h2>4. Use of Service</h2>
          <h3>4.1 Acceptable Use</h3>
          <p>You agree to use the Service only for lawful purposes and in accordance with these Terms. You agree NOT to:</p>
          <ul>
            <li>Violate any applicable laws or regulations</li>
            <li>Infringe upon the rights of others</li>
            <li>Upload or distribute malware, viruses, or malicious code</li>
            <li>Attempt to gain unauthorized access to the Service or related systems</li>
            <li>Use the Service to mine cryptocurrency without explicit authorization</li>
            <li>Interfere with or disrupt the Service or servers</li>
            <li>Impersonate any person or entity</li>
            <li>Collect or harvest information about other users</li>
            <li>Use automated systems (bots, scrapers) without permission</li>
          </ul>

          <h3>4.2 Resource Limits</h3>
          <p>
            Your use of the Service is subject to resource limits based on your subscription plan, including but not 
            limited to virtual machines, storage capacity, and bandwidth. Exceeding these limits may result in 
            additional charges or service interruption.
          </p>

          <h3>4.3 Data Storage</h3>
          <p>
            You are responsible for maintaining backups of your data. While we implement security measures to protect 
            your data, we are not responsible for any data loss that may occur.
          </p>
        </section>

        <section className="legal-section">
          <h2>5. Intellectual Property</h2>
          <h3>5.1 Our Property</h3>
          <p>
            The Service, including its design, code, text, graphics, logos, and other content, is owned by Zenith 
            and protected by copyright, trademark, and other intellectual property laws. You may not copy, modify, 
            distribute, or create derivative works without our written permission.
          </p>

          <h3>5.2 Your Content</h3>
          <p>
            You retain all rights to the data and content you upload to the Service ("Your Content"). By uploading 
            Your Content, you grant us a worldwide, non-exclusive, royalty-free license to use, store, and process 
            Your Content solely to provide the Service to you.
          </p>

          <h3>5.3 Feedback</h3>
          <p>
            If you provide us with feedback, suggestions, or ideas about the Service, you grant us the right to use 
            such feedback without compensation or attribution.
          </p>
        </section>

        <section className="legal-section">
          <h2>6. Third-Party Services</h2>
          <p>
            The Service integrates with third-party cloud providers (AWS, Google Cloud Platform, Microsoft Azure). 
            Your use of these providers' services is subject to their respective terms of service and privacy policies. 
            We are not responsible for the actions or policies of these third-party providers.
          </p>
        </section>

        <section className="legal-section">
          <h2>7. Privacy and Data Protection</h2>
          <p>
            Our collection and use of personal information is described in our Privacy Policy. By using the Service, 
            you consent to our collection and use of information as described in the Privacy Policy.
          </p>
        </section>

        <section className="legal-section">
          <h2>8. Disclaimers and Limitation of Liability</h2>
          <h3>8.1 Service Availability</h3>
          <p>
            The Service is provided "as is" and "as available" without warranties of any kind, either express or implied. 
            We do not guarantee that the Service will be uninterrupted, secure, or error-free.
          </p>

          <h3>8.2 Limitation of Liability</h3>
          <p>
            To the maximum extent permitted by law, Zenith shall not be liable for any indirect, incidental, special, 
            consequential, or punitive damages, including but not limited to loss of profits, data, or goodwill, 
            arising from your use of or inability to use the Service.
          </p>

          <h3>8.3 Maximum Liability</h3>
          <p>
            Our total liability to you for any claims arising from these Terms or your use of the Service shall not 
            exceed the amount you paid us in the 12 months preceding the claim.
          </p>
        </section>

        <section className="legal-section">
          <h2>9. Indemnification</h2>
          <p>
            You agree to indemnify, defend, and hold harmless Zenith, its officers, directors, employees, and agents 
            from any claims, damages, losses, liabilities, and expenses (including attorney's fees) arising from:
          </p>
          <ul>
            <li>Your use of the Service</li>
            <li>Your violation of these Terms</li>
            <li>Your violation of any rights of another party</li>
            <li>Your Content uploaded to the Service</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>10. Termination</h2>
          <h3>10.1 Termination by You</h3>
          <p>
            You may cancel your account at any time through your account settings or by contacting support. 
            Cancellation will take effect at the end of your current billing period.
          </p>

          <h3>10.2 Termination by Us</h3>
          <p>
            We reserve the right to suspend or terminate your account at any time, with or without notice, if:
          </p>
          <ul>
            <li>You violate these Terms</li>
            <li>Your account has been inactive for an extended period</li>
            <li>We are required to do so by law</li>
            <li>Continuing to provide the Service would create legal liability or security risks</li>
          </ul>

          <h3>10.3 Effect of Termination</h3>
          <p>
            Upon termination, your right to use the Service will immediately cease. We may delete your data after 
            a reasonable period following termination. It is your responsibility to export your data before termination.
          </p>
        </section>

        <section className="legal-section">
          <h2>11. Changes to Terms</h2>
          <p>
            We may modify these Terms at any time. We will notify you of material changes via email or through the 
            Service. Your continued use of the Service after such modifications constitutes acceptance of the updated Terms. 
            If you do not agree to the modified Terms, you must stop using the Service.
          </p>
        </section>

        <section className="legal-section">
          <h2>12. Dispute Resolution</h2>
          <h3>12.1 Governing Law</h3>
          <p>
            These Terms shall be governed by and construed in accordance with the laws of India, without regard to 
            its conflict of law provisions.
          </p>

          <h3>12.2 Arbitration</h3>
          <p>
            Any dispute arising from these Terms or your use of the Service shall be resolved through binding arbitration 
            in accordance with the Arbitration and Conciliation Act, 1996, rather than in court, except that you may 
            assert claims in small claims court if they qualify.
          </p>
        </section>

        <section className="legal-section">
          <h2>13. Miscellaneous</h2>
          <h3>13.1 Entire Agreement</h3>
          <p>
            These Terms, together with our Privacy Policy, constitute the entire agreement between you and Zenith 
            regarding the Service.
          </p>

          <h3>13.2 Severability</h3>
          <p>
            If any provision of these Terms is found to be unenforceable, the remaining provisions will continue 
            in full force and effect.
          </p>

          <h3>13.3 Waiver</h3>
          <p>
            Our failure to enforce any right or provision of these Terms will not be considered a waiver of those rights.
          </p>

          <h3>13.4 Assignment</h3>
          <p>
            You may not assign or transfer these Terms without our prior written consent. We may assign our rights 
            and obligations under these Terms without restriction.
          </p>
        </section>

        <section className="legal-section">
          <h2>14. Contact Information</h2>
          <p>
            If you have any questions about these Terms, please contact us at:
          </p>
          <div className="contact-info">
            <p><strong>Email:</strong> aangatla957@gmail.com</p>
            <p><strong>Website:</strong> <a href="http://localhost:5173/contact">Contact Us</a></p>
          </div>
        </section>

        <div className="legal-footer">
          <p>
            By using Zenith, you acknowledge that you have read and understood these Terms of Service and agree to be 
            bound by them.
          </p>
        </div>
      </div>
    </div>
    </MarketingPageLayout>
  );
};

export default TermsOfServicePage;
