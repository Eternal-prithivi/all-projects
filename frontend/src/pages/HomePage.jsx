import React from 'react';
import { Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground.jsx';
import '../styles/home.css';

function HomePage() {
  return (
    <div className="home-container">
      <AnimatedBackground />
      <header className="home-header">
        <h1 className="main-title">Welcome to Zenith</h1>
        <p className="subtitle">The pinnacle of cloud resource optimization.</p>
      </header>
      <main className="features-grid">
        <div className="feature-card">
          <h3 className="feature-title">Intelligent Cost Management</h3>
          <p className="feature-description">Gain deep insights into your cloud spending and receive AI-driven recommendations to eliminate waste.</p>
        </div>
        <div className="feature-card">
          <h3 className="feature-title">Automated Optimization</h3>
          <p className="feature-description">Let Zenith automatically adjust your storage tiers and compute instances for maximum performance at the lowest cost.</p>
        </div>
        <div className="feature-card">
          <h3 className="feature-title">Enhanced Security</h3>
          <p className="feature-description">Monitor your cloud environment for security vulnerabilities and ensure compliance with industry standards.</p>
        </div>
      </main>
      <footer className="home-footer">
        <p>Ready to take control of your cloud?</p>
        <div className="button-group">
          <Link to="/login" className="btn btn-primary">Login</Link>
          <Link to="/register" className="btn btn-secondary">Join Now</Link>
        </div>
      </footer>
    </div>
  );
}

export default HomePage;
