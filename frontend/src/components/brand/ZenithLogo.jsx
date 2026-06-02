import React from 'react';
import { Link } from 'react-router-dom';
import { LOGO_ICON_PATH, LOGO_WORDMARK_PATH } from '../../config/site.js';

/**
 * Zenith brand mark — icon, wordmark, or both.
 * @param {'icon'|'wordmark'|'full'} variant
 */
export default function ZenithLogo({
  variant = 'icon',
  size = 32,
  className = '',
  linkTo = null,
  showText = false,
  subtitle = null,
}) {
  const icon = (
    <img
      src={LOGO_ICON_PATH}
      alt=""
      width={size}
      height={size}
      className={`zenith-logo-icon ${className}`.trim()}
      aria-hidden
    />
  );

  const wordmark = (
    <img
      src={LOGO_WORDMARK_PATH}
      alt="Zenith Cloud"
      height={Math.max(size, 28)}
      className={`zenith-logo-wordmark ${className}`.trim()}
      style={{ width: 'auto', height: Math.max(size, 28) }}
    />
  );

  let content;
  if (variant === 'wordmark') {
    content = wordmark;
  } else if (variant === 'full' || showText) {
    content = (
      <span className="zenith-logo-full">
        {icon}
        <span className="zenith-logo-text">
          <span className="zenith-logo-name">Zenith</span>
          {subtitle ? <span className="zenith-logo-sub">{subtitle}</span> : null}
        </span>
      </span>
    );
  } else {
    content = icon;
  }

  if (linkTo) {
    return (
      <Link to={linkTo} className="zenith-logo-link" aria-label="Zenith home">
        {content}
      </Link>
    );
  }

  return <span className="zenith-logo">{content}</span>;
}
