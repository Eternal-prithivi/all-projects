import React from 'react';

/**
 * Shared page header — kicker + gradient title + subtitle (Zenith design system).
 */
export default function PageHeader({
  kicker,
  title,
  subtitle,
  children,
  className = '',
  premium = true,
}) {
  return (
    <header
      className={[
        'zenith-page-header',
        premium ? 'zenith-page-header--premium' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {kicker ? (
        <span className="zenith-page-kicker zenith-page-kicker--shine">{kicker}</span>
      ) : null}
      {title ? <h1 className="zenith-page-title">{title}</h1> : null}
      {subtitle ? <p className="zenith-page-subtitle">{subtitle}</p> : null}
      {children}
    </header>
  );
}
