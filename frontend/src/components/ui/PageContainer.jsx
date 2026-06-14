import React from 'react';

export default function PageContainer({
  children,
  variant = 'ops',
  wide = false,
  className = '',
}) {
  const isConfig = variant === 'config';

  return (
    <div
      className={[
        'enterprise-page',
        'zenith-page-enter',
        isConfig ? 'enterprise-page--config' : '',
        wide && !isConfig ? 'enterprise-page--wide' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  );
}
