import React from 'react';
import { Link } from 'react-router-dom';
import Footer from '../components/layout/Footer.jsx';
import '../styles/about.css';

function AboutPage() {
  return (
    <>
      <div className="about-page">
        <div className="about-container">
          {/* Hero Section */}
          <section className="about-hero">
            <h1 className="about-title">About Zenith</h1>
            <p className="about-subtitle">
              Cloud Resource Optimization Platform for Modern Businesses
            </p>
          </section>

          {/* Mission Section */}
          <section className="about-section">
            <div className="section-content">
              <h2>Our Mission</h2>
              <p>
                Zenith is dedicated to helping businesses optimize their cloud infrastructure 
                costs while maintaining peak performance. We believe cloud computing should be 
                accessible, efficient, and cost-effective for everyone.
              </p>
              <p>
                Our platform provides intelligent VM cluster management, multi-cloud storage 
                optimization, and real-time cost analysis to help you make informed decisions 
                about your cloud resources.
              </p>
            </div>
          </section>

          {/* What We Do */}
          <section className="about-section">
            <div className="section-content">
              <h2>What We Do</h2>
              <div className="features-grid">
                <div className="feature-card">
                  <div className="feature-icon">🖥️</div>
                  <h3>VM Cluster Management</h3>
                  <p>
                    Efficiently manage and optimize your virtual machine clusters across 
                    multiple cloud providers with intelligent workload analysis.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">☁️</div>
                  <h3>Multi-Cloud Storage</h3>
                  <p>
                    Optimize storage costs with ML-powered recommendations across AWS, 
                    GCP, and Azure, with intelligent tiering strategies.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">📊</div>
                  <h3>Cost Analytics</h3>
                  <p>
                    Real-time cost tracking, forecasting, and optimization recommendations 
                    to reduce your cloud spend by up to 40%.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">🔒</div>
                  <h3>Security First</h3>
                  <p>
                    Enterprise-grade security with 2FA, encrypted file storage, activity 
                    logging, and session management.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Technology Stack */}
          <section className="about-section tech-section">
            <div className="section-content">
              <h2>Built with Modern Technology</h2>
              <div className="tech-stack">
                <div className="tech-category">
                  <h4>Frontend</h4>
                  <ul>
                    <li>React 19</li>
                    <li>Vite</li>
                    <li>React Router</li>
                  </ul>
                </div>

                <div className="tech-category">
                  <h4>Backend</h4>
                  <ul>
                    <li>FastAPI</li>
                    <li>Python</li>
                    <li>MongoDB</li>
                  </ul>
                </div>

                <div className="tech-category">
                  <h4>Cloud Providers</h4>
                  <ul>
                    <li>AWS</li>
                    <li>Google Cloud</li>
                    <li>Azure</li>
                  </ul>
                </div>

                <div className="tech-category">
                  <h4>Infrastructure</h4>
                  <ul>
                    <li>Celery</li>
                    <li>Redis</li>
                    <li>Docker</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Stats Section */}
          <section className="about-section stats-section">
            <div className="section-content">
              <h2>By the Numbers</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-number">40%</div>
                  <div className="stat-label">Average Cost Reduction</div>
                </div>

                <div className="stat-card">
                  <div className="stat-number">99.9%</div>
                  <div className="stat-label">Uptime Guaranteed</div>
                </div>

                <div className="stat-card">
                  <div className="stat-number">3</div>
                  <div className="stat-label">Cloud Providers</div>
                </div>

                <div className="stat-card">
                  <div className="stat-number">24/7</div>
                  <div className="stat-label">Support Available</div>
                </div>
              </div>
            </div>
          </section>

          {/* CTA Section */}
          <section className="about-cta">
            <h2>Ready to Optimize Your Cloud Costs?</h2>
            <p>Join businesses already saving up to 40% on their cloud infrastructure.</p>
            <div className="cta-buttons">
              <Link to="/register" className="cta-btn primary">Get Started Free</Link>
              <Link to="/contact" className="cta-btn secondary">Contact Sales</Link>
            </div>
          </section>
        </div>
      </div>
      <Footer />
    </>
  );
}

export default AboutPage;
