import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GO_NAV_TIMEOUT_MS,
  isTypingTarget,
} from '../utils/keyboardShortcuts';

/**
 * Global keyboard shortcuts for dashboard/admin shells.
 * Skips handlers while the user is typing in form fields.
 */
export function useAppKeyboardShortcuts({
  goRoutes = null,
  onOpenSearch,
  onOpenShortcuts,
  overlaysOpen = false,
}) {
  const navigate = useNavigate();
  const goPendingRef = useRef(false);
  const goTimerRef = useRef(null);

  useEffect(() => {
    const clearGoPending = () => {
      goPendingRef.current = false;
      if (goTimerRef.current) {
        clearTimeout(goTimerRef.current);
        goTimerRef.current = null;
      }
    };

    const handleKeyPress = (e) => {
      if (isTypingTarget(e.target)) return;

      const key = e.key.toLowerCase();

      if ((e.metaKey || e.ctrlKey) && key === 'k') {
        e.preventDefault();
        onOpenSearch();
        clearGoPending();
        return;
      }

      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        onOpenShortcuts();
        clearGoPending();
        return;
      }

      if (overlaysOpen) {
        clearGoPending();
        return;
      }

      if (!goRoutes) return;

      if (!goPendingRef.current && key === 'g' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        goPendingRef.current = true;
        goTimerRef.current = setTimeout(clearGoPending, GO_NAV_TIMEOUT_MS);
        return;
      }

      if (goPendingRef.current && goRoutes[key]) {
        e.preventDefault();
        navigate(goRoutes[key]);
        clearGoPending();
      }
    };

    const handleShowShortcuts = () => onOpenShortcuts();
    const handleOpenSearch = () => onOpenSearch();

    document.addEventListener('keydown', handleKeyPress);
    window.addEventListener('show-shortcuts', handleShowShortcuts);
    window.addEventListener('open-global-search', handleOpenSearch);

    return () => {
      document.removeEventListener('keydown', handleKeyPress);
      window.removeEventListener('show-shortcuts', handleShowShortcuts);
      window.removeEventListener('open-global-search', handleOpenSearch);
      clearGoPending();
    };
  }, [goRoutes, navigate, onOpenSearch, onOpenShortcuts, overlaysOpen]);
}
