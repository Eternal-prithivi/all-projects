import React from 'react';
import { Link } from 'react-router-dom';
import { LOGO_ICON_PATH } from '../../config/site.js';

/**
 * Zenith brand mark — icon, or icon + wordmark.
 * @param {'icon'|'full'} variant
 * @param {'stacked'|'inline'} textLayout — inline matches dashboard header (Zenith + Cloud pill)
 */
export default function ZenithLogo({
  variant = 'icon',
  size = 32,
  className = '',
  linkTo = null,
  badge = 'Cloud',
  textLayout = 'inline',
}) {
  const icon = (
    <img
      src={LOGO_ICON_PATH}
      alt=""
      width={size}
      height={size}
      className={`zenith-logo-icon ${className}`.trim()}
      aria-hidden
      decoding="async"
    />
  );

  let content = icon;

  if (variant === 'full') {
    content = (
      <span className={`zenith-logo-full zenith-logo-full--${textLayout}`}>
        {icon}
        <span className="zenith-logo-text">
          <span className="zenith-logo-name">Zenith</span>
          {badge ? <span className="zenith-logo-badge">{badge}</span> : null}
        </span>
      </span>
    );
  }

  if (linkTo) {
    return (
      <Link to={linkTo} className="zenith-logo-link" aria-label="Zenith Cloud home">
        {content}
      </Link>
    );
  }

  return <span className="zenith-logo">{content}</span>;
}
