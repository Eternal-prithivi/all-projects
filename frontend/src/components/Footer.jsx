import React from 'react';
import '../styles/footer.css';

const Footer = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-left">
          <span className="footer-copyright">© 2025 Zenith Cloud</span>
          <span className="footer-divider">•</span>
          <span className="footer-version">v1.0.0</span>
          <span className="footer-divider">•</span>
          <div className="footer-status">
            <span className="status-indicator"></span>
            <span>All Systems Operational</span>
          </div>
        </div>
        <div className="footer-right">
          <a href="#" className="footer-link">Privacy Policy</a>
          <a href="#" className="footer-link">Terms</a>
          <a href="#" className="footer-link">Documentation</a>
          <a href="#" className="footer-link">Support</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
