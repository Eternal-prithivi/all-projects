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
  FaCheck,
  FaExternalLinkAlt,
  FaMobileAlt,
} from 'react-icons/fa';
import { usePwaInstall } from '../hooks/usePwaInstall.js';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import HeroPreview from '../components/landing/HeroPreview.jsx';
import HeroTiltVisual from '../components/landing/HeroTiltVisual.jsx';
import { detectPlatform, PLATFORM_LABELS } from '../utils/detectPlatform.js';
import { DESKTOP_DOWNLOAD_FAQ } from '../data/productFacts.js';
import '../styles/download-page.css';

const PLATFORM_ICONS = {
  mac: FaApple,
  win: FaWindows,
  linux: FaLinux,
};

const VALUE_PROPS = [
  {
    title: 'Focused workspace',
    text: 'Run Zenith in its own window — no competing browser tabs or bookmark clutter.',
  },
  {
    title: 'Same secure session',
    text: 'Sign in once with the same account, 2FA, and org policies you use on the web.',
  },
  {
    title: 'Always up to date',
    text: 'The app loads the live platform, so you get new features without reinstalling.',
  },
  {
    title: 'Enterprise-ready',
    text: 'BYOC, billing, and team governance work identically to the browser experience.',
  },
];

const INSTALL_STEPS = {
  mac: [
    'Download the .dmg installer and open it.',
    'Drag Zenith into your Applications folder.',
    'Launch from Applications. If macOS blocks the app, open System Settings → Privacy & Security → Open Anyway.',
  ],
  win: [
    'Run the .exe installer and complete the setup wizard.',
    'If SmartScreen appears, choose More info → Run anyway (beta builds are unsigned).',
    'Open Zenith from the Start menu — it connects to the same cloud dashboard as your browser.',
  ],
  linux: [
    'AppImage: chmod +x the file, then run it from your file manager or terminal.',
    'Debian/Ubuntu: install the .deb package with your preferred package manager.',
    'Sign in with your Zenith account — all clouds and settings sync from the web app.',
  ],
};

function buildReleaseUrl(releaseTag, artifactName, githubRepo) {
  const encoded = encodeURIComponent(artifactName);
  return `https://github.com/${githubRepo}/releases/download/${releaseTag}/${encoded}`;
}

function buildReleasesPageUrl(githubRepo) {
  return `https://github.com/${githubRepo}/releases`;
}

function DownloadCta({ href, className, releaseStatus, children }) {
  if (releaseStatus === 'loading') {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true">
        Checking download…
      </span>
    );
  }
  if (releaseStatus !== 'ready') {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true">
        {children}
      </span>
    );
  }
  return (
    <a href={href} className={className} download>
      {children}
    </a>
  );
}

const PWA_STEPS_IOS = [
  { step: 1, title: 'Open in Safari', desc: 'Open rajverse.me in Safari on your iPhone or iPad. (Chrome on iOS does not support this yet.)' },
  { step: 2, title: 'Tap the Share icon', desc: 'Tap the Share button (rectangle with arrow) in the Safari toolbar.' },
  { step: 3, title: 'Add to Home Screen', desc: 'Scroll down in the share sheet and tap "Add to Home Screen".' },
  { step: 4, title: 'Name and Add', desc: 'Edit the name if you like, then tap "Add". Zenith appears on your home screen like a native app.' },
];

const PWA_STEPS_ANDROID = [
  { step: 1, title: 'Open in Chrome', desc: 'Visit rajverse.me in Chrome on your Android phone.' },
  { step: 2, title: 'Tap the menu (⋮)', desc: 'Tap the three-dot menu in the top-right corner of Chrome.' },
  { step: 3, title: 'Add to Home screen', desc: 'Tap "Add to Home screen" (or "Install app" if Chrome shows an install banner).' },
  { step: 4, title: 'Confirm', desc: 'Tap "Add" in the prompt. Zenith opens in a dedicated window without browser chrome.' },
];

