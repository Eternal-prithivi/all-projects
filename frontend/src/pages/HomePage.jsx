import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/home.css';

function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* Navigation Header */}
      <nav className="landing-nav">
        <div className="nav-container">
          <div className="nav-logo">
            <h2>Zenith</h2>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#benefits">Benefits</a>
            <a href="#pricing">Pricing</a>
            {user ? (
              <Link to="/dashboard" className="btn-nav-signup">Go to Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="btn-nav-login">Login</Link>
                <Link to="/register" className="btn-nav-signup">Sign Up</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Optimize Your Cloud.
            <br />
            <span className="gradient-text">Maximize Your Savings.</span>
          </h1>
          <p className="hero-subtitle">
            Zenith is the intelligent cloud resource optimization platform that reduces costs by up to 60% 
            while improving performance across AWS, GCP, and Azure.
          </p>
          <div className="hero-actions">
            <Link to="/register" className="btn-hero-primary">Start Free Trial</Link>
            <a href="#features" className="btn-hero-secondary">Learn More</a>
          </div>
          <p className="hero-note">No credit card required • 14-day free trial</p>
        </div>
        <div className="hero-visual">
          <div className="floating-card card-1">
            <div className="card-icon">💰</div>
            <div className="card-content">
              <div className="card-label">Cost Savings</div>
              <div className="card-value">$45,230</div>
            </div>
          </div>
          <div className="floating-card card-2">
            <div className="card-icon">⚡</div>
            <div className="card-content">
              <div className="card-label">Performance</div>
              <div className="card-value">+38%</div>
            </div>
          </div>
          <div className="floating-card card-3">
            <div className="card-icon">🔒</div>
            <div className="card-content">
              <div className="card-label">Security</div>
              <div className="card-value">100%</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="section-header">
          <h2 className="section-title">Everything you need to optimize your cloud</h2>
          <p className="section-subtitle">Powerful features to manage, monitor, and maximize your cloud infrastructure</p>
        </div>
        <div className="features-grid">
          <div className="feature-item">
            <div className="feature-icon">📊</div>
            <h3>Real-Time Analytics</h3>
            <p>Monitor your cloud resources with live dashboards and instant insights into usage patterns and costs.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon">🤖</div>
            <h3>AI-Powered Recommendations</h3>
            <p>Get intelligent suggestions to optimize resource allocation and reduce unnecessary spending.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon">☁️</div>
            <h3>Multi-Cloud Support</h3>
            <p>Seamlessly manage resources across AWS, Google Cloud, and Microsoft Azure from one platform.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon">💾</div>
            <h3>Intelligent Storage Tiering</h3>
            <p>Automatically move data between storage tiers based on access patterns to minimize costs.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon">🖥️</div>
            <h3>VM Cluster Management</h3>
            <p>Provision, monitor, and scale virtual machines with ease across multiple cloud providers.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon">🛡️</div>
            <h3>Enterprise Security</h3>
            <p>Bank-level encryption, 2FA, and compliance monitoring to keep your data safe.</p>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" className="benefits-section">
        <div className="benefits-content">
          <h2 className="section-title">Why teams choose Zenith</h2>
          <div className="benefits-list">
            <div className="benefit-item">
              <div className="benefit-number">60%</div>
              <div className="benefit-text">Average cost reduction in the first month</div>
            </div>
            <div className="benefit-item">
              <div className="benefit-number">10min</div>
              <div className="benefit-text">To set up and start optimizing</div>
            </div>
            <div className="benefit-item">
              <div className="benefit-number">24/7</div>
              <div className="benefit-text">Automated monitoring and optimization</div>
            </div>
            <div className="benefit-item">
              <div className="benefit-number">3+</div>
              <div className="benefit-text">Cloud providers in one unified platform</div>
            </div>
            <div className="benefit-item">
              <div className="benefit-number">AI</div>
              <div className="benefit-text">Powered recommendations for smart optimization</div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="pricing-section">
        <div className="section-header">
          <h2 className="section-title">Simple, transparent pricing</h2>
          <p className="section-subtitle">Pay only for what you use. We consolidate your cloud bills and help you save.</p>
        </div>
        <div className="pricing-grid">
          <div className="pricing-card">
            <h3 className="pricing-tier">Starter</h3>
            <div className="pricing-price">
              <span className="price-currency">$</span>
              <span className="price-amount">9</span>
              <span className="price-period">/month</span>
            </div>
            <ul className="pricing-features">
              <li>✓ Up to 10 VMs</li>
              <li>✓ 500GB Storage</li>
              <li>✓ Basic Analytics</li>
              <li>✓ Consolidated billing</li>
              <li>✓ Email Support</li>
            </ul>
            <Link to="/register" className="pricing-btn">Get Started</Link>
          </div>
          <div className="pricing-card featured">
            <div className="pricing-badge">Most Popular</div>
            <h3 className="pricing-tier">Professional</h3>
            <div className="pricing-price">
              <span className="price-currency">$</span>
              <span className="price-amount">29</span>
              <span className="price-period">/month</span>
            </div>
            <ul className="pricing-features">
              <li>✓ Up to 50 VMs</li>
              <li>✓ 5TB Storage</li>
              <li>✓ Advanced Analytics</li>
              <li>✓ AI Recommendations</li>
              <li>✓ Unified cloud billing</li>
              <li>✓ Priority Support</li>
            </ul>
            <Link to="/register" className="pricing-btn">Get Started</Link>
          </div>
          <div className="pricing-card">
            <h3 className="pricing-tier">Enterprise</h3>
            <div className="pricing-price">
              <span className="price-currency">$</span>
              <span className="price-amount">99</span>
              <span className="price-period">/month</span>
            </div>
            <ul className="pricing-features">
              <li>✓ Unlimited VMs</li>
              <li>✓ Unlimited Storage</li>
              <li>✓ Custom Analytics</li>
              <li>✓ Multi-cloud billing consolidation</li>
              <li>✓ Dedicated Support</li>
              <li>✓ SLA Guarantee</li>
            </ul>
            <Link to="/register" className="pricing-btn">Contact Sales</Link>
          </div>
        </div>
        <div className="section-header" style={{ marginTop: '60px' }}>
          <p className="section-subtitle">
            💡 We consolidate bills from AWS, GCP, and Azure. You only pay our platform fee plus your actual cloud usage costs.
          </p>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2 className="cta-title">Ready to optimize your cloud?</h2>
        <p className="cta-subtitle">Join thousands of companies saving millions on cloud costs</p>
        <Link to="/register" className="btn-cta">Start Free Trial</Link>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>Zenith</h4>
            <p>The intelligent cloud optimization platform</p>
          </div>
          <div className="footer-section">
            <h4>Product</h4>
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="#">Documentation</a>
          </div>
          <div className="footer-section">
            <h4>Company</h4>
            <a href="#">About</a>
            <a href="#">Blog</a>
            <a href="#">Careers</a>
          </div>
          <div className="footer-section">
            <h4>Legal</h4>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Security</a>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2025 Zenith. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default HomePage;
