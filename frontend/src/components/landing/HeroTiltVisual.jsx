import React from 'react';
import { usePointerTilt } from '../../hooks/usePointerTilt.js';

/**
 * Hero dashboard mock — tilts toward the cursor (3D pointer follow).
 */
export default function HeroTiltVisual({ children }) {
  const { ref, pointerProps } = usePointerTilt();

  return (
    <div
      ref={ref}
      className="landing-hero__visual-wrap landing-hero__tilt"
      {...pointerProps}
    >
      <span className="landing-hero__tilt-frame" aria-hidden="true" />
      <div className="landing-hero__tilt-target">
        {children}
      </div>
    </div>
  );
}
