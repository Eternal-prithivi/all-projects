import React from 'react';

/**
 * Glassmorphic panel wrapper per DESIGN_SYSTEM.md §3.
 */
export default function GlassPanel({ children, className = '', as, ...rest }) {
  const Wrapper = as || 'div';
  return (
    <Wrapper className={`zenith-glass-panel ${className}`.trim()} {...rest}>
      {children}
    </Wrapper>
  );
}