export default function DownloadPage() {
  const [manifest, setManifest] = useState(null);
  const [releaseStatus, setReleaseStatus] = useState('loading');
  const [openFaq, setOpenFaq] = useState(null);
  const [pwaTab, setPwaTab] = useState('android');
  const { canInstall, triggerInstall } = usePwaInstall();
  const detected = useMemo(() => detectPlatform(), []);
  const [activePlatform, setActivePlatform] = useState(detected === 'unknown' ? 'mac' : detected);
  const [installTab, setInstallTab] = useState(detected === 'unknown' ? 'mac' : detected);

  useEffect(() => {
    fetch('/releases.json')
      .then((r) => r.json())
      .then(setManifest)
      .catch(() => setManifest(null));
  }, []);

  useEffect(() => {
    if (!manifest?.githubRepo || !manifest?.releaseTag) {
      setReleaseStatus('missing');
      return undefined;
    }

    const controller = new AbortController();
    fetch(
      `https://api.github.com/repos/${manifest.githubRepo}/releases/tags/${manifest.releaseTag}`,
      {
        signal: controller.signal,
        headers: { Accept: 'application/vnd.github+json' },
      }
    )
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        const hasAssets = Array.isArray(data?.assets) && data.assets.length > 0;
        setReleaseStatus(hasAssets ? 'ready' : 'missing');
      })
      .catch(() => setReleaseStatus('missing'));

    return () => controller.abort();
  }, [manifest]);

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

  const active = platforms.find((p) => p.key === activePlatform) || platforms[0];
  const detectedPlatform = platforms.find((p) => p.key === detected);

  return (
    <MarketingPageLayout>
      <div className="download-page">
        {/* Hero */}
        <section className="download-hero reveal-group">
          <div className="download-hero__grid">
            <div className="download-hero__copy reveal-item">
              <p className="download-kicker">Zenith for desktop</p>
              <h1>
                Your cloud command center,
                <span className="download-hero__gradient"> on your desktop.</span>
              </h1>
              <p className="download-hero__lead">
                Install Zenith for macOS, Windows, or Linux. One native window for multi-cloud
                cost, storage, VMs, and security — powered by the same platform you trust in the
                browser.
              </p>

              {manifest?.beta && (
                <div className="download-beta-callout" role="note">
                  <FaShieldAlt aria-hidden />
                  <span>
                    Public beta · Installers are unsigned today. Step-by-step trust guidance below.
                  </span>
                </div>
              )}

              {releaseStatus === 'missing' && manifest && (
                <div className="download-unavailable-callout" role="alert">
                  <FaShieldAlt aria-hidden />
                  <span>
                    Installers for version {manifest.version} are not on GitHub yet. Use Zenith in
                    your browser today, or watch{' '}
                    <a
                      href={buildReleasesPageUrl(manifest.githubRepo)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      GitHub Releases
                      <FaExternalLinkAlt aria-hidden />
                    </a>{' '}
                    for the .dmg, .exe, and Linux builds.
                  </span>
                </div>
              )}

              <div className="download-platform-tabs" role="tablist" aria-label="Choose platform">
                {platforms.map((p) => {
                  const Icon = PLATFORM_ICONS[p.key];
                  const isActive = p.key === activePlatform;
                  return (
                    <button
                      key={p.key}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      className={`download-platform-tab${isActive ? ' is-active' : ''}${
                        p.key === detected ? ' is-detected' : ''
                      }`}
                      onClick={() => setActivePlatform(p.key)}
                    >
                      <Icon aria-hidden />
                      <span>{p.label}</span>
                      {p.key === detected && (
                        <span className="download-platform-tab__pill">Your device</span>
                      )}
                    </button>
                  );
                })}
              </div>

              {active && (
                <div className="download-hero__cta-block">
                  <DownloadCta
                    href={active.url}
                    className="download-cta-primary"
                    releaseStatus={releaseStatus}
                  >
                    <FaDownload aria-hidden />
                    Download for {active.label}
                  </DownloadCta>
                  <div className="download-hero__meta">
                    <span className="download-hero__version">
                      Version {manifest?.version}
                      {manifest?.publishedAt ? ` · ${manifest.publishedAt}` : ''}
                    </span>
                    <span className="download-hero__meta-dot" aria-hidden>
                      ·
                    </span>
                    <span>{active.minOs}</span>
                  </div>
                  {active.altUrl && releaseStatus === 'ready' && (
                    <a href={active.altUrl} className="download-hero__alt" download>
                      Also available: {active.altArtifactName}
                    </a>
                  )}
                </div>
              )}

              <div className="download-hero__chips">
                <span>Free download</span>
                <span>No credit card</span>
                <span>Internet required</span>
              </div>
            </div>

            <div className="download-hero__visual reveal-item reveal-item--delay-2" aria-hidden="true">
              <HeroTiltVisual>
                <HeroPreview />
              </HeroTiltVisual>
            </div>
          </div>
        </section>

        {/* Value props */}
        <section className="download-value reveal-group">
          <div className="download-section-head reveal-item">
            <h2>Why teams install Zenith</h2>
            <p>Everything you get in the browser — in a dedicated app built for daily cloud operations.</p>
          </div>
          <div className="download-value__grid reveal-stagger">
            {VALUE_PROPS.map((item) => (
              <article key={item.title} className="download-value__card reveal-item">
                <FaCheck className="download-value__check" aria-hidden />
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        {/* All platforms */}
        <section className="download-all-platforms reveal-group">
          <div className="download-section-head reveal-item">
            <h2>Download for your operating system</h2>
            <p>Pick the installer that matches your machine. All builds connect to rajverse.me.</p>
          </div>
          <div className="download-all-platforms__grid reveal-stagger">
            {platforms.map((p) => {
              const Icon = PLATFORM_ICONS[p.key];
              const isRecommended = p.key === detected;
              return (
                <article
                  key={p.key}
                  className={`download-os-card reveal-item${isRecommended ? ' download-os-card--recommended' : ''}`}
                >
                  {isRecommended && (
                    <span className="download-os-card__ribbon">Recommended for you</span>
                  )}
                  <div className="download-os-card__icon-wrap">
                    <Icon aria-hidden />
                  </div>
                  <h3>{p.label}</h3>
                  <p className="download-os-card__req">{p.minOs}</p>
                  <ul className="download-os-card__formats">
                    <li>
                      <FaCheck aria-hidden /> {p.extension.toUpperCase()} installer
                    </li>
                    {p.altArtifactName && (
                      <li>
                        <FaCheck aria-hidden /> DEB package (Linux)
                      </li>
                    )}
                  </ul>
                  <DownloadCta
                    href={p.url}
                    className="download-os-card__btn"
                    releaseStatus={releaseStatus}
                  >
                    <FaDownload aria-hidden />
                    Download
                  </DownloadCta>
                  {p.altUrl && releaseStatus === 'ready' && (
                    <a href={p.altUrl} className="download-os-card__alt" download>
                      {p.altArtifactName}
                    </a>
                  )}
                  {p.sha256 && (
                    <code className="download-os-card__sha" title="SHA-256">
                      sha256:{p.sha256.slice(0, 12)}…
                    </code>
                  )}
                </article>
              );
            })}
          </div>
          {manifest?.releaseTag && (
            <p className="download-release-note reveal-item">
              Release{' '}
              <a
                href={`https://github.com/${manifest.githubRepo}/releases/tag/${manifest.releaseTag}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {manifest.releaseTag}
                <FaExternalLinkAlt aria-hidden />
              </a>
              {' · '}
              Verify downloads with SHA256SUMS.txt on GitHub Releases.
            </p>
          )}
        </section>

        {/* Install guide — tabbed */}
        <section className="download-install reveal-group">
          <div className="download-section-head reveal-item">
            <h2>Installation guide</h2>
            <p>Follow the steps for your OS. Beta builds may show a one-time security prompt.</p>
          </div>
          <div className="download-install__panel reveal-item">
            <div className="download-install__tabs" role="tablist" aria-label="Installation steps">
              {['mac', 'win', 'linux'].map((key) => {
                const Icon = PLATFORM_ICONS[key];
                const label = PLATFORM_LABELS[key];
                return (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={installTab === key}
                    className={`download-install__tab${installTab === key ? ' is-active' : ''}`}
                    onClick={() => setInstallTab(key)}
                  >
                    <Icon aria-hidden />
                    {label}
                  </button>
                );
              })}
            </div>
            <ol className="download-install__steps" role="tabpanel">
              {INSTALL_STEPS[installTab].map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </section>

        {/* Requirements */}
        <section className="download-specs reveal-group">
          <div className="download-section-head reveal-item">
            <h2>System requirements</h2>
          </div>
          <div className="download-specs__grid reveal-stagger">
            <article className="download-spec-card reveal-item">
              <h3>Hardware</h3>
              <ul>
                <li>4 GB RAM minimum</li>
                <li>8 GB RAM recommended</li>
                <li>200 MB disk for the app shell</li>
              </ul>
            </article>
            <article className="download-spec-card reveal-item">
              <h3>Network</h3>
              <ul>
                <li>Stable broadband connection</li>
                <li>HTTPS access to rajverse.me</li>
                <li>Same APIs as the web app</li>
              </ul>
            </article>
            <article className="download-spec-card reveal-item">
              <h3>Supported OS</h3>
              <ul>
                <li>macOS 11 Big Sur or later</li>
                <li>Windows 10/11 (64-bit)</li>
                <li>Ubuntu 20.04+ or equivalent Linux</li>
              </ul>
            </article>
          </div>
        </section>

        {/* PWA / Add to Home Screen */}
        <section className="download-pwa reveal-group">
          <div className="download-section-head reveal-item">
            <span className="download-kicker">No App Store required</span>
            <h2>Add to Home Screen</h2>
            <p>
              Get a native-feeling Zenith icon on your phone or tablet — no download, no App Store,
              no browser bar. Works on any modern iPhone or Android device.
            </p>
          </div>

          {/* Feature chips */}
          <div className="download-pwa__chips reveal-item">
            {[
              'Launches like a native app',
              'Full-screen, no browser bar',
              'Same secure session',
              'Works on iOS & Android',
              'Instant — no download',
            ].map((chip) => (
              <span key={chip} className="download-pwa__chip">
                <FaCheck aria-hidden /> {chip}
              </span>
            ))}
          </div>

          {/* Android install CTA — only shown when browser supports it */}
          {canInstall && (
            <div className="download-pwa__android-cta reveal-item">
              <FaMobileAlt aria-hidden />
              <span>Your browser supports one-tap install:</span>
              <button
                id="pwa-download-page-install-btn"
                type="button"
                className="download-cta-primary download-pwa__install-btn"
                onClick={triggerInstall}
              >
                <FaDownload aria-hidden /> Install Zenith Now
              </button>
            </div>
          )}

          {/* Step-by-step guide tabs */}
          <div className="download-install__panel download-pwa__panel reveal-item">
            <div className="download-install__tabs" role="tablist" aria-label="Platform install guide">
              <button
                type="button"
                role="tab"
                aria-selected={pwaTab === 'android'}
                className={`download-install__tab${pwaTab === 'android' ? ' is-active' : ''}`}
                onClick={() => setPwaTab('android')}
              >
                <FaMobileAlt aria-hidden /> Android (Chrome)
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={pwaTab === 'ios'}
                className={`download-install__tab${pwaTab === 'ios' ? ' is-active' : ''}`}
                onClick={() => setPwaTab('ios')}
              >
                <FaApple aria-hidden /> iPhone / iPad
              </button>
            </div>

            <div className="download-pwa__steps" role="tabpanel">
              {(pwaTab === 'ios' ? PWA_STEPS_IOS : PWA_STEPS_ANDROID).map((item) => (
                <div key={item.step} className="download-pwa__step">
                  <span className="download-pwa__step-num">{item.step}</span>
                  <div>
                    <p className="download-pwa__step-title">{item.title}</p>
                    <p className="download-pwa__step-desc">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="download-release-note reveal-item">
            <FaGlobe aria-hidden style={{ marginRight: '0.4em' }} />
            Or just open{' '}
            <Link to="/">rajverse.me</Link>{' '}
            in any browser — Zenith works with full feature parity in Chrome, Edge, Firefox, and Safari.
          </p>
        </section>

        {/* FAQ */}
        <section className="download-faq reveal-group">
          <div className="download-section-head reveal-item">
            <h2>Frequently asked questions</h2>
          </div>
          <div className="download-faq__list reveal-item">
            {DESKTOP_DOWNLOAD_FAQ.map((item) => (
              <div
                key={item.id}
                className={`download-faq__item${openFaq === item.id ? ' is-open' : ''}`}
              >
                <button
                  type="button"
                  className="download-faq__question"
                  aria-expanded={openFaq === item.id}
                  onClick={() => setOpenFaq(openFaq === item.id ? null : item.id)}
                >
                  {item.question}
                  <FaChevronDown className="download-faq__chevron" aria-hidden />
                </button>
                <div className="download-faq__answer-wrap">
                  <p className="download-faq__answer">{item.answer}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="download-bottom-cta reveal-group">
          <div className="download-bottom-cta__inner reveal-item">
            <h2>Ready to optimize your cloud?</h2>
            <p>Download Zenith or sign in from the browser — your AWS, GCP, and Azure estate in one place.</p>
            <div className="download-bottom-cta__actions">
              {detectedPlatform ? (
                <DownloadCta
                  href={detectedPlatform.url}
                  className="download-cta-primary"
                  releaseStatus={releaseStatus}
                >
                  <FaDownload aria-hidden />
                  Download for {PLATFORM_LABELS[detected]}
                </DownloadCta>
              ) : (
                <Link to="/register" className="download-cta-primary">
                  Create free account
                </Link>
              )}
              <Link to="/contact" className="download-cta-secondary">
                Talk to sales
              </Link>
            </div>
          </div>
        </section>
      </div>
    </MarketingPageLayout>
  );
}
