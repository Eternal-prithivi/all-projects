import React, { useRef, useCallback } from 'react';

/**
 * Card with cursor-following soft spotlight on hover (no slash sweep).
 */
export default function SpotlightCard({ children, className = '', as, ...rest }) {
  const Wrapper = as || 'div';
  const ref = useRef(null);

  const onMove = useCallback((e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty('--spot-x', `${e.clientX - rect.left}px`);
    el.style.setProperty('--spot-y', `${e.clientY - rect.top}px`);
  }, []);

  const onLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.removeProperty('--spot-x');
    el.style.removeProperty('--spot-y');
  }, []);

  return (
    <Wrapper
      ref={ref}
      className={`spotlight-card ${className}`.trim()}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      {...rest}
    >
      <span className="spotlight-card__glow" aria-hidden="true" />
      {children}
    </Wrapper>
  );
}
