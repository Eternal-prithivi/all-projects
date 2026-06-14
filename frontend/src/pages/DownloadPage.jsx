import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaApple,
  FaWindows,
  FaLinux,
  FaDownload,
  FaGlobe,
  FaShieldAlt,
  FaChevronDown,
} from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import { detectPlatform, PLATFORM_LABELS } from '../utils/detectPlatform.js';
import { DESKTOP_DOWNLOAD_FAQ } from '../data/productFacts.js';
import '../styles/download-page.css';

const PLATFORM_ICONS = {
  mac: FaApple,
  win: FaWindows,
  linux: FaLinux,
};

function buildReleaseUrl(releaseTag, artifactName, githubRepo) {
  const encoded = encodeURIComponent(artifactName);
  return `https://github.com/${githubRepo}/releases/download/${releaseTag}/${encoded}`;
}

export default function DownloadPage() {
  const [manifest, setManifest] = useState(null);
  const [openFaq, setOpenFaq] = useState(null);
  const detected = useMemo(() => detectPlatform(), []);

  useEffect(() => {
    fetch('/releases.json')
      .then((r) => r.json())
      .then(setManifest)
      .catch(() => setManifest(null));
  }, []);

  const primaryKey = manifest?.platforms?.[detected] ? detected : 'mac';

  const platforms = useMemo(() => {
    if (!manifest?.platforms) return [];
    return ['mac', 'win', 'linux'].map((key) => {
      const p = manifest.platforms[key];
      const url = buildReleaseUrl(manifest.releaseTag, p.artifactName, manifest.githubRepo);
      const altUrl = p.altArtifactName
        ? buildReleaseUrl(manifest.releaseTag, p.altArtifactName, manifest.githubRepo)
        : null;
      return { key, ...p, url, altUrl };
    });
  }, [manifest]);

  const primary = platforms.find((p) => p.key === primaryKey) || platforms[0];

  return (
    <MarketingPageLayout>
      <div className="download-page">
        <section className="download-hero landing-section reveal-group">
          <div className="download-hero__inner reveal-item">
            <span className="landing-section__eyebrow">Zenith for desktop</span>
            <h1 className="landing-section__title">Run Zenith in a dedicated app</h1>
            <p className="landing-section__subtitle">
              The desktop app opens the same Zenith you use in the browser — one window, your clouds,
              no tab clutter. Requires an internet connection.
            </p>
            {manifest?.beta && (
              <p className="download-beta-badge">
                <FaShieldAlt aria-hidden /> Beta — unsigned installers; see install steps below
              </p>
            )}
            {primary && (
              <div className="download-hero__cta-row">
                <a
                  href={primary.url}
                  className="download-btn download-btn--primary"
                  download
                >
                  <FaDownload aria-hidden />
                  Download for {PLATFORM_LABELS[primary.key]}
                </a>
                <span className="download-version">
                  v{manifest?.version} · {primary.extension}
                </span>
              </div>
            )}
          </div>
        </section>

        <section className="download-platforms landing-section">
          <h2 className="download-section-title">Choose your platform</h2>
          <div className="download-platform-grid">
            {platforms.map((p) => {
              const Icon = PLATFORM_ICONS[p.key];
              const isRecommended = p.key === primaryKey;
              return (
                <article
                  key={p.key}
                  className={`download-platform-card${isRecommended ? ' download-platform-card--highlight' : ''}`}
                >
                  {isRecommended && <span className="download-platform-card__badge">Recommended</span>}
                  <div className="download-platform-card__icon">
                    <Icon aria-hidden />
                  </div>
                  <h3>{p.label}</h3>
                  <p className="download-platform-card__req">{p.minOs}</p>
                  <a href={p.url} className="download-btn download-btn--secondary" download>
                    {p.artifactName}
                  </a>
                  {p.altUrl && (
                    <a href={p.altUrl} className="download-alt-link" download>
                      Also: {p.altArtifactName}
                    </a>
                  )}
                  {p.sha256 && (
                    <code className="download-sha" title="SHA-256 checksum">
                      sha256: {p.sha256.slice(0, 16)}…
                    </code>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        <section className="download-install landing-section">
          <h2 className="download-section-title">Install instructions</h2>
          <div className="download-install-grid">
            <article className="download-install-card">
              <h3>
                <FaApple aria-hidden /> macOS
              </h3>
              <ol>
                <li>Download the <strong>.dmg</strong> file and open it.</li>
                <li>Drag Zenith into Applications.</li>
                <li>
                  If macOS shows “unidentified developer”, open <strong>System Settings → Privacy &amp; Security</strong>{' '}
                  and choose <strong>Open Anyway</strong>, or right-click the app → Open.
                </li>
              </ol>
            </article>
            <article className="download-install-card">
              <h3>
                <FaWindows aria-hidden /> Windows
              </h3>
              <ol>
                <li>Run the <strong>.exe</strong> installer and follow the prompts.</li>
                <li>
                  If SmartScreen warns about an unknown publisher, click <strong>More info</strong> →{' '}
                  <strong>Run anyway</strong> (beta builds are unsigned).
                </li>
                <li>Launch Zenith from the Start menu — it loads the same site as Edge or Chrome.</li>
              </ol>
            </article>
            <article className="download-install-card">
              <h3>
                <FaLinux aria-hidden /> Linux
              </h3>
              <ol>
                <li>
                  <strong>AppImage:</strong> chmod +x the file, then double-click or run from terminal.
                </li>
                <li>
                  <strong>Debian/Ubuntu:</strong> install the <strong>.deb</strong> with your package manager.
                </li>
              </ol>
            </article>
          </div>
        </section>

        <section className="download-browser landing-section">
          <div className="download-browser-card">
            <FaGlobe className="download-browser-card__icon" aria-hidden />
            <div>
              <h2>Prefer the browser?</h2>
              <p>
                Zenith works fully in Chrome, Firefox, Safari, and Edge. You can also add it to your home
                screen as a progressive web app.
              </p>
              <div className="download-browser-card__actions">
                <Link to="/" className="download-btn download-btn--secondary">
                  Open in browser
                </Link>
                <Link to="/register" className="download-btn download-btn--ghost">
                  Create free account
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="download-requirements landing-section">
          <h2 className="download-section-title">System requirements</h2>
          <ul className="download-req-list">
            <li>4 GB RAM minimum (8 GB recommended)</li>
            <li>Stable internet connection (app loads rajverse.me)</li>
            <li>macOS 11+, Windows 10+ 64-bit, or modern Linux 64-bit</li>
          </ul>
        </section>

        <section className="download-faq landing-section">
          <h2 className="download-section-title">FAQ</h2>
          <div className="download-faq-list">
            {DESKTOP_DOWNLOAD_FAQ.map((item) => (
              <div key={item.id} className="download-faq-item">
                <button
                  type="button"
                  className="download-faq-question"
                  aria-expanded={openFaq === item.id}
                  onClick={() => setOpenFaq(openFaq === item.id ? null : item.id)}
                >
                  {item.question}
                  <FaChevronDown className={`download-faq-chevron${openFaq === item.id ? ' open' : ''}`} />
                </button>
                {openFaq === item.id && <p className="download-faq-answer">{item.answer}</p>}
              </div>
            ))}
          </div>
        </section>
      </div>
    </MarketingPageLayout>
  );
}
