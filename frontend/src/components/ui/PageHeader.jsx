import React from 'react';
import PageRefreshButton from './PageRefreshButton.jsx';

/**
 * Shared page header — kicker + gradient title + subtitle + optional actions & refresh.
 */
export default function PageHeader({
  kicker,
  title,
  subtitle,
  children,
  actions = null,
  onRefresh,
  refreshing = false,
  refreshDisabled = false,
  refreshLabel = 'Refresh',
  className = '',
  premium = true,
}) {
  const hasRefresh = typeof onRefresh === 'function';
  const hasActions = Boolean(actions) || hasRefresh;

  return (
    <header
      className={[
        'zenith-page-header',
        premium ? 'zenith-page-header--premium' : '',
        hasActions ? 'zenith-page-header--row' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="zenith-page-header-main">
        {kicker ? (
          <span className="zenith-page-kicker zenith-page-kicker--shine">{kicker}</span>
        ) : null}
        {title ? <h1 className="zenith-page-title">{title}</h1> : null}
        {subtitle ? <p className="zenith-page-subtitle">{subtitle}</p> : null}
        {children}
      </div>
      {hasActions ? (
        <div className="zenith-page-header-actions">
          {actions}
          {hasRefresh ? (
            <PageRefreshButton
              onClick={onRefresh}
              busy={refreshing}
              disabled={refreshDisabled}
              label={refreshLabel}
            />
          ) : null}
        </div>
      ) : null}
    </header>
  );
}
