import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Footer from '../components/layout/Footer.jsx';
import AnimatedBackground from '../components/AnimatedBackground.jsx';
import HeroPreview from '../components/landing/HeroPreview.jsx';
import HeroTiltVisual from '../components/landing/HeroTiltVisual.jsx';
import SpotlightCard from '../components/landing/SpotlightCard.jsx';
import { useLandingNav } from '../hooks/useLandingNav.js';
import { useLandingReveal } from '../hooks/useLandingReveal.js';
import { MARKETING_PRICING } from '../data/marketingPricing.js';
import '../styles/home.css';
import '../styles/animated-background.css';
import ZenithLogo from '../components/brand/ZenithLogo.jsx';

const MARQUEE_ITEMS = [
  'AWS',
  'Google Cloud',
  'Microsoft Azure',
  'S3 Intelligent Tiering',
  'VM Clusters',
  'Secure Vault',
  'ML Cost Engine',
  'BYOC Ready',
];

const BENTO_FEATURES = [
  {
    span: 'landing-bento__card--span-8',
    icon: '🤖',
    title: 'AI-powered placement',
    text: 'Analyze every upload and route files to the optimal tier and cloud — AWS, GCP, or Azure — with ensemble ML confidence scores.',
    link: true,
  },
  {
    span: 'landing-bento__card--span-4',
    icon: '📊',
    title: 'Live cost analytics',
    text: 'Real-time dashboards surface waste, trends, and savings opportunities across your entire estate.',
  },
  {
    span: 'landing-bento__card--span-4',
    icon: '💾',
    title: 'Smart storage tiering',
    text: 'Hot, cool, and archive tiers move automatically as access patterns change.',
  },
  {
    span: 'landing-bento__card--span-4',
    icon: '🖥️',
    title: 'VM cluster control',
    text: 'Provision, monitor, and scale workloads from one pane of glass.',
  },
  {
    span: 'landing-bento__card--span-4',
    icon: '🛡️',
    title: 'Enterprise security',
    text: 'Encrypted vaults, 2FA, and isolated secure buckets for sensitive data.',
  },
];

const STEPS = [
  {
    title: 'Connect your clouds',
    text: 'Link AWS, GCP, or Azure in minutes — platform-managed or bring your own credentials.',
  },
  {
    title: 'Let ML analyze workloads',
    text: 'Zenith scores access patterns, cost, and intent to recommend the right tier and provider.',
  },
  {
    title: 'Optimize continuously',
    text: 'Automated tiering, sync, and monitoring keep spend down while performance stays high.',
  },
];

const TESTIMONIALS = [
  {
    quote:
      'We cut our S3 bill by half in the first month. The ML recommendations felt like having a FinOps engineer on the team.',
    name: 'Priya Sharma',
    role: 'Head of Platform, Series B SaaS',
    initials: 'PS',
  },
  {
    quote:
      'Finally one dashboard for AWS and GCP. Secure vault + standard storage separation is exactly what our compliance team needed.',
    name: 'Marcus Chen',
    role: 'Cloud Architect, Fintech',
    initials: 'MC',
  },
  {
    quote:
      'Setup took under ten minutes. The VM cluster view alone replaced three internal scripts we maintained for years.',
    name: 'Elena Rodriguez',
    role: 'DevOps Lead, E-commerce',
    initials: 'ER',
  },
];

