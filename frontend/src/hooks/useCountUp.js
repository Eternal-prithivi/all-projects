import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook that animates a number from 0 to a target value.
 * Uses requestAnimationFrame for smooth 60fps animation with ease-out deceleration.
 * 
 * @param {number} target - The target number to count up to
 * @param {number} duration - Animation duration in milliseconds (default: 1200ms)
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} The current animated value
 */
export function useCountUp(target, duration = 1200, decimals = 0) {
  const [current, setCurrent] = useState(0);
  const startTimeRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (target === 0 || target === null || target === undefined) {
      setCurrent(0);
      return;
    }

    startTimeRef.current = null;

    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);

      // Ease-out cubic for natural deceleration
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = eased * target;

      setCurrent(value);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        setCurrent(target);
      }
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [target, duration]);

  return decimals > 0 ? current.toFixed(decimals) : Math.round(current);
}

export default useCountUp;
