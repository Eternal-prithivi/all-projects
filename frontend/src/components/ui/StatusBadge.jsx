import React from 'react';

const TONE_CLASS = {
  success: 'enterprise-status--success',
  warning: 'enterprise-status--warning',
  danger: 'enterprise-status--danger',
  neutral: 'enterprise-status--neutral',
  info: 'enterprise-status--info',
};

export default function StatusBadge({ tone = 'neutral', children, className = '' }) {
  return (
    <span
      className={[
        'enterprise-status',
        TONE_CLASS[tone] || TONE_CLASS.neutral,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </span>
  );
}
