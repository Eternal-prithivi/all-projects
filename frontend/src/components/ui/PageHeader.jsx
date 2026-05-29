import React from 'react';

/**
 * Shared page header — kicker + gradient title + subtitle (Zenith design system).
 */
export default function PageHeader({ kicker, title, subtitle, children, className = '' }) {
  return (
    <header className={`zenith-page-header ${className}`.trim()}>
      {kicker ? <span className="zenith-page-kicker">{kicker}</span> : null}
      {title ? <h1 className="zenith-page-title">{title}</h1> : null}
      {subtitle ? <p className="zenith-page-subtitle">{subtitle}</p> : null}
      {children}
    </header>
  );
}