function HomePage() {
  const { user } = useAuth();
  const navScrolled = useLandingNav(16);
  useLandingReveal();
  const marqueeDoubled = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  return (
    <div className="landing-page">
      <div className="landing-scroll-progress" aria-hidden="true" />
      <AnimatedBackground />

      <nav className={`landing-nav ${navScrolled ? 'landing-nav--scrolled' : ''}`}>
        <div className="nav-container">
          <Link to="/" className="nav-logo">
            <ZenithLogo variant="full" size={40} badge="Cloud" textLayout="inline" />
          </Link>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#pricing">Pricing</a>
            {user ? (
              <Link to="/dashboard" className="btn-nav-signup">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-nav-login">
                  Login
                </Link>
                <Link to="/register" className="btn-nav-signup">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <header className="landing-hero">
        <div className="landing-hero__grid">
          <div className="landing-hero__copy">
            <div>
              <p className="landing-hero__badge">
                <span className="landing-hero__badge-dot" />
                Multi-cloud optimization platform
              </p>
              <h1 className="landing-hero__title">
                Cut cloud waste.
                <span className="text-gradient">Ship with confidence.</span>
              </h1>
              <p className="landing-hero__subtitle">
                Zenith unifies AWS, GCP, and Azure with ML-driven storage tiering, VM
                orchestration, and enterprise security — so teams save up to 60% without
                sacrificing performance.
              </p>
              <div className="landing-hero__actions">
                <Link to="/register" className="btn-hero-primary">
                  Start free trial
                </Link>
                <a href="#how-it-works" className="btn-hero-secondary">
                  See how it works
                </a>
              </div>
              <p className="landing-hero__note">No credit card · 14-day trial · BYOC supported</p>
              <div className="landing-hero__stats">
                <div className="landing-hero__stat">
                  <strong>60%</strong>
                  <span>avg. cost reduction</span>
                </div>
                <div className="landing-hero__stat">
                  <strong>3+</strong>
                  <span>cloud providers</span>
                </div>
                <div className="landing-hero__stat">
                  <strong>10 min</strong>
                  <span>to first insight</span>
                </div>
              </div>
            </div>
          </div>
          <HeroTiltVisual>
            <HeroPreview />
          </HeroTiltVisual>
        </div>
      </header>

      <section className="landing-marquee reveal-group" aria-label="Platform capabilities">
        <p className="landing-marquee__label reveal-item">Built for modern cloud teams</p>
        <div className="landing-marquee__track reveal-item reveal-item--fade">
          {marqueeDoubled.map((label, i) => (
            <span key={`${label}-${i}`}>{label}</span>
          ))}
        </div>
      </section>

      <section id="features" className="landing-section landing-section--wide reveal-group">
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Platform</span>
          <h2 className="landing-section__title">Everything in one control plane</h2>
          <p className="landing-section__subtitle">
            From intelligent ingestion to secure vaults — designed for operators who need
            clarity, not another tab.
          </p>
        </div>
        <div className="landing-bento reveal-stagger">
          {BENTO_FEATURES.map((f) => (
            <SpotlightCard
              key={f.title}
              className={`landing-bento__card reveal-item ${f.span}`}
            >
              <div className="landing-bento__icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
              {f.link && (
                <a href="#how-it-works" className="landing-bento__link">
                  Explore the workflow →
                </a>
              )}
            </SpotlightCard>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="landing-steps reveal-group">
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Workflow</span>
          <h2 className="landing-section__title">From connect to optimize in three steps</h2>
          <p className="landing-section__subtitle">
            A clear path from onboarding to measurable savings — no consultants required.
          </p>
        </div>
        <div className="landing-steps__grid reveal-stagger">
          {STEPS.map((step, i) => (
            <article
              key={step.title}
              className={`landing-step reveal-item ${i === 1 ? 'reveal-item--scale' : ''}`}
            >
              <span className="landing-step__num">{String(i + 1).padStart(2, '0')}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-testimonials reveal-group">
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Social proof</span>
          <h2 className="landing-section__title">Loved by platform teams</h2>
          <p className="landing-section__subtitle">
            Operators and architects who need real savings — not another spreadsheet.
          </p>
        </div>
        <div className="landing-testimonials__grid reveal-stagger">
          {TESTIMONIALS.map((t, i) => (
            <blockquote
              key={t.name}
              className={`landing-quote reveal-item ${
                i % 2 === 0 ? 'reveal-item--from-left' : 'reveal-item--from-right'
              }`}
            >
              <div className="landing-quote__stars" aria-hidden="true">
                ★★★★★
              </div>
              <p className="landing-quote__text">&ldquo;{t.quote}&rdquo;</p>
              <footer className="landing-quote__author">
                <span className="landing-quote__avatar">{t.initials}</span>
                <div>
                  <div className="landing-quote__name">{t.name}</div>
                  <div className="landing-quote__role">{t.role}</div>
                </div>
              </footer>
            </blockquote>
          ))}
        </div>
      </section>

      <section id="benefits" className="landing-benefits reveal-group">
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Outcomes</span>
          <h2 className="landing-section__title">Why teams choose Zenith</h2>
        </div>
        <div className="landing-benefits__grid reveal-stagger">
          {[
            ['60%', 'Average cost reduction in the first month'],
            ['10m', 'To connect and start optimizing'],
            ['24/7', 'Automated monitoring and tiering'],
            ['3+', 'Clouds in one unified platform'],
            ['AI', 'Ensemble models for placement decisions'],
          ].map(([num, text]) => (
            <div key={num} className="reveal-item reveal-item--scale">
              <div className="landing-benefits__num">{num}</div>
              <p className="landing-benefits__text">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="pricing" className="landing-pricing reveal-group">
        <div className="landing-section__header reveal-item">
          <span className="landing-section__eyebrow">Pricing</span>
          <h2 className="landing-section__title">Simple, transparent plans</h2>
          <p className="landing-section__subtitle">
            Start free. Scale when your infrastructure grows. All plans include multi-cloud
            management.
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
              <Link to={plan.ctaTo || '/register'} className="landing-pricing__btn">
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-cta reveal-group">
        <h2 className="landing-cta__title">Ready to optimize your cloud?</h2>
        <p className="landing-cta__subtitle">
          Join teams cutting spend while keeping performance — start your free trial today.
        </p>
        <div className="landing-cta__actions">
          <Link to="/register" className="btn-hero-primary">
            Start free trial
          </Link>
          <Link to="/contact" className="btn-hero-secondary">
            Talk to sales
          </Link>
        </div>
        <div className="landing-cta__trust">
          <span>SOC-ready security</span>
          <span>14-day free trial</span>
          <span>No credit card</span>
        </div>
      </section>

      <div className="reveal-item landing-footer-wrap">
        <Footer />
      </div>
    </div>
  );
}

export default HomePage;
