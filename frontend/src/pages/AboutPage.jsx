import React from 'react';
import { Link } from 'react-router-dom';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/about.css';

function AboutPage() {
  return (
    <MarketingPageLayout>
      <div className="about-page">
        <div className="about-container">
          <section className="about-hero reveal-group">
            <div className="reveal-item">
              <p className="marketing-page-hero__eyebrow">Company</p>
              <h1 className="about-title">About Zenith</h1>
              <p className="about-subtitle">
                Cloud Resource Optimization Platform for Modern Businesses
              </p>
            </div>
          </section>

          <section className="about-section reveal-group">
            <div className="section-content reveal-item">
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

          <section className="about-section reveal-group">
            <div className="section-content">
              <h2 className="reveal-item">What We Do</h2>
              <div className="features-grid reveal-stagger">
                <div className="feature-card reveal-item">
                  <div className="feature-icon">🖥️</div>
                  <h3>VM Cluster Management</h3>
                  <p>
                    Efficiently manage and optimize your virtual machine clusters across
                    multiple cloud providers with intelligent workload analysis.
                  </p>
                </div>
                <div className="feature-card reveal-item">
                  <div className="feature-icon">☁️</div>
                  <h3>Multi-Cloud Storage</h3>
                  <p>
                    Optimize storage costs with ML-powered recommendations across AWS,
                    GCP, and Azure, with intelligent tiering strategies.
                  </p>
                </div>
                <div className="feature-card reveal-item">
                  <div className="feature-icon">📊</div>
                  <h3>Cost Analytics</h3>
                  <p>
                    Real-time cost tracking, forecasting, and optimization recommendations
                    to reduce your cloud spend by up to 40%.
                  </p>
                </div>
                <div className="feature-card reveal-item">
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

          <section className="about-section reveal-group">
            <div className="section-content reveal-item">
              <h2>Technology Stack</h2>
              <p>
                Built with modern technologies to ensure reliability, scalability, and performance.
              </p>
              <div className="tech-stack reveal-stagger">
                <div className="tech-category reveal-item">
                  <h3>Frontend</h3>
                  <ul>
                    <li>React 18</li>
                    <li>Vite</li>
                    <li>Modern CSS</li>
                  </ul>
                </div>
                <div className="tech-category reveal-item">
                  <h3>Backend</h3>
                  <ul>
                    <li>Python FastAPI</li>
                    <li>MongoDB</li>
                    <li>Redis</li>
                  </ul>
                </div>
                <div className="tech-category reveal-item">
                  <h3>Cloud</h3>
                  <ul>
                    <li>AWS</li>
                    <li>Google Cloud</li>
                    <li>Microsoft Azure</li>
                  </ul>
                </div>
                <div className="tech-category reveal-item">
                  <h3>ML/AI</h3>
                  <ul>
                    <li>Scikit-learn</li>
                    <li>XGBoost</li>
                    <li>TensorFlow</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section className="about-section reveal-group">
            <div className="section-content reveal-item">
              <h2>Our Values</h2>
              <div className="values-list">
                <div className="value-item">
                  <h3>🎯 Customer Success</h3>
                  <p>Your success is our success. We're committed to helping you achieve your goals.</p>
                </div>
                <div className="value-item">
                  <h3>🔒 Security & Privacy</h3>
                  <p>We take data security seriously and implement industry best practices.</p>
                </div>
                <div className="value-item">
                  <h3>💡 Innovation</h3>
                  <p>Continuously improving our platform with cutting-edge AI and ML technologies.</p>
                </div>
                <div className="value-item">
                  <h3>🤝 Transparency</h3>
                  <p>Clear pricing, honest communication, and no hidden fees.</p>
                </div>
              </div>
            </div>
          </section>

          <section className="about-cta reveal-group">
            <div className="reveal-item">
              <h2>Ready to Optimize Your Cloud Costs?</h2>
              <p>Join businesses already saving up to 40% on their cloud infrastructure.</p>
              <div className="cta-buttons">
                <Link to="/register" className="cta-btn primary">Get Started Free</Link>
                <Link to="/contact" className="cta-btn secondary">Contact Sales</Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </MarketingPageLayout>
  );
}

export default AboutPage;
