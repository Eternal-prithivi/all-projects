import React from 'react';

/** CSS-only dashboard preview for the marketing hero. */
export default function HeroPreview() {
  return (
    <div className="hero-preview" aria-hidden="true">
      <div className="hero-preview__edge-glow" />
      <div className="hero-preview__scan" />
      <div className="hero-preview__chrome">
        <span className="hero-preview__dot hero-preview__dot--r" />
        <span className="hero-preview__dot hero-preview__dot--y" />
        <span className="hero-preview__dot hero-preview__dot--g" />
        <span className="hero-preview__url">app.zenith.cloud / dashboard</span>
        <span className="hero-preview__live">
          <span className="hero-preview__live-dot" />
          Live
        </span>
      </div>
      <div className="hero-preview__body">
        <aside className="hero-preview__rail">
          <span className="hero-preview__rail-item hero-preview__rail-item--active" />
          <span className="hero-preview__rail-item" />
          <span className="hero-preview__rail-item" />
          <span className="hero-preview__rail-item" />
          <span className="hero-preview__rail-item" />
        </aside>
        <div className="hero-preview__main">
          <div className="hero-preview__metrics">
            <div className="hero-preview__metric">
              <span className="hero-preview__metric-label">Monthly savings</span>
              <strong>$45,230</strong>
              <em className="hero-preview__metric-delta">↓ 38%</em>
            </div>
            <div className="hero-preview__metric">
              <span className="hero-preview__metric-label">Active resources</span>
              <strong>128</strong>
              <em className="hero-preview__metric-delta hero-preview__metric-delta--up">↑ 12</em>
            </div>
            <div className="hero-preview__metric">
              <span className="hero-preview__metric-label">ML recommendations</span>
              <strong>24</strong>
              <em className="hero-preview__metric-delta">pending</em>
            </div>
          </div>
          <div className="hero-preview__chart">
            <div className="hero-preview__chart-header">
              <span>Cost trend</span>
              <span className="hero-preview__chart-pill">7d</span>
            </div>
            <div className="hero-preview__chart-bars">
              {[42, 68, 55, 82, 61, 94, 72, 88, 76, 91].map((h, i) => (
                <span
                  key={i}
                  className="hero-preview__bar"
                  style={{ '--h': `${h}%`, '--i': i }}
                />
              ))}
            </div>
          </div>
          <div className="hero-preview__rows">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
      <div className="hero-preview__float hero-preview__float--savings">
        <span>Cost optimized</span>
        <strong>AWS S3 → Glacier</strong>
      </div>
      <div className="hero-preview__float hero-preview__float--secure">
        <span>Secure vault</span>
        <strong>AES-256</strong>
      </div>
      <div className="hero-preview__float hero-preview__float--ml">
        <span>ML ensemble</span>
        <strong>94% confidence</strong>
      </div>
    </div>
  );
}
