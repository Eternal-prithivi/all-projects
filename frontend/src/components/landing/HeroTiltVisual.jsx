import React from 'react';
import { usePointerTilt } from '../../hooks/usePointerTilt.js';
import { useMediaQuery, MOBILE_MEDIA_QUERY } from '../../hooks/useMediaQuery.js';

/**
 * Hero dashboard mock — tilts toward the cursor (3D pointer follow).
 */
export default function HeroTiltVisual({ children }) {
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY);
  const { ref, pointerProps } = usePointerTilt({ enabled: !isMobile });

  return (
    <div
      ref={ref}
      className={`landing-hero__visual-wrap landing-hero__tilt${isMobile ? ' landing-hero__tilt--static' : ''}`}
      {...(isMobile ? {} : pointerProps)}
    >
      <span className="landing-hero__tilt-frame" aria-hidden="true" />
      <div className="landing-hero__tilt-target">
        {children}
      </div>
    </div>
  );
}
