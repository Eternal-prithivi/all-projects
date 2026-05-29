import React from 'react';
import { Link } from 'react-router-dom';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/features.css';

function FeaturesPage() {
  return (
    <MarketingPageLayout>
      <div className="features-page">
        <section className="features-hero reveal-group">
          <div className="features-hero-inner">
            <div className="features-hero-content reveal-item">
              <p className="features-kicker">Zenith Platform Features</p>
              <h1>Everything you need to run cloud ops like a pro</h1>
              <p>
                Zenith brings FinOps clarity, AI optimization, and secure multi-cloud operations into one workspace.
                Get real-time insights, faster provisioning, and automated savings without changing your stack.
              </p>
              <div className="features-hero-actions">
                <Link to="/register" className="btn-primary">Start Free Trial</Link>
                <Link to="/contact" className="btn-secondary">Book a Demo</Link>
              </div>
              <div className="features-hero-badges">
                <span>Multi-cloud ready</span>
                <span>Finance-grade reporting</span>
                <span>Secure by default</span>
              </div>
            </div>
            <div className="features-hero-panel reveal-item reveal-item--delay-2">
              <div className="features-glow-card">
                <div className="features-glow-header">
                  <span className="pulse-dot"></span>
                  Live savings
                </div>
                <div className="features-glow-value">-32.4%</div>
                <p>Tracked across AWS, GCP, and Azure in the last 30 days.</p>
              </div>
              <div className="features-glow-card secondary">
                <div className="features-glow-header">
                  <span className="pulse-dot"></span>
                  Optimization queue
                </div>
                <ul>
                  <li>Right-size 12 VMs</li>
                  <li>Tier 8 cold buckets</li>
                  <li>Schedule 3 dev clusters</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="features-grid-section reveal-group">
          <div className="section-heading reveal-item">
            <h2>Core capabilities</h2>
            <p>Designed for teams that want fewer surprises and more control.</p>
          </div>
          <div className="features-grid reveal-stagger">
            <article className="feature-card reveal-item">
              <h3>Cost intelligence</h3>
              <p>Instantly see spend by project, team, and provider with drill-down analytics.</p>
              <span className="feature-tag">FinOps</span>
            </article>
            <article className="feature-card reveal-item">
              <h3>AI optimization</h3>
              <p>Recommendations highlight right-sizing, idle resources, and schedule automation.</p>
              <span className="feature-tag">ML Engine</span>
            </article>
            <article className="feature-card reveal-item">
              <h3>Unified VM control</h3>
              <p>Provision, scale, and monitor compute from a single workspace.</p>
              <span className="feature-tag">Compute</span>
            </article>
            <article className="feature-card reveal-item">
              <h3>Smart storage tiers</h3>
              <p>Auto-classify cold data and keep active files on premium tiers.</p>
              <span className="feature-tag">Storage</span>
            </article>
            <article className="feature-card reveal-item">
              <h3>Security posture</h3>
              <p>2FA, encrypted storage, and audit trails keep compliance in check.</p>
              <span className="feature-tag">Security</span>
            </article>
            <article className="feature-card reveal-item">
              <h3>Team visibility</h3>
              <p>Role-based dashboards, alerts, and approval workflows.</p>
              <span className="feature-tag">Collaboration</span>
            </article>
          </div>
        </section>

        <section className="features-steps reveal-group">
          <div className="section-heading reveal-item">
            <h2>How it works</h2>
            <p>From connection to savings in three steps.</p>
          </div>
          <div className="steps-grid reveal-stagger">
            <div className="step-card reveal-item">
              <span className="step-index">01</span>
              <h3>Connect your cloud</h3>
              <p>Securely link AWS, GCP, and Azure using read-only roles or keys.</p>
            </div>
            <div className="step-card reveal-item">
              <span className="step-index">02</span>
              <h3>Analyze and plan</h3>
              <p>Zenith creates a baseline with forecasts, anomalies, and top savings.</p>
            </div>
            <div className="step-card reveal-item">
              <span className="step-index">03</span>
              <h3>Automate savings</h3>
              <p>Apply recommendations or schedule them with approvals.</p>
            </div>
          </div>
        </section>

        <section className="features-metrics reveal-stagger reveal-group">
          <div className="metrics-card reveal-item reveal-item--scale">
            <h3>60%</h3>
            <p>Average savings in the first month</p>
          </div>
          <div className="metrics-card reveal-item reveal-item--scale">
            <h3>10 min</h3>
            <p>To connect the first cloud account</p>
          </div>
          <div className="metrics-card reveal-item reveal-item--scale">
            <h3>24/7</h3>
            <p>Optimization and anomaly detection</p>
          </div>
          <div className="metrics-card reveal-item reveal-item--scale">
            <h3>3+</h3>
            <p>Cloud providers supported</p>
          </div>
        </section>

        <section className="features-integrations reveal-group">
          <div className="section-heading reveal-item">
            <h2>Built for your stack</h2>
            <p>Integrate without changing your deployment flow.</p>
          </div>
          <div className="integrations-grid reveal-item reveal-item--fade">
            <span>AWS</span>
            <span>Google Cloud</span>
            <span>Azure</span>
            <span>Terraform</span>
            <span>Kubernetes</span>
            <span>Datadog</span>
          </div>
        </section>

        <section className="features-cta reveal-group">
          <div className="features-cta-inner reveal-item">
            <div>
              <h2>Ready to unlock immediate cloud savings?</h2>
              <p>Start with a free trial or talk to our team about enterprise rollouts.</p>
            </div>
            <div className="features-cta-actions">
              <Link to="/register" className="btn-primary">Start Free Trial</Link>
              <Link to="/contact" className="btn-secondary">Talk to Sales</Link>
            </div>
          </div>
        </section>
      </div>
    </MarketingPageLayout>
  );
}

export default FeaturesPage;
