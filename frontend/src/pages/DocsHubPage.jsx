import React from 'react';
import { Link } from 'react-router-dom';
import { FaBook, FaCode } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/docs-hub.css';

const API_DOCS_URL = `${(import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/api\/?$/, '')}/docs`;

export default function DocsHubPage() {
  return (
    <MarketingPageLayout>
      <div className="docs-hub">
        <header className="docs-hub__header reveal-group">
          <div className="reveal-item">
            <h1>Documentation</h1>
            <p>Guides and API reference for Zenith</p>
          </div>
        </header>

        <div className="docs-hub__grid reveal-stagger">
          <a
            href={API_DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="docs-hub__card reveal-item"
          >
            <FaCode className="docs-hub__icon" />
            <h2>API reference</h2>
            <p>Interactive OpenAPI (Swagger) documentation for all REST endpoints.</p>
          </a>
          <Link to="/help" className="docs-hub__card reveal-item">
            <FaBook className="docs-hub__icon" />
            <h2>Help center</h2>
            <p>FAQs, getting started, and troubleshooting for common tasks.</p>
          </Link>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
