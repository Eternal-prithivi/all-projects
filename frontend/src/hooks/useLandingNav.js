import { useEffect, useState } from 'react';

/** Sticky nav + pause heavy backdrop/marquee animations while scrolling. */
export function useLandingNav(threshold = 20) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    let scrollEndTimer = 0;

    const onScroll = () => {
      const next = window.scrollY > threshold;
      setScrolled((prev) => (prev === next ? prev : next));
      root.classList.add('is-scrolling');
      window.clearTimeout(scrollEndTimer);
      scrollEndTimer = window.setTimeout(() => {
        root.classList.remove('is-scrolling');
      }, 120);
    };

    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.clearTimeout(scrollEndTimer);
      root.classList.remove('is-scrolling');
    };
  }, [threshold]);

  return scrolled;
}
