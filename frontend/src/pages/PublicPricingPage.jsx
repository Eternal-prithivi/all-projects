import React from 'react';
import { Link } from 'react-router-dom';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import { MARKETING_PRICING } from '../data/marketingPricing.js';
import '../styles/home.css';

export default function PublicPricingPage() {
  return (
    <MarketingPageLayout>
      <section className="landing-pricing landing-section reveal-group" style={{ paddingTop: '7rem' }}>
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Pricing</span>
          <h1 className="landing-section__title">Simple, transparent plans</h1>
          <p className="landing-section__subtitle">
            Start free. Scale when your infrastructure grows. All plans include multi-cloud management.
          </p>
        </div>
        <div className="landing-pricing__grid reveal-stagger">
          {MARKETING_PRICING.map((plan, i) => (
            <div
              key={plan.tier}
              className={`landing-pricing__card reveal-item reveal-item--scale ${
                plan.featured ? 'landing-pricing__card--featured' : ''
              }`}
              style={{ '--reveal-i': i }}
            >
              {plan.featured && <span className="landing-pricing__badge">Most popular</span>}
              <h3 className="landing-pricing__tier">{plan.tier}</h3>
              <div className="landing-pricing__price">
                <span className="landing-pricing__currency">₹</span>
                <span className="landing-pricing__amount">{plan.amount}</span>
                <span className="landing-pricing__period">/month</span>
              </div>
              <ul className="landing-pricing__features">
                {plan.features.map((item) => (
                  <li key={item}>✓ {item}</li>
                ))}
              </ul>
              <Link to={plan.ctaTo} className="landing-pricing__btn">
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="landing-section__subtitle reveal-item" style={{ textAlign: 'center', marginTop: '2rem' }}>
          Need a custom rollout? <Link to="/contact">Talk to sales</Link>
        </p>
      </section>
    </MarketingPageLayout>
  );
}
