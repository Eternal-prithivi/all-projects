import React from 'react';
import { Link } from 'react-router-dom';
import { FaTwitter, FaGithub, FaLinkedin } from 'react-icons/fa';
import '../../styles/footer.css';

function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="footer-container">
        <div className="footer-content">
          {/* Left: Brand + Description */}
          <div className="footer-brand-section">
            <h3>Zenith</h3>
            <p>AI-powered cloud optimization platform</p>
          </div>

          {/* Center: Links Grid */}
          <div className="footer-links-grid">
            <div className="footer-link-column">
              <h4>Product</h4>
              <Link to="/features">Features</Link>
              <Link to="/download">Download</Link>
              <Link to="/pricing">Pricing</Link>
              <Link to="/docs">Documentation</Link>
              <Link to="/dashboard">Dashboard</Link>
            </div>
            <div className="footer-link-column">
              <h4>Company</h4>
              <Link to="/about">About</Link>
              <Link to="/contact">Contact</Link>
              <Link to="/help">Help Center</Link>
              <Link to="/status">System Status</Link>
              <Link to="/trust">Trust Center</Link>
            </div>
            <div className="footer-link-column">
              <h4>Legal</h4>
              <Link to="/legal/terms">Terms</Link>
              <Link to="/legal/privacy">Privacy</Link>
              <Link to="/legal/cookies">Cookies</Link>
              <Link to="/legal/dpa">DPA</Link>
            </div>
          </div>

          {/* Right: Social */}
          <div className="footer-social-section">
            <h4>Follow Us</h4>
            <div className="footer-social">
              <a href="https://x.com/a_prithiviraj" target="_blank" rel="noopener noreferrer" aria-label="Twitter">
                <FaTwitter />
              </a>
              <a href="https://github.com/a-prithiviraj" target="_blank" rel="noopener noreferrer" aria-label="GitHub">
                <FaGithub />
              </a>
              <a href="https://linkedin.com/in/a-prithiviraj" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                <FaLinkedin />
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <p>© {currentYear} Zenith. All rights reserved.</p>
          <div className="footer-meta">
            <span>Made with ❤️ in India</span>
            <span className="footer-divider">•</span>
            <a href="mailto:support@rajverse.me">support@rajverse.me</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
