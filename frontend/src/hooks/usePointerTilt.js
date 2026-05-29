import { useCallback, useEffect, useRef } from 'react';

const LERP = 0.14;
const MAX_ROTATE_Y = 12;
const MAX_ROTATE_X = 8;
const SETTLE_EPS = 0.08;

/**
 * 3D tilt toward pointer — RAF runs only while the pointer is over the card or values are settling.
 */
export function usePointerTilt({
  maxRotateY = MAX_ROTATE_Y,
  maxRotateX = MAX_ROTATE_X,
  enabled = true,
} = {}) {
  const ref = useRef(null);
  const target = useRef({ rx: 0, ry: 0, px: 50, py: 50 });
  const current = useRef({ rx: 0, ry: 0, px: 50, py: 50 });
  const rafId = useRef(0);
  const active = useRef(false);

  const setTargetFromEvent = useCallback(
    (clientX, clientY) => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) return;
      const x = (clientX - rect.left) / rect.width;
      const y = (clientY - rect.top) / rect.height;
      const nx = Math.max(-1, Math.min(1, (x - 0.5) * 2));
      const ny = Math.max(-1, Math.min(1, (y - 0.5) * 2));

      target.current = {
        ry: nx * maxRotateY,
        rx: -ny * maxRotateX,
        px: x * 100,
        py: y * 100,
      };
    },
    [maxRotateX, maxRotateY]
  );

  const needsFrame = useCallback(() => {
    const t = target.current;
    const c = current.current;
    return (
      active.current ||
      Math.abs(t.rx - c.rx) > SETTLE_EPS ||
      Math.abs(t.ry - c.ry) > SETTLE_EPS ||
      Math.abs(t.px - c.px) > SETTLE_EPS ||
      Math.abs(t.py - c.py) > SETTLE_EPS
    );
  }, []);

  const scheduleFrame = useCallback(() => {
    if (rafId.current) return;
    rafId.current = requestAnimationFrame(function tick() {
      const el = ref.current;
      if (!el || !needsFrame()) {
        rafId.current = 0;
        return;
      }

      const t = target.current;
      const c = current.current;
      c.rx += (t.rx - c.rx) * LERP;
      c.ry += (t.ry - c.ry) * LERP;
      c.px += (t.px - c.px) * LERP;
      c.py += (t.py - c.py) * LERP;

      el.style.setProperty('--tilt-x', `${c.rx.toFixed(2)}deg`);
      el.style.setProperty('--tilt-y', `${c.ry.toFixed(2)}deg`);
      el.style.setProperty('--pointer-x', `${c.px.toFixed(1)}%`);
      el.style.setProperty('--pointer-y', `${c.py.toFixed(1)}%`);

      rafId.current = requestAnimationFrame(tick);
    });
  }, [needsFrame]);

  const onPointerMove = useCallback(
    (e) => {
      setTargetFromEvent(e.clientX, e.clientY);
      scheduleFrame();
    },
    [setTargetFromEvent, scheduleFrame]
  );

  const onPointerEnter = useCallback(
    (e) => {
      active.current = true;
      setTargetFromEvent(e.clientX, e.clientY);
      scheduleFrame();
    },
    [setTargetFromEvent, scheduleFrame]
  );

  const onPointerLeave = useCallback(() => {
    active.current = false;
    target.current = { rx: 0, ry: 0, px: 50, py: 50 };
    scheduleFrame();
  }, [scheduleFrame]);

  useEffect(() => {
    if (!enabled) return undefined;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    return () => {
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, [enabled]);

  return {
    ref,
    pointerProps: enabled
      ? {
          onPointerMove,
          onPointerEnter,
          onPointerLeave,
        }
      : {},
  };
}
