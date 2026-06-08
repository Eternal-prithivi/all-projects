import { useEffect } from 'react';

/** After melt animation, drop filter so scroll stays smooth. */
function wireRevealSettle(el) {
  if (el.classList.contains('reveal-settled')) return;

  el.addEventListener(
    'animationend',
    (e) => {
      if (e.target !== el) return;
      const name = String(e.animationName || '');
      if (!name.includes('landing-reveal-melt')) return;
      el.classList.add('reveal-settled');
    },
    { once: true }
  );
}

function revealElement(el, observer) {
  el.classList.add('is-visible');
  observer.unobserve(el);

  if (el.classList.contains('reveal-group')) {
    el.querySelectorAll('.reveal-item').forEach(wireRevealSettle);
    el.querySelectorAll(
      '.landing-cta__title, .landing-cta__subtitle, .landing-cta__actions, .landing-cta__trust'
    ).forEach(wireRevealSettle);
  } else {
    wireRevealSettle(el);
  }
}

function attachRevealObserver() {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        revealElement(entry.target, revealObserver);
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -5% 0px' }
  );

  const observe = (selector) => {
    document.querySelectorAll(selector).forEach((el) => revealObserver.observe(el));
  };

  observe('.reveal-group');
  document.querySelectorAll('.reveal-item').forEach((el) => {
    if (!el.closest('.reveal-group')) revealObserver.observe(el);
  });
  observe('.landing-reveal');

  if (reducedMotion) {
    document.querySelectorAll('.reveal-group, .reveal-item, .landing-reveal').forEach((el) => {
      el.classList.add('is-visible', 'reveal-settled');
    });
    return { disconnect: () => revealObserver.disconnect() };
  }

  return { disconnect: () => revealObserver.disconnect() };
}

/**
 * Scroll reveals via IntersectionObserver (melt-in blur runs once per block).
 * Re-runs when routeKey changes so lazy-loaded marketing subpages are observed.
 */
export function useLandingReveal(routeKey = '') {
  useEffect(() => {
    let observer = null;
    let cancelled = false;
    let scrollCleanup = null;

    const setup = () => {
      if (cancelled) return;
      observer = attachRevealObserver();

      if (!CSS.supports('animation-timeline', 'scroll()')) {
        const bar = document.querySelector('.landing-scroll-progress');
        let ticking = false;
        let lastRatio = -1;

        const updateBar = () => {
          ticking = false;
          if (!bar) return;
          const docHeight = document.documentElement.scrollHeight - window.innerHeight;
          const ratio = docHeight > 0 ? Math.min(1, window.scrollY / docHeight) : 0;
          if (Math.abs(ratio - lastRatio) < 0.01) return;
          lastRatio = ratio;
          bar.style.transform = `scaleX(${ratio})`;
        };

        const onScroll = () => {
          if (ticking) return;
          ticking = true;
          requestAnimationFrame(updateBar);
        };

        updateBar();
        window.addEventListener('scroll', onScroll, { passive: true });
        scrollCleanup = () => window.removeEventListener('scroll', onScroll);
      }
    };

    // Wait for lazy route chunks to paint before observing reveal targets.
    const rafId = requestAnimationFrame(() => {
      requestAnimationFrame(setup);
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      observer?.disconnect();
      scrollCleanup?.();
    };
  }, [routeKey]);
}
