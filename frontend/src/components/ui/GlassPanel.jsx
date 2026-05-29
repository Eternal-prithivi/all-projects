import React from 'react';

/**
 * Glassmorphic panel wrapper per DESIGN_SYSTEM.md §3.
 */
export default function GlassPanel({ children, className = '', as: Tag = 'div', ...rest }) {
  return (
    <Tag className={`zenith-glass-panel ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}
